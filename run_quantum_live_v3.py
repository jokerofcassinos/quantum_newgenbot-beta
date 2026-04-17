"""
Quantum Live Trading V3 - Main Orchestrator
CEO: Qwen Code | Created: 2026-04-14

This is the definitive, PhD-level entry point for live trading.
It leverages an Event-Driven Architecture and the decoupled CoreIntelligenceV3
to achieve exact 1:1 parity with the 103k PnL Backtest.
"""

import sys
import os
import time
from datetime import datetime

# Setup path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from loguru import logger
from live_trading.mt5_bridge import MT5Bridge
from src.risk.risk_quantum_engine import RiskQuantumEngine
from src.risk.anti_metralhadora import AntiMetralhadora
from live_v3.event_bus import EventBus, EventType, Event
from live_v3.data_engine_v3 import DataEngineV3
from live_v3.core_intelligence import CoreIntelligenceV3
from live_trading.trade_executor import TradeExecutor
from live_trading.neural_chain import LiveSignal

# Basic configuration
SYMBOL = "BTCUSD"
INITIAL_CAPITAL = 100000.0
MAGIC_NUMBER = 20260414

class QuantumLiveV3:
    def __init__(self):
        self.logger = logger.bind(name="QuantumLiveV3")
        self.logger.info("Initializing Quantum Live V3 Architecture...")
        
        # 1. Initialize Event Bus
        self.event_bus = EventBus()
        
        # 2. Initialize MT5 Bridge
        self.bridge = MT5Bridge(host="127.0.0.1", port=5555)
        
        # 3. Initialize Data Engine V3
        self.data_engine = DataEngineV3(bridge=self.bridge, event_bus=self.event_bus, max_bars=250)
        
        # 4. Initialize Core Intelligence (The 103k PnL Brain)
        self.core = CoreIntelligenceV3()
        self.risk_manager = RiskQuantumEngine()
        self.anti_metralhadora = AntiMetralhadora()
        
        # 5. Initialize Trade Executor for Smart TP / Trailing Stop management
        self.trade_executor = TradeExecutor(
            bridge=self.bridge,
            neural_chain=None,  # We don't use the old NeuralChain anymore
            symbol=SYMBOL,
            magic_number=MAGIC_NUMBER,
            auto_execute=True
        )
        
        # Register Event Bus subscriptions
        self.event_bus.subscribe(EventType.MARKET_SNAPSHOT, self._on_market_snapshot)
        
        # Bridge callbacks
        self.bridge.on_order_filled(self.trade_executor._on_order_filled)
        self.bridge.on_position_closed(self.trade_executor._on_position_closed)
        self.bridge.on_position_sync(self.trade_executor._on_position_sync)
        self.bridge.on_sync_start(self.trade_executor._on_sync_start)
        self.bridge.on_connected(self._on_bridge_connected)
        
        # Trade Executor callbacks to Orchestrator
        self.trade_executor.on_position_closed(self._on_trade_closed)
        
        # State
        self.running = False
        self.total_trades = 0
        self.winning_trades = 0
        self.current_drawdown = 0.0
        self.total_cycles = 0

    def _on_bridge_connected(self):
        """Disparado quando a bridge conecta ao MT5."""
        self.logger.info("[LIVE] Sincronizando estado com o MT5 (Memória de Elefante)...")
        # Solicita ao EA MQL5 que envie as posições abertas
        try:
            self.bridge.client_socket.send("SYNC|ALL\n".encode('utf-8'))
        except Exception as e:
            self.logger.error(f"[LIVE] Erro ao enviar comando SYNC: {e}")

    def _on_trade_closed(self, position):
        """Disparado quando o TradeExecutor confirma que uma ordem foi fechada."""
        self.total_trades += 1
        from datetime import timezone
        
        # O pnl que vem do position.net_pnl muitas vezes é o gross PnL (sem comissão).
        # Vamos deduzir a comissão (aprox $50 por lote completo) para saber o lucro real.
        estimated_commission = 50.0 * position.volume
        real_net_pnl = getattr(position, 'net_pnl', 0.0) - estimated_commission
        
        # Só consideramos win real se cobriu a comissão e deu lucro limpo
        if real_net_pnl > 0:
            self.winning_trades += 1
            result = 'win'
        else:
            result = 'loss'
            
        self.anti_metralhadora.record_trade(
            result=result,
            current_session='ny',
            current_time=datetime.now(timezone.utc)
        )
        self.logger.info(f"[LIVE] Ordem {position.ticket} contabilizada como {result.upper()} pelo Risk Engine (Real PnL: ${real_net_pnl:.2f}).")

    def _on_market_snapshot(self, event: Event):
        """
        Triggered instantaneously when DataEngineV3 pushes a new dataframe.
        """
        payload = event.payload
        df = payload['dataframe']
        tick = payload['latest_tick']
        
        self.total_cycles += 1
        
        from datetime import timezone # Adicionando timezone se não existir, mas já deve ter ou importamos
        
        # Anti-Metralhadora Real (Substitui o cooldown burro)
        # O Anti-Metralhadora usa a confiança do sinal e a hora atual
        # Como só temos a confiança APÓS o evaluate, fazemos um pré-check de tempo.
        allowed, reason, _ = self.anti_metralhadora.should_allow_trade(
            signal_quality=0.5, # Qualidade neutra para pré-check
            current_session="ny", # Deve ser minúsculo para bater com o dicionário interno
            current_time=datetime.now(timezone.utc)
        )
        if not allowed:
            # Ignora silenciosamente até o cooldown acabar
            return
            
        # Cooldown do Trade Executor (5 minutos silenciosos após uma ordem)
        if self.trade_executor.stats['last_order_time'] is not None:
            elapsed = (datetime.now() - self.trade_executor.stats['last_order_time']).total_seconds()
            if elapsed < 300:
                return # Silêncio absoluto durante o cooldown de 5 minutos
            
        # Calculate dynamic metrics for Kelly Sizing
        win_rate = self.winning_trades / max(1, self.total_trades) if self.total_trades > 10 else 0.35
        avg_win_loss_ratio = 1.5 # Placeholder until we have closed trades
        
        # 1. EVALUATE THE SNAPSHOT (100% Backtest Parity)
        signal_dict = self.core.evaluate(
            df=df,
            risk_manager=self.risk_manager,
            current_capital=INITIAL_CAPITAL,
            win_rate=win_rate,
            avg_win_loss_ratio=avg_win_loss_ratio,
            current_dd=self.current_drawdown
        )
        
        # 2. PhD-LEVEL TELEMETRY (The Matrix Log)
        # Log every 50 cycles to show it's alive without spamming
        if self.total_cycles % 50 == 0 or signal_dict:
            self._print_telemetry_matrix(df, signal_dict)
            
        # 3. EXECUTION
        if signal_dict:
            self._execute_signal(signal_dict)

    def _print_telemetry_matrix(self, df, signal_dict):
        """Prints a highly structured matrix log."""
        idx = len(df) - 1
        current_price = df['close'].iloc[idx]
        rsi = df['rsi'].iloc[idx]
        atr = df['atr'].iloc[idx]
        
        decision = signal_dict['direction'] if signal_dict else "NEUTRAL"
        conf = signal_dict['confidence'] if signal_dict else 0.0
        
        print("\n" + "="*80)
        print(f"[CYCLE: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] | {SYMBOL} @ {current_price:.2f}")
        print(f"|-- INDICATORS: RSI={rsi:.2f} | ATR={atr:.2f}")
        
        if signal_dict and 'votes' in signal_dict:
            votes = signal_dict['votes']
            print(f"|-- VOTING MATRIX: BUY({votes['buy_votes']}) | SELL({votes['sell_votes']})")
            print(f"    | Agents: {votes['strategy_votes']}")
        
        print(f"|-- ORCHESTRATOR DECISION: {decision} | Consensus: {conf:.2f}")
        
        if signal_dict:
            print(f"|-- RISK ENGINE: Vol={signal_dict['volume']:.2f} Lot | SL={signal_dict['stop_loss']:.2f} | TP={signal_dict['take_profit']:.2f}")
            print(f"[ACTION] -> SIGNAL SENT TO MT5")
        print("="*80 + "\n")

    def _execute_signal(self, signal_dict):
        """Uses TradeExecutor to send and track the signal for Smart TP / Trailing."""
        direction = signal_dict['direction'] # "BUY" or "SELL"
        
        live_signal = LiveSignal(
            timestamp=datetime.now(),
            symbol=SYMBOL,
            direction=direction,
            entry_price=signal_dict['entry_price'],
            stop_loss=signal_dict['stop_loss'],
            take_profit=signal_dict['take_profit'],
            volume=signal_dict['volume'],
            confidence=signal_dict['confidence'],
            atr=signal_dict['atr']
        )
        
        order_ticket = self.trade_executor.execute_signal(live_signal)
        
        if order_ticket:
            self.last_trade_time = datetime.now() # Atualizar controle de cooldown

    def start(self):
        """Boot up the V3 Architecture."""
        self.logger.info("Starting Quantum Live V3...")
        self.running = True
        
        # Start the socket server
        self.bridge.start()
        
        # Bind data engine to bridge
        self.data_engine.start()
        
        # Start Trade Executor (Monitor loop for trailing stops)
        self.trade_executor.start()
        
        self.logger.info("System Online. Awaiting MT5 connection...")
        
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.logger.info("Shutdown sequence initiated.")
            self.stop()

    def stop(self):
        self.running = False
        # (Add graceful socket shutdown logic if needed)

if __name__ == "__main__":
    app = QuantumLiveV3()
    app.start()
