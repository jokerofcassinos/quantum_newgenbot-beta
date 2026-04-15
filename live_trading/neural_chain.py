import sys
import os
from typing import Optional, Dict, List
from datetime import datetime
from dataclasses import dataclass, field
import numpy as np
import pandas as pd
from loguru import logger

# Adicionar projeto ao path para importar modulos do backtest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importar modulos necessários
from live_trading.mt5_bridge import MT5Bridge, TickData
from live_trading.data_engine import IndicatorData, MarketState
from live_trading.logger import get_logger
from src.risk.risk_quantum_engine import RiskQuantumEngine
from src.monitoring.veto_orchestrator import VetoOrchestrator
from src.strategies.strategy_orchestrator import StrategyOrchestrator

@dataclass
class LiveSignal:
    timestamp: datetime
    symbol: str
    direction: str
    entry_price: float
    stop_loss: float
    take_profit: float
    volume: float
    confidence: float
    atr: float
    strategy_votes: Dict = field(default_factory=dict)

class LiveNeuralChain:
    def __init__(self, symbol: str = "BTCUSD", initial_capital: float = 100000.0):
        self.symbol = symbol
        self.initial_capital = initial_capital
        self.logger = get_logger("LiveNeuralChain")
        
        # Core engines
        self.orchestrator = StrategyOrchestrator(dna_params={})
        self.risk_quantum = RiskQuantumEngine()
        self.veto_orchestrator = VetoOrchestrator()
        
        # State tracking
        self.stats = {'signals_generated': 0, 'trades_executed': 0, 'vetoes': {}}
        self.total_vetoes = 0
        self.price_buffer = []
        self.high_buffer = []
        self.low_buffer = []
        self.volume_buffer = []
        self.max_buffer_size = 200
        self.last_trade_time = None
        self.min_cooldown_bars = 5

    def get_stats(self) -> Dict:
        """Retorna estatísticas da cadeia neural"""
        return {
            "signals_generated": self.stats.get('signals_generated', 0),
            "trades_executed": self.stats.get('trades_executed', 0),
            "vetoes": self.stats.get('vetoes', {}),
            "total_vetoes": self.total_vetoes
        }

    def update_market_data(self, tick: TickData, indicators: IndicatorData):
        mid_price = (tick.bid + tick.ask) / 2
        self.price_buffer.append(mid_price)
        self.high_buffer.append(tick.ask)
        self.low_buffer.append(tick.bid)
        self.volume_buffer.append(tick.volume)
        if len(self.price_buffer) > self.max_buffer_size:
            self.price_buffer.pop(0); self.high_buffer.pop(0); self.low_buffer.pop(0); self.volume_buffer.pop(0)

    def process_tick(self, tick: TickData, indicators: IndicatorData, market_state: MarketState) -> Optional[LiveSignal]:
        self.update_market_data(tick, indicators)
        if len(self.price_buffer) < 50: return None
        
        # Preparar dados para o motor (simulando backtest fast mode)
        df = pd.DataFrame({
            'open': list(self.high_buffer),
            'high': list(self.high_buffer), 
            'low': list(self.low_buffer), 
            'close': list(self.price_buffer),
            'volume': list(self.volume_buffer)
        })
        
        # Votação real dos 12 agentes
        result = self.orchestrator.orchestrate(df, market_state.price, market_state.regime)
        
        if result.final_direction == 'NEUTRAL': return None

        # Veto System
        context = {
            'market_regime': {'regime_type': market_state.regime},
            'direction': result.final_direction,
            'indicators': {'rsi_14': indicators.rsi}
        }
        if not self.veto_orchestrator.check_trade(context).approved:
            self.total_vetoes += 1
            return None

        # Cálculo de SL/TP Robusto (Backtest Parity)
        atr = max(indicators.atr, 10.0) 
        sl_dist = min(max(atr * 1.5, 100), 1000)
        tp_dist = sl_dist * 2.5
        
        entry = market_state.price
        sl = entry - sl_dist if result.final_direction == 'BUY' else entry + sl_dist
        tp = entry + tp_dist if result.final_direction == 'BUY' else entry - tp_dist
        
        # Calcular volume (Kelly/Risk)
        volume = self.risk_quantum.calculate_position_size(
            equity=self.initial_capital,
            win_rate=0.45,
            avg_win_loss_ratio=1.5,
            signal_confidence=abs(result.weighted_consensus),
            current_volatility=atr,
            avg_volatility=atr,
            current_drawdown=0.0,
            correlation_factor=1.0
        )['position_size']

        self.stats['signals_generated'] += 1
        self.logger.info(f"[NEURAL_CHAIN] SIGNAL: {result.final_direction} @ {entry:.2f} | TP: {tp:.2f} | SL: {sl:.2f} | Vol: {volume:.4f}")
        
        return LiveSignal(
            timestamp=datetime.now(), symbol=self.symbol, direction=result.final_direction,
            entry_price=entry, stop_loss=max(0.1, sl), take_profit=max(0.1, tp),
            volume=max(0.01, volume), confidence=result.weighted_consensus, atr=atr
        )
