"""
Position Manager Avanado - Gerenciamento completo de posies

Este mdulo implementa gerenciamento avanado de posies:
1. Breakeven automtico baseado em lucro
2. Trailing stop dinmico baseado em ATR
3. Partial exit (fechar 50% no TP1, restante trailing)
4. Consulta de histrico do MT5 para detectar fechamentos
5. Clculo preciso de PnL com comisses e swap
6. Time-based exits (fechar aps X tempo se no foi no TP)

Integrao:
- Trade Executor usa este mdulo para gerenciar posies abertas
- Neural chain fornece parmetros de gesto
- MT5 Bridge fornece dados de mercado
"""

import sys
import os
import time
import threading
from typing import Optional, Dict, List, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum

# Adicionar projeto ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from live_trading.mt5_bridge import MT5Bridge, TickData
from live_trading.logger import get_logger


class ExitReason(Enum):
    """Razo de sada de uma posio"""
    TAKE_PROFIT = "take_profit"
    STOP_LOSS = "stop_loss"
    TRAILING_STOP = "trailing_stop"
    BREAKEVEN = "breakeven"
    PARTIAL_EXIT = "partial_exit"
    TIME_EXIT = "time_exit"
    MANUAL_CLOSE = "manual_close"
    EMERGENCY_CLOSE = "emergency_close"


@dataclass
class PartialExit:
    """Sada parcial de uma posio"""
    timestamp: datetime
    volume: float
    price: float
    pnl: float
    reason: str
    remaining_volume: float


@dataclass
class TrailingStopUpdate:
    """Atualizao de trailing stop"""
    timestamp: datetime
    price: float
    new_sl: float
    atr: float
    distance: float


class AdvancedPositionManager:
    """
    Gerenciador avanado de posies
    
    Funcionalidades:
    - Breakeven automtico
    - Trailing stop dinmico (ATR-based)
    - Partial exits multi-nvel
    - Time-based exits
    - Emergency closes
    - PnL calculation preciso
    """
    
    def __init__(
        self,
        bridge: MT5Bridge,
        breakeven_min_profit: float = 100.0,
        trailing_atr_multiplier: float = 2.0,
        trailing_activation_percent: float = 1.0,
        partial_exit_levels: Optional[List[Dict]] = None,
        max_position_time_hours: float = 24.0
    ):
        self.bridge = bridge
        self.logger = get_logger("AdvPositionManager")
        
        # Configuraes de breakeven
        self.breakeven_min_profit = breakeven_min_profit
        
        # Configuraes de trailing
        self.trailing_atr_multiplier = trailing_atr_multiplier
        self.trailing_activation_percent = trailing_activation_percent
        
        # Partial exit levels
        self.partial_exit_levels = partial_exit_levels or [
            {"tp_rr": 2.0, "portion": 0.50, "reason": "TP1"}
        ]
        
        # Time-based exit
        self.max_position_time_hours = max_position_time_hours
        
        # Tracking
        self.trailing_updates: Dict[int, List[TrailingStopUpdate]] = {}
        self.partial_exits: Dict[int, List[PartialExit]] = {}
        
        # Lock para thread safety
        self.lock = threading.Lock()
        
        self.logger.info("[ADV_POS_MGR] Advanced position manager initialized")
        self.logger.info(f"[ADV_POS_MGR] Breakeven min profit: ${breakeven_min_profit}")
        self.logger.info(f"[ADV_POS_MGR] Trailing ATR multiplier: {trailing_atr_multiplier}")
        self.logger.info(f"[ADV_POS_MGR] Partial exit levels: {len(self.partial_exit_levels)}")
        self.logger.info(f"[ADV_POS_MGR] Max position time: {max_position_time_hours}h")
    
    def check_and_manage_position(self, position) -> Optional[Dict]:
        """
        Verifica e gerencia posio aberta
        
        Returns:
            Dict com ao se necessrio (modify, partial_close, close)
            None se no precisa de ao
        """
        with self.lock:
            actions = []
            
            # 1. Verificar breakeven
            breakeven_action = self._check_breakeven(position)
            if breakeven_action:
                actions.append(breakeven_action)
            
            # 2. Verificar trailing stop
            trailing_action = self._check_trailing_stop(position)
            if trailing_action:
                actions.append(trailing_action)
            
            # 3. Verificar partial exits
            partial_action = self._check_partial_exits(position)
            if partial_action:
                actions.append(partial_action)
            
            # 4. Verificar time-based exit
            time_action = self._check_time_exit(position)
            if time_action:
                actions.append(time_action)
            
            # Retornar primeira ao (prioridade: breakeven > trailing > partial > time)
            return actions[0] if actions else None
    
    def _check_breakeven(self, position) -> Optional[Dict]:
        """
        Verifica se deve aplicar breakeven
        
        Critrios:
        - Lucro atual >= breakeven_min_profit
        - Breakeven ainda no foi aplicado
        - Posio no est em trailing
        """
        if position.breakeven_applied or position.trailing_applied:
            return None
        
        if position.current_pnl < self.breakeven_min_profit:
            return None
        
        # Aplicar breakeven
        self.logger.info(f"[ADV_POS_MGR]  Breakeven triggered: Position {position.ticket} | PnL: ${position.current_pnl:.2f}")
        
        # Mover SL para preo de entrada + compensação da comissão (aprox 50/lote) e spread
        offset = 55.0 / max(position.volume, 0.01)
        if position.direction == "BUY":
            new_sl = position.entry_price + offset
        else:
            new_sl = position.entry_price - offset
        
        action = {
            "type": "modify",
            "ticket": position.mt5_ticket,
            "new_sl": new_sl,
            "new_tp": position.take_profit,
            "reason": "breakeven"
        }
        
        position.breakeven_applied = True
        position.state = position.state.__class__.BREAKEVEN
        
        return action
    
    def _check_trailing_stop(self, position) -> Optional[Dict]:
        """
        Verifica se deve aplicar trailing stop
        
        Critrios:
        - Preo moveu X% a favor (trailing_activation_percent)
        - ATR disponvel
        - Novo SL > SL atual (para BUY) ou < SL atual (para SELL)
        """
        tick = self.bridge.get_latest_tick()
        if not tick:
            return None
        
        atr = tick.atr
        if atr <= 0:
            return None
        
        # Calcular distncia de trailing
        trailing_distance = atr * self.trailing_atr_multiplier
        
        # Verificar se ativou trailing
        if position.entry_price <= 0 or position.volume <= 0:
            return None
            
        price_move_percent = abs(position.current_pnl / (position.entry_price * position.volume)) * 100
        
        if price_move_percent < self.trailing_activation_percent:
            return None
        
        # Calcular novo SL
        if position.direction == "BUY":
            new_sl = position.current_price - trailing_distance
            # S mover SL pra cima, nunca pra baixo
            if new_sl <= position.stop_loss and not position.trailing_applied:
                return None
            new_sl = max(new_sl, position.stop_loss)
        else:
            new_sl = position.current_price + trailing_distance
            # S mover SL pra baixo, nunca pra cima
            if new_sl >= position.stop_loss and not position.trailing_applied:
                return None
            new_sl = min(new_sl, position.stop_loss)
        
        # Verificar se SL realmente melhorou
        if position.direction == "BUY" and new_sl <= position.stop_loss:
            return None
        if position.direction == "SELL" and new_sl >= position.stop_loss:
            return None
        
        # Aplicar trailing
        self.logger.info(f"[ADV_POS_MGR]  Trailing stop updated: Position {position.ticket} | New SL: {new_sl:.2f} | ATR: {atr:.5f}")
        
        action = {
            "type": "modify",
            "ticket": position.mt5_ticket,
            "new_sl": new_sl,
            "new_tp": position.take_profit,
            "reason": "trailing_stop"
        }
        
        position.trailing_applied = True
        position.state = position.state.__class__.TRAILING
        position.stop_loss = new_sl
        
        # Registrar atualizao
        update = TrailingStopUpdate(
            timestamp=datetime.now(),
            price=position.current_price,
            new_sl=new_sl,
            atr=atr,
            distance=trailing_distance
        )
        
        if position.ticket not in self.trailing_updates:
            self.trailing_updates[position.ticket] = []
        self.trailing_updates[position.ticket].append(update)
        
        return action
    
    def _check_partial_exits(self, position) -> Optional[Dict]:
        """
        Verifica se deve fazer partial exit
        
        Critrios:
        - Preo atingiu nvel de TP parcial
        - Partial exit ainda no foi feito para este nvel
        """
        if not self.partial_exit_levels:
            return None
        
        for level in self.partial_exit_levels:
            tp_rr = level["tp_rr"]
            portion = level["portion"]
            reason = level.get("reason", "TP")
            
            # Calcular preo de TP parcial
            risk_distance = abs(position.entry_price - position.stop_loss)
            tp_price = position.entry_price + (risk_distance * tp_rr) if position.direction == "BUY" else position.entry_price - (risk_distance * tp_rr)
            
            # Verificar se preo atingiu TP parcial
            hit_tp = (position.direction == "BUY" and position.current_price >= tp_price) or \
                     (position.direction == "SELL" and position.current_price <= tp_price)
            
            if not hit_tp:
                continue
            
            # Verificar se j fez partial exit para este nvel
            already_done = False
            if position.ticket in self.partial_exits:
                for exit in self.partial_exits[position.ticket]:
                    if exit.reason == reason:
                        already_done = True
                        break
            
            if already_done:
                continue
            
            # Calcular volume para partial exit
            exit_volume = position.volume * portion
            
            self.logger.info(f"[ADV_POS_MGR]  Partial exit triggered: Position {position.ticket} | {reason} | Volume: {exit_volume:.2f} | Price: {position.current_price:.2f}")
            
            action = {
                "type": "partial_close",
                "ticket": position.mt5_ticket,
                "volume": exit_volume,
                "price": position.current_price,
                "reason": reason
            }
            
            # Registrar partial exit
            pnl = (position.current_price - position.entry_price) * exit_volume if position.direction == "BUY" else (position.entry_price - position.current_price) * exit_volume
            
            partial_exit = PartialExit(
                timestamp=datetime.now(),
                volume=exit_volume,
                price=position.current_price,
                pnl=pnl,
                reason=reason,
                remaining_volume=position.volume - exit_volume
            )
            
            if position.ticket not in self.partial_exits:
                self.partial_exits[position.ticket] = []
            self.partial_exits[position.ticket].append(partial_exit)
            
            # Atualizar volume restante
            position.volume -= exit_volume
            position.state = position.state.__class__.PARTIAL_EXIT
            
            return action
        
        return None
    
    def _check_time_exit(self, position) -> Optional[Dict]:
        """
        Verifica se deve fechar por tempo
        
        Critrios:
        - Posio aberta h mais de max_position_time_hours
        - Ainda no foi fechada
        """
        position_age = (datetime.now() - position.open_time).total_seconds() / 3600
        
        if position_age < self.max_position_time_hours:
            return None
        
        # Fechar por tempo
        self.logger.warning(f"[ADV_POS_MGR]  Time exit triggered: Position {position.ticket} | Age: {position_age:.1f}h")
        
        action = {
            "type": "close",
            "ticket": position.mt5_ticket,
            "reason": "time_exit"
        }
        
        return action
    
    def calculate_precise_pnl(
        self,
        entry_price: float,
        exit_price: float,
        volume: float,
        direction: str,
        commission: float = 90.0,
        swap: float = 0.0
    ) -> Tuple[float, float, float]:
        """
        Calcula PnL preciso com comisses e swap
        
        Returns:
            (gross_pnl, net_pnl, total_costs)
        """
        # Gross PnL
        if direction == "BUY":
            gross_pnl = (exit_price - entry_price) * volume
        else:
            gross_pnl = (entry_price - exit_price) * volume
        
        # Comisses (entrada + sada)
        total_commission = commission * 2
        
        # Total costs
        total_costs = total_commission + swap
        
        # Net PnL
        net_pnl = gross_pnl - total_costs
        
        return gross_pnl, net_pnl, total_costs
    
    def get_position_summary(self, position) -> Dict:
        """Retorna resumo detalhado da posio"""
        summary = {
            "ticket": position.ticket,
            "mt5_ticket": position.mt5_ticket,
            "symbol": position.symbol,
            "direction": position.direction,
            "volume": position.volume,
            "entry_price": position.entry_price,
            "current_price": position.current_price,
            "stop_loss": position.stop_loss,
            "take_profit": position.take_profit,
            "current_pnl": position.current_pnl,
            "max_profit": position.max_profit,
            "max_drawdown": position.max_drawdown,
            "state": position.state.value if hasattr(position.state, 'value') else str(position.state),
            "breakeven_applied": position.breakeven_applied,
            "trailing_applied": position.trailing_applied,
            "open_time": position.open_time.isoformat(),
            "position_age_hours": (datetime.now() - position.open_time).total_seconds() / 3600,
        }
        
        # Adicionar trailing updates
        if position.ticket in self.trailing_updates:
            summary["trailing_updates"] = len(self.trailing_updates[position.ticket])
            last_update = self.trailing_updates[position.ticket][-1]
            summary["last_trailing_sl"] = last_update.new_sl
            summary["last_trailing_atr"] = last_update.atr
        
        # Adicionar partial exits
        if position.ticket in self.partial_exits:
            summary["partial_exits"] = len(self.partial_exits[position.ticket])
            total_partial_pnl = sum(e.pnl for e in self.partial_exits[position.ticket])
            summary["partial_exit_pnl"] = total_partial_pnl
        
        return summary
    
    def emergency_close_all(self, positions: List, bridge: MT5Bridge) -> List[Dict]:
        """Fecha todas as posies em emergncia"""
        self.logger.critical("[ADV_POS_MGR]  EMERGENCY CLOSE ALL triggered!")
        
        actions = []
        for position in positions:
            action = {
                "type": "close",
                "ticket": position.mt5_ticket,
                "reason": "emergency_close"
            }
            actions.append(action)
            
            self.logger.critical(f"[ADV_POS_MGR] Emergency closing: Position {position.ticket} | PnL: ${position.current_pnl:.2f}")
        
        return actions




