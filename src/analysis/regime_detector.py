"""
RegimeDetector - Market Regime Classification System
Source: DubaiMatrixASI (salvaged and improved)
Created: 2026-04-11

Classifies market into regimes using multiple indicators:
1. Hurst Exponent (trending vs mean-reverting)
2. ADX Strength (trend strength)
3. Volatility Regime (high/normal/low)
4. Price Structure (HH/HL vs LH/LL)
"""

from typing import Dict, Any, Tuple, List
from loguru import logger
import numpy as np


class RegimeDetector:
    """
    Market regime classification system.
    
    Inspired by DubaiMatrixASI implementation but simplified and improved.
    """

    def __init__(
        self,
        hurst_lookback: int = 100,
        adx_period: int = 14,
        volatility_lookback: int = 50,
    ):
        """
        Initialize RegimeDetector.
        
        Args:
            hurst_lookback: Period for Hurst exponent calculation
            adx_period: ADX calculation period
            volatility_lookback: Period for volatility classification
        """
        self.hurst_lookback = hurst_lookback
        self.adx_period = adx_period
        self.volatility_lookback = volatility_lookback
        
        logger.info(" RegimeDetector initialized")
        logger.info(f"   Hurst lookback: {hurst_lookback}")
        logger.info(f"   ADX period: {adx_period}")
        logger.info(f"   Volatility lookback: {volatility_lookback}")

    def detect_regime(
        self,
        highs: List[float],
        lows: List[float],
        closes: List[float],
    ) -> Dict[str, Any]:
        """
        Detect current market regime.
        
        Args:
            highs: Price highs
            lows: Price lows
            closes: Price closes
            
        Returns:
            Dict with regime classification and confidence
        """
        if len(closes) < 50:
            return self._default_regime()
        
        closes = np.array(closes)
        highs = np.array(highs)
        lows = np.array(lows)
        
        # 1. Hurst Exponent (trending vs mean-reverting)
        hurst = self._calculate_hurst(closes)
        
        # 2. ADX (trend strength)
        adx = self._calculate_adx(highs, lows, closes)
        
        # 3. Volatility Regime
        vol_regime = self._classify_volatility(closes)
        
        # 4. Price Structure
        structure = self._analyze_structure(highs, lows)
        
        # Determine trend type based on Hurst
        if hurst > 0.6:
            trend_type = 'trending'
            trend_direction = 'bullish' if closes[-1] > closes[-20] else 'bearish'
        elif hurst < 0.4:
            trend_type = 'ranging'
            trend_direction = 'neutral'
        else:
            trend_type = 'transitional'
            trend_direction = 'bullish' if closes[-1] > closes[-20] else 'bearish'
        
        # Calculate overall confidence
        confidence = 0.5
        if abs(hurst - 0.5) > 0.15:
            confidence += 0.2
        if adx > 25:
            confidence += 0.15
        if structure['clarity'] > 0.7:
            confidence += 0.15
        
        confidence = min(0.95, confidence)
        
        return {
            'trend_type': trend_type,
            'trend_direction': trend_direction,
            'volatility_regime': vol_regime,
            'hurst_exponent': hurst,
            'adx': adx,
            'structure': structure,
            'confidence': confidence,
            'regime_name': f"{trend_type}_{trend_direction}_{vol_regime}",
        }

    def _calculate_hurst(self, closes: np.ndarray) -> float:
        """
        Calculate Hurst Exponent using R/S analysis.
        
        H > 0.5 = Trending
        H = 0.5 = Random walk
        H < 0.5 = Mean-reverting
        """
        # Simplified Hurst calculation using log returns
        log_returns = np.diff(np.log(closes[-self.hurst_lookback:]))
        
        if len(log_returns) < 20:
            return 0.5
        
        # Use variance ratio method (simplified)
        var_short = np.var(log_returns[:10])
        var_long = np.var(log_returns)
        
        if var_short > 0 and var_long > 0:
            hurst = 0.5 * np.log(var_long / var_short) / np.log(2)
            return max(0.1, min(0.9, hurst))
        
        return 0.5

    def _calculate_adx(
        self,
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray,
    ) -> float:
        """Calculate ADX (simplified)."""
        period = min(self.adx_period, len(highs) - 1)
        if period < 14:
            return 20.0  # Default moderate
        
        high_diff = np.diff(highs[-period-1:])
        low_diff = np.diff(lows[-period-1:])
        
        plus_dm = np.where(high_diff > low_diff, np.maximum(high_diff, 0), 0)
        minus_dm = np.where(low_diff > high_diff, np.maximum(low_diff, 0), 0)
        
        atr = np.mean(np.maximum(highs[-period:] - lows[-period:], 
                                 np.maximum(np.abs(highs[-period:] - closes[-period-1:-1]),
                                           np.abs(lows[-period:] - closes[-period-1:-1]))))
        
        if atr == 0:
            return 20.0
        
        plus_di = 100 * np.mean(plus_dm) / atr
        minus_di = 100 * np.mean(minus_dm) / atr
        
        if plus_di + minus_di == 0:
            return 20.0
        
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        
        return min(100, dx)

    def _classify_volatility(self, closes: np.ndarray) -> str:
        """Classify volatility regime."""
        returns = np.diff(np.log(closes[-self.volatility_lookback:]))
        current_vol = np.std(returns[-20:])
        avg_vol = np.std(returns)
        
        if avg_vol == 0:
            return 'normal'
        
        vol_ratio = current_vol / avg_vol
        
        if vol_ratio > 1.5:
            return 'high'
        elif vol_ratio < 0.7:
            return 'low'
        else:
            return 'normal'

    def _analyze_structure(
        self,
        highs: np.ndarray,
        lows: np.ndarray,
    ) -> Dict[str, Any]:
        """Analyze price structure (HH/HL vs LH/LL)."""
        if len(highs) < 40:
            return {'type': 'unknown', 'clarity': 0.0}
        
        # Find recent swing highs and lows
        recent_highs = highs[-20:]
        recent_lows = lows[-20:]
        
        hh_count = sum(1 for i in range(1, len(recent_highs)) if recent_highs[i] > recent_highs[i-1])
        lh_count = len(recent_highs) - 1 - hh_count
        
        hl_count = sum(1 for i in range(1, len(recent_lows)) if recent_lows[i] > recent_lows[i-1])
        ll_count = len(recent_lows) - 1 - hl_count
        
        total = hh_count + lh_count + hl_count + ll_count
        if total == 0:
            return {'type': 'unknown', 'clarity': 0.0}
        
        bullish_score = (hh_count + hl_count) / total
        clarity = abs(bullish_score - 0.5) * 2  # 0-1 clarity
        
        if bullish_score > 0.6:
            structure_type = 'uptrend'
        elif bullish_score < 0.4:
            structure_type = 'downtrend'
        else:
            structure_type = 'range'
        
        return {'type': structure_type, 'clarity': clarity}

    def _default_regime(self) -> Dict[str, Any]:
        """Return default regime when insufficient data."""
        return {
            'trend_type': 'unknown',
            'trend_direction': 'neutral',
            'volatility_regime': 'normal',
            'hurst_exponent': 0.5,
            'adx': 20.0,
            'structure': {'type': 'unknown', 'clarity': 0.0},
            'confidence': 0.3,
            'regime_name': 'unknown_neutral_normal',
        }




