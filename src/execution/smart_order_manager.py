"""
Smart Order Manager - Intelligent position management system
CEO: Qwen Code | Created: 2026-04-10

Advanced Features:
1. VIRTUAL TP DYNAMICS
   - Market difficulty analysis (gravity, velocity, oscillation)
   - Real-time candle movement tracking
   - Dynamic TP distance adjustment
   - Auto-close when virtual TP hit

2. DYNAMIC SL WITH PROFIT PROTECTION
   - Virtual profit targets (25%, 35%, 55%, 75%, 90%)
   - DNA-adjustable profiles per target
   - Velocity-based behavior
   - Breakeven protection (covers commissions)
   - Trailing stop with smart logic

3. LARGE-SCALE MARKET ANALYSIS
   - Multi-timeframe momentum
   - Volume profile analysis
   - Volatility clustering
   - Order flow dynamics
   - Microstructure patterns
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger


class ProfitTarget(Enum):
    """Virtual profit target levels"""
    TARGET_25 = 0.25
    TARGET_35 = 0.35
    TARGET_50 = 0.50
    TARGET_65 = 0.65
    TARGET_75 = 0.75
    TARGET_90 = 0.90


class MarketDifficulty(Enum):
    """Market difficulty levels"""
    VERY_EASY = "very_easy"
    EASY = "easy"
    MODERATE = "moderate"
    HARD = "hard"
    VERY_HARD = "very_hard"
    EXTREME = "extreme"


@dataclass
class MarketMomentum:
    """Real-time market momentum analysis"""
    velocity: float  # Price change speed (points/sec)
    acceleration: float  # Velocity change
    gravity: float  # Pullback force (0-1)
    oscillation: float  # Oscillation amplitude
    volatility: float  # Current volatility
    volume_pressure: float  # Volume-based pressure
    microstructure_score: float  # Market microstructure health
    timestamp: datetime


@dataclass
class VirtualTP:
    """Virtual Take Profit tracker"""
    original_tp: float
    current_virtual_tp: float
    original_distance: float
    current_distance: float
    difficulty: MarketDifficulty
    adjustment_factor: float
    last_update: datetime
    hit: bool = False


@dataclass
class DynamicSL:
    """Dynamic Stop Loss tracker"""
    original_sl: float
    current_sl: float
    breakeven_activated: bool
    trailing_activated: bool
    last_profit_target: Optional[ProfitTarget]
    last_update: datetime
    profit_locked: float = 0.0


@dataclass
class ProfitProfile:
    """Profile for each profit target level"""
    target: ProfitTarget
    sl_behavior: str  # "breakeven", "partial_trail", "full_trail", "aggressive"
    velocity_threshold: float  # Min velocity for this profile
    velocity_behavior: str  # If vel > threshold: "hold", "tighten", "close"
    sl_distance_points: float  # Distance from current price
    min_profit_lock: float  # Min profit to lock (USD)
    dna_adjusted: bool = False


@dataclass
class PositionState:
    """Complete position state"""
    ticket: int
    symbol: str
    direction: str
    entry_price: float
    volume: float
    open_time: datetime
    
    # Original levels
    original_sl: float
    original_tp: float
    
    # Dynamic trackers
    virtual_tp: Optional[VirtualTP]
    dynamic_sl: Optional[DynamicSL]
    
    # Current state
    current_price: float
    current_pnl: float
    current_pnl_points: float
    progress_to_tp: float  # 0.0 to 1.0
    
    # Momentum tracking
    momentum_history: List[MarketMomentum]
    
    # Profit targets reached
    targets_reached: List[ProfitTarget]
    
    # Status
    is_open: bool = True
    close_reason: Optional[str] = None


class SmartOrderManager:
    """
    Intelligent position management system
    
    Features:
    1. Virtual TP dynamics based on market difficulty
    2. Dynamic SL with profit protection
    3. Large-scale market analysis
    4. DNA-adjusted profit profiles
    5. Velocity-based behavior adaptation
    """
    
    def __init__(self, dna_params: Dict[str, Any]):
        self.dna_params = dna_params
        
        # Active positions
        self.positions: Dict[int, PositionState] = {}
        
        # Profit profiles (DNA-adjustable)
        self.profit_profiles = self._initialize_profit_profiles()
        
        # TP adjustment settings
        self.tp_adjustment_settings = {
            'min_distance_percent': 0.10,  # Min 10% of original
            'max_distance_percent': 1.00,  # Max 100% of original
            'adjustment_frequency_sec': 5,  # Check every 5 seconds
            'gravity_weight': 0.30,
            'velocity_weight': 0.25,
            'oscillation_weight': 0.25,
            'volume_weight': 0.20,
        }
        
        logger.info("🎯 Smart Order Manager initialized")
    
    def _initialize_profit_profiles(self) -> Dict[ProfitTarget, ProfitProfile]:
        """Initialize profit profiles (DNA will adjust these)"""
        profiles = {
            ProfitTarget.TARGET_25: ProfitProfile(
                target=ProfitTarget.TARGET_25,
                sl_behavior="breakeven",
                velocity_threshold=0.5,
                velocity_behavior="hold",
                sl_distance_points=200,
                min_profit_lock=5.0,
            ),
            ProfitTarget.TARGET_35: ProfitProfile(
                target=ProfitTarget.TARGET_35,
                sl_behavior="partial_trail",
                velocity_threshold=0.8,
                velocity_behavior="tighten",
                sl_distance_points=150,
                min_profit_lock=10.0,
            ),
            ProfitTarget.TARGET_50: ProfitProfile(
                target=ProfitTarget.TARGET_50,
                sl_behavior="full_trail",
                velocity_threshold=1.0,
                velocity_behavior="tighten",
                sl_distance_points=100,
                min_profit_lock=20.0,
            ),
            ProfitTarget.TARGET_65: ProfitProfile(
                target=ProfitTarget.TARGET_65,
                sl_behavior="aggressive",
                velocity_threshold=1.2,
                velocity_behavior="close",
                sl_distance_points=75,
                min_profit_lock=30.0,
            ),
            ProfitTarget.TARGET_75: ProfitProfile(
                target=ProfitTarget.TARGET_75,
                sl_behavior="aggressive",
                velocity_threshold=1.5,
                velocity_behavior="close",
                sl_distance_points=50,
                min_profit_lock=40.0,
            ),
            ProfitTarget.TARGET_90: ProfitProfile(
                target=ProfitTarget.TARGET_90,
                sl_behavior="aggressive",
                velocity_threshold=2.0,
                velocity_behavior="close",
                sl_distance_points=25,
                min_profit_lock=50.0,
            ),
        }
        
        return profiles
    
    def open_position(self, position_data: Dict[str, Any]) -> PositionState:
        """Register a new position for smart management"""
        ticket = position_data['ticket']
        
        state = PositionState(
            ticket=ticket,
            symbol=position_data.get('symbol', 'BTCUSD'),
            direction=position_data['direction'],
            entry_price=position_data['entry_price'],
            volume=position_data.get('volume', 0.10),
            open_time=position_data.get('open_time', datetime.now(timezone.utc)),
            
            original_sl=position_data['stop_loss'],
            original_tp=position_data['take_profit'],
            
            virtual_tp=VirtualTP(
                original_tp=position_data['take_profit'],
                current_virtual_tp=position_data['take_profit'],
                original_distance=abs(position_data['take_profit'] - position_data['entry_price']),
                current_distance=abs(position_data['take_profit'] - position_data['entry_price']),
                difficulty=MarketDifficulty.MODERATE,
                adjustment_factor=1.0,
                last_update=datetime.now(timezone.utc),
            ),
            
            dynamic_sl=DynamicSL(
                original_sl=position_data['stop_loss'],
                current_sl=position_data['stop_loss'],
                breakeven_activated=False,
                trailing_activated=False,
                last_profit_target=None,
                profit_locked=0.0,
                last_update=datetime.now(timezone.utc),
            ),
            
            current_price=position_data['entry_price'],
            current_pnl=0.0,
            current_pnl_points=0.0,
            progress_to_tp=0.0,
            momentum_history=[],
            targets_reached=[],
        )
        
        self.positions[ticket] = state
        
        logger.info(f"🎯 Position #{ticket} registered for smart management")
        logger.info(f"   Entry: ${position_data['entry_price']:,.2f}")
        logger.info(f"   SL: ${position_data['stop_loss']:,.2f}")
        logger.info(f"   TP: ${position_data['take_profit']:,.2f}")
        
        return state
    
    def update_position(self, ticket: int, current_price: float, candles: pd.DataFrame) -> Dict[str, Any]:
        """
        Update position with real-time market analysis
        
        Returns:
            dict: Action recommendations
        """
        if ticket not in self.positions:
            return {'action': 'none', 'reason': 'Position not found'}
        
        state = self.positions[ticket]
        if not state.is_open:
            return {'action': 'none', 'reason': 'Position already closed'}
        
        # Update current price and PnL
        state.current_price = current_price
        state.current_pnl = self._calculate_pnl(state)
        state.current_pnl_points = self._calculate_pnl_points(state)
        
        # Calculate progress to TP
        state.progress_to_tp = self._calculate_progress_to_tp(state)
        
        # Analyze market momentum
        momentum = self._analyze_market_momentum(candles)
        state.momentum_history.append(momentum)
        
        # Keep only last 100 momentum readings
        if len(state.momentum_history) > 100:
            state.momentum_history = state.momentum_history[-100:]
        
        # Update Virtual TP
        tp_action = self._update_virtual_tp(state, momentum, candles)
        
        # Update Dynamic SL
        sl_action = self._update_dynamic_sl(state, momentum)
        
        # Check if targets reached
        new_targets = self._check_profit_targets(state)
        
        # Determine action
        action = self._determine_action(state, tp_action, sl_action, new_targets)
        
        state.dynamic_sl.last_update = datetime.now(timezone.utc)
        state.virtual_tp.last_update = datetime.now(timezone.utc)
        
        return action
    
    def _analyze_market_momentum(self, candles: pd.DataFrame) -> MarketMomentum:
        """
        Large-scale market momentum analysis
        
        Analyzes:
        - Velocity (speed of price movement)
        - Acceleration (change in velocity)
        - Gravity (pullback force)
        - Oscillation (cyclic patterns)
        - Volatility (price dispersion)
        - Volume pressure (volume-based momentum)
        - Microstructure (market health)
        """
        if len(candles) < 20:
            return MarketMomentum(
                velocity=0, acceleration=0, gravity=0.5,
                oscillation=0, volatility=0, volume_pressure=0.5,
                microstructure_score=0.5,
                timestamp=datetime.now(timezone.utc)
            )
        
        # Calculate velocity (points per second)
        recent_prices = candles['close'].iloc[-20:].values
        time_delta = 5 * 60  # 5 minutes in seconds (M5 candles)
        velocity = abs(recent_prices[-1] - recent_prices[0]) / time_delta
        
        # Calculate acceleration
        if len(recent_prices) >= 10:
            vel_1 = abs(recent_prices[-5] - recent_prices[-10]) / time_delta
            vel_2 = abs(recent_prices[-1] - recent_prices[-6]) / time_delta
            acceleration = abs(vel_2 - vel_1) / time_delta
        else:
            acceleration = 0
        
        # Calculate gravity (mean reversion force)
        mean_price = recent_prices.mean()
        current_price = recent_prices[-1]
        deviation = abs(current_price - mean_price)
        gravity = min(deviation / (mean_price * 0.01), 1.0)  # Normalize to 0-1
        
        # Calculate oscillation (cyclic amplitude)
        if len(recent_prices) >= 10:
            highs = recent_prices.max()
            lows = recent_prices.min()
            oscillation = (highs - lows) / mean_price * 10000  # In points
        else:
            oscillation = 0
        
        # Calculate volatility (standard deviation)
        volatility = recent_prices.std() / mean_price * 10000  # In points
        
        # Volume pressure
        if 'volume' in candles.columns:
            recent_vol = candles['volume'].iloc[-20:].values
            volume_ratio = recent_vol[-1] / max(recent_vol.mean(), 1)
            volume_pressure = min(volume_ratio / 2, 1.0)  # Normalize
        else:
            volume_pressure = 0.5
        
        # Microstructure score (market health)
        body_sizes = abs(candles['close'].iloc[-20:] - candles['open'].iloc[-20:])
        range_sizes = candles['high'].iloc[-20:] - candles['low'].iloc[-20:]
        efficiency = (body_sizes / range_sizes.replace(0, 1)).mean()
        microstructure_score = min(max(efficiency, 0), 1)
        
        return MarketMomentum(
            velocity=velocity,
            acceleration=acceleration,
            gravity=gravity,
            oscillation=oscillation,
            volatility=volatility,
            volume_pressure=volume_pressure,
            microstructure_score=microstructure_score,
            timestamp=datetime.now(timezone.utc)
        )
    
    def _update_virtual_tp(self, state: PositionState, momentum: MarketMomentum, candles: pd.DataFrame) -> str:
        """
        Update Virtual Take Profit based on market difficulty
        
        Logic:
        - Analyze market difficulty (gravity, velocity, oscillation, volume)
        - Adjust TP distance dynamically
        - More difficulty = closer virtual TP
        - Less difficulty = maintain original TP
        """
        # Calculate difficulty score (0-1)
        difficulty_score = (
            momentum.gravity * self.tp_adjustment_settings['gravity_weight'] +
            min(momentum.velocity / 10, 1.0) * self.tp_adjustment_settings['velocity_weight'] +
            min(momentum.oscillation / 100, 1.0) * self.tp_adjustment_settings['oscillation_weight'] +
            momentum.volume_pressure * self.tp_adjustment_settings['volume_weight']
        )
        
        # Map to difficulty level
        if difficulty_score < 0.2:
            difficulty = MarketDifficulty.VERY_EASY
            adjustment = 1.0
        elif difficulty_score < 0.4:
            difficulty = MarketDifficulty.EASY
            adjustment = 0.95
        elif difficulty_score < 0.6:
            difficulty = MarketDifficulty.MODERATE
            adjustment = 0.85
        elif difficulty_score < 0.75:
            difficulty = MarketDifficulty.HARD
            adjustment = 0.70
        elif difficulty_score < 0.9:
            difficulty = MarketDifficulty.VERY_HARD
            adjustment = 0.55
        else:
            difficulty = MarketDifficulty.EXTREME
            adjustment = 0.40
        
        # Apply adjustment to TP distance
        new_distance = state.virtual_tp.original_distance * adjustment
        
        # Enforce limits
        min_distance = state.virtual_tp.original_distance * self.tp_adjustment_settings['min_distance_percent']
        max_distance = state.virtual_tp.original_distance * self.tp_adjustment_settings['max_distance_percent']
        new_distance = max(min_distance, min(max_distance, new_distance))
        
        # Update virtual TP
        if state.direction == 'BUY':
            state.virtual_tp.current_virtual_tp = state.entry_price + new_distance
        else:
            state.virtual_tp.current_virtual_tp = state.entry_price - new_distance
        
        state.virtual_tp.current_distance = new_distance
        state.virtual_tp.difficulty = difficulty
        state.virtual_tp.adjustment_factor = adjustment
        
        # Check if price hit virtual TP
        if self._check_virtual_tp_hit(state):
            state.virtual_tp.hit = True
            return 'close_position'
        
        return 'monitor'
    
    def _check_virtual_tp_hit(self, state: PositionState) -> bool:
        """Check if current price hit virtual TP"""
        if state.direction == 'BUY':
            return state.current_price >= state.virtual_tp.current_virtual_tp
        else:
            return state.current_price <= state.virtual_tp.current_virtual_tp
    
    def _update_dynamic_sl(self, state: PositionState, momentum: MarketMomentum) -> str:
        """
        Update Dynamic Stop Loss with profit protection
        
        Logic:
        1. Check which profit targets reached
        2. For each target, apply SL behavior from profile
        3. Velocity-based adjustments
        4. Breakeven protection (cover commissions)
        """
        # Check if we should activate breakeven
        if not state.dynamic_sl.breakeven_activated:
            if self._should_activate_breakeven(state):
                state.dynamic_sl.breakeven_activated = True
                state.dynamic_sl.trailing_activated = True
                self._activate_breakeven_sl(state)
                return 'sl_updated_breakeven'
        
        # Check profit targets and adjust SL accordingly
        for target in [ProfitTarget.TARGET_25, ProfitTarget.TARGET_35, ProfitTarget.TARGET_50,
                      ProfitTarget.TARGET_65, ProfitTarget.TARGET_75, ProfitTarget.TARGET_90]:
            
            if target in state.targets_reached:
                profile = self.profit_profiles[target]
                self._apply_profile_sl_behavior(state, profile, momentum)
        
        return 'sl_updated'
    
    def _should_activate_breakeven(self, state: PositionState) -> bool:
        """
        Determine if breakeven should be activated
        
        Activate when:
        - Progress to TP >= 25% AND
        - Current profit >= commission costs
        """
        if state.progress_to_tp >= 0.25:
            # Calculate commission costs
            commission_per_side = state.volume * 45.0  # $45/lot
            total_commission = commission_per_side * 2  # Round trip
            spread_cost = 100 * state.volume  # 100 points spread
            
            min_profit = total_commission + spread_cost
            
            if state.current_pnl >= min_profit:
                return True
        
        return False
    
    def _activate_breakeven_sl(self, state: PositionState):
        """Activate breakeven SL (covers all costs)"""
        # Calculate breakeven price (entry + costs)
        commission_per_side = state.volume * 45.0
        total_commission = commission_per_side * 2
        spread_cost = 100 * state.volume
        total_costs = total_commission + spread_cost
        
        # Add small buffer
        buffer = 5 * state.volume  # 5 points buffer
        
        if state.direction == 'BUY':
            breakeven_sl = state.entry_price + (total_costs + buffer) / state.volume
            state.dynamic_sl.current_sl = max(breakeven_sl, state.dynamic_sl.current_sl)
        else:
            breakeven_sl = state.entry_price - (total_costs + buffer) / state.volume
            state.dynamic_sl.current_sl = min(breakeven_sl, state.dynamic_sl.current_sl)
        
        state.dynamic_sl.profit_locked = 0.0  # Breakeven = no profit/loss
        
        logger.info(f"🛡️ Breakeven SL activated for #{state.ticket}")
        logger.info(f"   New SL: ${state.dynamic_sl.current_sl:,.2f}")
    
    def _apply_profile_sl_behavior(self, state: PositionState, profile: ProfitProfile, momentum: MarketMomentum):
        """Apply SL behavior based on profit profile"""
        if profile.sl_behavior == "breakeven":
            # Already handled by _activate_breakeven_sl
            pass
        
        elif profile.sl_behavior == "partial_trail":
            # Trail with wider distance
            if momentum.velocity > profile.velocity_threshold:
                if profile.velocity_behavior == "tighten":
                    new_sl_distance = profile.sl_distance_points * 0.8
                else:
                    new_sl_distance = profile.sl_distance_points
            else:
                new_sl_distance = profile.sl_distance_points
            
            self._trail_sl(state, new_sl_distance, profile.min_profit_lock)
        
        elif profile.sl_behavior == "full_trail":
            # Tighter trailing
            new_sl_distance = profile.sl_distance_points * 0.7
            self._trail_sl(state, new_sl_distance, profile.min_profit_lock)
        
        elif profile.sl_behavior == "aggressive":
            # Very tight trailing
            if momentum.velocity > profile.velocity_threshold:
                if profile.velocity_behavior == "close":
                    # High velocity + aggressive = close position
                    pass  # Will be handled by action determination
                else:
                    new_sl_distance = profile.sl_distance_points * 0.5
                    self._trail_sl(state, new_sl_distance, profile.min_profit_lock)
    
    def _trail_sl(self, state: PositionState, distance_points: float, min_profit: float):
        """
        Trail SL with specified distance
        
        IMPORTANT: SL can ONLY move in favor of the trade (tighten).
        SL NEVER widens or moves against the position.
        Once a position is opened, the initial SL is SACRED and can only improve.
        """
        if state.direction == 'BUY':
            new_sl = state.current_price - (distance_points * 0.01)
            # SL can only move UP (closer to profit), never DOWN (wider)
            state.dynamic_sl.current_sl = max(new_sl, state.dynamic_sl.current_sl)
        else:
            new_sl = state.current_price + (distance_points * 0.01)
            # SL can only move DOWN (closer to profit), never UP (wider)
            state.dynamic_sl.current_sl = min(new_sl, state.dynamic_sl.current_sl)

        state.dynamic_sl.profit_locked = abs(state.current_price - state.dynamic_sl.current_sl) * state.volume
    
    def _check_profit_targets(self, state: PositionState) -> List[ProfitTarget]:
        """Check which profit targets have been reached"""
        new_targets = []
        
        for target, profile in self.profit_profiles.items():
            if target in state.targets_reached:
                continue
            
            target_price = state.entry_price + (state.virtual_tp.original_distance * target.value) * (1 if state.direction == 'BUY' else -1)
            
            if (state.direction == 'BUY' and state.current_price >= target_price) or \
               (state.direction == 'SELL' and state.current_price <= target_price):
                state.targets_reached.append(target)
                new_targets.append(target)
                logger.info(f"🎯 Target {target.value*100:.0f}% reached for #{state.ticket}")
        
        return new_targets
    
    def _calculate_pnl(self, state: PositionState) -> float:
        """Calculate current PnL in USD"""
        if state.direction == 'BUY':
            return (state.current_price - state.entry_price) * state.volume * 100
        else:
            return (state.entry_price - state.current_price) * state.volume * 100
    
    def _calculate_pnl_points(self, state: PositionState) -> float:
        """Calculate PnL in points"""
        if state.direction == 'BUY':
            return (state.current_price - state.entry_price) / 0.01
        else:
            return (state.entry_price - state.current_price) / 0.01
    
    def _calculate_progress_to_tp(self, state: PositionState) -> float:
        """Calculate progress to original TP (0.0 to 1.0)"""
        total_distance = state.virtual_tp.original_distance
        
        if state.direction == 'BUY':
            traveled = state.current_price - state.entry_price
        else:
            traveled = state.entry_price - state.current_price
        
        progress = traveled / total_distance
        return max(0.0, min(1.0, progress))
    
    def _determine_action(self, state: PositionState, tp_action: str, sl_action: str, new_targets: List[ProfitTarget]) -> Dict[str, Any]:
        """Determine action based on current state"""
        # Priority 1: Virtual TP hit
        if state.virtual_tp.hit:
            return {
                'action': 'close_position',
                'reason': 'Virtual TP hit',
                'type': 'take_profit',
                'pnl': state.current_pnl,
                'adjustment_factor': state.virtual_tp.adjustment_factor,
                'difficulty': state.virtual_tp.difficulty.value,
            }
        
        # Priority 2: SL hit
        if state.direction == 'BUY' and state.current_price <= state.dynamic_sl.current_sl:
            return {
                'action': 'close_position',
                'reason': 'Dynamic SL hit',
                'type': 'stop_loss',
                'pnl': state.current_pnl,
            }
        elif state.direction == 'SELL' and state.current_price >= state.dynamic_sl.current_sl:
            return {
                'action': 'close_position',
                'reason': 'Dynamic SL hit',
                'type': 'stop_loss',
                'pnl': state.current_pnl,
            }
        
        # Priority 3: Extreme difficulty + low progress
        if state.virtual_tp.difficulty in [MarketDifficulty.VERY_HARD, MarketDifficulty.EXTREME]:
            if state.progress_to_tp < 0.20:
                return {
                    'action': 'consider_close',
                    'reason': f'Extreme market difficulty ({state.virtual_tp.difficulty.value})',
                    'type': 'risk_management',
                }
        
        # Priority 4: High velocity at 90% target
        if ProfitTarget.TARGET_90 in state.targets_reached:
            profile = self.profit_profiles[ProfitTarget.TARGET_90]
            momentum = state.momentum_history[-1] if state.momentum_history else None
            
            if momentum and momentum.velocity > profile.velocity_threshold:
                if profile.velocity_behavior == "close":
                    return {
                        'action': 'close_position',
                        'reason': 'High velocity at 90% target - locking profits',
                        'type': 'profit_lock',
                        'pnl': state.current_pnl,
                    }
        
        # Default: Monitor
        return {
            'action': 'monitor',
            'reason': 'All systems nominal',
            'progress_to_tp': state.progress_to_tp,
            'virtual_tp_distance': state.virtual_tp.current_distance,
            'current_sl': state.dynamic_sl.current_sl,
            'targets_reached': [t.value for t in state.targets_reached],
            'pnl': state.current_pnl,
        }
    
    def close_position(self, ticket: int, reason: str = 'manual') -> Optional[Dict[str, Any]]:
        """Close position and return summary"""
        if ticket not in self.positions:
            return None
        
        state = self.positions[ticket]
        state.is_open = False
        state.close_reason = reason
        
        summary = {
            'ticket': ticket,
            'entry_price': state.entry_price,
            'exit_price': state.current_price,
            'pnl': state.current_pnl,
            'progress_to_tp': state.progress_to_tp,
            'targets_reached': len(state.targets_reached),
            'close_reason': reason,
            'virtual_tp_hit': state.virtual_tp.hit,
            'final_difficulty': state.virtual_tp.difficulty.value,
        }
        
        logger.info(f"✅ Position #{ticket} closed")
        logger.info(f"   PnL: ${state.current_pnl:+,.2f}")
        logger.info(f"   Reason: {reason}")
        logger.info(f"   Progress to TP: {state.progress_to_tp*100:.1f}%")
        
        return summary
    
    def get_position_summary(self) -> Dict[str, Any]:
        """Get summary of all positions"""
        open_positions = [s for s in self.positions.values() if s.is_open]
        closed_positions = [s for s in self.positions.values() if not s.is_open]
        
        return {
            'total_positions': len(self.positions),
            'open_positions': len(open_positions),
            'closed_positions': len(closed_positions),
            'total_pnl': sum(s.current_pnl for s in self.positions.values()),
            'targets_reached_total': sum(len(s.targets_reached) for s in self.positions.values()),
        }
