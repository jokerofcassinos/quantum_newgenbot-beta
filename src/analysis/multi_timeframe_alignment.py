"""
MultiTimeframeAlignment - Cross-Timeframe Signal Confirmation
Source: Atl4s (salvaged and improved)
Created: 2026-04-12

Analyzes signal alignment across multiple timeframes:
- M1, M5, M15, H1, H4, D1
- Only trades when 3+ timeframes agree
- Increases win rate by filtering conflicting signals
"""

from typing import Dict, Any, List, Tuple
from loguru import logger
import numpy as np


class MultiTimeframeAlignment:
    """
    Multi-timeframe signal alignment system.
    
    Inspired by Atl4s implementation but simplified.
    """

    def __init__(
        self,
        timeframes: List[str] = None,
        min_aligned_timeframes: int = 3,
    ):
        """
        Initialize MultiTimeframeAlignment.
        
        Args:
            timeframes: List of timeframes to analyze
            min_aligned_timeframes: Minimum timeframes that must agree
        """
        self.timeframes = timeframes or ['M5', 'M15', 'H1', 'H4']
        self.min_aligned = min_aligned_timeframes
        
        logger.info("📊 MultiTimeframeAlignment initialized")
        logger.info(f"   Timeframes: {self.timeframes}")
        logger.info(f"   Min aligned: {min_aligned_timeframes}")

    def analyze_alignment(
        self,
        closes: Dict[str, List[float]],
        direction: str,
    ) -> Dict[str, Any]:
        """
        Analyze signal alignment across timeframes.
        
        Args:
            closes: Dict of timeframe -> price closes
            direction: Proposed trade direction ('BUY' or 'SELL')
            
        Returns:
            Dict with alignment analysis
        """
        alignment_count = 0
        total_timeframes = len(closes)
        timeframe_signals = {}
        
        for tf, tf_closes in closes.items():
            if len(tf_closes) < 20:
                continue
            
            # Calculate simple trend for this timeframe
            ema_fast = self._ema(tf_closes, 8)
            ema_slow = self._ema(tf_closes, 21)
            
            if ema_fast > ema_slow:
                tf_direction = 'BUY'
            elif ema_fast < ema_slow:
                tf_direction = 'SELL'
            else:
                tf_direction = 'NEUTRAL'
            
            timeframe_signals[tf] = tf_direction
            
            # Check if this timeframe aligns with proposed direction
            if tf_direction == direction:
                alignment_count += 1
        
        alignment_score = alignment_count / max(1, total_timeframes)
        is_aligned = alignment_count >= self.min_aligned
        
        return {
            'is_aligned': is_aligned,
            'alignment_count': alignment_count,
            'total_timeframes': total_timeframes,
            'alignment_score': alignment_score,
            'timeframe_signals': timeframe_signals,
            'recommended_action': 'ALLOW' if is_aligned else 'VETO',
        }

    def _ema(self, data: List[float], span: int) -> float:
        """Calculate EMA."""
        if len(data) < span:
            return data[-1] if data else 0
        
        alpha = 2.0 / (span + 1)
        ema = data[0]
        for price in data[1:]:
            ema = alpha * price + (1 - alpha) * ema
        return ema

    def should_trade(
        self,
        closes: Dict[str, List[float]],
        direction: str,
    ) -> Tuple[bool, str]:
        """
        Determine if trade should be allowed based on multi-TF alignment.
        
        Args:
            closes: Dict of timeframe -> price closes
            direction: Proposed trade direction
            
        Returns:
            Tuple of (allowed: bool, reason: str)
        """
        analysis = self.analyze_alignment(closes, direction)
        
        if analysis['is_aligned']:
            return True, f"{analysis['alignment_count']}/{analysis['total_timeframes']} timeframes aligned"
        else:
            return False, f"Only {analysis['alignment_count']}/{analysis['total_timeframes']} timeframes aligned (need {self.min_aligned})"
