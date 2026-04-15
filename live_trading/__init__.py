"""
Live Trading System - Forex Quantum Bot V3

Sistema de live trading com cadeia neural completa, comunicao TCP Socket HFT
e logs ultra-detalhados em tempo real.

Mdulos:
- mt5_bridge: TCP Socket bridge para comunicao com MT5
- data_engine: Background worker para extrao contnua de dados
- logger: Sistema de logs com 5 handlers simultneos
- neural_chain: Cadeia neural completa (33+ mdulos)
- trade_executor: Execuo real de trades no MT5
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




