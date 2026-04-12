"""
Neural Regime Profiles - Dynamic self-evolving profiles for each regime
CEO: Qwen Code | Created: 2026-04-10

5 Neural Profiles:
1. AGGRESSIVE - High risk, high reward (trending strong)
2. MOMENTUM - Follow trends (trending moderate)
3. MEAN_REVERSION - Trade ranges (ranging markets)
4. DEFENSIVE - Low risk, survival mode (high volatility/crash)
5. SCALPER - Quick trades, tight stops (low volatility chop)

Each profile auto-evolves based on:
- Performance in current regime
- Market physics analysis
- Complex graphical pattern recognition
- DNA-driven adaptation
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger


class NeuralProfileType(Enum):
    """5 neural profile types"""
    AGGRESSIVE = "aggressive"
    MOMENTUM = "momentum"
    MEAN_REVERSION = "mean_reversion"
    DEFENSIVE = "defensive"
    SCALPER = "scalper"


@dataclass
class ProfileMetrics:
    """Performance metrics for a profile"""
    total_trades: int = 0
    wins: int = 0
    losses: int = 0
    win_rate: float = 0.5
    avg_profit: float = 0.0
    avg_loss: float = 0.0
    profit_factor: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    regime_suitability: Dict[str, float] = field(default_factory=dict)
    last_updated: Optional[str] = None


@dataclass
class NeuralProfile:
    """Complete neural profile with dynamic parameters"""
    name: NeuralProfileType
    confidence: float = 0.5  # How confident we are in this profile
    
    # Operation dynamics
    max_position_size: float = 0.10  # Max lot size
    risk_per_trade: float = 0.5  # Risk %
    max_trades_per_day: int = 10
    min_rr_ratio: float = 1.5
    confidence_threshold: float = 0.65
    
    # Entry/Exit behavior
    entry_style: str = "standard"  # standard, limit, market, scale_in
    exit_style: str = "standard"  # standard, trailing, partial, scale_out
    stop_loss_style: str = "fixed"  # fixed, atr_based, dynamic, breakeven_fast
    take_profit_style: str = "fixed"  # fixed, runner, scale_out
    
    # Risk behavior
    pyramiding_allowed: bool = False
    max_pyramid_levels: int = 1
    hedging_allowed: bool = False
    counter_trend_allowed: bool = False
    
    # Session preferences
    preferred_sessions: List[str] = field(default_factory=lambda: ["ny_overlap", "london", "ny"])
    avoided_sessions: List[str] = field(default_factory=lambda: ["asian", "weekend"])
    
    # Volatility preferences
    min_volatility: float = 0.0
    max_volatility: float = 1.0
    preferred_atr_percentile: Tuple[float, float] = field(default=(20.0, 80.0))
    
    # Performance tracking
    metrics: ProfileMetrics = field(default_factory=ProfileMetrics)
    regime_performance: Dict[str, float] = field(default_factory=dict)  # regime -> win_rate
    last_regime: str = "unknown"
    
    # DNA mutation history
    mutation_count: int = 0
    last_mutation_time: Optional[str] = None
    adaptation_speed: float = 0.1  # How fast profile adapts (0-1)


class NeuralRegimeProfiler:
    """
    Neural Regime Profiling System
    
    Features:
    1. Auto-detect best profile for current regime
    2. Complex analysis (graphics + market + physics)
    3. Self-evolution based on performance
    4. DNA-driven adaptation
    """
    
    def __init__(self, dna_params: Dict[str, Any]):
        self.dna_params = dna_params
        
        # Initialize 5 neural profiles
        self.profiles = {
            NeuralProfileType.AGGRESSIVE: self._create_aggressive_profile(),
            NeuralProfileType.MOMENTUM: self._create_momentum_profile(),
            NeuralProfileType.MEAN_REVERSION: self._create_mean_reversion_profile(),
            NeuralProfileType.DEFENSIVE: self._create_defensive_profile(),
            NeuralProfileType.SCALPER: self._create_scalper_profile(),
        }
        
        # Current active profile
        self.active_profile: Optional[NeuralProfile] = None
        self.current_regime: str = "unknown"
        
        # Profile selection history
        self.selection_history: List[Dict[str, Any]] = []
        
        logger.info("🧠 Neural Regime Profiler initialized")
        logger.info(f"   5 Profiles: Aggressive, Momentum, Mean Reversion, Defensive, Scalper")
    
    def _create_aggressive_profile(self) -> NeuralProfile:
        """AGGRESSIVE - High risk, high reward for strong trends"""
        return NeuralProfile(
            name=NeuralProfileType.AGGRESSIVE,
            max_position_size=0.20,
            risk_per_trade=1.0,
            max_trades_per_day=15,
            min_rr_ratio=1.3,
            confidence_threshold=0.60,
            entry_style="market",
            exit_style="scale_out",
            stop_loss_style="atr_based",
            take_profit_style="scale_out",
            pyramiding_allowed=True,
            max_pyramid_levels=3,
            counter_trend_allowed=False,
            preferred_sessions=["ny_overlap", "london"],
            avoided_sessions=["asian"],
            min_volatility=0.5,
            max_volatility=1.0,
        )
    
    def _create_momentum_profile(self) -> NeuralProfile:
        """MOMENTUM - Follow trends for moderate trends"""
        return NeuralProfile(
            name=NeuralProfileType.MOMENTUM,
            max_position_size=0.15,
            risk_per_trade=0.75,
            max_trades_per_day=12,
            min_rr_ratio=1.5,
            confidence_threshold=0.65,
            entry_style="standard",
            exit_style="trailing",
            stop_loss_style="dynamic",
            take_profit_style="runner",
            pyramiding_allowed=True,
            max_pyramid_levels=2,
            counter_trend_allowed=False,
            preferred_sessions=["ny_overlap", "london", "ny"],
            avoided_sessions=["asian", "weekend"],
            min_volatility=0.3,
            max_volatility=0.8,
        )
    
    def _create_mean_reversion_profile(self) -> NeuralProfile:
        """MEAN REVERSION - Trade ranges for ranging markets"""
        return NeuralProfile(
            name=NeuralProfileType.MEAN_REVERSION,
            max_position_size=0.10,
            risk_per_trade=0.5,
            max_trades_per_day=20,
            min_rr_ratio=1.8,
            confidence_threshold=0.70,
            entry_style="limit",
            exit_style="partial",
            stop_loss_style="fixed",
            take_profit_style="fixed",
            pyramiding_allowed=False,
            max_pyramid_levels=1,
            counter_trend_allowed=True,
            preferred_sessions=["ny_overlap", "london"],
            avoided_sessions=["asian"],
            min_volatility=0.2,
            max_volatility=0.6,
        )
    
    def _create_defensive_profile(self) -> NeuralProfile:
        """DEFENSIVE - Low risk, survival mode for high vol/crash"""
        return NeuralProfile(
            name=NeuralProfileType.DEFENSIVE,
            max_position_size=0.05,
            risk_per_trade=0.25,
            max_trades_per_day=5,
            min_rr_ratio=2.0,
            confidence_threshold=0.80,
            entry_style="limit",
            exit_style="partial",
            stop_loss_style="breakeven_fast",
            take_profit_style="fixed",
            pyramiding_allowed=False,
            max_pyramid_levels=1,
            hedging_allowed=True,
            counter_trend_allowed=False,
            preferred_sessions=["ny_overlap"],
            avoided_sessions=["asian", "weekend", "london"],
            min_volatility=0.0,
            max_volatility=0.4,
        )
    
    def _create_scalper_profile(self) -> NeuralProfile:
        """SCALPER - Quick trades, tight stops for low vol chop"""
        return NeuralProfile(
            name=NeuralProfileType.SCALPER,
            max_position_size=0.10,
            risk_per_trade=0.3,
            max_trades_per_day=30,
            min_rr_ratio=1.2,
            confidence_threshold=0.60,
            entry_style="market",
            exit_style="standard",
            stop_loss_style="fixed",
            take_profit_style="fixed",
            pyramiding_allowed=False,
            max_pyramid_levels=1,
            counter_trend_allowed=True,
            preferred_sessions=["ny_overlap", "london", "ny"],
            avoided_sessions=["weekend"],
            min_volatility=0.1,
            max_volatility=0.5,
        )
    
    def select_best_profile(self, candles: pd.DataFrame, market_state: Dict[str, Any]) -> NeuralProfile:
        """
        Select best profile for current conditions using complex analysis
        
        Analyzes:
        - Market regime (trending, ranging, crashing)
        - Volatility level
        - Session/time
        - Volume patterns
        - Price action characteristics
        - Physics-based market analysis
        
        Returns:
            NeuralProfile: Best profile for current conditions
        """
        if len(candles) < 100:
            return self.profiles[NeuralProfileType.MOMENTUM]
        
        # Complex market analysis
        regime_analysis = self._analyze_regime(candles)
        volatility_analysis = self._analyze_volatility(candles)
        session_analysis = self._analyze_session(candles)
        volume_analysis = self._analyze_volume(candles)
        physics_analysis = self._analyze_physics(candles)
        
        # Score each profile
        profile_scores = {}
        
        for profile_type, profile in self.profiles.items():
            score = 0.0
            
            # Regime suitability
            regime = regime_analysis['regime']
            if profile_type == NeuralProfileType.AGGRESSIVE and regime in ["trending_strong_bull", "trending_strong_bear"]:
                score += 0.3
            elif profile_type == NeuralProfileType.MOMENTUM and regime in ["trending_moderate_bull", "trending_moderate_bear"]:
                score += 0.3
            elif profile_type == NeuralProfileType.MEAN_REVERSION and regime == "ranging":
                score += 0.3
            elif profile_type == NeuralProfileType.DEFENSIVE and regime in ["crashing", "high_volatility"]:
                score += 0.3
            elif profile_type == NeuralProfileType.SCALPER and regime == "chop":
                score += 0.3
            
            # Volatility match
            vol_pct = volatility_analysis['atr_percentile']
            if profile.min_volatility <= vol_pct / 100 <= profile.max_volatility:
                score += 0.2
            
            # Session match
            current_session = session_analysis['current_session']
            if current_session in profile.preferred_sessions:
                score += 0.15
            elif current_session in profile.avoided_sessions:
                score -= 0.2
            
            # Volume characteristics
            if volume_analysis['volume_trend'] == "increasing" and profile_type in [NeuralProfileType.AGGRESSIVE, NeuralProfileType.MOMENTUM]:
                score += 0.15
            elif volume_analysis['volume_trend'] == "decreasing" and profile_type == NeuralProfileType.SCALPER:
                score += 0.15
            
            # Physics-based market state
            if physics_analysis['market_energy'] > 0.7 and profile_type == NeuralProfileType.AGGRESSIVE:
                score += 0.2
            elif physics_analysis['market_energy'] < 0.3 and profile_type == NeuralProfileType.MEAN_REVERSION:
                score += 0.2
            
            # Historical performance in this regime
            if regime in profile.regime_performance:
                hist_performance = profile.regime_performance[regime]
                score += hist_performance * 0.2  # Weight historical performance
            
            profile_scores[profile_type] = score
        
        # Select best profile
        best_profile_type = max(profile_scores, key=profile_scores.get)
        best_profile = self.profiles[best_profile_type]
        
        # Update confidence based on score spread
        scores = list(profile_scores.values())
        confidence = (max(scores) - np.mean(scores)) / max(0.01, np.std(scores)) if len(scores) > 1 else 0.5
        best_profile.confidence = max(0.1, min(0.95, 0.5 + confidence * 0.5))
        
        # Record selection
        self.selection_history.append({
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'selected_profile': best_profile_type.value,
            'regime': regime_analysis['regime'],
            'confidence': best_profile.confidence,
            'scores': {k.value: v for k, v in profile_scores.items()},
        })
        
        # Keep last 1000 selections
        if len(self.selection_history) > 1000:
            self.selection_history = self.selection_history[-1000:]
        
        self.active_profile = best_profile
        self.current_regime = regime_analysis['regime']
        
        logger.info(f"🧠 Profile Selected: {best_profile_type.value.upper()}")
        logger.info(f"   Regime: {regime_analysis['regime']}")
        logger.info(f"   Confidence: {best_profile.confidence:.2f}")
        logger.info(f"   Volatility: {volatility_analysis['atr_percentile']:.1f}%")
        logger.info(f"   Session: {session_analysis['current_session']}")
        
        return best_profile
    
    def _analyze_regime(self, candles: pd.DataFrame) -> Dict[str, Any]:
        """Analyze market regime"""
        close = candles['close'].iloc[-100:]
        
        # EMA alignment
        ema_9 = close.ewm(span=9).mean()
        ema_21 = close.ewm(span=21).mean()
        ema_50 = close.ewm(span=50).mean()
        ema_200_val = close.ewm(span=200).mean().iloc[-1] if len(close) >= 200 else close.iloc[-1]
        
        current_price = close.iloc[-1]
        
        # Trend strength
        if ema_9.iloc[-1] > ema_21.iloc[-1] > ema_50.iloc[-1] > ema_200_val:
            trend_strength = 1.0
            trend_dir = "bull"
        elif ema_9.iloc[-1] < ema_21.iloc[-1] < ema_50.iloc[-1] < ema_200_val:
            trend_strength = 1.0
            trend_dir = "bear"
        elif ema_9.iloc[-1] > ema_21.iloc[-1] > ema_50.iloc[-1]:
            trend_strength = 0.7
            trend_dir = "bull"
        elif ema_9.iloc[-1] < ema_21.iloc[-1] < ema_50.iloc[-1]:
            trend_strength = 0.7
            trend_dir = "bear"
        else:
            trend_strength = 0.3
            trend_dir = "neutral"
        
        # Volatility
        atr_pct = (candles['high'].iloc[-20:] - candles['low'].iloc[-20:]).mean() / current_price * 100
        
        # Determine regime
        if trend_strength > 0.8 and atr_pct > 1.0:
            regime = f"trending_strong_{trend_dir}"
        elif trend_strength > 0.5:
            regime = f"trending_moderate_{trend_dir}"
        elif atr_pct > 3.0:
            regime = "crashing"
        elif atr_pct > 2.0:
            regime = "high_volatility"
        elif trend_strength < 0.4 and atr_pct < 0.5:
            regime = "chop"
        else:
            regime = "ranging"
        
        return {
            'regime': regime,
            'trend_strength': trend_strength,
            'trend_direction': trend_dir,
            'volatility_pct': atr_pct,
        }
    
    def _analyze_volatility(self, candles: pd.DataFrame) -> Dict[str, Any]:
        """Analyze volatility characteristics"""
        high = candles['high'].iloc[-100:]
        low = candles['low'].iloc[-100:]
        close = candles['close'].iloc[-100:]
        
        # ATR
        tr = pd.concat([
            high - low,
            (high - close.shift(1)).abs(),
            (low - close.shift(1)).abs()
        ], axis=1).max(axis=1)
        atr = tr.rolling(14).mean()
        
        # ATR percentile
        current_atr = atr.iloc[-1]
        atr_percentile = (atr < current_atr).sum() / len(atr) * 100
        
        return {
            'atr_percentile': atr_percentile,
            'current_atr': current_atr,
            'volatility_regime': 'high' if atr_percentile > 70 else 'low' if atr_percentile < 30 else 'medium',
        }
    
    def _analyze_session(self, candles: pd.DataFrame) -> Dict[str, Any]:
        """Analyze current session"""
        last_time = candles['time'].iloc[-1]
        hour = last_time.hour
        
        if 0 <= hour < 7:
            session = "asian"
        elif 7 <= hour < 13:
            session = "london"
        elif 13 <= hour < 17:
            session = "ny_overlap"
        elif 17 <= hour < 22:
            session = "ny"
        else:
            session = "late_ny"  # 22-23 UTC — BTCUSD trades 24/7, no 'weekend' concept
        
        return {
            'current_session': session,
            'hour': hour,
        }
    
    def _analyze_volume(self, candles: pd.DataFrame) -> Dict[str, Any]:
        """Analyze volume patterns"""
        if 'volume' not in candles.columns:
            return {'volume_trend': 'stable', 'volume_ratio': 1.0}
        
        vol = candles['volume'].iloc[-50:]
        recent_vol = vol.iloc[-10:].mean()
        older_vol = vol.iloc[:-10].mean()
        
        volume_ratio = recent_vol / max(1, older_vol)
        
        if volume_ratio > 1.3:
            trend = "increasing"
        elif volume_ratio < 0.7:
            trend = "decreasing"
        else:
            trend = "stable"
        
        return {
            'volume_trend': trend,
            'volume_ratio': volume_ratio,
        }
    
    def _analyze_physics(self, candles: pd.DataFrame) -> Dict[str, Any]:
        """Analyze market using physics-based analysis"""
        close = candles['close'].iloc[-50:]
        
        # Market energy (volatility * volume)
        returns = close.pct_change()
        energy = returns.std() * abs(returns.mean()) if len(returns) > 1 else 0
        
        # Momentum velocity
        velocity = abs(close.iloc[-1] - close.iloc[-10]) / 10
        
        # Acceleration
        if len(close) >= 20:
            vel_1 = abs(close.iloc[-10] - close.iloc[-20]) / 10
            vel_2 = abs(close.iloc[-1] - close.iloc[-10]) / 10
            acceleration = abs(vel_2 - vel_1) / 10
        else:
            acceleration = 0
        
        # Market temperature (normalized energy)
        temperature = min(1.0, energy * 1000)
        
        return {
            'market_energy': min(1.0, energy * 100),
            'velocity': velocity,
            'acceleration': acceleration,
            'temperature': temperature,
        }
    
    def update_profile_performance(self, profile: NeuralProfile, trade_result: Dict[str, Any]):
        """Update profile performance after trade"""
        profile.metrics.total_trades += 1
        
        pnl = trade_result.get('net_pnl', 0)
        if pnl > 0:
            profile.metrics.wins += 1
            profile.metrics.avg_profit = (profile.metrics.avg_profit * (profile.metrics.wins - 1) + pnl) / profile.metrics.wins
        else:
            profile.metrics.losses += 1
            profile.metrics.avg_loss = (profile.metrics.avg_loss * (profile.metrics.losses - 1) + abs(pnl)) / profile.metrics.losses
        
        # Update win rate
        profile.metrics.win_rate = profile.metrics.wins / max(1, profile.metrics.total_trades)
        
        # Update regime performance
        regime = trade_result.get('regime', 'unknown')
        if regime not in profile.regime_performance:
            profile.regime_performance[regime] = 0.5  # Default
        
        # Update with weighted average
        old_perf = profile.regime_performance[regime]
        profile.regime_performance[regime] = old_perf * 0.9 + (1 if pnl > 0 else 0) * 0.1
        
        # Self-evolution: adapt profile parameters based on performance
        if profile.metrics.total_trades >= 10:
            self._adapt_profile(profile)
    
    def _adapt_profile(self, profile: NeuralProfile):
        """Auto-evolve profile based on performance"""
        wr = profile.metrics.win_rate
        
        # If win rate is high, can increase risk slightly
        if wr > 0.6:
            profile.risk_per_trade = min(2.0, profile.risk_per_trade * 1.05)
            profile.confidence_threshold = max(0.50, profile.confidence_threshold - 0.02)
        
        # If win rate is low, decrease risk
        elif wr < 0.4:
            profile.risk_per_trade = max(0.1, profile.risk_per_trade * 0.95)
            profile.confidence_threshold = min(0.85, profile.confidence_threshold + 0.02)
        
        profile.mutation_count += 1
        profile.last_mutation_time = datetime.now(timezone.utc).isoformat()
        
        logger.debug(f"🧬 Profile {profile.name.value} adapted: risk={profile.risk_per_trade:.2f}%, conf_thresh={profile.confidence_threshold:.2f}")
    
    def get_profile_state(self) -> Dict[str, Any]:
        """Get current profile state for reporting"""
        return {
            'active_profile': self.active_profile.name.value if self.active_profile else None,
            'confidence': self.active_profile.confidence if self.active_profile else 0,
            'current_regime': self.current_regime,
            'profiles': {
                name.value: {
                    'confidence': prof.confidence,
                    'trades': prof.metrics.total_trades,
                    'win_rate': prof.metrics.win_rate,
                }
                for name, prof in self.profiles.items()
            },
        }
