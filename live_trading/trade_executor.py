"""
Trade Executor - Execuo real de trades no MT5

Este mdulo integra a neural chain com o MT5 Bridge para executar trades reais:
1. Recebe sinal da neural chain
2. Valida sinal final
3. Envia para MT5 via TCP Socket
4. Aguarda confirmao de execuo
5. Registra posio aberta
6. Monitora posio at fechamento
"""

import sys
import os
import time
import threading
from typing import Optional, Dict, List
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

# Adicionar projeto ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from live_trading.mt5_bridge import MT5Bridge, TickData
from live_trading.neural_chain import LiveNeuralChain, LiveSignal
from live_trading.logger import get_logger
from live_trading.position_manager import AdvancedPositionManager


class OrderState(Enum):
    """Estado de uma ordem"""
    PENDING = "pending"
    SENT_TO_MT5 = "sent_to_mt5"
    EXECUTED = "executed"
    REJECTED = "rejected"
    FAILED = "failed"
    CLOSED = "closed"


class PositionState(Enum):
    """Estado de uma posio"""
    OPEN = "open"
    BREAKEVEN = "breakeven"
    TRAILING = "trailing"
    PARTIAL_EXIT = "partial_exit"
    CLOSED_TP = "closed_take_profit"
    CLOSED_SL = "closed_stop_loss"
    CLOSED_MANUAL = "closed_manual"


@dataclass
class Order:
    """Ordem de trading"""
    ticket: int
    timestamp: datetime
    signal: LiveSignal
    state: OrderState = OrderState.PENDING
    mt5_ticket: Optional[int] = None
    execution_price: Optional[float] = None
    execution_time: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class Position:
    """Posio aberta"""
    ticket: int
    mt5_ticket: int
    symbol: str
    direction: str  # BUY ou SELL
    volume: float
    entry_price: float
    stop_loss: float
    take_profit: float
    open_time: datetime
    state: PositionState = PositionState.OPEN
    current_price: Optional[float] = None
    current_pnl: float = 0.0
    max_profit: float = 0.0
    max_drawdown: float = 0.0
    breakeven_applied: bool = False
    trailing_applied: bool = False
    partial_exit_price: Optional[float] = None
    partial_exit_volume: Optional[float] = None
    close_time: Optional[datetime] = None
    close_price: Optional[float] = None
    close_reason: Optional[str] = None
    net_pnl: float = 0.0
    commission: float = 0.0
    swap: float = 0.0


class TradeExecutor:
    """
    Executor de trades reais no MT5
    """
    
    def __init__(
        self,
        bridge: MT5Bridge,
        neural_chain: LiveNeuralChain,
        symbol: str = "BTCUSD",
        magic_number: int = 20260413,
        auto_execute: bool = True
    ):
        self.bridge = bridge
        self.neural_chain = neural_chain
        self.symbol = symbol
        self.magic_number = magic_number
        self.auto_execute = auto_execute
        self.logger = get_logger("TradeExecutor")
        
        # State tracking
        self.orders: Dict[int, Order] = {}  # ticket  Order
        self.positions: Dict[int, Position] = {}  # ticket  Position
        self.order_counter = 10000  # Comear de 10000 para diferenciar de backtest
        
        # Lock para thread safety
        self.lock = threading.Lock()
        
        # Thread de monitoramento
        self.monitor_thread: Optional[threading.Thread] = None
        self.running = False
        
        # Estatsticas
        self.stats = {
            "orders_sent": 0,
            "orders_executed": 0,
            "orders_rejected": 0,
            "orders_failed": 0,
            "positions_open": 0,
            "positions_closed": 0,
            "total_pnl": 0.0,
            "last_order_time": None,
            "last_position_close_time": None,
        }
        
        # Callbacks
        self._on_order_executed = None
        self._on_position_closed = None
        
        # Advanced Position Manager
        self.position_manager = AdvancedPositionManager(
            bridge=self.bridge,
            breakeven_min_profit=100.0,
            trailing_atr_multiplier=2.0,
            trailing_activation_percent=1.0,
            max_position_time_hours=24.0
        )
        
        self.logger.info(f"[TRADE_EXEC] Trade executor initialized for {symbol}")
        self.logger.info(f"[TRADE_EXEC] Auto execute: {auto_execute}")
        self.logger.info(f"[TRADE_EXEC] Magic number: {magic_number}")
    
    def start(self):
        """Inicia o executor"""
        self.logger.info("[TRADE_EXEC] Starting trade executor...")
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        self.bridge.on_tick(self._on_tick_received)
        self.logger.info("[TRADE_EXEC]  Trade executor started")
    
    def stop(self):
        """Para o executor"""
        self.logger.info("[TRADE_EXEC] Stopping trade executor...")
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=3)
        self.logger.info("[TRADE_EXEC]  Trade executor stopped")
    
    def execute_signal(self, signal: LiveSignal) -> Optional[int]:
        """Executa sinal da neural chain"""
        if not self.auto_execute:
            self.logger.warning("[TRADE_EXEC] Auto execute disabled, skipping signal")
            return None
        
        with self.lock:
            order_ticket = self.order_counter
            self.order_counter += 1
            
            order = Order(
                ticket=order_ticket,
                timestamp=datetime.now(),
                signal=signal,
                state=OrderState.PENDING
            )
            
            if not self._validate_order(order):
                self.logger.error(f"[TRADE_EXEC] Order validation failed: {order.rejection_reason}")
                order.state = OrderState.REJECTED
                self.orders[order_ticket] = order
                self.stats['orders_rejected'] += 1
                return None
            
            self.logger.info(f"[TRADE_EXEC]  Sending order to MT5: {signal.direction} {signal.volume} {signal.symbol} @ {signal.entry_price:.2f}")
            self.logger.info(f"[TRADE_EXEC]    SL: {signal.stop_loss:.2f} | TP: {signal.take_profit:.2f} | Conf: {signal.confidence:.2f}")
            
            success = self._send_to_mt5(order)
            
            if success:
                order.state = OrderState.SENT_TO_MT5
                self.orders[order_ticket] = order
                self.stats['orders_sent'] += 1
                self.stats['last_order_time'] = datetime.now()
                self.logger.info(f"[TRADE_EXEC]  Order {order_ticket} sent to MT5, awaiting confirmation...")
                return order_ticket
            else:
                order.state = OrderState.FAILED
                order.error_message = "Failed to send to MT5"
                self.orders[order_ticket] = order
                self.stats['orders_failed'] += 1
                self.logger.error(f"[TRADE_EXEC]  Order {order_ticket} failed to send to MT5")
                return None
    
    def _validate_order(self, order: Order) -> bool:
        signal = order.signal
        if signal.volume <= 0:
            order.rejection_reason = "Invalid volume"
            return False
        
        tick = self.bridge.get_latest_tick()
        if tick:
            spread = tick.spread
            if spread > 50:  # Max 50 points
                order.rejection_reason = f"Spread too high: {spread:.2f}"
                return False
        
        if self.stats['last_order_time']:
            time_since_last = (datetime.now() - self.stats['last_order_time']).total_seconds()
            if time_since_last < 300:  # Min 5 minutos
                order.rejection_reason = f"Too soon since last order: {time_since_last:.0f}s"
                return False
        
        open_positions = [p for p in self.positions.values() if p.state in [PositionState.OPEN, PositionState.BREAKEVEN, PositionState.TRAILING]]
        if len(open_positions) >= 1:
            order.rejection_reason = f"Max positions reached: {len(open_positions)}"
            return False
        
        return True
    
    def _send_to_mt5(self, order: Order) -> bool:
        """Envia ordem para MT5 via socket formatada como string com protocolo de 7 partes."""
        signal = order.signal
        
        # Obter preço mais recente real para evitar 0.0
        tick = self.bridge.get_latest_tick()
        if not tick or tick.bid == 0 or tick.ask == 0:
            self.logger.error("[TRADE_EXEC] Invalid tick data from bridge")
            return False
            
        entry_price = (tick.bid + tick.ask) / 2
        
        # Calcular SL/TP baseados no preço de mercado real
        atr = max(signal.atr, 10.0)
        sl_dist = 500.0 # Valor fixo de segurança
        tp_dist = 1000.0
        
        if signal.direction == 'BUY':
            sl = entry_price - sl_dist
            tp = entry_price + tp_dist
        else: # SELL
            sl = entry_price + sl_dist
            tp = entry_price - tp_dist
            
        # Garantir que TP e SL sejam sempre positivos e lógicos
        sl = max(0.1, sl)
        tp = max(0.1, tp)
            
        # Protocolo esperado pelo EA: SIGNAL|SYMBOL|DIRECTION|LOT|SL|TP|MAGIC|TIMESTAMP
        timestamp_str = datetime.now().strftime("%Y%m%d%H%M%S")
        command = f"SIGNAL|{signal.symbol}|{signal.direction}|{signal.volume:.2f}|{sl:.2f}|{tp:.2f}|{self.magic_number}|{timestamp_str}\n"
        
        try:
            self.bridge.send_signal(command)
            return True
        except Exception as e:
            self.logger.error(f"[TRADE_EXEC] Error sending signal: {e}")
            return False
    
    def _on_order_filled(self, mt5_ticket: int, symbol: str, direction: str, volume: float, price: float, sl: float, tp: float):
        """Callback quando MT5 confirma execuo de ordem"""
        self.logger.info(f"[TRADE_EXEC]  ORDER FILLED: MT5 ticket={mt5_ticket} {direction} {volume} {symbol} @ {price:.2f}")
        with self.lock:
            pending_orders = [o for o in self.orders.values() if o.state == OrderState.SENT_TO_MT5]
            if not pending_orders:
                self.logger.warning("[TRADE_EXEC] Order filled but no pending orders found")
                return
            order = max(pending_orders, key=lambda o: o.timestamp)
            order.state = OrderState.EXECUTED
            order.mt5_ticket = mt5_ticket
            order.execution_price = price
            order.execution_time = datetime.now()
            
            position = Position(
                ticket=order.ticket,
                mt5_ticket=mt5_ticket,
                symbol=symbol,
                direction=direction,
                volume=volume,
                entry_price=price,
                stop_loss=sl,
                take_profit=tp,
                open_time=datetime.now()
            )
            self.positions[order.ticket] = position
            self.stats['orders_executed'] += 1
            self.stats['positions_open'] += 1
            self.logger.info(f"[TRADE_EXEC]  Position opened: Ticket {order.ticket} (MT5: {mt5_ticket})")
            if self._on_order_executed:
                self._on_order_executed(position)
    
    def _on_position_closed(self, mt5_ticket: int, close_price: float, close_reason: str, pnl: float):
        """Callback quando posio  fechada"""
        with self.lock:
            position = next((pos for pos in self.positions.values() if pos.mt5_ticket == mt5_ticket), None)
            if not position:
                self.logger.warning(f"[TRADE_EXEC] Position closed but not found: MT5 ticket={mt5_ticket}")
                return
            position.state = PositionState.CLOSED_MANUAL if close_reason == "manual" else PositionState.CLOSED_TP if "TP" in close_reason else PositionState.CLOSED_SL
            position.close_time = datetime.now()
            position.close_price = close_price
            position.close_reason = close_reason
            position.net_pnl = pnl
            self.stats['positions_closed'] += 1
            self.stats['positions_open'] = max(0, self.stats['positions_open'] - 1)
            self.stats['total_pnl'] += pnl
            self.stats['last_position_close_time'] = datetime.now()
            self.logger.info(f"[TRADE_EXEC]  Position closed: Ticket {position.ticket} | PnL: ${pnl:.2f} | Reason: {close_reason}")
            if hasattr(self.neural_chain, 'record_trade_result'):
                self.neural_chain.record_trade_result(position.ticket, pnl)
            if self._on_position_closed:
                self._on_position_closed(position)
    
    def _monitor_loop(self):
        """Loop de monitoramento de posies"""
        self.logger.info("[TRADE_EXEC] Monitor loop started")
        while self.running:
            try:
                self._update_positions()
                self._manage_open_positions()
                self._check_closed_positions()
                time.sleep(1)
            except Exception as e:
                self.logger.error(f"[TRADE_EXEC] Monitor loop error: {e}")
                time.sleep(2)
        self.logger.info("[TRADE_EXEC] Monitor loop stopped")
    
    def _manage_open_positions(self):
        open_positions = self.get_open_positions()
        for position in open_positions:
            action = self.position_manager.check_and_manage_position(position)
            if action:
                if action["type"] == "modify":
                    success = self.bridge.send_signal(f"MODIFY|{action['ticket']}|{action['new_sl']}|{action['new_tp']}\n")
                    if success:
                        self.logger.info(f"[TRADE_EXEC]  Position modified: Ticket {position.ticket} | Reason: {action['reason']}")
                    else:
                        self.logger.error(f"[TRADE_EXEC]  Failed to modify position: Ticket {position.ticket}")
                elif action["type"] == "partial_close":
                    success = self.bridge.send_signal(f"CLOSE|{action['ticket']}\n")
                    if success:
                        self.logger.info(f"[TRADE_EXEC]  Partial close: Ticket {position.ticket} | Reason: {action['reason']}")
    
    def _update_positions(self):
        tick = self.bridge.get_latest_tick()
        if not tick: return
        with self.lock:
            for ticket, position in self.positions.items():
                if position.state not in [PositionState.OPEN, PositionState.BREAKEVEN, PositionState.TRAILING]:
                    continue
                position.current_price = (tick.bid + tick.ask) / 2
                if position.direction == "BUY":
                    position.current_pnl = (position.current_price - position.entry_price) * position.volume
                else:
                    position.current_pnl = (position.entry_price - position.current_price) * position.volume
                position.max_profit = max(position.max_profit, position.current_pnl)
                position.max_drawdown = min(position.max_drawdown, position.current_pnl)
    
    def _check_closed_positions(self): pass
    
    def _on_tick_received(self, tick: TickData): pass
    
    def get_open_positions(self) -> List[Position]:
        with self.lock:
            return [p for p in self.positions.values() if p.state in [PositionState.OPEN, PositionState.BREAKEVEN, PositionState.TRAILING]]
    
    def get_stats(self) -> Dict:
        return {
            **self.stats,
            "open_positions": len(self.get_open_positions()),
            "total_orders": len(self.orders),
            "total_positions": len(self.positions)
        }
    
    def register_callbacks(self, on_order_executed=None, on_position_closed=None):
        if on_order_executed: self._on_order_executed = on_order_executed
        if on_position_closed: self._on_position_closed = on_position_closed

    def on_order_executed(self, callback):
        self._on_order_executed = callback
        return self

    def on_position_closed(self, callback):
        self._on_position_closed = callback
        return self
