"""
Signal Generator for MQL5 EA Integration
CEO: Qwen Code | Created: 2026-04-12

Generates trade signals from complete neural quantum analysis
and writes them to CSV file for MQL5 EA consumption.

This bridges Python (AI/Quantum) with MQL5 (Execution).
"""

import sys
from pathlib import Path
import asyncio
import time
import csv
from datetime import datetime, timezone
from loguru import logger

# Add project root
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import all systems
from src.core.config_manager import ConfigManager
from src.execution.mt5.mt5_connector import MT5Connector
from src.execution.mt5.market_data import MarketDataFetcher
from src.strategies.neural_regime_profiles import NeuralRegimeProfiler
from src.strategies.strategy_orchestrator import StrategyOrchestrator
from src.strategies.coherence_engine import CoherenceEngine
from src.dna.realtime_dna import RealTimeDNAEngine
from src.monitoring.telegram_full import TelegramNotifier

# C++ Integration
cpp_path = project_root / "cpp-quantum-systems" / "python_integration"
sys.path.insert(0, str(cpp_path))
from quantum_trading import QuantumTradingSystems


class SignalGenerator:
    """
    Generates trading signals for MQL5 EA
    
    Pipeline:
    1. Get real market data from MT5
    2. Run C++ Monte Carlo + Quantum analysis
    3. Run Python Neural analysis
    4. Generate signal with all confluences
    5. Write to CSV file for EA
    6. Send Telegram notification
    """
    
    def __init__(self, signal_file: str = None):
        # Use MT5 Common Files folder for EA-Python communication
        # MT5 Common Files is at: C:\Users\<user>\AppData\Roaming\MetaQuotes\Terminal\Common\Files\
        mt5_common_path = Path.home() / "AppData" / "Roaming" / "MetaQuotes" / "Terminal" / "Common" / "Files" / "quantum_signals"
        mt5_common_path.mkdir(parents=True, exist_ok=True)
        
        if signal_file is None:
            signal_file = str(mt5_common_path / "trade_signal.csv")
        
        self.signal_file = signal_file
        self.handshake_file = str(mt5_common_path / "connection.txt")
        self.mt5_common_path = str(mt5_common_path)
        self.last_signal_time = 0
        self.signal_interval = 300  # 5 minutes (matches M5 timeframe)
        self.running = False
        self.ea_connected = False
        
        # Performance tracking
        self.signals_generated = 0
        self.signals_executed = 0
        
        logger.info("="*80)
        logger.info("📡 SIGNAL GENERATOR INITIALIZING")
        logger.info("="*80)
        logger.info(f"   Signal file: {self.signal_file}")
        logger.info(f"   Handshake file: {self.handshake_file}")
        logger.info(f"   MT5 Common: {self.mt5_common_path}")
        
        # Initialize all systems
        self._initialize_systems()
    
    def _initialize_systems(self):
        """Initialize ALL trading systems"""
        import MetaTrader5 as mt5
        
        # 1. MT5 Connection
        logger.info("\n📡 Initializing MT5...")
        if not mt5.initialize():
            logger.error(f"❌ MT5 init failed: {mt5.last_error()}")
            raise Exception("MT5 initialization failed")
        
        account = mt5.account_info()
        if account:
            logger.info(f"✅ Connected: {account.login} | Balance: ${account.balance:,.2f}")
        else:
            raise Exception("No account info")
        
        self.market_data = MarketDataFetcher(config=ConfigManager())
        
        # 2. C++ Quantum Systems
        logger.info("\n🧬 Initializing C++ Quantum Systems...")
        self.quantum_systems = QuantumTradingSystems()
        logger.info("✅ C++ Monte Carlo + Quantum Dimensions ready")
        
        # 3. Python Neural Systems
        logger.info("\n🧠 Initializing Python Neural Systems...")
        config = ConfigManager()
        dna_params = config.load_dna()
        
        self.neural_profiler = NeuralRegimeProfiler(dna_params=dna_params)
        self.strategy_orchestrator = StrategyOrchestrator(dna_params=dna_params)
        self.coherence_engine = CoherenceEngine(dna_params=dna_params)
        self.realtime_dna = RealTimeDNAEngine(initial_dna=dna_params)
        
        logger.info("✅ Neural Profiles + Orchestrator + Coherence + DNA ready")
        
        # 4. Telegram
        self.telegram = TelegramNotifier()
        if self.telegram.enabled:
            logger.info("✅ Telegram notifications enabled")
        
        logger.info("\n" + "="*80)
        logger.info("✅ ALL SYSTEMS INITIALIZED")
        logger.info("="*80)
        
        # Step 4: Write handshake file for EA (Python writes, EA reads)
        logger.info("\n📡 Step 4: Writing handshake file for EA...")
        self.write_handshake_for_ea()
    
    def write_handshake_for_ea(self):
        """
        Python writes handshake file that EA can read
        This avoids MT5 sandbox file write issues
        """
        import os
        
        # Create directory if doesn't exist
        Path(self.handshake_file).parent.mkdir(parents=True, exist_ok=True)
        
        # Also write to MT5 Common Files folder (where EA can read with FILE_COMMON)
        mt5_common = Path.home() / "AppData" / "Roaming" / "MetaQuotes" / "Terminal" / "Common" / "Files" / "quantum_signals" / "connection.txt"
        mt5_common.parent.mkdir(parents=True, exist_ok=True)
        
        handshake_content = f"""PYTHON_CONNECTED=true
PYTHON_START_TIME={datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}
PYTHON_STATUS=READY
SIGNAL_FILE={self.signal_file}
MT5_COMMON_FILE={mt5_common}
"""
        
        # Write to both locations
        try:
            with open(self.handshake_file, 'w') as f:
                f.write(handshake_content)
            logger.info(f"✅ Handshake written: {self.handshake_file}")
        except Exception as e:
            logger.warning(f"⚠️ Could not write local handshake: {e}")
        
        try:
            with open(str(mt5_common), 'w') as f:
                f.write(handshake_content)
            logger.info(f"✅ Handshake written to MT5 Common: {mt5_common}")
        except Exception as e:
            logger.warning(f"⚠️ Could not write MT5 common handshake: {e}")
        
        self.ea_connected = True  # Consider EA connected once we write handshake
    
    async def generate_signal(self) -> bool:
        """
        Generate one trading signal
        
        Returns:
            True if signal generated, False if no clear signal
        """
        try:
            logger.info(f"\n{'='*60}")
            logger.info(f"🔬 SIGNAL GENERATION - {datetime.now().strftime('%H:%M:%S')}")
            logger.info(f"{'='*60}")
            
            # 1. Get real market data
            candles = await self.market_data.get_candles(timeframe="M5", count=200)
            if candles is None or len(candles) < 100:
                logger.warning("⚠️ Insufficient market data - skipping")
                return False
            
            current_price = candles['close'].iloc[-1]
            volatility = candles['close'].pct_change().std() * (252 * 288) ** 0.5
            
            logger.info(f"📊 Market: ${current_price:,.2f} | Vol: {volatility*100:.1f}%")
            
            # 2. C++ Quantum Analysis
            logger.info("\n🧬 Step 1: C++ Quantum Analysis")
            quantum_results = self.quantum_systems.run_complete_analysis(
                spot_price=current_price,
                volatility=volatility
            )
            
            # 3. Python Neural Analysis
            logger.info("\n🧠 Step 2: Python Neural Analysis")
            recent = candles.iloc[-100:]
            
            market_state = {'price': current_price, 'volatility': candles['close'].std()}
            profile = self.neural_profiler.select_best_profile(recent, market_state)
            
            orchestration = self.strategy_orchestrator.orchestrate(
                candles=recent,
                current_price=current_price,
                regime=self.neural_profiler.current_regime,
            )
            
            risk_ctx = {'consecutive_losses': 0, 'current_drawdown': 0}
            coherence_result = self.coherence_engine.analyze(
                orchestration_result=orchestration,
                candles=recent,
                regime=self.neural_profiler.current_regime,
                profile=profile,
                risk_context=risk_ctx,
            )
            
            # 4. DNA Transmutation
            logger.info("\n🧬 Step 3: DNA Adaptation")
            returns = recent['close'].pct_change()
            physics = {
                'market_energy': returns.std() * 100,
                'velocity': abs(current_price - recent['close'].iloc[-10]) / 10,
                'acceleration': 0
            }
            
            mutations = self.realtime_dna.transmutate(
                coherence_result=coherence_result,
                orchestration_result=orchestration,
                regime=self.neural_profiler.current_regime,
                profile=profile,
                market_physics=physics,
                performance_metrics={'net_pnl': 0},
            )
            
            # 5. Generate final signal
            signal = self._create_signal(
                current_price, volatility, quantum_results,
                orchestration, coherence_result, profile, mutations
            )
            
            if signal:
                # Write to CSV for EA
                self._write_signal_csv(signal)
                self.signals_generated += 1
                
                logger.info(f"\n✅ SIGNAL GENERATED")
                logger.info(f"   Direction: {signal['direction']}")
                logger.info(f"   Confidence: {signal['confidence']:.2f}")
                logger.info(f"   Entry: ${signal['entry_price']:,.2f}")
                logger.info(f"   SL: ${signal['stop_loss']:,.2f}")
                logger.info(f"   TP: ${signal['take_profit']:,.2f}")
                
                # Send Telegram notification
                if self.telegram.enabled:
                    self._send_telegram_alert(signal)
                
                return True
            else:
                logger.info("\n⏸️ No clear signal - standing aside")
                return False
        
        except Exception as e:
            logger.error(f"❌ Signal generation error: {e}", exc_info=True)
            return False
    
    def _create_signal(self, price, volatility, quantum, orchestration, 
                      coherence, profile, mutations) -> dict:
        """Create final trading signal with CORRECT voting structure"""
        
        # ============================================================
        # PART 1: Calculate BASELINE threshold adjustments
        # Monte Carlo, Quantum, and Coherence ADJUST threshold - they DON'T vote
        # ============================================================
        
        base_threshold = 0.60  # Default threshold
        threshold_adjustments = []
        
        # 1. Monte Carlo adjusts threshold
        if quantum.get('monte_carlo'):
            mc_prob = quantum['monte_carlo'].get('probability_profit', 0.5)
            mc_mean = quantum['monte_carlo']['mean_price']
            
            if mc_prob > 0.60:
                adjustment = -0.10  # Strong MC signal → easier to trade
                threshold_adjustments.append({
                    'system': 'Monte Carlo',
                    'value': f"Prob profit {mc_prob:.1%}",
                    'adjustment': adjustment,
                    'reason': 'High probability of profit'
                })
            elif mc_prob < 0.40:
                adjustment = +0.15  # Weak MC signal → harder to trade
                threshold_adjustments.append({
                    'system': 'Monte Carlo',
                    'value': f"Prob profit {mc_prob:.1%}",
                    'adjustment': adjustment,
                    'reason': 'Low probability of profit'
                })
            else:
                threshold_adjustments.append({
                    'system': 'Monte Carlo',
                    'value': f"Prob profit {mc_prob:.1%}",
                    'adjustment': 0.0,
                    'reason': 'Neutral zone'
                })
        
        # 2. Quantum Prediction adjusts threshold
        if quantum.get('quantum_prediction'):
            q_pred = quantum['quantum_prediction']
            mc_mean = quantum['monte_carlo']['mean_price']
            price_diff_pct = abs(q_pred['predicted_price'] - mc_mean) / mc_mean
            
            if price_diff_pct > 0.02:  # > 2% difference
                adjustment = -0.05  # Strong quantum signal
                threshold_adjustments.append({
                    'system': 'Quantum Prediction',
                    'value': f"Predicted ${q_pred['predicted_price']:,.2f}",
                    'adjustment': adjustment,
                    'reason': f'Strong prediction ({price_diff_pct:.1%} from MC mean)'
                })
            elif price_diff_pct < 0.005:  # < 0.5% difference
                adjustment = +0.10  # Weak/uncertain quantum signal
                threshold_adjustments.append({
                    'system': 'Quantum Prediction',
                    'value': f"Predicted ${q_pred['predicted_price']:,.2f}",
                    'adjustment': adjustment,
                    'reason': 'Weak prediction (close to MC mean)'
                })
            else:
                threshold_adjustments.append({
                    'system': 'Quantum Prediction',
                    'value': f"Predicted ${q_pred['predicted_price']:,.2f}",
                    'adjustment': 0.0,
                    'reason': 'Moderate prediction'
                })
        
        # 3. Coherence Engine adjusts threshold
        if coherence:
            if coherence.overall_coherence > 0.7:
                adjustment = -0.05  # High coherence → easier to trade
                threshold_adjustments.append({
                    'system': 'Coherence Engine',
                    'value': f"Coherence {coherence.overall_coherence:.2f}",
                    'adjustment': adjustment,
                    'reason': 'High market coherence'
                })
            elif coherence.overall_coherence < 0.4:
                adjustment = +0.10  # Low coherence → harder to trade
                threshold_adjustments.append({
                    'system': 'Coherence Engine',
                    'value': f"Coherence {coherence.overall_coherence:.2f}",
                    'adjustment': adjustment,
                    'reason': 'Low market coherence'
                })
            else:
                threshold_adjustments.append({
                    'system': 'Coherence Engine',
                    'value': f"Coherence {coherence.overall_coherence:.2f}",
                    'adjustment': 0.0,
                    'reason': 'Moderate coherence'
                })
        
        # Calculate final threshold
        total_adjustment = sum(ta['adjustment'] for ta in threshold_adjustments)
        final_threshold = base_threshold + total_adjustment
        final_threshold = max(0.40, min(0.80, final_threshold))  # Clamp between 0.40-0.80
        
        # ============================================================
        # PART 2: ACTUAL VOTERS - 5 Advanced Strategies
        # ============================================================
        
        votes = {
            'BUY': [],
            'SELL': [],
            'NEUTRAL': []
        }
        
        # Get individual strategy votes from orchestrator
        if orchestration and hasattr(orchestration, 'individual_votes') and orchestration.individual_votes:
            for strat_name, vote_data in orchestration.individual_votes.items():
                direction = vote_data['direction']
                confidence = vote_data['confidence']
                weight = vote_data['weight']
                reason = vote_data.get('reason', '')
                
                vote_entry = {
                    'strategy': strat_name.replace('_', ' ').title(),
                    'weight': weight,
                    'confidence': confidence,
                    'weighted_vote': confidence * weight,
                    'reason': reason
                }
                
                if direction == 'BUY':
                    votes['BUY'].append(vote_entry)
                elif direction == 'SELL':
                    votes['SELL'].append(vote_entry)
                else:
                    votes['NEUTRAL'].append(vote_entry)
        else:
            logger.warning("⚠️ No individual votes from orchestrator")
            return None
        
        # ============================================================
        # PART 3: Log detailed voting
        # ============================================================
        
        logger.info(f"\n{'='*60}")
        logger.info(f"🗳️ STRATEGY VOTING DETAILS")
        logger.info(f"{'='*60}")
        
        logger.info(f"\n🟢 BUY VOTES ({len(votes['BUY'])}):")
        for vote in votes['BUY']:
            logger.info(f"   ✅ {vote['strategy']}: {vote['reason']} (conf: {vote['confidence']:.2f}, weight: {vote['weight']:.2f})")
        
        logger.info(f"\n🔴 SELL VOTES ({len(votes['SELL'])}):")
        for vote in votes['SELL']:
            logger.info(f"   ❌ {vote['strategy']}: {vote['reason']} (conf: {vote['confidence']:.2f}, weight: {vote['weight']:.2f})")
        
        logger.info(f"\n⚪ NEUTRAL VOTES ({len(votes['NEUTRAL'])}):")
        for vote in votes['NEUTRAL']:
            logger.info(f"   ⏸️ {vote['strategy']}: {vote['reason']} (conf: {vote['confidence']:.2f}, weight: {vote['weight']:.2f})")
        
        # ============================================================
        # PART 4: Calculate final result
        # ============================================================
        
        buy_weight = sum(v['weighted_vote'] for v in votes['BUY'])
        sell_weight = sum(v['weighted_vote'] for v in votes['SELL'])
        neutral_weight = sum(v['weighted_vote'] for v in votes['NEUTRAL'])
        total_weight = buy_weight + sell_weight + neutral_weight
        
        logger.info(f"\n📊 VOTE SUMMARY:")
        logger.info(f"   BUY:    {len(votes['BUY'])} strategies ({buy_weight:.2f} weighted)")
        logger.info(f"   SELL:   {len(votes['SELL'])} strategies ({sell_weight:.2f} weighted)")
        logger.info(f"   NEUTRAL: {len(votes['NEUTRAL'])} strategies ({neutral_weight:.2f} weighted)")
        
        # Determine direction
        if buy_weight > sell_weight and buy_weight > neutral_weight:
            direction = 'BUY'
            confidence = buy_weight / total_weight if total_weight > 0 else 0
        elif sell_weight > buy_weight and sell_weight > neutral_weight:
            direction = 'SELL'
            confidence = sell_weight / total_weight if total_weight > 0 else 0
        else:
            logger.info(f"\n⏸️ No clear majority - standing aside")
            return None
        
        # Check against threshold
        logger.info(f"\n📊 THRESHOLD CHECK:")
        logger.info(f"   Base Threshold: {base_threshold:.2f}")
        logger.info(f"   Adjustments: {total_adjustment:+.2f}")
        logger.info(f"   Final Threshold: {final_threshold:.2f}")
        logger.info(f"   Confidence: {confidence:.2f}")
        
        if confidence < final_threshold:
            logger.info(f"   ❌ Confidence {confidence:.2f} < Threshold {final_threshold:.2f} - NO SIGNAL")
            return None
        
        logger.info(f"   ✅ Confidence {confidence:.2f} >= Threshold {final_threshold:.2f} - SIGNAL!")
        
        # Calculate SL/TP
        if direction == 'BUY':
            sl = price - 300
            tp = price + 600
        else:
            sl = price + 300
            tp = price - 600
        
        # Create strategy lists for CSV
        buy_strategies = ", ".join([v['strategy'] for v in votes['BUY']]) if votes['BUY'] else "None"
        sell_strategies = ", ".join([v['strategy'] for v in votes['SELL']]) if votes['SELL'] else "None"
        neutral_strategies = ", ".join([v['strategy'] for v in votes['NEUTRAL']]) if votes['NEUTRAL'] else "None"
        
        # Create threshold adjustment summary
        threshold_summary = "; ".join([f"{t['system']}: {t['adjustment']:+.2f} ({t['reason']})" for t in threshold_adjustments])
        
        signal = {
            'timestamp': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
            'direction': direction,
            'confidence': confidence,
            'entry_price': price,
            'stop_loss': sl,
            'take_profit': tp,
            'profile': profile.name.value if profile else 'unknown',
            'regime': self.neural_profiler.current_regime,
            'signal_count': len(votes['BUY']) + len(votes['SELL']) + len(votes['NEUTRAL']),
            'volatility': volatility,
            'buy_votes': len(votes['BUY']),
            'sell_votes': len(votes['SELL']),
            'neutral_votes': len(votes['NEUTRAL']),
            'buy_weight': buy_weight,
            'sell_weight': sell_weight,
            'buy_strategies': buy_strategies,
            'sell_strategies': sell_strategies,
            'neutral_strategies': neutral_strategies,
            'threshold': final_threshold,
            'threshold_adjustments': threshold_summary,
        }
        
        return signal
    
    def _write_signal_csv(self, signal: dict):
        """Write signal to CSV file for MQL5 EA with voting details"""
        try:
            # Write main signal CSV (for EA)
            with open(self.signal_file, 'w', newline='') as f:
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
            
            # Write detailed voting log (for humans)
            signal_dir = Path(self.signal_file).parent
            vote_log_file = signal_dir / f"vote_log_{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.csv"
            
            file_exists = vote_log_file.exists()
            with open(vote_log_file, 'a', newline='') as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow([
                        'Timestamp', 'Direction', 'Confidence', 'Entry', 'SL', 'TP',
                        'Profile', 'Regime', 'Signal Count', 'Volatility',
                        'Buy Votes', 'Sell Votes', 'Neutral Votes',
                        'Buy Weight', 'Sell Weight',
                        'Buy Strategies', 'Sell Strategies', 'Neutral Strategies'
                    ])
                
                writer.writerow([
                    signal['timestamp'],
                    signal['direction'],
                    f"{signal['confidence']:.2f}",
                    f"{signal['entry_price']:.2f}",
                    f"{signal['stop_loss']:.2f}",
                    f"{signal['take_profit']:.2f}",
                    signal['profile'],
                    signal['regime'],
                    signal['signal_count'],
                    f"{signal['volatility']*100:.1f}%",
                    signal['buy_votes'],
                    signal['sell_votes'],
                    signal['neutral_votes'],
                    f"{signal['buy_weight']:.2f}",
                    f"{signal['sell_weight']:.2f}",
                    signal['buy_strategies'],
                    signal['sell_strategies'],
                    signal['neutral_strategies'],
                ])
            
            logger.info(f"💾 Signal written to: {self.signal_file}")
            logger.info(f"📊 Vote log saved to: {vote_log_file}")
            self.last_signal_time = time.time()
        
        except Exception as e:
            logger.error(f"❌ Failed to write signal file: {e}")
    
    def _send_telegram_alert(self, signal: dict):
        """Send Telegram alert for new signal with voting details"""
        emoji = "🟢" if signal['direction'] == 'BUY' else "🔴"
        
        message = f"""
{emoji} <b>NEW SIGNAL GENERATED</b>
━━━━━━━━━━━━━━━━━━━━
📊 <b>{signal['direction']} BTCUSD</b>

💰 Entry: ${signal['entry_price']:,.2f}
🛑 SL: ${signal['stop_loss']:,.2f}
🎯 TP: ${signal['take_profit']:,.2f}
📈 R:R: 1:2.0

🧬 Confidence: {signal['confidence']:.2f}
🧠 Profile: {signal['profile']}
📊 Regime: {signal['regime']}
🔬 Total Signals: {signal['signal_count']}
📊 Threshold: {signal.get('threshold', 0.60):.2f}

🗳️ <b>VOTING BREAKDOWN:</b>
🟢 BUY: {signal['buy_votes']} strategies ({signal['buy_weight']:.2f} weighted)
{signal['buy_strategies']}

🔴 SELL: {signal['sell_votes']} votes ({signal['sell_weight']:.2f} weight)
{signal['sell_strategies']}

⚪ NEUTRAL: {signal['neutral_votes']} votes
{signal['neutral_strategies']}

━━━━━━━━━━━━━━━━━━━━
⏰ {datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}
"""
        
        try:
            self.telegram.send_message(message)
        except Exception as e:
            logger.error(f"❌ Telegram error: {e}")
    
    async def run(self, duration_hours: int = 24):
        """
        Run signal generator continuously
        
        Args:
            duration_hours: How long to run
        """
        self.running = True
        start_time = time.time()
        duration_seconds = duration_hours * 3600
        
        logger.info(f"\n🚀 Starting signal generator for {duration_hours} hours")
        logger.info(f"   Signal interval: {self.signal_interval}s")
        
        # Send startup notification
        if self.telegram.enabled:
            self.telegram.send_message(f"""
🚀 <b>SIGNAL GENERATOR STARTED</b>
━━━━━━━━━━━━━━━━━━━━
⏰ Duration: {duration_hours} hours
📊 Interval: {self.signal_interval}s

Systems:
✅ C++ Monte Carlo
✅ C++ Quantum Dimensions
✅ Neural Profiles
✅ Strategy Orchestrator
✅ Coherence Engine
✅ DNA Adaptation

⏰ {datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}
""")
        
        try:
            cycle_count = 0
            while self.running:
                # Check duration
                elapsed = time.time() - start_time
                if elapsed > duration_seconds:
                    logger.info(f"✅ Duration reached - stopping")
                    break
                
                cycle_count += 1
                logger.info(f"\n🔄 Cycle #{cycle_count}")
                
                # Generate signal
                await self.generate_signal()
                
                # Wait for next cycle
                remaining = self.signal_interval
                logger.info(f"\n⏳ Next signal in {remaining}s")
                while remaining > 0:
                    await asyncio.sleep(min(10, remaining))
                    remaining -= 10
                    if remaining > 0 and remaining % 30 == 0:
                        logger.info(f"   ⏰ Next signal in {remaining}s")
        
        except KeyboardInterrupt:
            logger.warning("\n⚠️ Interrupted by user")
        except Exception as e:
            logger.error(f"\n❌ Error: {e}", exc_info=True)
        finally:
            await self._shutdown()
    
    async def _shutdown(self):
        """Graceful shutdown"""
        logger.info("\n" + "="*80)
        logger.info("🛑 SIGNAL GENERATOR SHUTTING DOWN")
        logger.info("="*80)
        
        self.running = False
        
        # Send shutdown notification
        if self.telegram.enabled:
            self.telegram.send_message(f"""
🛑 <b>SIGNAL GENERATOR STOPPED</b>
━━━━━━━━━━━━━━━━━━━━
📊 Signals Generated: {self.signals_generated}
⏰ {datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}
""")
        
        # Cleanup MT5
        import MetaTrader5 as mt5
        mt5.shutdown()
        
        logger.info("✅ Shutdown complete")


async def main():
    """Run signal generator"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Signal Generator for MQL5 EA')
    parser.add_argument('--hours', type=int, default=24, help='Duration in hours')
    parser.add_argument('--interval', type=int, default=60, help='Signal interval (seconds)')
    
    args = parser.parse_args()
    
    print("\n" + "="*80)
    print("📡 FOREX QUANTUM BOT - MQL5 SIGNAL GENERATOR")
    print("   Bridges Python AI with MQL5 Execution")
    print("="*80 + "\n")
    
    # Initialize
    generator = SignalGenerator()
    generator.signal_interval = args.interval
    
    # Run
    await generator.run(duration_hours=args.hours)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
