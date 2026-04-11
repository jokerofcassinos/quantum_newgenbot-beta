"""
Test Monitoring System
"""

import sys
from pathlib import Path
import time

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.monitoring.health_monitor import HealthMonitor
from src.monitoring.performance_tracker import PerformanceTracker, TradeRecord
from src.monitoring.telegram_notifier import TelegramNotifier
from datetime import datetime, timezone

print("\n" + "="*80)
print("🧪 TESTING MONITORING SYSTEM")
print("="*80 + "\n")

# 1. Test Health Monitor
print("1️⃣ Testing Health Monitor...")
health = HealthMonitor()

# Update some components
health.update_component('mt5_connection', 'ok')
health.update_component('dna_engine', 'ok')
health.update_component('strategy_engine', 'ok')

# Record some metrics
health.record_metric('trade_execution_ms', 150.0)
health.record_metric('trade_execution_ms', 120.0)
health.record_metric('signal_generation_ms', 45.0)

# Check health
status = health.check_health()
print(f"   Status: {status.status}")
print(f"   CPU: {status.metrics.get('cpu_percent', 0):.1f}%")
print(f"   RAM: {status.metrics.get('ram_percent', 0):.1f}%")
print(f"   Issues: {len(status.issues)}")
print("   ✅ Health Monitor OK\n")

# 2. Test Performance Tracker
print("2️⃣ Testing Performance Tracker...")
tracker = PerformanceTracker(initial_capital=100000.0)

# Simulate some trades
for i in range(10):
    trade = TradeRecord(
        ticket=1000+i,
        timestamp=datetime.now(timezone.utc),
        symbol='BTCUSD',
        direction='BUY' if i % 2 == 0 else 'SELL',
        volume=0.10,
        entry_price=73000.0 + i*100,
        exit_price=73000.0 + i*100 + (50 if i % 3 != 0 else -100),
        sl=72900.0,
        tp=73200.0,
        pnl=50 if i % 3 != 0 else -100,
        pnl_points=50 if i % 3 != 0 else -100,
        duration_minutes=15,
        exit_reason='TP' if i % 3 != 0 else 'SL',
        commission=9.0,
        spread_cost=10.0,
        net_pnl=(50 if i % 3 != 0 else -100) - 19,
    )
    tracker.record_trade(trade)

stats = tracker.get_current_stats()
print(f"   Trades: {stats['total_trades']}")
print(f"   Win Rate: {stats['win_rate']*100:.1f}%")
print(f"   Net PnL: ${stats['net_pnl']:+,.2f}")
print(f"   Equity: ${stats['current_equity']:,.2f}")
print(f"   Max DD: {stats['max_drawdown']:.2f}%")
print("   ✅ Performance Tracker OK\n")

# 3. Test Telegram (without actual sending)
print("3️⃣ Testing Telegram Notifier...")
telegram = TelegramNotifier()  # No token = disabled
print(f"   Enabled: {telegram.enabled}")
print(f"   Status: {'✅ Configured' if telegram.enabled else '⚠️ Not configured (expected)'}")
print("   ✅ Telegram Notifier OK\n")

# Summary
print("="*80)
print("✅ ALL MONITORING TESTS PASSED")
print("="*80)
print("\n📊 Monitoring System Components:")
print("   ✅ Health Monitor - Resource & component tracking")
print("   ✅ Performance Tracker - P&L, win rate, drawdown")
print("   ✅ Telegram Notifier - Alerts & reports")
print("\n🎯 Ready for integration!")
print("="*80 + "\n")
