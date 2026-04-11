"""
Fast Backtest - Quick test with debug
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from loguru import logger

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.core.config_manager import ConfigManager
from src.backtesting.backtester import BacktestEngine, BacktestConfig
from src.backtesting.report_generator import ReportGenerator

logger.remove()
logger.add(sys.stdout, format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>", level="INFO")

def generate_fast_data(days=30):
    """Generate smaller dataset for fast testing"""
    bars_per_day = 288
    total_bars = days * bars_per_day
    start_price = 73000.0
    
    np.random.seed(42)
    annual_drift = 0.15
    annual_vol = 0.65
    dt = 5 / (365 * 24 * 60)
    
    base_vol = np.abs(np.random.normal(annual_vol, 0.1, total_bars))
    drift = (annual_drift - 0.5 * annual_vol**2) * dt
    diffusion = np.sqrt(dt) * base_vol * np.random.normal(0, 1, total_bars)
    log_returns = np.clip(drift + diffusion, -0.10, 0.10)
    log_prices = np.insert(np.cumsum(log_returns), 0, np.log(start_price))
    prices = np.maximum(np.exp(log_prices), 65000)  # Minimum $65K for BTC (realistic 2025-2026 range)
    
    candles = []
    current_time = datetime.now() - timedelta(days=days)
    current_time = current_time.replace(hour=0, minute=0, second=0)
    
    for i in range(total_bars):
        open_p = prices[i]
        close_p = prices[i+1] if i+1 < len(prices) else prices[i]
        vol = base_vol[i] * np.sqrt(dt) * open_p * 2
        high_p = max(open_p, close_p) + np.random.exponential(max(vol, 10))
        low_p = min(open_p, close_p) - np.random.exponential(max(vol, 10))
        
        hour = current_time.hour
        if 0 <= hour < 7:
            vol_base = 500
        elif 7 <= hour < 13:
            vol_base = 1000
        elif 13 <= hour < 17:
            vol_base = 1500
        else:
            vol_base = 800
        volume = vol_base * np.random.lognormal(0, 0.3)
        
        candles.append({
            'time': current_time,
            'open': round(open_p, 2),
            'high': round(high_p, 2),
            'low': round(max(low_p, 1000), 2),
            'close': round(close_p, 2),
            'volume': round(volume, 0)
        })
        current_time += timedelta(minutes=5)
    
    return pd.DataFrame(candles)

print("\n" + "="*80)
print("🚀 FAST BACKTEST - DEBUG MODE")
print("="*80 + "\n")

# Generate data
print("📊 Generating 30 days of data...")
candles = generate_fast_data(days=30)
print(f"✅ {len(candles)} candles | Price: ${candles['close'].iloc[0]:,.0f} → ${candles['close'].iloc[-1]:,.0f}\n")

# Config
config_manager = ConfigManager()
dna = config_manager.load_dna()

backtest_config = BacktestConfig(
    initial_capital=100000.0,
    commission_per_lot=45.0,
    spread_points=100.0,
    slippage_points=10.0,
)

# Run
print("🚀 Running backtest...\n")
engine = BacktestEngine(config=backtest_config, dna_params=dna)
results = engine.run(candles)

# Summary
summary = results.get('summary', {})
ftmo = results.get('ftmo', {})
costs = results.get('costs', {})

print("\n" + "="*80)
print("📊 RESULTS")
print("="*80)
print(f"Net Profit: ${summary.get('net_profit', 0):,.2f}")
print(f"Trades: {summary.get('total_trades', 0)}")
print(f"Win Rate: {summary.get('win_rate', 0)*100:.1f}%")
print(f"Profit Factor: {summary.get('profit_factor', 0):.2f}")
print(f"FTMO: {'✅ PASS' if ftmo.get('overall_pass') else '❌ FAIL'}")
print(f"Costs: ${costs.get('total_costs', 0):,.2f}")
print("="*80)

# Generate report
report_gen = ReportGenerator()
path = report_gen.generate_report(results, "backtest_fast.html")
print(f"\n📄 Report: {path}\n")
