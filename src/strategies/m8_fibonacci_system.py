"""
M8 Fibonacci System - 8-Minute Timeframe with Phi Envelopes
Source: Laplace-Demon-AGI v3.0 (salvaged and improved)
Created: 2026-04-11

Unique 8-minute Fibonacci-based analysis system:
- 8-minute candles (Phi time unit)
- Phi-based volatility envelopes (0.618, 1.618)
- Karma Efficiency metric (volume/displacement ratio)
- Golden Coil entry pattern (EMA8/EMA55 crossovers)
"""

from typing import Dict, Any, Tuple, List, Optional
from loguru import logger
import numpy as np


class M8FibonacciSystem:
    """
    8-minute Fibonacci timeframe analysis system.
    
    Inspired by Laplace-Demon-AGI v3.0 implementation.
    This was identified as a genuinely novel concept across all legacy projects.
    """

    def __init__(self, phi: float = 1.618033988749895):
        """
        Initialize M8 Fibonacci System.
        
        Args:
            phi: Golden ratio constant
        """
        self.phi = phi
        self.phi_levels = [0.236, 0.382, 0.500, 0.618, 0.786, 1.0, 1.618, 2.618]
        
        logger.info("🌀 M8FibonacciSystem initialized")
        logger.info(f"   Phi: {phi:.6f}")
        logger.info(f"   Levels: {self.phi_levels}")

    def calculate_karma_efficiency(
        self,
        volume: float,
        price_displacement: float,
    ) -> float:
        """
        Calculate Karma Efficiency - volume/displacement ratio.
        
        This measures how much volume was required for the price move.
        High karma = efficient move (low volume, high displacement)
        Low karma = inefficient move (high volume, low displacement)
        
        Args:
            volume: Trading volume
            price_displacement: Absolute price change
            
        Returns:
            Karma efficiency score (0.0 to 1.0)
        """
        if volume <= 0 or price_displacement <= 0:
            return 0.5
        
        # Karma = displacement / volume (normalized)
        karma = price_displacement / volume
        
        # Normalize to 0-1 range using sigmoid
        karma_normalized = 1.0 / (1.0 + np.exp(-karma * 10))
        
        return karma_normalized

    def calculate_phi_envelopes(
        self,
        high: float,
        low: float,
        close: float,
    ) -> Dict[str, float]:
        """
        Calculate Phi-based volatility envelopes.
        
        Args:
            high: Period high
            low: Period low
            close: Current close
            
        Returns:
            Dict with envelope levels
        """
        range_val = high - low
        median = (high + low) / 2
        
        envelopes = {}
        for level in self.phi_levels:
            envelopes[f'upper_{level}'] = median + (range_val * level)
            envelopes[f'lower_{level}'] = median - (range_val * level)
        
        envelopes['median'] = median
        envelopes['range'] = range_val
        
        return envelopes

    def detect_golden_coil(
        self,
        ema_fast: float,
        ema_slow: float,
        price: float,
    ) -> Tuple[bool, str]:
        """
        Detect Golden Coil entry pattern (EMA8/EMA55 crossovers).
        
        Args:
            ema_fast: Fast EMA (e.g., 8-period)
            ema_slow: Slow EMA (e.g., 55-period)
            price: Current price
            
        Returns:
            Tuple of (signal_detected: bool, signal_type: str)
        """
        diff = ema_fast - ema_slow
        diff_pct = (diff / max(1, ema_slow)) * 100
        
        # Golden Coil = Fast EMA crosses above Slow EMA with momentum
        if diff > 0 and abs(diff_pct) < 0.5:
            # Bullish coil - fast just crossed above slow
            return True, "BULLISH_COIL"
        
        # Death Coil = Fast EMA crosses below Slow EMA
        if diff < 0 and abs(diff_pct) < 0.5:
            return True, "BEARISH_COIL"
        
        return False, "NO_COIL"

    def analyze(
        self,
        highs: List[float],
        lows: List[float],
        closes: List[float],
        volumes: List[float],
    ) -> Dict[str, Any]:
        """
        Complete M8 Fibonacci analysis.
        
        Args:
            highs: Price highs
            lows: Price lows
            closes: Price closes
            volumes: Trading volumes
            
        Returns:
            Complete analysis dict
        """
        if len(closes) < 10:
            return {'signal': 'INSUFFICIENT_DATA'}
        
        highs = np.array(highs)
        lows = np.array(lows)
        closes = np.array(closes)
        volumes = np.array(volumes)
        
        # Calculate EMAs
        ema8 = self._ema(closes, 8)
        ema55 = self._ema(closes, 55)
        
        # Calculate Phi envelopes
        period_high = highs[-20:].max()
        period_low = lows[-20:].min()
        envelopes = self.calculate_phi_envelopes(period_high, period_low, closes[-1])
        
        # Calculate Karma Efficiency
        price_displacement = abs(closes[-1] - closes[-20])
        total_volume = volumes[-20:].sum()
        karma = self.calculate_karma_efficiency(total_volume, price_displacement)
        
        # Detect Golden Coil
        coil_detected, coil_type = self.detect_golden_coil(ema8, ema55, closes[-1])
        
        # Determine signal
        signal = 'NEUTRAL'
        confidence = 0.5
        
        if coil_detected and karma > 0.6:
            if coil_type == 'BULLISH_COIL':
                signal = 'BUY'
                confidence = min(0.9, karma + 0.3)
            elif coil_type == 'BEARISH_COIL':
                signal = 'SELL'
                confidence = min(0.9, karma + 0.3)
        
        # Check Phi envelope position
        current_price = closes[-1]
        if current_price > envelopes.get('upper_0.618', current_price):
            signal = 'SELL'  # Overextended above 0.618
            confidence = max(confidence, 0.6)
        elif current_price < envelopes.get('lower_0.618', current_price):
            signal = 'BUY'  # Overextended below 0.618
            confidence = max(confidence, 0.6)
        
        return {
            'signal': signal,
            'confidence': confidence,
            'karma_efficiency': karma,
            'golden_coil': coil_detected,
            'coil_type': coil_type,
            'ema8': ema8,
            'ema55': ema55,
            'envelopes': envelopes,
            'current_price': current_price,
        }

    def _ema(self, data: np.ndarray, span: int) -> float:
        """Calculate EMA."""
        alpha = 2.0 / (span + 1)
        ema = data[0]
        for price in data[1:]:
            ema = alpha * price + (1 - alpha) * ema
        return ema
