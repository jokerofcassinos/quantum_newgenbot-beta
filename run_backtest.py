"""
Main Backtesting Script - Execute backtests and generate reports
CEO: Qwen Code | Created: 2026-04-10

Usage:
    python run_backtest.py
    
This will:
1. Load historical BTCUSD data from MT5
2. Synthesize all timeframes (M1 reconstruction)
3. Run backtest with realistic costs
4. Generate interactive HTML report
5. Save results and DNA memory updates
"""

import sys
from pathlib import Path
import asyncio
from datetime import datetime, timezone, timedelta
import json

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import MetaTrader5 as mt5
import pandas as pd
from loguru import logger

from src.core.config_manager import ConfigManager
from src.backtesting.timeframe_synthesizer import TimeframeSynthesizer
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
    logger.add(
        "logs/backtest_{time:YYYY-MM-DD}.log",
        rotation="00:00",
        retention="30 days",
        level="DEBUG"
    )


async def load_historical_data(days_back: int = 180) -> dict:
    """
    Load historical data from MT5 for multiple timeframes
    
    Args:
        days_back: How many days of history to load
    
    Returns:
        dict: Dataframes for each timeframe
    """
    logger.info("="*80)
    logger.info("📥 LOADING HISTORICAL DATA FROM MT5")
    logger.info("="*80)
    
    # Initialize MT5
    if not mt5.initialize():
        logger.error(f"❌ MT5 initialization failed: {mt5.last_error()}")
        return {}
    
    symbol = "BTCUSD"
    start_date = datetime.now() - timedelta(days=days_back)
    
    data = {}
    
    # Load M5 data (primary timeframe)
    logger.info(f"📊 Loading M5 data from {start_date.strftime('%Y-%m-%d')}...")
    
    tf_map = {
        'M5': mt5.TIMEFRAME_M5,
        'M15': mt5.TIMEFRAME_M15,
        'H1': mt5.TIMEFRAME_H1,
        'H4': mt5.TIMEFRAME_H4,
        'D1': mt5.TIMEFRAME_D1,
    }
    
    for tf_name, tf_const in tf_map.items():
        logger.info(f"   Loading {tf_name}...")
        rates = mt5.copy_rates_from(symbol, tf_const, start_date, 100000)
        
        if rates is not None and len(rates) > 0:
            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            data[tf_name] = df
            logger.info(f"   ✅ {tf_name}: {len(df)} candles loaded")
        else:
            logger.warning(f"   ⚠️ {tf_name}: No data available")
    
    mt5.shutdown()
    
    return data


async def run_backtest():
    """Main backtest execution"""
    
    setup_logging()
    
    logger.info("\n" + "="*80)
    logger.info("🚀 FOREX QUANTUM BOT - BACKTESTING SYSTEM")
    logger.info("="*80)
    logger.info("💡 This will run a complete backtest with realistic FTMO costs")
    logger.info("="*80 + "\n")
    
    # 1. Load configuration
    logger.info("⚙️ Step 1: Loading configuration...")
    config_manager = ConfigManager()
    dna = config_manager.load_dna()
    limits = config_manager.load_absolute_limits()
    logger.info("✅ Configuration loaded\n")
    
    # 2. Load historical data
    logger.info("📥 Step 2: Loading historical data...")
    historical_data = await load_historical_data(days_back=180)
    
    if not historical_data or 'M5' not in historical_data:
        logger.error("❌ No historical data available!")
        logger.info("\n💡 TIP: Make sure MT5 is installed and BTCUSD is available")
        return
    
    m5_data = historical_data['M5']
    logger.info(f"✅ Loaded {len(m5_data)} M5 candles\n")
    
    # 3. Synthesize missing timeframes
    logger.info("🔬 Step 3: Synthesizing timeframes...")
    synthesizer = TimeframeSynthesizer()
    
    all_timeframes = synthesizer.synthesize_all_timeframes(
        m5_candles=m5_data,
        h1_candles=historical_data.get('H1'),
        h4_candles=historical_data.get('H4')
    )
    
    m1_data = all_timeframes.get('M1', m5_data)
    logger.info(f"✅ Timeframe synthesis complete\n")
    
    # 4. Configure backtest
    logger.info("⚙️ Step 4: Configuring backtest...")
    
    backtest_config = BacktestConfig(
        initial_capital=100000.0,
        symbol="BTCUSD",
        timeframe="M5",
        risk_percent=0.5,
        min_rr_ratio=1.5,
        max_positions=1,
        commission_per_lot=45.0,  # FTMO: $45/lot/side
        spread_points=100.0,  # BTCUSD typical spread
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
    
    # 5. Run backtest
    logger.info("🚀 Step 5: Running backtest...")
    engine = BacktestEngine(config=backtest_config, dna_params=dna)
    
    results = engine.run(m5_data)
    
    if 'error' in results:
        logger.error(f"❌ Backtest error: {results['error']}")
        return
    
    # 6. Print summary
    logger.info("\n" + "="*80)
    logger.info("📊 BACKTEST RESULTS SUMMARY")
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
    
    logger.info(f"\n⚠️ RISK:")
    logger.info(f"   Max Drawdown: {risk_metrics.get('max_drawdown_percent', 0):.2f}%")
    logger.info(f"   Recovery Factor: {risk_metrics.get('recovery_factor', 0):.2f}")
    logger.info(f"   Max Consecutive Wins: {risk_metrics.get('consecutive_wins_max', 0)}")
    logger.info(f"   Max Consecutive Losses: {risk_metrics.get('consecutive_losses_max', 0)}")
    
    logger.info(f"\n💸 COSTS (FTMO REALISTIC):")
    logger.info(f"   Total Commissions: ${costs.get('total_commissions', 0):,.2f}")
    logger.info(f"   Total Spread Costs: ${costs.get('total_spread_costs', 0):,.2f}")
    logger.info(f"   Total Slippage: ${costs.get('total_slippage_costs', 0):,.2f}")
    logger.info(f"   TOTAL COSTS: ${costs.get('total_costs', 0):,.2f}")
    logger.info(f"   Costs as % of Gross: {costs.get('costs_as_percent_of_gross', 0):.1f}%")
    
    logger.info(f"\n🎯 FTMO COMPLIANCE:")
    logger.info(f"   Daily Loss Limit: {'✅ PASS' if ftmo.get('daily_loss_limit_pass') else '❌ FAIL'}")
    logger.info(f"   Total Drawdown: {'✅ PASS' if ftmo.get('total_drawdown_pass') else '❌ FAIL'}")
    logger.info(f"   Min Trading Days: {'✅ PASS' if ftmo.get('min_trading_days_pass') else '❌ FAIL'} ({ftmo.get('trading_days_count', 0)} days)")
    logger.info(f"   Consistency Rule: {'✅ PASS' if ftmo.get('consistency_rule_pass') else '❌ FAIL'}")
    logger.info(f"   OVERALL: {'✅ WOULD PASS FTMO' if ftmo.get('overall_pass') else '❌ WOULD NOT PASS'}")
    
    # 7. Generate HTML report
    logger.info("\n" + "="*80)
    logger.info("📄 Step 6: Generating interactive HTML report...")
    
    report_gen = ReportGenerator()
    report_path = report_gen.generate_report(results)
    
    logger.info(f"✅ Report saved: {report_path}")
    logger.info(f"💡 Open in browser to view interactive charts\n")
    
    # 8. Save DNA memory updates
    logger.info("🧠 Step 7: Updating DNA memory...")
    
    # Extract regime performance
    dna_memory = config_manager.load_dna_memory()
    
    if 'regimes' not in dna_memory:
        dna_memory['regimes'] = {}
    
    # Add backtest results to memory
    dna_memory['backtest_results'] = {
        'last_run': datetime.now(timezone.utc).isoformat(),
        'net_profit': summary.get('net_profit', 0),
        'win_rate': summary.get('win_rate', 0),
        'profit_factor': summary.get('profit_factor', 0),
        'max_drawdown': risk_metrics.get('max_drawdown_percent', 0),
        'ftmo_pass': ftmo.get('overall_pass', False),
        'total_trades': summary.get('total_trades', 0),
    }
    
    config_manager.save_dna_memory(dna_memory)
    logger.info("✅ DNA memory updated\n")
    
    # 9. Save detailed results
    results_path = Path("data/backtest-results/backtest_results.json")
    results_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Convert datetime objects to strings for JSON serialization
    serializable_results = json.loads(json.dumps(results, default=str))
    
    with open(results_path, 'w') as f:
        json.dump(serializable_results, f, indent=2)
    
    logger.info(f"💾 Detailed results saved: {results_path}")
    
    logger.info("\n" + "="*80)
    logger.info("✅ BACKTEST COMPLETE")
    logger.info("="*80)
    logger.info(f"\n📊 Key Takeaways:")
    logger.info(f"   - Net Profit: ${summary.get('net_profit', 0):,.2f}")
    logger.info(f"   - Win Rate: {summary.get('win_rate', 0)*100:.1f}%")
    logger.info(f"   - FTMO: {'✅ PASS' if ftmo.get('overall_pass') else '❌ FAIL'}")
    logger.info(f"   - Costs Impact: {costs.get('costs_as_percent_of_gross', 0):.1f}% of gross profit")
    logger.info(f"\n🌐 Open the HTML report in your browser for interactive charts!")
    logger.info(f"   File: {report_path}")
    logger.info("="*80 + "\n")


def main():
    """Entry point"""
    try:
        asyncio.run(run_backtest())
    except KeyboardInterrupt:
        logger.warning("\n⚠️ Backtest interrupted by user")
    except Exception as e:
        logger.error(f"\n❌ Backtest failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
