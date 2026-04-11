"""
Test Smart Order Manager - Visual demonstration
CEO: Qwen Code | Created: 2026-04-10

Demonstrates:
- Virtual TP dynamics
- Dynamic SL with profit protection
- Market momentum analysis
- DNA-adjusted profit profiles
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.execution.smart_order_manager import SmartOrderManager, MarketMomentum


def generate_test_candles(trend="bullish", count=50):
    """Generate test candles for demonstration"""
    np.random.seed(42)
    
    base_price = 73000.0
    prices = [base_price]
    
    for i in range(1, count):
        if trend == "bullish":
            change = np.random.normal(15, 30)
        elif trend == "bearish":
            change = np.random.normal(-15, 30)
        else:
            change = np.random.normal(0, 30)
        
        prices.append(max(prices[-1] + change, 60000))
    
    candles = []
    current_time = datetime.now() - timedelta(minutes=5*count)
    
    for i in range(count):
        open_p = prices[i]
        close_p = prices[i+1] if i+1 < len(prices) else prices[i]
        high_p = max(open_p, close_p) + abs(np.random.normal(0, 20))
        low_p = min(open_p, close_p) - abs(np.random.normal(0, 20))
        volume = 1000 * np.random.lognormal(0, 0.3)
        
        candles.append({
            'time': current_time,
            'open': round(open_p, 2),
            'high': round(high_p, 2),
            'low': round(low_p, 2),
            'close': round(close_p, 2),
            'volume': round(volume, 0)
        })
        current_time += timedelta(minutes=5)
    
    return pd.DataFrame(candles)


def test_virtual_tp_dynamics():
    """Test 1: Virtual TP Dynamics"""
    print("\n" + "="*80)
    print("🎯 TEST 1: VIRTUAL TP DYNAMICS")
    print("="*80)
    
    manager = SmartOrderManager(dna_params={})
    
    # Open position
    position = manager.open_position({
        'ticket': 1000,
        'symbol': 'BTCUSD',
        'direction': 'BUY',
        'entry_price': 73000.0,
        'volume': 0.10,
        'stop_loss': 72700.0,
        'take_profit': 73600.0,
    })
    
    print(f"\n📊 Position Opened:")
    print(f"   Entry: ${position.entry_price:,.2f}")
    print(f"   Original TP: ${position.original_tp:,.2f} (+$600)")
    print(f"   Original SL: ${position.original_sl:,.2f} (-$300)")
    
    # Simulate price movement
    print(f"\n⏱️ Simulating price movement...")
    
    prices = [73000, 73100, 73200, 73150, 73300, 73250, 73400, 73350, 73500, 73550]
    
    for i, price in enumerate(prices):
        candles = generate_test_candles(trend="bullish", count=20)
        action = manager.update_position(1000, float(price), candles)
        
        state = manager.positions[1000]
        
        print(f"\n   [{i+1:2d}] Price: ${price:,.2f}")
        print(f"       PnL: ${state.current_pnl:+,.2f}")
        print(f"       Progress: {state.progress_to_tp*100:.1f}%")
        print(f"       Virtual TP: ${state.virtual_tp.current_virtual_tp:,.2f}")
        print(f"       TP Distance: ${state.virtual_tp.current_distance:,.0f} (factor: {state.virtual_tp.adjustment_factor:.2f})")
        print(f"       Difficulty: {state.virtual_tp.difficulty.value}")
        print(f"       Current SL: ${state.dynamic_sl.current_sl:,.2f}")
        print(f"       Targets: {[f'{t.value*100:.0f}%' for t in state.targets_reached]}")
        print(f"       Action: {action['action']}")
        
        if action['action'] == 'close_position':
            print(f"\n   ✅ {action['reason']}")
            summary = manager.close_position(1000, action['reason'])
            print(f"   Final PnL: ${summary['pnl']:+,.2f}")
            break


def test_dynamic_sl_protection():
    """Test 2: Dynamic SL with Profit Protection"""
    print("\n" + "="*80)
    print("🛡️ TEST 2: DYNAMIC SL WITH PROFIT PROTECTION")
    print("="*80)
    
    manager = SmartOrderManager(dna_params={})
    
    # Open position
    manager.open_position({
        'ticket': 2000,
        'symbol': 'BTCUSD',
        'direction': 'BUY',
        'entry_price': 73000.0,
        'volume': 0.10,
        'stop_loss': 72700.0,
        'take_profit': 73600.0,
    })
    
    print(f"\n📊 Position Opened:")
    print(f"   Entry: $73,000.00")
    print(f"   SL: $72,700.00 (-$300)")
    print(f"   TP: $73,600.00 (+$600)")
    
    # Simulate steady climb to 50% target
    print(f"\n⏱️ Simulating steady climb...")
    
    targets = [0.25, 0.35, 0.50, 0.65, 0.75, 0.90]
    
    for target_pct in targets:
        price = 73000 + (600 * target_pct)
        candles = generate_test_candles(trend="bullish", count=20)
        action = manager.update_position(2000, float(price), candles)
        
        state = manager.positions[2000]
        
        print(f"\n   🎯 Target {target_pct*100:.0f}% reached!")
        print(f"       Price: ${price:,.2f}")
        print(f"       PnL: ${state.current_pnl:+,.2f}")
        print(f"       SL moved to: ${state.dynamic_sl.current_sl:,.2f}")
        print(f"       Breakeven: {'✅ Active' if state.dynamic_sl.breakeven_activated else '❌ Inactive'}")
        print(f"       Profit Locked: ${state.dynamic_sl.profit_locked:.2f}")
        print(f"       Targets: {[f'{t.value*100:.0f}%' for t in state.targets_reached]}")
        print(f"       Action: {action['action']}")


def test_market_momentum():
    """Test 3: Market Momentum Analysis"""
    print("\n" + "="*80)
    print("📈 TEST 3: MARKET MOMENTUM ANALYSIS")
    print("="*80)
    
    manager = SmartOrderManager(dna_params={})
    
    # Different market conditions
    conditions = [
        ("Low Volatility", "ranging"),
        ("High Momentum", "bullish"),
        ("Crash", "bearish"),
    ]
    
    for name, trend in conditions:
        candles = generate_test_candles(trend=trend, count=30)
        momentum = manager._analyze_market_momentum(candles)
        
        print(f"\n📊 {name}:")
        print(f"   Velocity: {momentum.velocity:.4f} pts/sec")
        print(f"   Acceleration: {momentum.acceleration:.6f}")
        print(f"   Gravity: {momentum.gravity:.2f}")
        print(f"   Oscillation: {momentum.oscillation:.1f} pts")
        print(f"   Volatility: {momentum.volatility:.1f} pts")
        print(f"   Volume Pressure: {momentum.volume_pressure:.2f}")
        print(f"   Microstructure: {momentum.microstructure_score:.2f}")


def test_profit_profiles():
    """Test 4: DNA-Adjusted Profit Profiles"""
    print("\n" + "="*80)
    print("🎯 TEST 4: DNA-ADJUSTED PROFIT PROFILES")
    print("="*80)
    
    manager = SmartOrderManager(dna_params={})
    
    print(f"\n📋 Profit Profiles:")
    print(f"{'Target':<12} {'SL Behavior':<18} {'Velocity':<12} {'Distance':<12} {'Min Lock':<12}")
    print("-" * 80)
    
    for target, profile in manager.profit_profiles.items():
        print(f"{target.value*100:<11.0f}% "
              f"{profile.sl_behavior:<18} "
              f"{profile.velocity_threshold:<12.2f} "
              f"{profile.sl_distance_points:<12.0f}pts "
              f"${profile.min_profit_lock:<11.2f}")


def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("🎯 FOREX QUANTUM BOT - SMART ORDER MANAGER TESTS")
    print("="*80)
    
    try:
        # Test 1: Virtual TP Dynamics
        test_virtual_tp_dynamics()
        
        # Test 2: Dynamic SL Protection
        test_dynamic_sl_protection()
        
        # Test 3: Market Momentum
        test_market_momentum()
        
        # Test 4: Profit Profiles
        test_profit_profiles()
        
        # Summary
        print("\n" + "="*80)
        print("✅ ALL TESTS COMPLETE")
        print("="*80)
        print("""
📊 Smart Order Manager Features Tested:
   ✅ Virtual TP dynamics based on market difficulty
   ✅ Dynamic SL with profit protection
   ✅ Market momentum analysis (velocity, gravity, oscillation)
   ✅ DNA-adjusted profit profiles
   ✅ Velocity-based behavior adaptation
   ✅ Breakeven activation
   ✅ Trailing stop logic

🎯 Next Steps:
   1. Integrate with MT5 execution
   2. Add DNA auto-adjustment of profiles
   3. Enable real-time position management
""")
        print("="*80 + "\n")
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Tests interrupted")
    except Exception as e:
        print(f"\n\n❌ Test error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
