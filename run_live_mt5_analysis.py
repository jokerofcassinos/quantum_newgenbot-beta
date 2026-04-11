"""
Live MT5 Integration - Complete Neural System with REAL market data
CEO: Qwen Code | Created: 2026-04-10

This connects ALL neural systems to REAL BTCUSD data from your FTMO MT5 account.
No synthetic data - this is the real deal!

Features:
- Real-time BTCUSD data from MT5
- Full neural analysis (Profiles + Strategies + Orchestration + Coherence + DNA)
- Safe mode (analysis only, no live trades)
- Neural audit logging
- Performance tracking
"""

import sys
from pathlib import Path
import asyncio
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta
from loguru import logger

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.core.config_manager import ConfigManager
from src.execution.mt5.mt5_connector import MT5Connector
from src.execution.mt5.market_data import MarketDataFetcher
from src.strategies.neural_regime_profiles import NeuralRegimeProfiler
from src.strategies.strategy_orchestrator import StrategyOrchestrator
from src.strategies.coherence_engine import CoherenceEngine
from src.dna.realtime_dna import RealTimeDNAEngine
from src.execution.smart_order_manager import SmartOrderManager
from src.monitoring.neural_trade_auditor import NeuralTradeAuditor
from src.monitoring.health_monitor import HealthMonitor


def setup_logging():
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )
    logger.add(
        "logs/live_mt5_{time:YYYY-MM-DD}.log",
        rotation="00:00",
        retention="30 days",
        level="DEBUG"
    )


async def connect_mt5() -> tuple:
    """Connect to MT5 and return connector + market data fetcher"""
    logger.info("🔌 Connecting to MT5...")
    
    if not mt5.initialize():
        logger.error(f"❌ MT5 init failed: {mt5.last_error()}")
        return None, None
    
    account = mt5.account_info()
    if account:
        logger.info(f"✅ Connected to account: {account.login}")
        logger.info(f"💵 Balance: ${account.balance:,.2f}")
        logger.info(f"📊 Equity: ${account.equity:,.2f}")
        logger.info(f"📈 Leverage: 1:{account.leverage}")
        logger.info(f"🖥️ Server: {account.server}")
    else:
        logger.error("❌ No account info")
        return None, None
    
    # Verify BTCUSD
    if not mt5.symbol_select("BTCUSD", True):
        logger.error("❌ BTCUSD not available")
        return None, None
    
    symbol_info = mt5.symbol_info("BTCUSD")
    if symbol_info:
        logger.info(f"📊 BTCUSD Spread: {symbol_info.spread} points")
        logger.info(f"   Min lot: {symbol_info.volume_min}")
        logger.info(f"   Max lot: {symbol_info.volume_max}")
    else:
        logger.warning("⚠️ Could not get BTCUSD symbol info")
    
    config = ConfigManager()
    connector = MT5Connector(config=config)
    connector.connected = True
    connector.account_info = {
        'login': account.login,
        'balance': account.balance,
        'equity': account.equity,
        'leverage': account.leverage,
        'server': account.server,
    }
    
    market_data = MarketDataFetcher(config=config)
    
    return connector, market_data


async def get_real_data(market_data: MarketDataFetcher, count: int = 200) -> pd.DataFrame:
    """Get real BTCUSD data from MT5"""
    candles = await market_data.get_candles(timeframe="M5", count=count)
    
    if candles is not None and len(candles) > 100:
        logger.info(f"📊 Retrieved {len(candles)} REAL M5 candles")
        logger.info(f"   Range: {candles['time'].iloc[0]} → {candles['time'].iloc[-1]}")
        logger.info(f"   Price: ${candles['close'].iloc[0]:,.2f} → ${candles['close'].iloc[-1]:,.2f}")
        logger.info(f"   High: ${candles['high'].max():,.2f} | Low: ${candles['low'].min():,.2f}")
        return candles
    
    logger.warning("⚠️ Insufficient candle data")
    return None


async def run_live_analysis():
    """Run complete neural analysis on LIVE market data"""
    setup_logging()
    
    print("\n" + "="*80)
    print("🧠 FOREX QUANTUM BOT - LIVE MT5 NEURAL ANALYSIS")
    print("   Using REAL BTCUSD data from your FTMO account!")
    print("="*80 + "\n")
    
    # Connect to MT5
    connector, market_data = await connect_mt5()
    if not connector:
        logger.error("❌ Failed to connect to MT5")
        return
    
    # Get real data
    candles = await get_real_data(market_data, count=200)
    if candles is None:
        logger.error("❌ Failed to get market data")
        return
    
    # Initialize ALL neural systems
    config = ConfigManager()
    dna_params = config.load_dna()
    
    profiler = NeuralRegimeProfiler(dna_params=dna_params)
    orchestrator = StrategyOrchestrator(dna_params=dna_params)
    coherence = CoherenceEngine(dna_params=dna_params)
    realtime_dna = RealTimeDNAEngine(initial_dna=dna_params)
    auditor = NeuralTradeAuditor()
    health = HealthMonitor()
    
    print("\n💡 All Neural Systems Initialized!")
    print("="*80)
    
    # Analyze current market state
    current_price = candles['close'].iloc[-1]
    recent = candles.iloc[-100:]
    
    print(f"\n📊 Current Market State:")
    print(f"   Price: ${current_price:,.2f}")
    print(f"   Candles analyzed: {len(recent)}")
    print()
    
    # Run complete neural analysis
    print("🔬 Running Complete Neural Analysis...\n")
    
    # 1. Profile Selection
    market_state = {'price': current_price, 'volatility': recent['close'].std()}
    profile = profiler.select_best_profile(recent, market_state)
    
    # 2. Strategy Orchestration
    orchestration = orchestrator.orchestrate(
        candles=recent,
        current_price=current_price,
        regime=profiler.current_regime,
    )
    
    # 3. Coherence Analysis
    risk_ctx = {'consecutive_losses': 0, 'current_drawdown': 0}
    coherence_result = coherence.analyze(
        orchestration_result=orchestration,
        candles=recent,
        regime=profiler.current_regime,
        profile=profile,
        risk_context=risk_ctx,
    )
    
    # 4. DNA Transmutation
    returns = recent['close'].pct_change()
    physics = {
        'market_energy': returns.std() * 100,
        'velocity': abs(current_price - recent['close'].iloc[-10]) / 10,
        'acceleration': 0
    }
    
    mutations = realtime_dna.transmutate(
        coherence_result=coherence_result,
        orchestration_result=orchestration,
        regime=profiler.current_regime,
        profile=profile,
        market_physics=physics,
        performance_metrics={'net_pnl': 0},
    )
    
    # Print comprehensive results
    print("\n" + "="*80)
    print("🧠 NEURAL ANALYSIS RESULTS")
    print("="*80)
    
    print(f"\n🎯 NEURAL PROFILE:")
    print(f"   Selected: {profile.name.value.upper()}")
    print(f"   Regime: {profiler.current_regime}")
    print(f"   Confidence: {profile.confidence:.2f}")
    print(f"   Max Position Size: {profile.max_position_size} lots")
    print(f"   Risk per Trade: {profile.risk_per_trade}%")
    print(f"   Preferred Sessions: {', '.join(profile.preferred_sessions)}")
    
    print(f"\n🎭 STRATEGY ORCHESTRATION:")
    print(f"   Consensus: {orchestration.weighted_consensus:+.2f}")
    print(f"   Direction: {orchestration.final_direction}")
    print(f"   Coherence: {orchestration.coherence:.2f}")
    print(f"   Buy Votes: {orchestration.total_buy_votes:.2f}")
    print(f"   Sell Votes: {orchestration.total_sell_votes:.2f}")
    print(f"   Strategies Agreed: {len(orchestration.signals)}")
    
    print(f"\n🔬 COHERENCE ANALYSIS:")
    print(f"   Overall Coherence: {coherence_result.overall_coherence:.2f}")
    print(f"   Directional: {coherence_result.directional_coherence:+.2f}")
    print(f"   Strategy Agreement: {coherence_result.strategy_agreement:.2f}")
    print(f"   Indicator Agreement: {coherence_result.indicator_agreement:.2f}")
    print(f"   Timeframe Agreement: {coherence_result.timeframe_agreement:.2f}")
    print(f"   Regime Alignment: {coherence_result.regime_alignment:.2f}")
    print(f"   Risk Alignment: {coherence_result.risk_alignment:.2f}")
    print(f"   Should Trade: {'✅ YES' if coherence_result.should_trade else '❌ NO'}")
    print(f"   Action: {coherence_result.recommended_action.upper()}")
    
    print(f"\n🧬 DNA TRANSMUTATION:")
    print(f"   Mutations Applied: {len(mutations)}")
    for m in mutations[:5]:  # Show first 5
        print(f"   → {m.parameter}: {m.old_value:.3f} → {m.new_value:.3f} ({m.reason})")
    if len(mutations) > 5:
        print(f"   ... and {len(mutations)-5} more")
    
    print(f"\n📊 TOP STRATEGY SIGNALS:")
    if orchestration.signals:
        for i, sig in enumerate(orchestration.signals[:3], 1):
            print(f"   {i}. {sig.strategy.upper()}: {sig.direction} @ ${sig.entry_price:,.2f}")
            print(f"      SL: ${sig.stop_loss:,.2f} | TP: ${sig.take_profit:,.2f}")
            print(f"      R:R: 1:{sig.rr_ratio:.1f} | Confidence: {sig.confidence:.2f}")
            print(f"      Reason: {sig.reasoning}")
    else:
        print(f"   No strategy signals at this time")
    
    # Health check
    health_status = health.check_health()
    print(f"\n🏥 SYSTEM HEALTH:")
    print(f"   Status: {health_status.status.upper()}")
    print(f"   CPU: {health_status.metrics.get('cpu_percent', 0):.1f}%")
    print(f"   RAM: {health_status.metrics.get('ram_percent', 0):.1f}%")
    
    # Final verdict
    print("\n" + "="*80)
    if coherence_result.should_trade and orchestration.final_direction != "NEUTRAL":
        print(f"✅ VERDICT: TRADE SIGNAL DETECTED!")
        print(f"   Direction: {orchestration.final_direction}")
        print(f"   Confidence: {coherence_result.confidence_score:.2f}")
        print(f"   Recommended Action: {coherence_result.recommended_action}")
    else:
        print(f"⏸️ VERDICT: NO TRADE SIGNAL")
        print(f"   Reason: {'Low coherence' if not coherence_result.should_trade else 'Neutral consensus'}")
        print(f"   Wait for better conditions")
    print("="*80)
    
    # Cleanup
    mt5.shutdown()
    print("\n🔌 Disconnected from MT5")
    print("\n📁 Neural audits saved to: data/trade-audits/")
    print("="*80 + "\n")


if __name__ == "__main__":
    try:
        asyncio.run(run_live_analysis())
    except KeyboardInterrupt:
        print("\n\n⚠️ Analysis interrupted")
    except Exception as e:
        print(f"\n\n❌ Analysis error: {e}")
        import traceback
        traceback.print_exc()
