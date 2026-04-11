"""
Advanced Trading Strategies - Liquidity, Thermodynamics, Physics, Order Blocks, FVG
CEO: Qwen Code | Created: 2026-04-10

5 New Advanced Strategies:
1. Liquidity Strategy - Based on liquidity pools, sweeps, grabs
2. Thermodynamic Strategy - Based on market energy, entropy, equilibrium
3. Physics Strategy - Based on momentum, forces, harmonic patterns
4. Order Block Strategy - Based on institutional order blocks
5. FVG Strategy - Based on Fair Value Gaps / Imbalances
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass
from loguru import logger


@dataclass
class AdvancedSignal:
    """Signal from advanced strategy"""
    strategy: str
    direction: str  # BUY, SELL, NEUTRAL
    confidence: float  # 0-1
    entry_price: float
    stop_loss: float
    take_profit: float
    rr_ratio: float
    reasoning: str
    timestamp: str
    regime_suitability: Dict[str, float] = None


class LiquidityStrategy:
    """
    Liquidity-based strategy
    
    Analyzes:
    - Liquidity pools above/below price
    - Liquidity sweeps and grabs
    - Stop hunt patterns
    - Institutional liquidity zones
    """
    
    def analyze(self, candles: pd.DataFrame, current_price: float) -> Optional[AdvancedSignal]:
        if len(candles) < 50:
            return None
        
        high = candles['high'].iloc[-50:]
        low = candles['low'].iloc[-50:]
        close = candles['close'].iloc[-50:]
        
        # Find liquidity pools (recent swing highs/lows)
        swing_highs = self._find_swing_points(high, lookback=5)
        swing_lows = self._find_swing_points(low, lookback=5, find_lows=True)
        
        # Check for liquidity sweeps
        current_high = candles['high'].iloc[-1]
        current_low = candles['low'].iloc[-1]
        
        liquidity_sweep_high = any(current_high > h * 1.0005 for h in swing_highs[-3:])
        liquidity_sweep_low = any(current_low < l * 0.9995 for l in swing_lows[-3:])
        
        # Check for rejection after sweep
        body_size = abs(close.iloc[-1] - close.iloc[-1])
        wick_ratio = (candles['high'].iloc[-1] - candles['low'].iloc[-1]) / max(body_size, 1)
        
        # Signal logic with FIXED SL capped at 300 points
        if liquidity_sweep_low and wick_ratio > 2.0:
            # Swept lows and rejected = bullish
            entry = current_price
            # Use fixed SL calculation (capped at 300 points)
            sl = self.calculate_fixed_sl(entry, "BUY", candles, max_points=300)
            tp = entry + (entry - sl) * 2
            return AdvancedSignal(
                strategy="liquidity",
                direction="BUY",
                confidence=0.75,
                entry_price=entry,
                stop_loss=sl,
                take_profit=tp,
                rr_ratio=2.0,
                reasoning=f"Liquidity sweep at ${current_low:,.0f} with rejection (wick ratio {wick_ratio:.1f}), SL capped at 300 pts",
                timestamp=datetime.now(timezone.utc).isoformat(),
                regime_suitability={"trending_bullish": 0.7, "ranging": 0.8, "crashing": 0.6},
            )
        elif liquidity_sweep_high and wick_ratio > 2.0:
            # Swept highs and rejected = bearish
            entry = current_price
            # Use fixed SL calculation (capped at 300 points)
            sl = self.calculate_fixed_sl(entry, "SELL", candles, max_points=300)
            tp = entry - (sl - entry) * 2
            return AdvancedSignal(
                strategy="liquidity",
                direction="SELL",
                confidence=0.75,
                entry_price=entry,
                stop_loss=sl,
                take_profit=tp,
                rr_ratio=2.0,
                reasoning=f"Liquidity sweep at ${current_high:,.0f} with rejection, SL capped at 300 pts",
                timestamp=datetime.now(timezone.utc).isoformat(),
                regime_suitability={"trending_bearish": 0.7, "ranging": 0.8, "pumping": 0.6},
            )
        
        return None
    
    def _find_swing_points(self, series: pd.Series, lookback: int = 5, find_lows: bool = False) -> List[float]:
        """Find swing highs or lows"""
        points = []
        for i in range(lookback, len(series) - lookback):
            window = series.iloc[i-lookback:i+lookback+1]
            if find_lows:
                if series.iloc[i] == window.min():
                    points.append(series.iloc[i])
            else:
                if series.iloc[i] == window.max():
                    points.append(series.iloc[i])
        return points[-5:]  # Last 5 points


class ThermodynamicStrategy:
    """
    Thermodynamic market analysis
    
    Based on:
    - Market energy (volatility * volume)
    - Entropy (disorder/randomness)
    - Equilibrium detection
    - Phase transitions (trending <-> ranging)
    """
    
    def analyze(self, candles: pd.DataFrame, current_price: float) -> Optional[AdvancedSignal]:
        if len(candles) < 100:
            return None
        
        close = candles['close'].iloc[-100:]
        returns = close.pct_change().dropna()
        
        # Market energy (vol * volume proxy)
        energy = returns.std() * len(returns)
        
        # Entropy (Shannon entropy of returns)
        hist, _ = np.histogram(returns, bins=20)
        probs = hist / hist.sum()
        entropy = -np.sum(probs * np.log2(probs + 1e-10))
        
        # Equilibrium detection
        mean_price = close.mean()
        deviation = abs(current_price - mean_price) / mean_price
        
        # Phase transition detection
        recent_vol = returns.iloc[-20:].std()
        older_vol = returns.iloc[:-20].std()
        vol_change = recent_vol / max(0.001, older_vol)
        
        # Signal logic with FIXED SL capped at 300 points
        if entropy < 3.0 and deviation > 0.02:
            # Low entropy + high deviation = mean reversion likely
            entry = current_price
            direction = "SELL" if current_price > mean_price else "BUY"
            # Use fixed SL calculation (capped at 300 points)
            sl = self.calculate_fixed_sl(entry, direction, candles, max_points=300)
            tp = mean_price
            rr = abs(tp - entry) / abs(sl - entry)

            return AdvancedSignal(
                strategy="thermodynamic",
                direction=direction,
                confidence=0.70,
                entry_price=entry,
                stop_loss=sl,
                take_profit=tp,
                rr_ratio=rr,
                reasoning=f"High deviation ({deviation:.1%}) from equilibrium, low entropy ({entropy:.2f}), SL capped at 300 pts",
                timestamp=datetime.now(timezone.utc).isoformat(),
                regime_suitability={"ranging": 0.9, "chop": 0.8},
            )
        elif vol_change > 1.5 and energy > 0.02:
            # Phase transition to trending
            direction = "BUY" if returns.iloc[-5:].mean() > 0 else "SELL"
            entry = current_price
            # Use fixed SL calculation (capped at 300 points)
            sl = self.calculate_fixed_sl(entry, direction, candles, max_points=300)
            tp = entry + (entry - sl) * 2 if direction == "BUY" else entry - (sl - entry) * 2

            return AdvancedSignal(
                strategy="thermodynamic",
                direction=direction,
                confidence=0.65,
                entry_price=entry,
                stop_loss=sl,
                take_profit=tp,
                rr_ratio=2.0,
                reasoning=f"Phase transition detected (vol change {vol_change:.1f}x), high energy, SL capped at 300 pts",
                timestamp=datetime.now(timezone.utc).isoformat(),
                regime_suitability={"trending_bullish": 0.8 if direction == "BUY" else 0.3,
                                   "trending_bearish": 0.8 if direction == "SELL" else 0.3},
            )
        
        return None


class PhysicsStrategy:
    """
    Physics-based market analysis
    
    Based on:
    - Momentum conservation
    - Force analysis (acceleration)
    - Harmonic patterns
    - Wave analysis
    """
    
    def analyze(self, candles: pd.DataFrame, current_price: float) -> Optional[AdvancedSignal]:
        if len(candles) < 50:
            return None
        
        close = candles['close'].iloc[-50:]
        
        # Momentum (velocity)
        vel_5 = (close.iloc[-1] - close.iloc[-5]) / 5
        vel_10 = (close.iloc[-1] - close.iloc[-10]) / 10
        
        # Acceleration
        accel = (vel_5 - vel_10) / 5
        
        # Force (mass * acceleration, where mass = volume proxy)
        volume_proxy = candles['volume'].iloc[-10:].mean() if 'volume' in candles.columns else 1000
        force = volume_proxy * accel
        
        # Check for momentum exhaustion
        if abs(vel_5) > abs(vel_10) * 1.5 and abs(accel) > 50:
            # Strong acceleration = potential reversal
            direction = "SELL" if vel_5 > 0 else "BUY"
            entry = current_price
            sl = entry + 300 if direction == "SELL" else entry - 300
            tp = entry - 600 if direction == "SELL" else entry + 600
            
            return AdvancedSignal(
                strategy="physics",
                direction=direction,
                confidence=0.70,
                entry_price=entry,
                stop_loss=sl,
                take_profit=tp,
                rr_ratio=2.0,
                reasoning=f"Momentum exhaustion (vel={vel_5:.2f}, accel={accel:.2f}, force={force:.0f})",
                timestamp=datetime.now(timezone.utc).isoformat(),
                regime_suitability={"trending_strong_bull": 0.7 if direction == "SELL" else 0.5,
                                   "trending_strong_bear": 0.7 if direction == "BUY" else 0.5},
            )
        
        return None


class OrderBlockStrategy:
    """
    Order Block strategy
    
    Based on:
    - Bullish/bearish order blocks
    - Break of structure
    - Institutional footprints
    - Supply/demand zones
    """
    
    def analyze(self, candles: pd.DataFrame, current_price: float) -> Optional[AdvancedSignal]:
        if len(candles) < 100:
            return None
        
        # Find order blocks (last down candle before strong up move, or vice versa)
        ob_bullish = self._find_bullish_order_blocks(candles)
        ob_bearish = self._find_bearish_order_blocks(candles)
        
        # Check if price is near order block - SL capped at 300 points
        if ob_bullish:
            nearest_ob = max(ob_bullish, key=lambda x: x['high'])  # Highest OB below price
            if current_price <= nearest_ob['high'] * 1.002 and current_price >= nearest_ob['low'] * 0.998:
                entry = current_price
                # Use fixed SL calculation (capped at 300 points)
                sl = self.calculate_fixed_sl(entry, "BUY", candles, max_points=300)
                tp = entry + (entry - sl) * 2

                return AdvancedSignal(
                    strategy="order_block",
                    direction="BUY",
                    confidence=0.72,
                    entry_price=entry,
                    stop_loss=sl,
                    take_profit=tp,
                    rr_ratio=2.0,
                    reasoning=f"Price at bullish order block (${nearest_ob['low']:,.0f}-${nearest_ob['high']:,.0f}), SL capped at 300 pts",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    regime_suitability={"trending_bullish": 0.85, "ranging": 0.7},
                )

        if ob_bearish:
            nearest_ob = min(ob_bearish, key=lambda x: x['low'])  # Lowest OB above price
            if current_price >= nearest_ob['low'] * 0.998 and current_price <= nearest_ob['high'] * 1.002:
                entry = current_price
                # Use fixed SL calculation (capped at 300 points)
                sl = self.calculate_fixed_sl(entry, "SELL", candles, max_points=300)
                tp = entry - (sl - entry) * 2

                return AdvancedSignal(
                    strategy="order_block",
                    direction="SELL",
                    confidence=0.72,
                    entry_price=entry,
                    stop_loss=sl,
                    take_profit=tp,
                    rr_ratio=2.0,
                    reasoning=f"Price at bearish order block (${nearest_ob['low']:,.0f}-${nearest_ob['high']:,.0f}), SL capped at 300 pts",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    regime_suitability={"trending_bearish": 0.85, "ranging": 0.7},
                )
        
        return None
    
    def _find_bullish_order_blocks(self, candles: pd.DataFrame, lookback: int = 100) -> List[Dict]:
        """Find bullish order blocks"""
        obs = []
        for i in range(2, lookback - 5):
            # Last down candle before strong up move
            if candles['close'].iloc[-i] < candles['open'].iloc[-i]:  # Red candle
                # Check if followed by strong move up
                if i > 1 and candles['close'].iloc[-i+1] > candles['open'].iloc[-i+1]:
                    move_up = candles['close'].iloc[-i+1] - candles['open'].iloc[-i+1]
                    if move_up > 100:  # Strong move
                        obs.append({
                            'high': candles['high'].iloc[-i],
                            'low': candles['low'].iloc[-i],
                            'index': -i,
                        })
        return obs[-3:]
    
    def _find_bearish_order_blocks(self, candles: pd.DataFrame, lookback: int = 100) -> List[Dict]:
        """Find bearish order blocks"""
        obs = []
        for i in range(2, lookback - 5):
            if candles['close'].iloc[-i] > candles['open'].iloc[-i]:  # Green candle
                if i > 1 and candles['close'].iloc[-i+1] < candles['open'].iloc[-i+1]:
                    move_down = candles['open'].iloc[-i+1] - candles['close'].iloc[-i+1]
                    if move_down > 100:
                        obs.append({
                            'high': candles['high'].iloc[-i],
                            'low': candles['low'].iloc[-i],
                            'index': -i,
                        })
        return obs[-3:]


class FVGStrategy:
    """
    Fair Value Gap / Imbalance strategy
    
    Based on:
    - FVG detection (3-candle pattern)
    - Imbalance fills
    - Institutional inefficiencies
    """
    
    def analyze(self, candles: pd.DataFrame, current_price: float) -> Optional[AdvancedSignal]:
        if len(candles) < 50:
            return None
        
        # Detect FVGs
        fvgs = self._detect_fvgs(candles)
        
        # Check if price is in FVG zone - SL capped at 300 points
        for fvg in fvgs:
            if fvg['low'] <= current_price <= fvg['high']:
                # Price is in FVG = potential reversal zone
                direction = "SELL" if fvg['type'] == "bullish_fvg" else "BUY"
                entry = current_price
                # Use fixed SL calculation (capped at 300 points)
                sl = self.calculate_fixed_sl(entry, direction, candles, max_points=300)
                tp = entry - (sl - entry) * 2 if direction == "SELL" else entry + (entry - sl) * 2

                return AdvancedSignal(
                    strategy="fvg",
                    direction=direction,
                    confidence=0.68,
                    entry_price=entry,
                    stop_loss=sl,
                    take_profit=tp,
                    rr_ratio=2.0,
                    reasoning=f"Price in {'bullish' if fvg['type'] == 'bullish_fvg' else 'bearish'} FVG (${fvg['low']:,.0f}-${fvg['high']:,.0f}), SL capped at 300 pts",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    regime_suitability={"ranging": 0.8, "trending_moderate_bull": 0.6, "trending_moderate_bear": 0.6},
                )
        
        return None
    
    def _detect_fvgs(self, candles: pd.DataFrame) -> List[Dict]:
        """Detect Fair Value Gaps"""
        fvgs = []
        
        for i in range(2, min(50, len(candles))):
            candle_1 = candles.iloc[-i]
            candle_2 = candles.iloc[-i+1]
            candle_3 = candles.iloc[-i+2]
            
            # Bullish FVG: Candle 1 high < Candle 3 low
            if candle_1['high'] < candle_3['low']:
                fvg_low = candle_1['high']
                fvg_high = candle_3['low']
                if fvg_high - fvg_low > 50:  # Minimum FVG size
                    fvgs.append({
                        'type': 'bullish_fvg',
                        'low': fvg_low,
                        'high': fvg_high,
                        'index': -i + 1,
                    })
            
            # Bearish FVG: Candle 1 low > Candle 3 high
            elif candle_1['low'] > candle_3['high']:
                fvg_low = candle_3['high']
                fvg_high = candle_1['low']
                if fvg_high - fvg_low > 50:
                    fvgs.append({
                        'type': 'bearish_fvg',
                        'low': fvg_low,
                        'high': fvg_high,
                        'index': -i + 1,
                    })
        
        return fvgs[-5:]  # Last 5 FVGs
