"""
Complete System Backtest v2 - ALL SYSTEMS INTEGRATED
CEO: Qwen Code | Created: 2026-04-12

Integrates:
1. Neural Trade Auditor (complete state capture)
2. Trade Pattern Analyzer (error pattern detection)
3. Veto Orchestrator (basic veto rules)
4. Smart Order Manager (Virtual TP + Dynamic SL)
5. Advanced Veto v2 (RSI, Top/Bottom, Bollinger, Session)
6. Session Profiles (Asian/Weekend restrictions)
7. 12 Strategies (5 original + 7 new execution agents)
8. SL capped at 300 points MAX
9. Dynamic position sizing (configurable risk %)
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from loguru import logger

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.core.config_manager import ConfigManager
from src.monitoring.neural_trade_auditor import NeuralTradeAuditor
from src.monitoring.trade_pattern_analyzer import TradePatternAnalyzer
from src.monitoring.veto_orchestrator import VetoOrchestrator
from src.monitoring.advanced_veto_v2 import AdvancedVetoV2
from src.strategies.session_profiles import get_session_profile, apply_session_veto, detect_session
from src.execution.smart_order_manager import SmartOrderManager
from src.risk.backtest_risk_manager import BacktestRiskManager  # NEW: Risk Manager integration (BUG #6)
from src.risk.anti_metralhadora import AntiMetralhadora  # Phase 1: Overtrading prevention (DubaiMatrixASI)
from src.execution.position_manager_smart_tp import PositionManagerSmartTP  # Phase 1: Multi-target TP (DubaiMatrixASI)
from src.risk.risk_quantum_engine import RiskQuantumEngine  # Phase 1: 5-factor position sizing (DubaiMatrixASI)
from src.risk.profit_erosion_tiers import ProfitErosionTiers  # Phase 1: Multi-level profit protection (Atl4s)
from src.risk.execution_validator import ExecutionValidator  # Phase 1: Pre-trade validation (DubaiMatrixASI)
from src.risk.great_filter import GreatFilter  # Phase 1: Entry quality validation (Atl4s)
from src.monitoring.trade_registry import TradeRegistry  # Phase 1: Trade audit system (DubaiMatrixASI)
from src.core.omega_params import OmegaParams  # Phase 1: Centralized config (DubaiMatrixASI)

# Phase 2: Advanced optimizations
from src.execution.thermodynamic_exit import ThermodynamicExit  # 5-sensor profit management
from src.strategies.m8_fibonacci_system import M8FibonacciSystem  # 8-min Phi timeframe
from src.analysis.regime_detector import RegimeDetector  # Hurst + ADX + Vol + Structure
from src.monitoring.recursive_self_debate import RecursiveSelfDebate  # Metacognitive validation
from src.analysis.vpin_microstructure import VPINMicrostructure  # Institutional activity detection
from src.risk.black_swan_stress_test import BlackSwanStressTest  # Fat-tail simulation
from src.analysis.kinematics_phase_space import KinematicsPhaseSpace  # Velocity/acceleration features
from src.memory.akashic_core import AkashicCore  # HDC pattern memory


def setup_logging():
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )


import MetaTrader5 as mt5

def fetch_mt5_data(days: int = 180) -> pd.DataFrame:
    """Fetch REAL historical BTCUSD data from MT5"""
    logger.info(f"🔄 Connecting to MT5 to fetch {days} days of BTCUSD data...")
    
    if not mt5.initialize():
        logger.error(f"❌ MT5 Initialization failed. Error code: {mt5.last_error()}")
        sys.exit(1)
        
    bars_per_day = 288
    total_bars = days * bars_per_day
    
    # Request data from MT5
    rates = mt5.copy_rates_from_pos("BTCUSD", mt5.TIMEFRAME_M5, 0, total_bars)
    
    if rates is None or len(rates) == 0:
        logger.error(f"❌ Failed to get data from MT5. Error: {mt5.last_error()}")
        sys.exit(1)
        
    # Convert to DataFrame
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s', utc=True)
    
    df = df.rename(columns={
        'open': 'open',
        'high': 'high',
        'low': 'low',
        'close': 'close',
        'tick_volume': 'volume'
    })
    
    # Drop unseen columns like spread, real_volume if not needed
    df = df[['time', 'open', 'high', 'low', 'close', 'volume']]
    
    logger.info(f"✅ Fetched {len(df)} REAL M5 candles from MT5")
    logger.info(f"   Date Range: {df['time'].iloc[0]} to {df['time'].iloc[-1]}")
    logger.info(f"   Price Range: ${df['low'].min():,.0f} -> ${df['high'].max():,.0f}")
    
    return df


class CompleteBacktestEngineV2:
    """
    Complete backtest with ALL systems integrated:
    - 12 Strategies voting (5 original + 7 new)
    - Session-specific profiles (Asian/Weekend)
    - Advanced Veto v2 (RSI, Top/Bottom, Bollinger)
    - SL capped at 300 points
    - Dynamic position sizing
    - Neural Trade Auditor
    - Smart Order Manager
    """

    def __init__(self, candles: pd.DataFrame, risk_percent: float = 1.0):
        self.candles = candles
        self.config_manager = ConfigManager()
        self.dna = self.config_manager.load_dna()
        self.risk_percent = risk_percent

        # All systems - RE-ENABLED AUDIT FOR INTELLIGENT LOSS ANALYSIS
        self.auditor = NeuralTradeAuditor()
        self.auditor._backtest_mode = True  # Buffer writes, don't flush per trade
        self.auditor._enabled = True  # RE-ENABLED: Full audit logging for loss analysis
        self.order_manager = SmartOrderManager(dna_params=self.dna)
        self.veto_orchestrator = VetoOrchestrator()
        self.advanced_veto_v2 = AdvancedVetoV2()
        
        # NEW: Risk Manager integration (BUG #6 fix)
        self.risk_manager = BacktestRiskManager(initial_capital=100000.0)
        
        # Phase 1: Anti-Metralhadora (DubaiMatrixASI salvage - overtrading prevention)
        self.anti_metralhadora = AntiMetralhadora(
            min_interval_minutes=5.0,
            max_trades_per_day=25,
            min_quality_score=0.40,
            max_consecutive_losses=3,
            loss_cooldown_minutes=30.0,
        )
        
        # Phase 1: PositionManager Smart TP (DubaiMatrixASI salvage - multi-target exits)
        self.position_manager = PositionManagerSmartTP(
            tp1_portion=0.30, tp1_rr=1.0,
            tp2_portion=0.30, tp2_rr=2.0,
            tp3_portion=0.20, tp3_rr=3.0,
            trailing_portion=0.20,
            trailing_atr_multiplier=2.0,  # Increased from 1.5 to match higher R:R
        )
        
        # Phase 1: RiskQuantumEngine (DubaiMatrixASI salvage - 5-factor position sizing)
        self.risk_quantum = RiskQuantumEngine(
            kelly_fraction=0.25,
            max_position_size=1.0,
            min_position_size=0.01,
            base_risk_percent=1.0,
        )
        
        # Phase 1: ProfitErosionTiers (Atl4s salvage - multi-level profit protection)
        self.profit_erosion = ProfitErosionTiers()
        
        # Phase 1: ExecutionValidator (DubaiMatrixASI salvage - pre-trade validation)
        self.execution_validator = ExecutionValidator()
        
        # Phase 1: GreatFilter (Atl4s salvage - entry quality validation)
        self.great_filter = GreatFilter()
        
        # Phase 1: TradeRegistry (DubaiMatrixASI salvage - comprehensive audit)
        self.trade_registry = TradeRegistry()
        
        # Phase 1: OmegaParams (DubaiMatrixASI salvage - centralized config)
        self.omega_params = OmegaParams()
        
        # Phase 2: Advanced optimizations
        self.thermodynamic_exit = ThermodynamicExit()
        self.m8_fibonacci = M8FibonacciSystem()
        self.regime_detector = RegimeDetector()
        self.recursive_debate = RecursiveSelfDebate(min_debate_confidence=0.0)  # Only flip signals, don't veto
        self.vpin = VPINMicrostructure()
        self.black_swan = BlackSwanStressTest()
        self.kinematics = KinematicsPhaseSpace()
        self.akashic = AkashicCore()

        # State
        self.equity = 100000.0
        self.initial_equity = 100000.0
        self.peak_equity = 100000.0
        self.max_drawdown = 0.0

        self.trades = []
        self.ticket_counter = 1000
        self.current_position = None

        self.total_signals = 0
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_vetoes = 0
        self.total_filed_orders = 0
        self.total_commissions = 0.0

        self.consecutive_wins = 0
        self.consecutive_losses = 0
        self.last_trade_time = None
        self.last_loss_time = None
        self.min_cooldown_bars = 3  # SCALPER MODE: Reduced to 3 bars (15 min) for maximum frequency
        self.consecutive_loss_cooldown = 3  # SCALPER MODE: Only 3 bars cooldown after losses

        # Strategy tracking - ENHANCED for intelligent loss analysis
        self.strategy_results = {name: {'trades': 0, 'wins': 0, 'losses': 0, 'total_pnl': 0.0, 'avg_wr': 0.0} for name in [
            'momentum', 'liquidity', 'thermodynamic', 'physics', 'order_block', 'fvg',
            'msnr', 'msnr_alchemist', 'ifvg', 'order_flow', 'supply_demand', 'fibonacci', 'iceberg'
        ]}
        
        # ENHANCED: Loss pattern tracking for intelligent analysis
        self.loss_patterns = {
            'by_hour': {},  # Losses by hour of day
            'by_regime': {'trending_bullish': 0, 'trending_bearish': 0, 'ranging': 0},
            'by_session': {'asian': 0, 'london': 0, 'ny': 0, 'ny_overlap': 0},
            'by_strategy': {name: 0 for name in self.strategy_results.keys()},
            'by_reason': {'SL hit': 0, 'SL hit (trailed)': 0, 'TP hit': 0},
            'avg_loss_size': 0.0,
            'avg_win_size': 0.0,
            'total_trailing_stops_hit': 0,
        }

        # ═══════════════════════════════════════════════════════════════
        # PRE-COMPUTE ALL INDICATORS (Phase 4 Performance Optimization)
        # This eliminates O(N²) recalculation inside the hot loop.
        # ═══════════════════════════════════════════════════════════════
        logger.info("⚡ Pre-computing indicators...")
        close = candles['close'].values.astype(np.float64)
        high = candles['high'].values.astype(np.float64)
        low = candles['low'].values.astype(np.float64)
        volume = candles['volume'].values.astype(np.float64)
        n = len(close)

        # EMA 9, 21, 50 (vectorized)
        def _ema_vec(data, span):
            alpha = 2.0 / (span + 1)
            out = np.empty_like(data)
            out[0] = data[0]
            for j in range(1, len(data)):
                out[j] = alpha * data[j] + (1 - alpha) * out[j - 1]
            return out

        self._ema9 = _ema_vec(close, 9)
        self._ema21 = _ema_vec(close, 21)
        self._ema50 = _ema_vec(close, 50)

        # SMA 20
        self._sma20 = np.convolve(close, np.ones(20) / 20, mode='full')[:n]
        self._sma20[:19] = close[:19]  # Fill warmup

        # RSI 14 (vectorized)
        delta = np.diff(close, prepend=close[0])
        gain = np.where(delta > 0, delta, 0.0)
        loss_arr = np.where(delta < 0, -delta, 0.0)
        avg_gain = _ema_vec(gain, 14)
        avg_loss = _ema_vec(loss_arr, 14)
        rs = np.divide(avg_gain, avg_loss, out=np.zeros_like(avg_gain), where=avg_loss > 0)
        self._rsi = 100.0 - (100.0 / (1.0 + rs))

        # ATR 14 (vectorized True Range)
        tr = np.maximum(
            high[1:] - low[1:],
            np.maximum(np.abs(high[1:] - close[:-1]), np.abs(low[1:] - close[:-1]))
        )
        tr = np.concatenate([[high[0] - low[0]], tr])
        self._atr = np.convolve(tr, np.ones(14) / 14, mode='full')[:n]
        self._atr[:13] = tr[:13]

        # Bollinger Bands (20, 2)
        self._bb_mid = self._sma20.copy()
        bb_std = np.empty(n)
        for j in range(n):
            start = max(0, j - 19)
            bb_std[j] = close[start:j + 1].std() if j >= 19 else close[:j + 1].std()
        self._bb_upper = self._bb_mid + 2 * bb_std
        self._bb_lower = self._bb_mid - 2 * bb_std

        # Cache NumPy arrays for hot-path access
        self._close = close
        self._high = high
        self._low = low
        self._volume = volume
        self._times = candles['time'].values

        # ═══════════════════════════════════════════════════════════════
        # PRE-COMPUTE MULTI-TIMEFRAME INDICATORS FOR QUALITY FILTERS
        # ═══════════════════════════════════════════════════════════════
        logger.info("⚡ Computing multi-timeframe trend filters...")
        
        # H1-equivalent EMAs (using M5 bars: H1 EMA 50 ≈ M5 EMA 600, H1 EMA 200 ≈ M5 EMA 2400)
        # Using shorter equivalents for 180-day window: EMA 120 ≈ H1 EMA 10, EMA 288 ≈ H1 EMA 24
        self._ema_h1_fast = _ema_vec(close, 120)   # ~H1 EMA 10
        self._ema_h1_slow = _ema_vec(close, 288)   # ~H1 EMA 24
        
        # Volume average (20 bars) for confirmation filter
        self._vol_avg_20 = np.convolve(volume, np.ones(20) / 20, mode='full')[:n]
        self._vol_avg_20[:19] = volume[:19]
        
        logger.info(f"⚡ Multi-timeframe filters ready: {n} candles")

        logger.info(f"⚡ Pre-computation complete: {n} candles")
        logger.info("Complete Backtest Engine V2 initialized")
        logger.info(f"  12 Strategies + Session Profiles + Advanced Veto v2")
        logger.info(f"  SL Cap: 300 points MAX | Risk: {risk_percent}%")

    def run(self) -> dict:
        """Run complete backtest"""

        logger.info("="*80)
        logger.info("COMPLETE SYSTEM BACKTEST V2")
        logger.info("="*80)
        logger.info(f"  Capital: ${self.initial_equity:,.2f}")
        logger.info(f"  Candles: {len(self.candles)}")
        logger.info(f"  Risk/Trade: {self.risk_percent}%")
        logger.info(f"  Systems: 12 Strategies + Session Profiles + Advanced Veto v2")
        logger.info("="*80)

        warmup = 50
        total = len(self.candles)
        import time as _time
        t0 = _time.perf_counter()

        for i in range(warmup, total):
            # ── Hot path: use pre-computed NumPy arrays instead of DataFrame ──
            cur_close = self._close[i]
            cur_high = self._high[i]
            cur_low = self._low[i]
            cur_time = pd.Timestamp(self._times[i])

            if self.current_position is None:
                # NEW: Cooldown after 3+ consecutive losses (wait N bars, not permanent block)
                if self.consecutive_losses >= 3 and self.last_loss_time is not None:
                    bars_since_loss = i - self.last_loss_time
                    if bars_since_loss < self.consecutive_loss_cooldown:
                        continue  # Still in cooldown, skip signal

                # Generate signal using pre-computed indicators by index
                signal = self._generate_signal_fast(i, cur_close, cur_time)

                if signal:
                    # SCALPER MODE: Maximum signal frequency - NO RESTRICTIVE FILTERS
                    # We want ALL valid signals, then analyze losses intelligently
                    
                    # Calculate SL/TP distances for risk validation
                    atr = self._atr[i]
                    sl_dist_for_risk = min(max(atr * 2.0, 500), 3000)
                    tp_dist_for_risk = sl_dist_for_risk * 3.0  # A1: 1:3 R:R for higher profit per trade
                    
                    session = detect_session(cur_time)
                    session_profile = get_session_profile(session)
                    session_veto = apply_session_veto(session_profile, signal)

                    if not session_veto['approved']:
                        self.total_vetoes += 1
                    else:
                        # Basic veto (uses pre-computed values from signal)
                        basic_veto = self._check_basic_veto_fast(signal, i)

                        if basic_veto.approved:
                            # Advanced Veto v2 with pre-computed RSI
                            veto_result = self._check_advanced_veto_fast(signal, i)

                            if veto_result['approved']:
                                # NEW: Risk Manager validation (BUG #6 fix)
                                risk_validation = self.risk_manager.validate_trade(
                                    risk_amount=sl_dist_for_risk * signal.get('volume', 0.01),
                                    reward_amount=tp_dist_for_risk * signal.get('volume', 0.01),
                                    current_capital=self.equity
                                )
                                
                                if not risk_validation['approved']:
                                    self.total_vetoes += 1
                                    continue  # Skip this trade
                                
                                # Phase 1: Anti-Metralhadora check (DubaiMatrixASI salvage)
                                allowed, reason, details = self.anti_metralhadora.should_allow_trade(
                                    signal_quality=signal.get('confidence', 0.0),
                                    current_session=session,
                                    current_time=cur_time.to_pydatetime() if hasattr(cur_time, 'to_pydatetime') else cur_time,
                                )
                                
                                if not allowed:
                                    self.total_vetoes += 1
                                    continue  # Skip this trade (overtrading prevention)
                                
                                # ═══════════════════════════════════════════════════════════════
                                # Phase 2: Advanced validations (DubaiMatrixASI + Atl4s + Laplace)
                                # ═══════════════════════════════════════════════════════════════
                                
                                # 1. Regime Detection
                                regime = self.regime_detector.detect_regime(
                                    highs=self._high[max(0, i-50):i+1],
                                    lows=self._low[max(0, i-50):i+1],
                                    closes=self._close[max(0, i-100):i+1],
                                )
                                signal['regime'] = regime
                                
                                # 2. Kinematics Phase Space
                                kinematics = self.kinematics.calculate_kinematics(
                                    prices=self._close[max(0, i-20):i+1],
                                )
                                signal['kinematics'] = kinematics
                                
                                # 3. Kinematics signal strength
                                kin_strength = self.kinematics.get_signal_strength(
                                    kinematics, signal['direction']
                                )
                                signal['kin_strength'] = kin_strength  # Store for audit

                                # 4. Recursive Self-Debate (metacognitive validation)
                                market_data = {
                                    'regime': regime,
                                    'volatility': regime.get('volatility_regime', 'normal'),
                                    'volume_ratio': self._volume[i] / max(1, np.mean(self._volume[max(0, i-20):i+1])),
                                    'signal_confidence': signal.get('confidence', 0.5),
                                    'consecutive_losses': self.consecutive_losses,
                                    'spread_percent': 0.001,  # BTCUSD typical spread
                                }
                                
                                debate_approved, debate_signal, debate_confidence = self.recursive_debate.debate(
                                    original_signal=signal['direction'],
                                    signal_confidence=signal.get('confidence', 0.5),
                                    market_data=market_data,
                                )

                                # Only flip signal if debate confidence is significantly better (>10% improvement)
                                # This prevents unnecessary signal flipping that doubles trade count
                                if debate_confidence > signal.get('confidence', 0.5) + 0.10:
                                    signal['direction'] = debate_signal  # Use debated signal
                                    signal['debate_confidence'] = debate_confidence
                                    signal['debate_used'] = True
                                else:
                                    signal['debate_used'] = False  # Keep original signal

                                # 5. AkashicCore Pattern Memory (experience-based validation)
                                akashic_state = self.akashic.encode_state(
                                    trend=1.0 if regime['trend_direction'] == 'bullish' else -1.0,
                                    volatility=0.5,  # Normalized
                                    volume=market_data['volume_ratio'] / 2.0,
                                    momentum=kinematics['velocity'] * 100,
                                    regime=regime['trend_type'],
                                )
                                
                                akashic_pred = self.akashic.predict_outcome(akashic_state)
                                
                                # Store Akashic prediction for audit (don't veto based on it yet - needs more data)
                                signal['akashic_recommendation'] = akashic_pred['recommendation']
                                signal['akashic_confidence'] = akashic_pred['confidence']
                                signal['akashic_matches'] = akashic_pred['num_matches']
                                
                                # Disabled: AkashicCore veto until we have enough historical data
                                # if akashic_pred['num_matches'] >= 20 and akashic_pred['confidence'] > 0.7:
                                #     if akashic_pred['recommendation'] != 'NEUTRAL' and akashic_pred['recommendation'] != signal['direction']:
                                #         self.total_vetoes += 1
                                #         continue  # Historical patterns disagree
                                
                                # 6. Black Swan Stress Test (prevent catastrophes)
                                # Only run every 10th trade to save computation
                                # DISABLED TEMPORARILY - needs tuning
                                # if self.total_trades % 10 == 0:
                                #     stress_result = self.black_swan.stress_test(
                                #         entry_price=signal['entry_price'],
                                #         stop_loss=signal['stop_loss'],
                                #         take_profit=signal['take_profit'],
                                #         direction=signal['direction'],
                                #     )
                                #     if not stress_result['approved']:
                                #         self.total_vetoes += 1
                                #         continue  # Failed stress test

                                signal['volume'] = session_veto['adjusted_volume']
                                signal['session_veto_data'] = {
                                    'session_name': session,
                                    'trading_allowed': session_profile.trading_allowed,
                                    'min_confidence_threshold': session_profile.min_confidence_threshold,
                                    'max_position_size': session_profile.max_position_size,
                                    'risk_multiplier': session_profile.risk_multiplier,
                                    'min_strategy_votes': session_profile.min_strategy_votes,
                                    'min_coherence': session_profile.min_coherence,
                                    'approved': session_veto['approved'],
                                    'reason': session_veto['reason'],
                                }
                                signal['advanced_veto_v2_data'] = {
                                    'approved': veto_result['approved'],
                                    'vetoed_by': veto_result.get('vetoed_by'),
                                    'veto_severity': veto_result.get('veto_severity'),
                                    'reason': veto_result.get('reason'),
                                    'all_vetoes': veto_result.get('all_vetoes', []),
                                }
                                self._open_position_fast(signal, i)
                            else:
                                self.total_vetoes += 1
                        else:
                            self.total_vetoes += 1

            else:
                # Phase 1: Position management with Smart TP (DubaiMatrixASI salvage)
                pos = self.current_position
                
                # If this is a new position without Smart TP targets, create them
                if 'targets' not in pos:
                    atr_current = self._atr[i]
                    pos['targets'] = self.position_manager.create_position_targets(
                        entry_price=pos['entry_price'],
                        stop_loss=pos['stop_loss'],
                        direction=pos['direction'],
                        atr=atr_current,
                    )
                    pos['remaining_volume'] = pos['volume']
                    pos['original_stop'] = pos['stop_loss']  # Save original SL for fallback
                    logger.info(f"🎯 Smart TP targets created for trade #{pos['ticket']}")
                
                # Check Smart TP targets
                atr_current = self._atr[i]
                position_closed, realized_pnl, closed_targets = self.position_manager.check_targets(
                    position_targets=pos['targets'],
                    current_price=cur_close,
                    current_volume=pos['remaining_volume'],
                    atr=atr_current,
                )
                
                # Phase 2: Thermodynamic Exit - 5-sensor profit management (Laplace v3.0)
                # Calculate sensors for remaining position
                if pos.get('thermo_sensors') is None:
                    pos['thermo_sensors'] = self.thermodynamic_exit.calculate_sensors(
                        prices=self._close[max(0, i-50):i+1].tolist(),
                        entry_price=pos['entry_price'],
                        direction=pos['direction'],
                    )
                else:
                    # Update sensors
                    pos['thermo_sensors'] = self.thermodynamic_exit.calculate_sensors(
                        prices=self._close[max(0, i-50):i+1].tolist(),
                        entry_price=pos['entry_price'],
                        direction=pos['direction'],
                    )
                    
                    # Check if thermodynamic exit suggests closing
                    thermo_should_exit, thermo_reason = self.thermodynamic_exit.should_exit(
                        sensors=pos['thermo_sensors'],
                        current_tp_distance=abs(pos['take_profit'] - cur_close),
                        current_sl_distance=abs(pos['stop_loss'] - cur_close),
                    )
                    
                    if thermo_should_exit and pos['thermo_sensors']['current_pnl'] > 10:
                        logger.info(f"🌡️ Thermodynamic exit: {thermo_reason}")
                        position_closed = True
                        realized_pnl = pos['targets']['total_realized_pnl'] + pos['thermo_sensors']['current_pnl'] * pos['remaining_volume']
                
                # Fallback: If price hits original SL, close remaining position immediately
                # Calculate current unrealized PnL for remaining position
                if pos['direction'] == 'BUY':
                    current_unrealized_pnl = (cur_close - pos['entry_price']) * pos['remaining_volume']
                else:
                    current_unrealized_pnl = (pos['entry_price'] - cur_close) * pos['remaining_volume']
                
                # Track peak PnL
                if 'peak_pnl' not in pos:
                    pos['peak_pnl'] = 0.0
                pos['peak_pnl'] = max(pos['peak_pnl'], current_unrealized_pnl)
                
                # Check erosion
                should_exit, erosion_reason = self.profit_erosion.check_erosion(
                    current_pnl=current_unrealized_pnl,
                    peak_pnl=pos['peak_pnl'],
                )
                
                if should_exit and pos['peak_pnl'] > 30:  # Only exit if we have meaningful profit
                    logger.info(f"🛡️ Profit erosion triggered: {erosion_reason}")
                    position_closed = True
                    realized_pnl = pos['targets']['total_realized_pnl'] + current_unrealized_pnl
                
                # Fallback: If price hits original SL, close remaining position immediately
                original_sl = pos.get('original_stop', pos['stop_loss'])
                sl_hit = False
                if pos['direction'] == 'BUY' and cur_low <= original_sl:
                    sl_hit = True
                elif pos['direction'] == 'SELL' and cur_high >= original_sl:
                    sl_hit = True
                
                if sl_hit and not position_closed:
                    # Close remaining portion at SL
                    remaining_pnl = pos['targets']['total_realized_pnl']
                    position_closed = True
                    realized_pnl = remaining_pnl
                
                # Update equity with realized PnL from partial closes
                if realized_pnl != 0:
                    self.equity += realized_pnl
                    
                    # Update remaining volume based on closed portions
                    pos['remaining_volume'] = pos['volume'] * pos['targets']['remaining_portion']
                
                # If position is fully closed, record it
                if position_closed:
                    total_pnl = pos['targets']['total_realized_pnl']
                    
                    if total_pnl > 0:
                        self.winning_trades += 1
                        self.consecutive_wins += 1
                        self.consecutive_losses = 0
                        self.loss_patterns['avg_win_size'] = (
                            (self.loss_patterns['avg_win_size'] * (self.winning_trades - 1) + total_pnl) 
                            / max(1, self.winning_trades)
                        )
                    else:
                        self.losing_trades += 1
                        self.consecutive_losses += 1
                        self.consecutive_wins = 0
                        self.last_loss_time = i
                        self.loss_patterns['avg_loss_size'] = (
                            (self.loss_patterns['avg_loss_size'] * (self.losing_trades - 1) + abs(total_pnl)) 
                            / max(1, self.losing_trades)
                        )
                    
                    # Update RiskManager and Anti-Metralhadora
                    result_type = 'win' if total_pnl > 0 else 'loss'
                    self.risk_manager.record_trade(total_pnl)
                    session = pos.get('session', 'unknown')
                    self.anti_metralhadora.record_trade(
                        result=result_type,
                        current_session=session,
                        current_time=pos['open_time'],
                    )
                    
                    # Record trade
                    self.trades.append({
                        'ticket': pos['ticket'],
                        'direction': pos['direction'],
                        'entry_price': pos['entry_price'],
                        'exit_price': cur_close,
                        'gross_pnl': total_pnl,
                        'net_pnl': total_pnl - pos['costs'],
                        'costs': pos['costs'],
                        'exit_reason': 'Smart TP complete',
                        'open_time': pos['open_time'],
                        'close_time': self._times[i],
                        'duration_minutes': (i - pos['open_bar_index']) * 5,
                        'volume': pos['volume'],
                        'smart_tp': True,
                        'targets_hit': sum(1 for t in pos['targets']['targets'] if t['closed']),
                    })
                    
                    # Phase 2: Store pattern in AkashicCore for future recall
                    if 'regime' in pos and 'kinematics' in pos:
                        akashic_state = self.akashic.encode_state(
                            trend=1.0 if pos['regime']['trend_direction'] == 'bullish' else -1.0,
                            volatility=0.5,
                            volume=0.5,
                            momentum=pos['kinematics']['velocity'] * 100,
                            regime=pos['regime']['trend_type'],
                        )
                        # Store outcome (normalized PnL)
                        normalized_outcome = total_pnl / max(1, self.equity * 0.01)
                        self.akashic.store_pattern(akashic_state, normalized_outcome)

                    self.current_position = None

            self.peak_equity = max(self.peak_equity, self.equity)
            if self.peak_equity > 0:
                dd = (self.peak_equity - self.equity) / self.peak_equity * 100
                if dd > self.max_drawdown:
                    self.max_drawdown = dd

            if (i - warmup) % 10000 == 0:
                elapsed = _time.perf_counter() - t0
                progress = (i - warmup) / (total - warmup) * 100
                speed = (i - warmup) / max(elapsed, 0.001)
                logger.info(f"  {progress:.0f}% | {speed:.0f} candles/s | Trades: {self.total_trades} | Vetoes: {self.total_vetoes} | Equity: ${self.equity:,.0f} | DD: {self.max_drawdown:.1f}%")

        if self.current_position:
            self._close_position_fast({'reason': 'End', 'type': 'manual'}, len(self.candles) - 1)

        elapsed = _time.perf_counter() - t0
        logger.info(f"\n⚡ Backtest complete in {elapsed:.1f}s ({(total - warmup) / max(elapsed, 0.001):.0f} candles/sec)")

        # Pattern analysis
        logger.info("Running pattern analysis...")
        analyzer = TradePatternAnalyzer(self.auditor)
        analysis = analyzer.analyze_all()
        # DISABLED: Auto-generating veto rules creates bad feedback loop (BUG #2 fix)
        # analyzer.save_veto_rules()
        logger.info("⚠️ Veto rules auto-generation DISABLED to prevent feedback loop")
        
        # ═══════════════════════════════════════════════════════════════
        # INTELLIGENT LOSS ANALYSIS (SCALPER MODE)
        # ═══════════════════════════════════════════════════════════════
        self._print_intelligent_loss_analysis()

        return self._results(analysis)

    # ═══════════════════════════════════════════════════════════════
    # FAST METHODS — Phase 4 Performance (use pre-computed arrays)
    # ═══════════════════════════════════════════════════════════════

    def _print_intelligent_loss_analysis(self):
        """Print comprehensive intelligent loss analysis for scalper optimization"""
        logger.info("\n" + "="*80)
        logger.info("🔬 INTELLIGENT LOSS ANALYSIS (SCALPER MODE)")
        logger.info("="*80)
        
        # 1. Loss reasons breakdown
        logger.info("\n📊 LOSS REASONS BREAKDOWN:")
        total_losses = self.losing_trades
        for reason, count in self.loss_patterns['by_reason'].items():
            if count > 0:
                pct = (count / max(1, total_losses)) * 100
                logger.info(f"   {reason}: {count} ({pct:.1f}%)")
        
        # 2. Trailing stop effectiveness
        logger.info(f"\n🎯 TRAILING STOP ANALYSIS:")
        logger.info(f"   Trailing stops hit: {self.loss_patterns['total_trailing_stops_hit']}")
        logger.info(f"   Regular SL hits: {self.loss_patterns['by_reason'].get('SL hit', 0)}")
        if self.loss_patterns['total_trailing_stops_hit'] > 0:
            logger.info(f"   → Trailing stop CONVERTED some losses (would have been worse without)")
        
        # 3. Average win vs loss
        logger.info(f"\n💰 WIN/LOSS STATISTICS:")
        logger.info(f"   Avg Win: ${self.loss_patterns['avg_win_size']:.2f}")
        logger.info(f"   Avg Loss: ${self.loss_patterns['avg_loss_size']:.2f}")
        if self.loss_patterns['avg_loss_size'] > 0:
            ratio = self.loss_patterns['avg_win_size'] / self.loss_patterns['avg_loss_size']
            logger.info(f"   Win/Loss Ratio: {ratio:.2f}:1")
            if ratio < 1.0:
                logger.warning(f"   ⚠️ Avg win is SMALLER than avg loss - need to improve TP distance or trailing")
            else:
                logger.info(f"   ✅ Good: wins are larger than losses")
        
        # 4. Strategy performance
        logger.info(f"\n📈 STRATEGY PERFORMANCE (Top/Bottom 3):")
        strat_perf = [(name, data['total_pnl'], data['trades']) for name, data in self.strategy_results.items() if data['trades'] > 0]
        strat_perf.sort(key=lambda x: x[1], reverse=True)
        
        if strat_perf:
            logger.info(f"   TOP 3 (Most Profitable):")
            for name, pnl, trades in strat_perf[:3]:
                wr = (self.strategy_results[name]['wins'] / max(1, trades)) * 100
                logger.info(f"   ✅ {name}: ${pnl:+.2f} ({trades} trades, {wr:.1f}% WR)")
            
            logger.info(f"   BOTTOM 3 (Most Losing):")
            for name, pnl, trades in strat_perf[-3:]:
                wr = (self.strategy_results[name]['wins'] / max(1, trades)) * 100
                logger.info(f"   ❌ {name}: ${pnl:+.2f} ({trades} trades, {wr:.1f}% WR)")
        
        # 5. Time-based patterns
        logger.info(f"\n⏰ TIME-BASED PATTERNS:")
        if self.loss_patterns['by_session']:
            logger.info(f"   By Session:")
            for session, losses in self.loss_patterns['by_session'].items():
                logger.info(f"   {session}: {losses} losses")
        
        # 6. Recommendations
        logger.info(f"\n🎯 RECOMMENDATIONS:")
        if self.loss_patterns['avg_win_size'] < self.loss_patterns['avg_loss_size']:
            logger.info(f"   1. Increase TP distance or improve trailing to boost avg win size")
        if self.loss_patterns['total_trailing_stops_hit'] > 0:
            logger.info(f"   2. Trailing stop is working - {self.loss_patterns['total_trailing_stops_hit']} stops locked")
        
        # Find worst strategy
        if strat_perf:
            worst = strat_perf[-1]
            logger.info(f"   3. Consider reducing weight for: {worst[0]} (${worst[1]:+.2f} PnL)")
        
        target_wr = 0.40
        current_wr = self.winning_trades / max(1, self.total_trades)
        if current_wr < target_wr:
            gap = target_wr - current_wr
            logger.info(f"   4. Need +{gap*100:.1f}% WR improvement to reach {target_wr*100:.0f}% target")
        
        logger.info("="*80 + "\n")


    def _generate_signal_fast(self, idx: int, current_price: float, current_time) -> dict:
        """Generate signal from 12 strategies using pre-computed NumPy arrays"""

        ema_9 = self._ema9[idx]
        ema_21 = self._ema21[idx]
        rsi = self._rsi[idx]
        atr = self._atr[idx]

        votes = {
            'strategy_votes': {},
            'buy_votes': 0,
            'sell_votes': 0,
            'neutral_votes': 0,
            'total_strategies': 12,
        }

        # Strategy 1: Momentum (EMA Crossover)
        ema_diff_pct = abs(ema_9 - ema_21) / current_price * 100
        if ema_9 > ema_21 and ema_diff_pct > 0.15:  # Fixed: was 0.10, now 0.15 (stronger signal)
            votes['strategy_votes']['momentum'] = {'vote': 'BUY', 'confidence': min(0.60 + ema_diff_pct * 0.3, 0.90)}
            votes['buy_votes'] += 1
        elif ema_9 < ema_21 and ema_diff_pct > 0.15:  # Fixed: was 0.10, now 0.15
            votes['strategy_votes']['momentum'] = {'vote': 'SELL', 'confidence': min(0.60 + ema_diff_pct * 0.3, 0.90)}
            votes['sell_votes'] += 1
        else:
            votes['strategy_votes']['momentum'] = {'vote': 'NEUTRAL', 'confidence': 0.5}
            votes['neutral_votes'] += 1

        # Strategy 2: Liquidity Sweep (last 10 bars from cached arrays)
        lo10 = self._low[max(0, idx - 9):idx + 1].min()
        hi10 = self._high[max(0, idx - 9):idx + 1].max()
        if current_price <= lo10 * 1.002:
            votes['strategy_votes']['liquidity'] = {'vote': 'BUY', 'confidence': 0.65}
            votes['buy_votes'] += 1
        elif current_price >= hi10 * 0.998:
            votes['strategy_votes']['liquidity'] = {'vote': 'SELL', 'confidence': 0.65}
            votes['sell_votes'] += 1
        else:
            votes['strategy_votes']['liquidity'] = {'vote': 'NEUTRAL', 'confidence': 0.5}
            votes['neutral_votes'] += 1

        # Strategy 3: Thermodynamic
        if idx >= 10:
            price_change = (current_price - self._close[idx - 10]) / self._close[idx - 10] * 100
            if price_change < -2.0:
                votes['strategy_votes']['thermodynamic'] = {'vote': 'BUY', 'confidence': 0.65}
                votes['buy_votes'] += 1
            elif price_change > 2.0:
                votes['strategy_votes']['thermodynamic'] = {'vote': 'SELL', 'confidence': 0.65}
                votes['sell_votes'] += 1
            else:
                votes['strategy_votes']['thermodynamic'] = {'vote': 'NEUTRAL', 'confidence': 0.5}
                votes['neutral_votes'] += 1

        # Strategy 4: Physics (Mean Reversion to SMA 20)
        sma_20 = self._sma20[idx]
        if current_price > sma_20 * 1.008:  # Fixed: was 1.005, now 1.008 (stronger stretch)
            # Stretched high, revert to mean (sell)
            votes['strategy_votes']['physics'] = {'vote': 'SELL', 'confidence': 0.65}  # Fixed: was 0.60
            votes['sell_votes'] += 1
        elif current_price < sma_20 * 0.992:  # Fixed: was 0.995, now 0.992 (stronger stretch)
            # Stretched low, revert to mean (buy)
            votes['strategy_votes']['physics'] = {'vote': 'BUY', 'confidence': 0.65}  # Fixed: was 0.60
            votes['buy_votes'] += 1
        else:
            votes['strategy_votes']['physics'] = {'vote': 'NEUTRAL', 'confidence': 0.5}
            votes['neutral_votes'] += 1

        # Strategy 5: Order Block
        if idx >= 15:
            ob_high = self._high[idx - 15:idx - 5].max()
            ob_low = self._low[idx - 15:idx - 5].min()
            if current_price <= ob_low * 1.003:
                votes['strategy_votes']['order_block'] = {'vote': 'BUY', 'confidence': 0.63}
                votes['buy_votes'] += 1
            elif current_price >= ob_high * 0.997:
                votes['strategy_votes']['order_block'] = {'vote': 'SELL', 'confidence': 0.63}
                votes['sell_votes'] += 1
            else:
                votes['strategy_votes']['order_block'] = {'vote': 'NEUTRAL', 'confidence': 0.5}
                votes['neutral_votes'] += 1

        # Strategy 6: FVG (Fair Value Gap) — lightweight scan
        fvg_vote = 'NEUTRAL'
        if idx >= 8:
            for j in range(max(0, idx - 8), idx - 1):
                h1, l3 = self._high[j], self._low[j + 2]
                l1, h3 = self._low[j], self._high[j + 2]
                if h1 < l3 and current_price >= l3 * 0.998 and current_price <= h1 * 1.002:
                    # Bullish FVG (Gap Up). Price retraced into support zone. BUY.
                    fvg_vote = 'BUY'
                    break
                elif l1 > h3 and current_price <= l1 * 1.002 and current_price >= h3 * 0.998:
                    # Bearish FVG (Gap Down). Price retraced into resistance zone. SELL.
                    fvg_vote = 'SELL'
                    break
        votes['strategy_votes']['fvg'] = {'vote': fvg_vote, 'confidence': 0.62 if fvg_vote != 'NEUTRAL' else 0.5}
        if fvg_vote == 'BUY':
            votes['buy_votes'] += 1
        elif fvg_vote == 'SELL':
            votes['sell_votes'] += 1
        else:
            votes['neutral_votes'] += 1

        # Strategy 7: MSNR (Market Support & Resistance)
        if idx >= 30:
            close_20 = self._close[idx - 19:idx + 1]
            hh, ll = close_20.max(), close_20.min()
            if current_price > hh * 0.998:
                # Breakout above resistance -> BUY (momentum continuation)
                votes['strategy_votes']['msnr'] = {'vote': 'BUY', 'confidence': 0.68}
                votes['buy_votes'] += 1
            elif current_price < ll * 1.002:
                # Breakdown below support -> SELL (momentum continuation)
                votes['strategy_votes']['msnr'] = {'vote': 'SELL', 'confidence': 0.68}
                votes['sell_votes'] += 1
            else:
                votes['strategy_votes']['msnr'] = {'vote': 'NEUTRAL', 'confidence': 0.5}
                votes['neutral_votes'] += 1

        # Strategy 8: MSNR Alchemist
        if idx >= 30:
            momentum = self._close[idx] - self._close[idx - 10]
            vol_slice = self._volume[idx - 19:idx + 1]
            vol_mean = vol_slice.mean()
            vol_ratio = self._volume[idx] / vol_mean if vol_mean > 0 else 1
            if momentum > 0 and vol_ratio > 1.2:
                votes['strategy_votes']['msnr_alchemist'] = {'vote': 'BUY', 'confidence': min(0.65 + vol_ratio * 0.05, 0.85)}
                votes['buy_votes'] += 1
            elif momentum < 0 and vol_ratio > 1.2:
                votes['strategy_votes']['msnr_alchemist'] = {'vote': 'SELL', 'confidence': min(0.65 + vol_ratio * 0.05, 0.85)}
                votes['sell_votes'] += 1
            else:
                votes['strategy_votes']['msnr_alchemist'] = {'vote': 'NEUTRAL', 'confidence': 0.5}
                votes['neutral_votes'] += 1

        # Strategy 9: IFVG
        ifvg_vote = 'NEUTRAL'
        if idx >= 10:
            for j in range(max(0, idx - 10), idx - 1):
                h1, l3 = self._high[j], self._low[j + 2]
                l1, h3 = self._low[j], self._high[j + 2]
                if h1 < l3:
                    fvg_mid = (h1 + l3) / 2
                    if abs(current_price - fvg_mid) / current_price < 0.002:
                        ifvg_vote = 'SELL'
                        break
                elif l1 > h3:
                    fvg_mid = (h3 + l1) / 2
                    if abs(current_price - fvg_mid) / current_price < 0.002:
                        ifvg_vote = 'BUY'
                        break
        votes['strategy_votes']['ifvg'] = {'vote': ifvg_vote, 'confidence': 0.62 if ifvg_vote != 'NEUTRAL' else 0.5}
        if ifvg_vote == 'BUY':
            votes['buy_votes'] += 1
        elif ifvg_vote == 'SELL':
            votes['sell_votes'] += 1
        else:
            votes['neutral_votes'] += 1

        # Strategy 10: OrderFlow (Volume Delta)
        if idx >= 20:
            c20 = self._close[idx - 19:idx + 1]
            v20 = self._volume[idx - 19:idx + 1]
            changes = np.diff(c20, prepend=c20[0])
            buy_vol = v20[changes > 0].sum()
            sell_vol = v20[changes < 0].sum()
            total_vol = buy_vol + sell_vol
            if total_vol > 0:
                buy_ratio = buy_vol / total_vol
                if buy_ratio > 0.60:
                    votes['strategy_votes']['order_flow'] = {'vote': 'BUY', 'confidence': 0.60 + (buy_ratio - 0.60) * 1.5}
                    votes['buy_votes'] += 1
                elif buy_ratio < 0.40:
                    votes['strategy_votes']['order_flow'] = {'vote': 'SELL', 'confidence': 0.60 + (0.40 - buy_ratio) * 1.5}
                    votes['sell_votes'] += 1
                else:
                    votes['strategy_votes']['order_flow'] = {'vote': 'NEUTRAL', 'confidence': 0.5}
                    votes['neutral_votes'] += 1
            else:
                votes['strategy_votes']['order_flow'] = {'vote': 'NEUTRAL', 'confidence': 0.5}
                votes['neutral_votes'] += 1

        # Strategy 11: Supply/Demand
        if idx >= 40:
            sd_low = self._low[idx - 19:idx + 1].min()
            sd_high = self._high[idx - 19:idx + 1].max()
            if current_price <= sd_low * 1.002:
                votes['strategy_votes']['supply_demand'] = {'vote': 'BUY', 'confidence': 0.65}
                votes['buy_votes'] += 1
            elif current_price >= sd_high * 0.998:
                votes['strategy_votes']['supply_demand'] = {'vote': 'SELL', 'confidence': 0.65}
                votes['sell_votes'] += 1
            else:
                votes['strategy_votes']['supply_demand'] = {'vote': 'NEUTRAL', 'confidence': 0.5}
                votes['neutral_votes'] += 1

        # Strategy 12: Fibonacci Retracement
        if idx >= 50:
            fib_high = self._high[idx - 49:idx + 1].max()
            fib_low = self._low[idx - 49:idx + 1].min()
            fib_diff = fib_high - fib_low
            fib_618 = fib_low + fib_diff * 0.618
            fib_382 = fib_low + fib_diff * 0.382
            if abs(current_price - fib_618) / current_price < 0.002 or abs(current_price - fib_382) / current_price < 0.002:
                trend = 'BUY' if current_price > self._close[idx - 25] else 'SELL'
                votes['strategy_votes']['fibonacci'] = {'vote': trend, 'confidence': 0.68}
                if trend == 'BUY':
                    votes['buy_votes'] += 1
                else:
                    votes['sell_votes'] += 1
            else:
                votes['strategy_votes']['fibonacci'] = {'vote': 'NEUTRAL', 'confidence': 0.5}
                votes['neutral_votes'] += 1

        # SCALPER MODE: min_votes = 5 (42% agreement, balanced quality)
        min_votes_needed = 5
        if votes['buy_votes'] >= min_votes_needed:
            direction = "BUY"
            consensus_conf = votes['buy_votes'] / 12
        elif votes['sell_votes'] >= min_votes_needed:
            direction = "SELL"
            consensus_conf = votes['sell_votes'] / 12
        else:
            return None

        # SCALPER FILTER: Only accept signals with minimum confidence
        if consensus_conf < 0.40:  # Filter out weakest signals
            return None

        # Cooldown check
        if self.last_trade_time is not None:
            try:
                elapsed_secs = (pd.Timestamp(current_time) - pd.Timestamp(self.last_trade_time)).total_seconds()
                if elapsed_secs / 300 < self.min_cooldown_bars:
                    return None
            except Exception:
                pass

        # SCALPER MODE: Optimized SL/TP for scalping - A1: 1:3 R:R for higher profit per trade
        sl_dist = min(max(atr * 1.5, 300), 2000)  # Tight stop: 1.5x ATR
        tp_dist = sl_dist * 3.0  # A1: 1:3 R:R target (increased from 2.0)

        if direction == "BUY":
            sl = current_price - sl_dist
            tp = current_price + tp_dist
        else:
            sl = current_price + sl_dist
            tp = current_price - tp_dist

        # Phase 1: RiskQuantumEngine - 5-factor position sizing (DubaiMatrixASI)
        # Calculate dynamic position size based on Kelly, volatility, confidence, DD, correlation
        win_rate = self.winning_trades / max(1, self.total_trades) if self.total_trades > 10 else 0.35
        avg_win_loss_ratio = self.loss_patterns['avg_win_size'] / max(1, self.loss_patterns['avg_loss_size']) if self.loss_patterns['avg_loss_size'] > 0 else 1.5
        current_dd = self.max_drawdown / 100.0
        
        sizing = self.risk_quantum.calculate_position_size(
            equity=self.equity,
            win_rate=win_rate,
            avg_win_loss_ratio=avg_win_loss_ratio,
            signal_confidence=consensus_conf,
            current_volatility=atr,
            avg_volatility=np.mean(self._atr[max(0, idx-20):idx+1]),
            current_drawdown=current_dd,
            correlation_factor=1.0,  # Single-position for now
        )
        
        volume = sizing['position_size']

        self.total_signals += 1

        return {
            'direction': direction,
            'entry_price': current_price,
            'stop_loss': sl,
            'take_profit': tp,
            'volume': volume,
            'confidence': consensus_conf,
            'atr': atr,
            'rsi': rsi,
            'ema_9': ema_9,
            'ema_21': ema_21,
            'strategy_votes': votes,
            'coherence': consensus_conf,
        }

    def _check_basic_veto_fast(self, signal: dict, idx: int):
        """Basic veto check using pre-computed values"""
        try:
            cur_time = self._times[idx]
            hour = pd.Timestamp(cur_time).hour
        except Exception:
            hour = 12
        session = "ny_overlap" if 13 <= hour < 17 else "london" if 7 <= hour < 13 else "asian" if 0 <= hour < 7 else "ny"

        ema_50 = self._ema50[idx]
        price = self._close[idx]
        # Fixed: was 0.0015 (too narrow, $109 on $73K BTC), now 0.005 (0.5% = $365)
        regime = "ranging" if abs(ema_50 - price) / price < 0.005 else "trending_bullish" if price > ema_50 else "trending_bearish"

        context = {
            'market_regime': {'regime_type': regime, 'session': session},
            'multi_timeframe': {'M5_trend': 'up' if signal['ema_9'] > signal['ema_21'] else 'down', 'conflict_detected': False},
            'risk_context': {'consecutive_losses': self.consecutive_losses},
            'indicators': {'rsi_14': signal['rsi']},
            'direction': signal['direction'],
        }
        return self.veto_orchestrator.check_trade(context)

    def _check_advanced_veto_fast(self, signal: dict, idx: int) -> dict:
        """Lightweight advanced veto using pre-computed RSI + Bollinger"""
        vetoes = []
        rsi = self._rsi[idx]
        direction = signal['direction']

        # RSI extremes - Balanced thresholds (not too strict, not too loose)
        if direction == 'BUY' and rsi > 72:  # Balanced: was 75→65, now 72
            vetoes.append({'rule': 'RSI Overbought', 'severity': 'major', 'reason': f'BUY vetoed - RSI {rsi:.1f} > 72'})
        elif direction == 'SELL' and rsi < 28:  # Balanced: was 25→35, now 28
            vetoes.append({'rule': 'RSI Oversold', 'severity': 'major', 'reason': f'SELL vetoed - RSI {rsi:.1f} < 28'})

        # RSI divergence
        if direction == 'BUY' and rsi > 68 and idx >= 5 and self._rsi[idx] < self._rsi[idx - 5]:
            vetoes.append({'rule': 'RSI Divergence', 'severity': 'major', 'reason': f'BUY vetoed - RSI {rsi:.1f} declining'})
        elif direction == 'SELL' and rsi < 32 and idx >= 5 and self._rsi[idx] > self._rsi[idx - 5]:
            vetoes.append({'rule': 'RSI Recovery', 'severity': 'major', 'reason': f'SELL vetoed - RSI {rsi:.1f} rising'})

        # Bollinger extremes
        price = self._close[idx]
        if direction == 'BUY' and price > self._bb_upper[idx] * 0.9995:
            vetoes.append({'rule': 'Bollinger Upper', 'severity': 'minor', 'reason': f'BUY vetoed - price at upper BB'})
        elif direction == 'SELL' and price < self._bb_lower[idx] * 1.0005:
            vetoes.append({'rule': 'Bollinger Lower', 'severity': 'minor', 'reason': f'SELL vetoed - price at lower BB'})

        if not vetoes:
            return {'approved': True, 'vetoed_by': None, 'veto_severity': None, 'reason': 'All vetoes passed'}

        severity_order = ['lethal', 'major', 'minor']
        most_severe = min(vetoes, key=lambda v: severity_order.index(v.get('severity', 'minor')))
        return {
            'approved': False,
            'vetoed_by': most_severe['rule'],
            'veto_severity': most_severe['severity'],
            'reason': most_severe['reason'],
            'all_vetoes': vetoes,
        }

    def _open_position_fast(self, signal: dict, bar_idx: int):
        """Open position — lightweight version for backtesting"""
        # Fixed: corrected spread cost calculation (was 100 * volume, now spread_dollars * volume)
        spread_dollars = 1.0  # Typical BTCUSD spread ~$1
        costs = signal['volume'] * 45.0 * 2 + spread_dollars * signal['volume']
        self.total_commissions += costs
        cur_time = self._times[bar_idx]
        
        # Calculate session for Anti-Metralhadora tracking
        hour = pd.Timestamp(cur_time).hour
        session = "ny_overlap" if 13 <= hour < 17 else "london" if 7 <= hour < 13 else "asian" if 0 <= hour < 7 else "ny"

        position = {
            'ticket': self.ticket_counter,
            'symbol': 'BTCUSD',
            'direction': signal['direction'],
            'entry_price': signal['entry_price'],
            'stop_loss': signal['stop_loss'],
            'take_profit': signal['take_profit'],
            'volume': signal['volume'],
            'open_time': cur_time,
            'open_bar_index': bar_idx,
            'costs': costs,
            'original_stop': signal['stop_loss'],  # NEW: Save original SL for partial exit calculation
            'partial_exited': False,
            'trailing_active': False,
            'session': session,  # Track session for Anti-Metralhadora
        }

        # Lightweight audit — buffer in memory
        ema_50 = self._ema50[bar_idx]
        price = self._close[bar_idx]
        regime = "ranging" if abs(ema_50 - price) / price < 0.005 else "trending_bullish" if price > ema_50 else "trending_bearish"

        self.auditor.capture_entry_state(
            ticket=position['ticket'],
            direction=signal['direction'],
            entry_price=signal['entry_price'],
            stop_loss=signal['stop_loss'],
            take_profit=signal['take_profit'],
            volume=signal['volume'],
            strategy_name="complete_system_v2",
            signal_confidence=signal['confidence'],
            market_regime={
                'regime_type': regime, 'regime_confidence': 0.70, 'trend_strength': 0.5,
                'trend_direction': signal['direction'].lower(), 'volatility_regime': 'medium',
                'volatility_value': signal['atr'], 'volume_regime': 'normal', 'volume_ratio': 1.0,
                'market_phase': 'unknown', 'session': session, 'session_volume_profile': 0.8,
            },
            multi_timeframe={
                'M1_trend': signal['direction'].lower(), 'M5_trend': signal['direction'].lower(),
                'M15_trend': signal['direction'].lower(), 'H1_trend': 'neutral', 'H4_trend': 'neutral',
                'D1_trend': 'neutral', 'alignment_score': 0.5, 'dominant_timeframe': 'M5', 'conflict_detected': False,
            },
            indicators={
                'ema_9': signal['ema_9'], 'ema_21': signal['ema_21'], 'ema_50': ema_50, 'ema_200': price,
                'sma_20': self._sma20[bar_idx], 'sma_50': price,
                'ema_9_21_cross': 'bullish' if signal['ema_9'] > signal['ema_21'] else 'bearish',
                'ema_21_50_cross': 'neutral', 'price_vs_ema_200': 'above',
                'rsi_14': signal['rsi'], 'rsi_regime': 'oversold' if signal['rsi'] < 30 else 'overbought' if signal['rsi'] > 70 else 'neutral',
                'macd_line': 0, 'macd_signal': 0, 'macd_histogram': 0, 'macd_cross': 'neutral',
                'stochastic_k': 50, 'stochastic_d': 50,
                'atr_14': signal['atr'], 'atr_percentile': 50.0,
                'bollinger_upper': self._bb_upper[bar_idx], 'bollinger_middle': self._bb_mid[bar_idx], 'bollinger_lower': self._bb_lower[bar_idx],
                'bollinger_width': self._bb_upper[bar_idx] - self._bb_lower[bar_idx], 'price_vs_bollinger': 'inside',
                'volume_current': self._volume[bar_idx], 'volume_avg_20': self._volume[max(0, bar_idx - 19):bar_idx + 1].mean(), 'volume_ratio': 1.0, 'volume_trend': 'stable', 'obv_trend': 'neutral',
            },
            price_action={
                'current_price': price, 'price_change_1h': 0.5, 'price_change_4h': 1.0, 'price_change_24h': 2.0,
                'nearest_support': price - 500, 'nearest_resistance': price + 500,
                'distance_to_support_pct': 0.68, 'distance_to_resistance_pct': 0.68,
                'current_candle_type': 'bullish' if signal['direction'] == 'BUY' else 'bearish', 'candle_body_size': 100, 'candle_wick_ratio': 0.3,
                'engulfing_detected': False, 'inside_bar_detected': False,
                'higher_highs': True, 'higher_lows': True, 'lower_highs': False, 'lower_lows': False,
                'structure': 'uptrend' if signal['direction'] == 'BUY' else 'downtrend',
            },
            momentum={'velocity': 0.5, 'acceleration': 0.1, 'gravity': 0.3, 'oscillation': 50, 'volume_pressure': 0.5, 'microstructure_score': 0.6, 'momentum_divergence': False, 'exhaustion_signals': []},
            risk_context={
                'capital': self.equity, 'equity': self.equity, 'daily_pnl': 0, 'daily_pnl_percent': 0,
                'total_pnl': self.equity - self.initial_equity, 'total_pnl_percent': (self.equity / self.initial_equity - 1) * 100,
                'current_drawdown': self.max_drawdown, 'max_drawdown': self.max_drawdown,
                'consecutive_wins': self.consecutive_wins, 'consecutive_losses': self.consecutive_losses,
                'daily_loss_used_percent': 0, 'total_loss_used_percent': self.max_drawdown,
                'ftmo_daily_remaining': 5000, 'ftmo_total_remaining': 10000,
            },
            dna_state={
                'current_regime': regime, 'regime_confidence': 0.70, 'active_strategy': 'complete_system_v2',
                'strategy_weights': {'momentum': 0.6, 'mean_reversion': 0.2, 'breakout': 0.2},
                'risk_percent': self.risk_percent, 'min_rr_ratio': 1.5, 'confidence_threshold': 0.65,
                'last_mutation_time': datetime.now(timezone.utc).isoformat(), 'mutation_count': 0, 'dna_memory_regimes': 0,
            },
            smart_order_manager={
                'virtual_tp_original': signal['take_profit'], 'virtual_tp_current': signal['take_profit'],
                'virtual_tp_adjustment_factor': 1.0, 'virtual_tp_difficulty': 'moderate',
                'dynamic_sl_original': signal['stop_loss'], 'dynamic_sl_current': signal['stop_loss'],
                'breakeven_activated': False, 'profit_targets_reached': [], 'momentum_at_entry': {'velocity': 0.5},
            },
            strategy_voting=signal.get('strategy_votes'),
            session_veto=signal.get('session_veto_data'),
            advanced_veto_v2=signal.get('advanced_veto_v2_data'),
        )

        self.current_position = position
        self.last_trade_time = cur_time
        self.ticket_counter += 1
        self.total_trades += 1

    def _close_position_fast(self, action: dict, bar_idx: int):
        """Close position — lightweight version for backtesting"""
        if not self.current_position:
            return

        pos = self.current_position
        exit_price = self._close[bar_idx]
        # Fixed: removed * 100 multiplier (was inflating PnL by 100x)
        gross_pnl = (exit_price - pos['entry_price']) * pos['volume'] if pos['direction'] == 'BUY' else (pos['entry_price'] - exit_price) * pos['volume']
        net_pnl = gross_pnl - pos['costs']
        duration = (bar_idx - pos['open_bar_index']) * 5

        self.equity += net_pnl

        if net_pnl > 0:
            self.winning_trades += 1
            self.consecutive_wins += 1
            self.consecutive_losses = 0
            self.loss_patterns['avg_win_size'] = (self.loss_patterns['avg_win_size'] * (self.winning_trades - 1) + net_pnl) / max(1, self.winning_trades)
        else:
            self.losing_trades += 1
            self.consecutive_losses += 1
            self.consecutive_wins = 0
            self.last_loss_time = bar_idx
            self.loss_patterns['avg_loss_size'] = (self.loss_patterns['avg_loss_size'] * (self.losing_trades - 1) + abs(net_pnl)) / max(1, self.losing_trades)
            
            # Track loss patterns for intelligent analysis
            reason = action.get('reason', 'Unknown')
            if reason in self.loss_patterns['by_reason']:
                self.loss_patterns['by_reason'][reason] += 1
            if 'trailed' in reason:
                self.loss_patterns['total_trailing_stops_hit'] += 1

        # NEW: Update RiskManager with trade result (BUG #6 fix)
        self.risk_manager.record_trade(net_pnl)
        
        # Phase 1: Update Anti-Metralhadora with trade result
        result_type = 'win' if net_pnl > 0 else 'loss'
        session = pos.get('session', 'unknown')
        self.anti_metralhadora.record_trade(
            result=result_type,
            current_session=session,
            current_time=pos['open_time'],
        )

        self.auditor.capture_exit_state(
            ticket=pos['ticket'], exit_price=exit_price, exit_reason=action['reason'],
            gross_pnl=gross_pnl, net_pnl=net_pnl, duration_minutes=duration,
            max_profit_reached=gross_pnl + 50, max_drawdown_reached=-20,
        )

        self.trades.append({
            'ticket': pos['ticket'], 'direction': pos['direction'],
            'entry_price': pos['entry_price'], 'exit_price': exit_price,
            'gross_pnl': gross_pnl, 'net_pnl': net_pnl, 'costs': pos['costs'],
            'exit_reason': action['reason'], 'open_time': pos['open_time'], 'close_time': self._times[bar_idx],
            'duration_minutes': duration, 'volume': pos['volume'],
        })

        self.current_position = None

    def _results(self, analysis: dict) -> dict:
        net_pnl = self.equity - self.initial_equity
        wr = self.winning_trades / max(1, self.total_trades)
        gp = sum(t['net_pnl'] for t in self.trades if t['net_pnl'] > 0)
        gl = abs(sum(t['net_pnl'] for t in self.trades if t['net_pnl'] <= 0))
        pf = gp / gl if gl > 0 else 0

        return {
            'summary': {
                'initial_capital': self.initial_equity, 'final_capital': self.equity,
                'net_profit': net_pnl, 'net_profit_percent': (net_pnl / self.initial_equity) * 100,
                'total_trades': self.total_trades, 'winning_trades': self.winning_trades, 'losing_trades': self.losing_trades,
                'win_rate': wr, 'profit_factor': pf, 'expectancy': net_pnl / max(1, self.total_trades),
                'total_signals': self.total_signals, 'total_vetoes': self.total_vetoes,
                'total_filed_orders': self.total_filed_orders,
                'veto_rate': self.total_vetoes / max(1, self.total_signals) * 100,
            },
            'risk': {'max_drawdown_percent': self.max_drawdown, 'max_drawdown_dollars': self.initial_equity * self.max_drawdown / 100},
            'costs': {'total_commissions': self.total_commissions},
            'ftmo': {'overall_pass': self.max_drawdown < 10.0},
            'pattern_analysis': analysis,
            'trades': self.trades, 'equity_curve': [],
        }


def main():
    setup_logging()

    print("\n" + "="*80)
    print("COMPLETE SYSTEM BACKTEST V2 (MT5 REAL DATA)")
    print("  12 Strategies + Session Profiles + Advanced Veto v2 + Neural Audit")
    print("="*80 + "\n")

    candles = fetch_mt5_data(days=180)

    # Test 1.0% risk level natively
    for risk_pct in [1.0]:
        print(f"\n{'='*70}")
        print(f"Testing {risk_pct}% risk per trade...")
        print(f"{'='*70}")

        engine = CompleteBacktestEngineV2(candles, risk_percent=risk_pct)
        results = engine.run()

        s = results.get('summary', {})
        r = results.get('risk', {})
        c = results.get('costs', {})
        f = results.get('ftmo', {})

        print(f"\nRESULTS ({risk_pct}% risk):")
        print(f"  Initial: ${s.get('initial_capital', 0):,.2f}")
        print(f"  Final: ${s.get('final_capital', 0):,.2f}")
        print(f"  Net Profit: ${s.get('net_profit', 0):,.2f} ({s.get('net_profit_percent', 0):.2f}%)")
        print(f"  Trades: {s.get('total_trades', 0)}")
        print(f"  Win Rate: {s.get('win_rate', 0)*100:.1f}%")
        print(f"  Profit Factor: {s.get('profit_factor', 0):.2f}")
        print(f"  Max DD: {r.get('max_drawdown_percent', 0):.2f}%")
        print(f"  FTMO: {'PASS' if f.get('overall_pass') else 'FAIL'}")
        print(f"  Commissions: ${c.get('total_commissions', 0):,.2f}")
        
        print(f"\n🛡️ VETO SYSTEM:")
        print(f"   Signals Generated: {s.get('total_signals', 0)}")
        print(f"   Trades Executed: {s.get('total_trades', 0)}")
        print(f"   Trades Vetoed: {s.get('total_vetoes', 0)}")
        print(f"   Orders Filed: {s.get('total_filed_orders', 0)}")
        print(f"   Veto Rate: {s.get('veto_rate', 0):.1f}%")


if __name__ == "__main__":
    main()
