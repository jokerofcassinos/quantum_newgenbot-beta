"""
Quick Test: Signal Generator → MQL5 EA Integration
CEO: Qwen Code | Created: 2026-04-12

Tests the complete pipeline:
1. Python generates signal
2. Writes to CSV
3. Verify CSV format for MQL5 EA
4. Show expected EA behavior
"""

import sys
from pathlib import Path
import asyncio
import csv
from datetime import datetime, timezone
from loguru import logger

# Add project root
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import systems
from src.core.config_manager import ConfigManager
from src.execution.mt5.market_data import MarketDataFetcher
from src.strategies.neural_regime_profiles import NeuralRegimeProfiler
from src.strategies.strategy_orchestrator import StrategyOrchestrator
from src.strategies.coherence_engine import CoherenceEngine
from src.dna.realtime_dna import RealTimeDNAEngine

# C++ Integration
cpp_path = project_root / "cpp-quantum-systems" / "python_integration"
sys.path.insert(0, str(cpp_path))
from quantum_trading import QuantumTradingSystems


async def main():
    print("\n" + "="*80)
    print("🧪 MQL5 EA INTEGRATION TEST - Signal Generation")
    print("="*80 + "\n")
    
    # Create signal directory
    signal_dir = project_root / "data" / "signals"
    signal_dir.mkdir(parents=True, exist_ok=True)
    signal_file = str(signal_dir / "trade_signal.csv")
    
    print("📁 Signal file path:")
    print(f"   {signal_file}\n")
    
    # Initialize systems
    print("🔧 Initializing systems...")
    
    import MetaTrader5 as mt5
    if not mt5.initialize():
        print(f"❌ MT5 init failed")
        return
    
    account = mt5.account_info()
    if account:
        print(f"✅ MT5: {account.login} | Balance: ${account.balance:,.2f}")
    
    market_data = MarketDataFetcher(config=ConfigManager())
    config = ConfigManager()
    dna_params = config.load_dna()
    
    neural_profiler = NeuralRegimeProfiler(dna_params=dna_params)
    strategy_orchestrator = StrategyOrchestrator(dna_params=dna_params)
    coherence_engine = CoherenceEngine(dna_params=dna_params)
    realtime_dna = RealTimeDNAEngine(initial_dna=dna_params)
    quantum_systems = QuantumTradingSystems()
    
    print("✅ All systems initialized\n")
    
    # Generate signal
    print("🔬 Generating trading signal...\n")
    
    # Get market data
    candles = await market_data.get_candles(timeframe="M5", count=200)
    if candles is None or len(candles) < 100:
        print("❌ Insufficient data")
        return
    
    current_price = candles['close'].iloc[-1]
    volatility = candles['close'].pct_change().std() * (252 * 288) ** 0.5
    
    print(f"📊 Market: ${current_price:,.2f} | Vol: {volatility*100:.1f}%\n")
    
    # C++ Quantum Analysis
    print("🧬 Step 1: C++ Quantum Analysis")
    quantum_results = quantum_systems.run_complete_analysis(
        spot_price=current_price,
        volatility=volatility
    )
    print(f"   Monte Carlo Mean: ${quantum_results['monte_carlo']['mean_price']:,.2f}")
    print(f"   Quantum Predicted: ${quantum_results['quantum_prediction']['predicted_price']:,.2f}\n")
    
    # Python Neural Analysis
    print("🧠 Step 2: Python Neural Analysis")
    recent = candles.iloc[-100:]
    
    market_state = {'price': current_price, 'volatility': candles['close'].std()}
    profile = neural_profiler.select_best_profile(recent, market_state)
    print(f"   Profile: {profile.name.value}")
    print(f"   Regime: {neural_profiler.current_regime}")
    
    orchestration = strategy_orchestrator.orchestrate(
        candles=recent,
        current_price=current_price,
        regime=neural_profiler.current_regime,
    )
    print(f"   Direction: {orchestration.final_direction}")
    print(f"   Consensus: {orchestration.weighted_consensus:+.2f}\n")
    
    # Coherence
    print("🔬 Step 3: Coherence Analysis")
    risk_ctx = {'consecutive_losses': 0, 'current_drawdown': 0}
    coherence_result = coherence_engine.analyze(
        orchestration_result=orchestration,
        candles=recent,
        regime=neural_profiler.current_regime,
        profile=profile,
        risk_context=risk_ctx,
    )
    print(f"   Overall Coherence: {coherence_result.overall_coherence:.2f}")
    print(f"   Should Trade: {'✅ YES' if coherence_result.should_trade else '❌ NO'}\n")
    
    # Create signal
    print("📝 Step 4: Creating Signal")
    
    # Collect signals
    signals = []
    
    if quantum_results['quantum_prediction']['predicted_price'] > quantum_results['monte_carlo']['mean_price']:
        signals.append(('BUY', quantum_results['quantum_prediction']['quantum_advantage']))
    else:
        signals.append(('SELL', quantum_results['quantum_prediction']['quantum_advantage']))
    
    if orchestration.final_direction in ['BUY', 'SELL']:
        signals.append((orchestration.final_direction, abs(orchestration.weighted_consensus)))
    
    if coherence_result.should_trade:
        if coherence_result.recommended_action in ['buy', 'strong_buy']:
            signals.append(('BUY', coherence_result.overall_coherence))
        elif coherence_result.recommended_action in ['sell', 'strong_sell']:
            signals.append(('SELL', coherence_result.overall_coherence))
    
    if len(signals) == 0:
        print("⏸️ No clear signals")
        print("\n✅ TEST COMPLETE - System working, no signals at this time")
        mt5.shutdown()
        return
    
    # Weighted vote
    buy_weight = sum(w for d, w in signals if d == 'BUY')
    sell_weight = sum(w for d, w in signals if d == 'SELL')
    total = buy_weight + sell_weight
    
    if buy_weight > sell_weight:
        direction = 'BUY'
        confidence = buy_weight / total
    elif sell_weight > buy_weight:
        direction = 'SELL'
        confidence = sell_weight / total
    else:
        print("⏸️ Neutral signal")
        mt5.shutdown()
        return
    
    # Calculate SL/TP
    if direction == 'BUY':
        sl = current_price - 300
        tp = current_price + 600
    else:
        sl = current_price + 300
        tp = current_price - 600
    
    signal = {
        'timestamp': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
        'direction': direction,
        'confidence': confidence,
        'entry_price': current_price,
        'stop_loss': sl,
        'take_profit': tp,
        'profile': profile.name.value,
        'regime': neural_profiler.current_regime,
        'signal_count': len(signals),
        'volatility': volatility,
    }
    
    # Write CSV
    print(f"   Direction: {signal['direction']}")
    print(f"   Confidence: {signal['confidence']:.2f}")
    print(f"   Entry: ${signal['entry_price']:,.2f}")
    print(f"   SL: ${signal['stop_loss']:,.2f}")
    print(f"   TP: ${signal['take_profit']:,.2f}")
    print(f"   R:R: 1:2.0")
    print(f"   Signals: {signal['signal_count']}\n")
    
    # Write to CSV
    with open(signal_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            signal['timestamp'],
            signal['direction'],
            f"{signal['confidence']:.2f}",
            f"{signal['entry_price']:.2f}",
            f"{signal['stop_loss']:.2f}",
            f"{signal['take_profit']:.2f}",
            signal['profile'],
            signal['regime'],
        ])
    
    print(f"💾 Signal written to: {signal_file}\n")
    
    # Verify CSV format
    print("🔍 Step 5: Verifying CSV format for MQL5 EA")
    with open(signal_file, 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            print(f"   {row}")
    
    print("\n" + "="*80)
    print("✅ INTEGRATION TEST COMPLETE")
    print("="*80)
    print("\n📋 What to do next:")
    print("   1. Copy ForexQuantumBot_EA.mq5 to MT5 Experts folder")
    print("   2. Compile in MetaEditor (F7)")
    print("   3. Attach EA to BTCUSD M5 chart")
    print("   4. Set InpAutoTrade = false (test mode)")
    print("   5. EA will read signals from CSV and log them")
    print("\n📊 Signal file location:")
    print(f"   {signal_file}")
    print("\n⏰ Signal generated at:")
    print(f"   {signal['timestamp']} UTC")
    print("="*80 + "\n")
    
    mt5.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
