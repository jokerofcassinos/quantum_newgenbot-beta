"""
Socket Bridge Configuration

Configuração para comunicação TCP Socket entre MT5 e Python
"""

SOCKET_CONFIG = {
    "host": "127.0.0.1",
    "port": 5555,
    "timeout_ms": 3000,
    "max_reconnect_attempts": 10,
    "reconnect_delay_seconds": 1.0,
    "heartbeat_interval_seconds": 1.0,
    "buffer_size": 8192
}

MT5_CONFIG = {
    "symbol": "BTCUSD",
    "timeframe": "M5",
    "magic_number": 20260413,
    "max_positions": 1,
    "auto_trade": True
}

RISK_CONFIG = {
    "max_daily_loss_usd": 5000.0,
    "max_total_loss_usd": 10000.0,
    "max_trades_per_day": 10,
    "min_trade_interval_seconds": 300,
    "max_spread_points": 50
}

INDICATOR_CONFIG = {
    "atr_period": 14,
    "rsi_period": 14,
    "ema_periods": [9, 21, 50, 200],
    "macd_fast": 12,
    "macd_slow": 26,
    "macd_signal": 9
}

POSITION_MANAGEMENT = {
    "use_smart_tp": True,
    "use_trailing_atr": True,
    "trailing_atr_multiplier": 2.0,
    "use_breakeven": True,
    "breakeven_min_profit_usd": 100.0
}
