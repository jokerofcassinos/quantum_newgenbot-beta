"""
Live Trading System - Forex Quantum Bot V3

Sistema de live trading com cadeia neural completa, comunicação TCP Socket HFT
e logs ultra-detalhados em tempo real.

Módulos:
- mt5_bridge: TCP Socket bridge para comunicação com MT5
- data_engine: Background worker para extração contínua de dados
- logger: Sistema de logs com 5 handlers simultâneos
- neural_chain: Cadeia neural completa (33+ módulos)
- trade_executor: Execução real de trades no MT5
- run_live_trading_v2: Entry point principal
"""

from live_trading.mt5_bridge import MT5Bridge, TickData, AccountData, PositionData, ConnectionState
from live_trading.data_engine import DataEngine, IndicatorData, MarketState
from live_trading.logger import (
    LiveTradingLoggerManager, 
    SystemLogger, 
    get_logger, 
    get_recent_logs, 
    get_logger_stats
)
from live_trading.neural_chain import LiveNeuralChain, LiveSignal
from live_trading.trade_executor import TradeExecutor, Position, Order, OrderState, PositionState

__version__ = "3.0.0"
__author__ = "Forex Quantum Bot - Qwen Code"
