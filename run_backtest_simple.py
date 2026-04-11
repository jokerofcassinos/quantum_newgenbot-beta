"""Simple backtest with REALISTIC data"""
import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.core.config_manager import ConfigManager
from src.backtesting.backtester import BacktestEngine, BacktestConfig
from src.backtesting.report_generator import ReportGenerator

print("\n" + "="*80)
print("🚀 SIMPLE BACKTEST - REALISTIC DATA")
print("="*80 + "\n")

# Generate realistic BTCUSD data with RANDOM WALK (not GBM)
np.random.seed(42)
days = 30
bars_per_day = 288
total_bars = days * bars_per_day

# Start at realistic BTC price
start_price = 73000.0

# Simple random walk with mean reversion
prices = [start_price]
for i in range(1, total_bars):
    # Random change (-300 to +300 per 5min bar)
    change = np.random.normal(0, 150)
    
    # Mean reversion (pull back to 73000)
    deviation = prices[-1] - 73000
    reversion = -deviation * 0.001  # 0.1% pull back
    
    new_price = prices[-1] + change + reversion
    new_price = max(60000, min(90000, new_price))  # Realistic range
    prices.append(new_price)

# Build candles
candles = []
current_time = datetime.now() - timedelta(days=days)
current_time = current_time.replace(hour=0, minute=0, second=0)

for i in range(total_bars):
    open_p = prices[i]
    close_p = prices[i+1] if i+1 < len(prices) else prices[i]
    
    # Realistic high/low
    bar_range = abs(np.random.normal(0, 100))
    high_p = max(open_p, close_p) + bar_range
    low_p = min(open_p, close_p) - bar_range
    
    # Volume
    hour = current_time.hour
    if 13 <= hour < 17:  # NY overlap
        vol_base = 1500
    elif 7 <= hour < 13:  # London
        vol_base = 1000
    else:
        vol_base = 500
    
    volume = vol_base * np.random.lognormal(0, 0.3)
    
    candles.append({
        'time': current_time,
        'open': round(open_p, 2),
        'high': round(high_p, 2),
        'low': round(low_p, 2),
        'close': round(close_p, 2),
        'volume': round(volume, 0)
    })
    current_time += timedelta(minutes=5)

df = pd.DataFrame(candles)

print(f"✅ Generated {len(df)} M5 candles")
print(f"   Period: {df['time'].iloc[0]} to {df['time'].iloc[-1]}")
print(f"   Price: ${df['close'].iloc[0]:,.0f} → ${df['close'].iloc[-1]:,.0f}")
print(f"   Range: ${df['low'].min():,.0f} - ${df['high'].max():,.0f}")
print(f"   Avg volume: {df['volume'].mean():,.0f}\n")

# Check first few prices
print("First 10 candles:")
for i in range(10):
    print(f"  {i}: ${df.iloc[i]['open']:,.0f} → ${df.iloc[i]['close']:,.0f}")

# Run backtest
print("\n🚀 Running backtest...\n")

config_manager = ConfigManager()
dna = config_manager.load_dna()

backtest_config = BacktestConfig(
    initial_capital=100000.0,
    commission_per_lot=45.0,
    spread_points=100.0,
    slippage_points=10.0,
)

engine = BacktestEngine(config=backtest_config, dna_params=dna)
results = engine.run(df)

# Summary
summary = results.get('summary', {})
ftmo = results.get('ftmo', {})

print("\n" + "="*80)
print("📊 RESULTS")
print("="*80)
print(f"Net Profit: ${summary.get('net_profit', 0):,.2f}")
print(f"Trades: {summary.get('total_trades', 0)}")
print(f"Win Rate: {summary.get('win_rate', 0)*100:.1f}%")
print(f"Profit Factor: {summary.get('profit_factor', 0):.2f}")
print(f"FTMO: {'✅ PASS' if ftmo.get('overall_pass') else '❌ FAIL'}")
print("="*80)

# Generate report
report_gen = ReportGenerator()
path = report_gen.generate_report(results, "backtest_realistic.html")
print(f"\n📄 Report: {path}\n")
