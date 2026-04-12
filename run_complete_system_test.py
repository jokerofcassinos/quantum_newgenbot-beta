"""
Complete System Test - MT5 + Telegram + Neural Analysis
CEO: Qwen Code | Created: 2026-04-11

Tests EVERYTHING:
1. MT5 Connection
2. Real Market Data
3. Neural Analysis (Profiles + Strategies + Coherence + DNA)
4. Telegram Notifications
5. System Health
"""

import sys
from pathlib import Path
import asyncio
import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timezone
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
from src.monitoring.telegram_full import TelegramFullNotifier as TelegramNotifier


def print_header(title: str):
    print("\n" + "="*80)
    print(f"🧠 {title}")
    print("="*80)


async def test_mt5():
    """Test 1: MT5 Connection & Data"""
    print_header("TEST 1: MT5 CONNECTION")
    
    if not mt5.initialize():
        print(f"❌ MT5 init failed: {mt5.last_error()}")
        return None, None
    
    account = mt5.account_info()
    if not account:
        print("❌ No account info")
        return None, None
    
    print(f"✅ Connected to MT5")
    print(f"   Account: {account.login}")
    print(f"   Balance: ${account.balance:,.2f}")
    print(f"   Equity: ${account.equity:,.2f}")
    print(f"   Server: {account.server}")
    print(f"   Leverage: 1:{account.leverage}")
    
    # Test BTCUSD
    if not mt5.symbol_select("BTCUSD", True):
        print("❌ BTCUSD not available")
        return None, None
    
    symbol_info = mt5.symbol_info("BTCUSD")
    print(f"📊 BTCUSD:")
    print(f"   Spread: {symbol_info.spread} points")
    print(f"   Min/Max Lot: {symbol_info.volume_min} - {symbol_info.volume_max}")
    
    # Get candles
    rates = mt5.copy_rates_from_pos("BTCUSD", mt5.TIMEFRAME_M5, 0, 200)
    if rates is None or len(rates) < 100:
        print("❌ Insufficient candle data")
        return None, None
    
    candles = pd.DataFrame(rates)
    candles['time'] = pd.to_datetime(candles['time'], unit='s')
    
    print(f"📈 Retrieved {len(candles)} M5 candles")
    print(f"   Range: ${candles['close'].min():,.2f} - ${candles['close'].max():,.2f}")
    print(f"   Current: ${candles['close'].iloc[-1]:,.2f}")
    
    return account, candles


def test_telegram():
    """Test 2: Telegram Connection"""
    print_header("TEST 2: TELEGRAM NOTIFICATIONS")
    
    notifier = TelegramNotifier()
    
    if not notifier.enabled:
        print("❌ Telegram not configured")
        print("   Make sure config/telegram-config.json exists with bot_token and chat_id")
        return None
    
    print("✅ Telegram configured")
    print(f"   Sending test message...")
    
    # Send test message
    success = notifier.send_message("""
🧠 <b>SYSTEM TEST</b>
━━━━━━━━━━━━━━━━━━━━
✅ Telegram connection successful!

🤖 Forex Quantum Bot is alive
⏰ Test message sent

This confirms your Telegram integration is working!
""")
    
    if success:
        print("✅ Test message sent successfully!")
        print("   Check your Telegram!")
        return notifier
    else:
        print("❌ Failed to send test message")
        return None


async def test_neural_analysis(candles):
    """Test 3: Complete Neural Analysis"""
    print_header("TEST 3: NEURAL ANALYSIS")
    
    config = ConfigManager()
    dna_params = config.load_dna()
    
    # Initialize all systems
    profiler = NeuralRegimeProfiler(dna_params=dna_params)
    orchestrator = StrategyOrchestrator(dna_params=dna_params)
    coherence = CoherenceEngine(dna_params=dna_params)
    realtime_dna = RealTimeDNAEngine(initial_dna=dna_params)
    
    current_price = candles['close'].iloc[-1]
    recent = candles.iloc[-100:]
    
    print(f"📊 Analyzing BTCUSD @ ${current_price:,.2f}")
    print()
    
    # 1. Profile Selection
    print("🎯 Selecting Neural Profile...")
    market_state = {'price': current_price, 'volatility': recent['close'].std()}
    profile = profiler.select_best_profile(recent, market_state)
    print(f"   Profile: {profile.name.value.upper()}")
    print(f"   Regime: {profiler.current_regime}")
    print(f"   Confidence: {profile.confidence:.2f}")
    
    # 2. Strategy Orchestration
    print("\n🎭 Running Strategy Orchestration...")
    orchestration = orchestrator.orchestrate(
        candles=recent,
        current_price=current_price,
        regime=profiler.current_regime,
    )
    print(f"   Direction: {orchestration.final_direction}")
    print(f"   Consensus: {orchestration.weighted_consensus:+.2f}")
    print(f"   Coherence: {orchestration.coherence:.2f}")
    print(f"   Buy: {orchestration.total_buy_votes:.2f} | Sell: {orchestration.total_sell_votes:.2f}")
    
    # 3. Coherence Analysis
    print("\n🔬 Running Coherence Analysis...")
    risk_ctx = {'consecutive_losses': 0, 'current_drawdown': 0}
    coherence_result = coherence.analyze(
        orchestration_result=orchestration,
        candles=recent,
        regime=profiler.current_regime,
        profile=profile,
        risk_context=risk_ctx,
    )
    print(f"   Overall Coherence: {coherence_result.overall_coherence:.2f}")
    print(f"   Should Trade: {'✅ YES' if coherence_result.should_trade else '❌ NO'}")
    print(f"   Action: {coherence_result.recommended_action.upper()}")
    
    # 4. DNA Transmutation
    print("\n🧬 Running DNA Transmutation...")
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
    print(f"   Mutations Applied: {len(mutations)}")
    if mutations:
        for m in mutations[:3]:
            print(f"   → {m.parameter}: {m.old_value:.3f} → {m.new_value:.3f}")
    
    return {
        'profile': profile.name.value,
        'regime': profiler.current_regime,
        'direction': orchestration.final_direction,
        'consensus': orchestration.weighted_consensus,
        'coherence': coherence_result.overall_coherence,
        'should_trade': coherence_result.should_trade,
        'mutations': len(mutations),
        'signals': len(orchestration.signals),
    }


def send_telegram_summary(notifier, analysis_results, account):
    """Send comprehensive summary to Telegram"""
    print_header("SENDING TELEGRAM SUMMARY")
    
    if not notifier:
        print("⏭️ Skipping Telegram (not configured)")
        return
    
    emoji = "🟢" if analysis_results['should_trade'] else "⏸️"
    direction = analysis_results['direction']
    
    message = f"""
{emoji} <b>LIVE MARKET ANALYSIS</b>
━━━━━━━━━━━━━━━━━━━━
📊 <b>BTCUSD @ ${analysis_results.get('current_price', 0):,.2f}</b>

🎯 Profile: <b>{analysis_results['profile'].upper()}</b>
📊 Regime: {analysis_results['regime']}
🎭 Direction: <b>{direction}</b>
📈 Consensus: {analysis_results['consensus']:+.2f}
🔬 Coherence: {analysis_results['coherence']:.2f}

━━━━━━━━━━━━━━━━━━━━
💰 Account: {account.login}
💵 Balance: ${account.balance:,.2f}
📊 Equity: ${account.equity:,.2f}

━━━━━━━━━━━━━━━━━━━━
🧬 DNA Mutations: {analysis_results['mutations']}
📊 Strategy Signals: {analysis_results['signals']}

━━━━━━━━━━━━━━━━━━━━
{analysis_results['verdict']}

⏰ {datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}
"""
    
    success = notifier.send_message(message.strip())
    if success:
        print("✅ Summary sent to Telegram!")
    else:
        print("❌ Failed to send summary")


async def main():
    """Run complete system test"""
    print("\n" + "="*80)
    print("🧠 FOREX QUANTUM BOT - COMPLETE SYSTEM TEST")
    print("   Testing: MT5 + Telegram + Neural Analysis")
    print("="*80 + "\n")
    
    # Test 1: MT5
    account, candles = await test_mt5()
    if not account or candles is None:
        print("\n❌ MT5 test failed - aborting")
        return
    
    # Test 2: Telegram
    notifier = test_telegram()
    
    # Test 3: Neural Analysis
    analysis_results = await test_neural_analysis(candles)
    analysis_results['current_price'] = candles['close'].iloc[-1]
    
    # Final verdict
    if analysis_results['should_trade']:
        analysis_results['verdict'] = "✅ TRADE SIGNAL DETECTED - Monitor for execution"
    else:
        analysis_results['verdict'] = "⏸️ NO TRADE - Waiting for better conditions"
    
    # Test 4: Send Telegram Summary
    send_telegram_summary(notifier, analysis_results, account)
    
    # Cleanup
    mt5.shutdown()
    
    print("\n" + "="*80)
    print("✅ ALL TESTS COMPLETE")
    print("="*80)
    print(f"\n📊 Results:")
    print(f"   MT5: ✅ Connected")
    print(f"   Telegram: {'✅ Working' if notifier else '❌ Not configured'}")
    print(f"   Neural Analysis: ✅ Complete")
    print(f"   Profile: {analysis_results['profile'].upper()}")
    print(f"   Regime: {analysis_results['regime']}")
    print(f"   Direction: {analysis_results['direction']}")
    print(f"   Should Trade: {'✅ YES' if analysis_results['should_trade'] else '❌ NO'}")
    print(f"   DNA Mutations: {analysis_results['mutations']}")
    print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️ Test interrupted")
    except Exception as e:
        print(f"\n\n❌ Test error: {e}")
        import traceback
        traceback.print_exc()
