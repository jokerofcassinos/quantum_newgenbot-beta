"""
Run Walk-Forward Optimization
CEO: Qwen Code | Created: 2026-04-10

Usage:
    python run_optimization.py
    
This runs walk-forward optimization to find optimal parameters.
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.core.config_manager import ConfigManager
from src.backtesting.walk_forward_optimizer import WalkForwardOptimizer


def generate_test_data(days=180):
    """Generate realistic test data for optimization"""
    print("📊 Generating test data...")
    
    np.random.seed(42)
    bars_per_day = 288
    total_bars = days * bars_per_day
    start_price = 73000.0
    
    # Random walk with mean reversion
    prices = [start_price]
    for i in range(1, total_bars):
        change = np.random.normal(0, 150)
        deviation = prices[-1] - 73000
        reversion = -deviation * 0.001
        new_price = max(60000, min(90000, prices[-1] + change + reversion))
        prices.append(new_price)
    
    candles = []
    current_time = datetime.now() - timedelta(days=days)
    current_time = current_time.replace(hour=0, minute=0, second=0)
    
    for i in range(total_bars):
        open_p = prices[i]
        close_p = prices[i+1] if i+1 < len(prices) else prices[i]
        high_p = max(open_p, close_p) + abs(np.random.normal(0, 100))
        low_p = min(open_p, close_p) - abs(np.random.normal(0, 100))
        
        hour = current_time.hour
        vol_base = 1500 if 13 <= hour < 17 else 1000 if 7 <= hour < 13 else 500
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
    print(f"   ✅ Generated {len(df)} candles")
    print(f"   Price range: ${df['close'].min():,.0f} - ${df['close'].max():,.0f}")
    
    return df


def main():
    """Run optimization"""
    print("\n" + "="*80)
    print("🔬 FOREX QUANTUM BOT - WALK-FORWARD OPTIMIZATION")
    print("="*80 + "\n")
    
    # Generate test data
    candles = generate_test_data(days=180)
    
    # Initialize optimizer
    config_manager = ConfigManager()
    optimizer = WalkForwardOptimizer(config_manager)
    
    # Run optimization
    results = optimizer.optimize(
        candles=candles,
        n_trials=50,  # Reduced for speed, increase to 100+ for production
        train_days=60,
        test_days=30,
        n_splits=3,
    )
    
    # Print summary
    summary = results['summary']
    best_params = results['best_parameters']
    
    print("\n" + "="*80)
    print("🏆 OPTIMIZATION RESULTS")
    print("="*80)
    print(f"\n📊 Summary:")
    print(f"   Splits: {summary['n_splits']}")
    print(f"   Avg In-Sample PnL: ${summary['avg_in_sample_pnl']:+,.2f}")
    print(f"   Avg Out-of-Sample PnL: ${summary['avg_out_of_sample_pnl']:+,.2f}")
    print(f"   Degradation: {summary['degradation_percent']:.1f}%")
    print(f"   Robustness Score: {summary['robustness_score']:.2f}/1.0")
    
    print(f"\n🧬 Best Parameters:")
    for param, value in best_params.items():
        print(f"   {param}: {value}")
    
    # Update DNA with optimized parameters
    print(f"\n🔄 Updating DNA with optimized parameters...")
    optimizer.update_dna_with_optimized_params(best_params)
    
    print("\n✅ Optimization complete!")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
