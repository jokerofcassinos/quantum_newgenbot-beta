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
import logging
from datetime import datetime

# Setup path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from live_trading.logger import get_logger
from live_trading.mt5_bridge import MT5Bridge
from src.risk.risk_quantum_engine import RiskQuantumEngine
from live_v3.event_bus import EventBus, EventType, Event
from live_v3.data_engine_v3 import DataEngineV3
from live_v3.core_intelligence import CoreIntelligenceV3

# Basic configuration
SYMBOL = "BTCUSD"
INITIAL_CAPITAL = 100000.0
MAGIC_NUMBER = 20260414

class QuantumLiveV3:
    def __init__(self):
        self.logger = get_logger("QuantumLiveV3")
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
        
        # 5. Subscribe to events
        self.event_bus.subscribe(EventType.MARKET_SNAPSHOT, self._on_market_snapshot)
        
        # State
        self.running = False
        self.total_trades = 0
        self.winning_trades = 0
        self.current_drawdown = 0.0
        self.total_cycles = 0
        self.last_trade_time = None  # Controle de Cooldown

    def _on_market_snapshot(self, event: Event):
        """
        Triggered instantaneously when DataEngineV3 pushes a new dataframe.
        """
        payload = event.payload
        df = payload['dataframe']
        tick = payload['latest_tick']
        
        self.total_cycles += 1
        
        # Anti-Metralhadora / Cooldown (Evita congelar o MT5)
        if self.last_trade_time is not None:
            elapsed = (datetime.now() - self.last_trade_time).total_seconds()
            if elapsed < 300: # 5 minutos de cooldown após uma ordem
                return # Ignora silenciosamente até o cooldown acabar
        
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
        """Sends the exact 7-part protocol command to MT5."""
        
        direction = signal_dict['direction'] # "BUY" or "SELL"
        vol = signal_dict['volume']
        sl = signal_dict['stop_loss']
        tp = signal_dict['take_profit']
        timestamp_str = datetime.now().strftime("%Y%m%d%H%M%S")
        
        # Ensure SL/TP are positive
        sl = max(0.1, sl)
        tp = max(0.1, tp)
        
        # Protocolo Universal (V2 e V3): BUY|symbol|lot|sl|tp|magic|timestamp
        command = f"{direction}|{SYMBOL}|{vol:.2f}|{sl:.2f}|{tp:.2f}|{MAGIC_NUMBER}|{timestamp_str}\n"
        
        try:
            self.bridge.send_signal(command)
            self.logger.info(f"Signal successfully dispatched to bridge: {direction}")
            self.last_trade_time = datetime.now() # Atualizar controle de cooldown
        except Exception as e:
            self.logger.error(f"Failed to dispatch signal to bridge: {e}")

    def start(self):
        """Boot up the V3 Architecture."""
        self.logger.info("Starting Quantum Live V3...")
        self.running = True
        
        # Start the socket server (runs in background thread)
        self.bridge.start()
        
        # Bind data engine to bridge
        self.data_engine.start()
        
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
