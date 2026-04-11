"""
Quick Backtest - Generate realistic BTCUSD data and run backtest
CEO: Qwen Code | Created: 2026-04-10

This version generates realistic synthetic BTCUSD data
(no MT5 connection required) for immediate testing.
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from loguru import logger

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.core.config_manager import ConfigManager
from src.backtesting.backtester import BacktestEngine, BacktestConfig
from src.backtesting.report_generator import ReportGenerator


def setup_logging():
    """Configure logging"""
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )


def generate_realistic_btcusd_data(days: int = 180) -> pd.DataFrame:
    """
    Generate realistic synthetic BTCUSD M5 data
    
    Features:
    - Geometric Brownian Motion with realistic drift/volatility
    - Time-varying volatility (volatility clustering)
    - Volume patterns (session-based)
    - Realistic price levels ($60K-$100K range)
    """
    
    logger.info(f"🔬 Generating {days} days of realistic BTCUSD M5 data...")
    
    # Parameters
    bars_per_day = 288  # 24h * 12 (5-min bars)
    total_bars = days * bars_per_day
    
    # Starting price (realistic BTC level)
    start_price = 73000.0
    
    # GBM parameters (calibrated to BTCUSD)
    annual_drift = 0.15  # 15% annual return
    annual_vol = 0.65    # 65% annual volatility (BTC is volatile!)
    
    dt = 5 / (365 * 24 * 60)  # 5 minutes in years
    
    # Generate returns with GARCH-like volatility clustering
    np.random.seed(42)  # Reproducible results
    
    # Base volatility with clustering
    base_vol = np.random.normal(annual_vol, 0.1, total_bars)
    base_vol = np.abs(base_vol)
    
    # Add volatility spikes (market events)
    event_days = np.random.choice(days, size=days//10, replace=False)
    for event_day in event_days:
        start_idx = event_day * bars_per_day
        end_idx = start_idx + bars_per_day
        base_vol[start_idx:end_idx] *= 1.5  # 50% vol increase on event days
    
    # Calculate drift
    drift = (annual_drift - 0.5 * annual_vol**2) * dt
    diffusion = np.sqrt(dt) * base_vol * np.random.normal(0, 1, total_bars)
    
    # Generate price path with Geometric Brownian Motion
    # Ensure prices stay positive
    log_returns = drift + diffusion
    
    # Clip extreme returns to avoid negative prices
    log_returns = np.clip(log_returns, -0.10, 0.10)  # Max 10% move per bar
    
    log_prices = np.cumsum(log_returns)
    log_prices = np.insert(log_prices, 0, np.log(start_price))
    
    prices = np.exp(log_prices)
    
    # Ensure minimum price floor
    prices = np.maximum(prices, 10000)  # Minimum $10K for BTC
    
    # Generate OHLCV from price path
    bars_per_candle = 1
    candles = []
    
    current_time = datetime.now() - timedelta(days=days)
    current_time = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
    
    time_delta = timedelta(minutes=5)
    
    for i in range(total_bars):
        open_price = prices[i]
        close_price = prices[i + 1] if i + 1 < len(prices) else prices[i]
        
        # Generate realistic high/low
        bar_volatility = base_vol[i] * np.sqrt(dt) * open_price * 2
        high_price = max(open_price, close_price) + np.random.exponential(bar_volatility)
        low_price = min(open_price, close_price) - np.random.exponential(bar_volatility)
        
        # Volume pattern (session-based)
        hour = current_time.hour
        if 0 <= hour < 7:
            volume_base = 500  # Asian session - low
        elif 7 <= hour < 13:
            volume_base = 1000  # London - medium
        elif 13 <= hour < 17:
            volume_base = 1500  # NY/London overlap - high
        else:
            volume_base = 800  # Evening - medium-low
        
        # Add noise
        volume = volume_base * np.random.lognormal(0, 0.3)
        
        candles.append({
            'time': current_time,
            'open': round(open_price, 2),
            'high': round(high_price, 2),
            'low': round(low_price, 2),
            'close': round(close_price, 2),
            'volume': round(volume, 0)
        })
        
        current_time += time_delta
    
    df = pd.DataFrame(candles)
    
    logger.info(f"✅ Generated {len(df)} M5 candles")
    logger.info(f"   Period: {df['time'].iloc[0]} to {df['time'].iloc[-1]}")
    logger.info(f"   Price range: ${df['low'].min():,.2f} - ${df['high'].max():,.2f}")
    logger.info(f"   Avg volume: {df['volume'].mean():,.0f}")
    
    return df


async def run_quick_backtest():
    """Run backtest with synthetic data"""
    
    setup_logging()
    
    logger.info("\n" + "="*80)
    logger.info("🚀 FOREX QUANTUM BOT - QUICK BACKTEST")
    logger.info("   Using realistic synthetic BTCUSD data")
    logger.info("="*80 + "\n")
    
    # 1. Load configuration
    logger.info("⚙️ Step 1: Loading configuration...")
    config_manager = ConfigManager()
    dna = config_manager.load_dna()
    logger.info("✅ Configuration loaded\n")
    
    # 2. Generate synthetic data
    logger.info("📊 Step 2: Generating realistic BTCUSD data...")
    candles = generate_realistic_btcusd_data(days=180)
    logger.info("")
    
    # 3. Configure backtest
    logger.info("⚙️ Step 3: Configuring backtest...")
    
    backtest_config = BacktestConfig(
        initial_capital=100000.0,
        symbol="BTCUSD",
        timeframe="M5",
        risk_percent=0.5,
        min_rr_ratio=1.5,
        max_positions=1,
        commission_per_lot=45.0,  # FTMO
        spread_points=100.0,
        slippage_points=10.0,
        ftmo_daily_loss_limit=5.0,
        ftmo_total_loss_limit=10.0,
        ftmo_min_trading_days=10,
        verbose=True
    )
    
    logger.info(f"   Capital: ${backtest_config.initial_capital:,.2f}")
    logger.info(f"   Commission: ${backtest_config.commission_per_lot}/lot/side")
    logger.info(f"   Spread: {backtest_config.spread_points} points")
    logger.info(f"   Slippage: {backtest_config.slippage_points} points\n")
    
    # 4. Run backtest
    logger.info("🚀 Step 4: Running backtest...\n")
    engine = BacktestEngine(config=backtest_config, dna_params=dna)
    
    results = engine.run(candles)
    
    if 'error' in results:
        logger.error(f"❌ Backtest error: {results['error']}")
        return
    
    # 5. Print summary
    logger.info("\n" + "="*80)
    logger.info("📊 BACKTEST RESULTS")
    logger.info("="*80)
    
    summary = results.get('summary', {})
    risk_metrics = results.get('risk', {})
    costs = results.get('costs', {})
    ftmo = results.get('ftmo', {})
    
    logger.info(f"\n💰 PERFORMANCE:")
    logger.info(f"   Initial Capital: ${backtest_config.initial_capital:,.2f}")
    logger.info(f"   Final Capital: ${summary.get('final_capital', 0):,.2f}")
    logger.info(f"   Net Profit: ${summary.get('net_profit', 0):,.2f} ({summary.get('net_profit_percent', 0):.2f}%)")
    logger.info(f"   Total Trades: {summary.get('total_trades', 0)}")
    logger.info(f"   Win Rate: {summary.get('win_rate', 0)*100:.1f}%")
    logger.info(f"   Profit Factor: {summary.get('profit_factor', 0):.2f}")
    logger.info(f"   Sharpe Ratio: {summary.get('sharpe_ratio', 0):.2f}")
    logger.info(f"   Expectancy: ${summary.get('expectancy', 0):.2f}/trade")
    
    logger.info(f"\n⚠️ RISK:")
    logger.info(f"   Max Drawdown: {risk_metrics.get('max_drawdown_percent', 0):.2f}% (${risk_metrics.get('max_drawdown_dollars', 0):,.2f})")
    logger.info(f"   Recovery Factor: {risk_metrics.get('recovery_factor', 0):.2f}")
    logger.info(f"   Max Consecutive Wins: {risk_metrics.get('consecutive_wins_max', 0)}")
    logger.info(f"   Max Consecutive Losses: {risk_metrics.get('consecutive_losses_max', 0)}")
    logger.info(f"   Avg Trade Duration: {risk_metrics.get('avg_trade_duration_minutes', 0):.0f} min")
    
    logger.info(f"\n💸 COSTS (FTMO REALISTIC):")
    logger.info(f"   Total Commissions: ${costs.get('total_commissions', 0):,.2f}")
    logger.info(f"   Total Spread Costs: ${costs.get('total_spread_costs', 0):,.2f}")
    logger.info(f"   Total Slippage: ${costs.get('total_slippage_costs', 0):,.2f}")
    logger.info(f"   TOTAL COSTS: ${costs.get('total_costs', 0):,.2f}")
    logger.info(f"   Costs as % of Gross: {costs.get('costs_as_percent_of_gross', 0):.1f}%")
    
    logger.info(f"\n🎯 FTMO COMPLIANCE:")
    logger.info(f"   Daily Loss Limit (5%): {'✅ PASS' if ftmo.get('daily_loss_limit_pass') else '❌ FAIL'} ({ftmo.get('max_daily_loss_percent', 0):.2f}%)")
    logger.info(f"   Total Drawdown (10%): {'✅ PASS' if ftmo.get('total_drawdown_pass') else '❌ FAIL'} ({risk_metrics.get('max_drawdown_percent', 0):.2f}%)")
    logger.info(f"   Min Trading Days (10): {'✅ PASS' if ftmo.get('min_trading_days_pass') else '❌ FAIL'} ({ftmo.get('trading_days_count', 0)} days)")
    logger.info(f"   Consistency Rule: {'✅ PASS' if ftmo.get('consistency_rule_pass') else '❌ FAIL'}")
    logger.info(f"\n   {'✅✅✅ WOULD PASS FTMO CHALLENGE! ✅✅✅' if ftmo.get('overall_pass') else '❌ WOULD NOT PASS FTMO CHALLENGE'}")
    
    # 6. Generate HTML report
    logger.info("\n" + "="*80)
    logger.info("📄 Step 5: Generating interactive HTML report...")
    
    report_gen = ReportGenerator()
    report_path = report_gen.generate_report(results)
    
    logger.info(f"✅ Report saved: {report_path}")
    logger.info(f"💡 Open in browser: file:///{report_path}\n")
    
    # 7. Update DNA memory
    logger.info("🧠 Step 6: Updating DNA memory...")
    dna_memory = config_manager.load_dna_memory()
    
    dna_memory['backtest_results'] = {
        'last_run': datetime.now().isoformat(),
        'data_type': 'synthetic_realistic',
        'days': 180,
        'net_profit': summary.get('net_profit', 0),
        'win_rate': summary.get('win_rate', 0),
        'profit_factor': summary.get('profit_factor', 0),
        'max_drawdown': risk_metrics.get('max_drawdown_percent', 0),
        'ftmo_pass': ftmo.get('overall_pass', False),
        'total_trades': summary.get('total_trades', 0),
    }
    
    config_manager.save_dna_memory(dna_memory)
    logger.info("✅ DNA memory updated\n")
    
    logger.info("="*80)
    logger.info("✅ QUICK BACKTEST COMPLETE")
    logger.info("="*80)
    logger.info(f"\n📊 Summary:")
    logger.info(f"   Net Profit: ${summary.get('net_profit', 0):,.2f}")
    logger.info(f"   Win Rate: {summary.get('win_rate', 0)*100:.1f}%")
    logger.info(f"   Profit Factor: {summary.get('profit_factor', 0):.2f}")
    logger.info(f"   FTMO: {'✅ PASS' if ftmo.get('overall_pass') else '❌ FAIL'}")
    logger.info(f"   Costs Impact: {costs.get('costs_as_percent_of_gross', 0):.1f}% of gross")
    logger.info(f"\n🌐 Open HTML report in browser for interactive charts!")
    logger.info("="*80 + "\n")


def main():
    """Entry point"""
    import asyncio
    try:
        asyncio.run(run_quick_backtest())
    except KeyboardInterrupt:
        logger.warning("\n⚠️ Backtest interrupted")
    except Exception as e:
        logger.error(f"\n❌ Backtest failed: {e}", exc_info=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
