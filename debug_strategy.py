"""Debug strategy signals"""
import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Generate simple test data
np.random.seed(42)
bars = 1000
prices = [73000]
for i in range(1, bars):
    change = np.random.normal(0, 200)
    prices.append(max(prices[-1] + change, 10000))

df = pd.DataFrame({
    'time': [datetime.now() - timedelta(minutes=5*(bars-i)) for i in range(bars)],
    'open': prices,
    'high': [p + abs(np.random.normal(0, 100)) for p in prices],
    'low': [p - abs(np.random.normal(0, 100)) for p in prices],
    'close': prices,
    'volume': np.random.lognormal(7, 0.5, bars)
})

print(f"Data: {len(df)} candles")
print(f"Price range: ${df['close'].min():,.0f} - ${df['close'].max():,.0f}")

# Calculate indicators
df['ema_9'] = df['close'].ewm(span=9, adjust=False).mean()
df['ema_21'] = df['close'].ewm(span=21, adjust=False).mean()

# RSI
delta = df['close'].diff()
gain = delta.where(delta > 0, 0).rolling(14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
rs = gain / loss
df['rsi'] = 100 - (100 / (1 + rs))

# ATR
tr = pd.DataFrame()
tr['h-l'] = df['high'] - df['low']
tr['h-pc'] = (df['high'] - df['close'].shift(1)).abs()
tr['l-pc'] = (df['low'] - df['close'].shift(1)).abs()
tr['tr'] = tr.max(axis=1)
df['atr'] = tr.max(axis=1).rolling(14).mean()

# Check last 20 bars
print("\nLast 20 bars analysis:")
for i in range(-20, 0):
    row = df.iloc[i]
    ema_diff_pct = abs(row['ema_9'] - row['ema_21']) / row['close'] * 100
    trend = "BUY" if row['ema_9'] > row['ema_21'] else "SELL"
    
    if row['ema_9'] > row['ema_21'] and ema_diff_pct > 0.1:
        confidence = min(0.65 + ema_diff_pct * 0.5, 0.95)
        signal = f"✅ BUY (conf={confidence:.2f})"
    elif row['ema_9'] < row['ema_21'] and ema_diff_pct > 0.1:
        confidence = min(0.65 + ema_diff_pct * 0.5, 0.95)
        signal = f"✅ SELL (conf={confidence:.2f})"
    elif row['rsi'] < 25:
        confidence = 0.60 + (30 - row['rsi']) * 0.02
        signal = f"✅ BUY RSI (conf={confidence:.2f})"
    elif row['rsi'] > 75:
        confidence = 0.60 + (row['rsi'] - 70) * 0.02
        signal = f"✅ SELL RSI (conf={confidence:.2f})"
    else:
        signal = "❌ NO SIGNAL"
    
    print(f"  Bar {i}: ${row['close']:,.0f} | {trend} | EMA diff: {ema_diff_pct:.2f}% | RSI: {row['rsi']:.1f} | {signal}")

# Summary
buy_signals = ((df['ema_9'] > df['ema_21']) & (abs(df['ema_9'] - df['ema_21']) / df['close'] * 100 > 0.1)).sum()
sell_signals = ((df['ema_9'] < df['ema_21']) & (abs(df['ema_9'] - df['ema_21']) / df['close'] * 100 > 0.1)).sum()
rsi_buy_signals = (df['rsi'] < 25).sum()
rsi_sell_signals = (df['rsi'] > 75).sum()

print(f"\nSignal counts (all data):")
print(f"  BUY signals: {buy_signals}")
print(f"  SELL signals: {sell_signals}")
print(f"  RSI BUY signals: {rsi_buy_signals}")
print(f"  RSI SELL signals: {rsi_sell_signals}")
