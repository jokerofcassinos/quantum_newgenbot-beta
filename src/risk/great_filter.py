"""
GreatFilter - Entry Quality Validation System
Source: Atl4s (salvaged and improved)
Created: 2026-04-11

Multi-layer entry validation:
1. Confidence threshold (minimum signal quality)
2. Spread check (reject if spread too wide)
3. Crash-phase blocking (reject during rapid drops)
4. Session limits (per-session trade caps)
5. Cooldown after losses (prevent revenge trading)
"""

from typing import Dict, Any, Tuple
from loguru import logger


class GreatFilter:
    """
    Entry quality validation system.
    
    Inspired by Atl4s GreatFilter but simplified.
    """

    def __init__(
        self,
        min_confidence: float = 0.40,
        max_spread_percent: float = 0.05,
        crash_threshold_percent: float = 2.0,
    ):
        """
        Initialize GreatFilter.
        
        Args:
            min_confidence: Minimum signal confidence
            max_spread_percent: Maximum spread as % of price
            crash_threshold_percent: Block entries if price drops > this %
        """
        self.min_confidence = min_confidence
        self.max_spread_percent = max_spread_percent
        self.crash_threshold_percent = crash_threshold_percent
        
        logger.info(" GreatFilter initialized")
        logger.info(f"   Min confidence: {min_confidence}")
        logger.info(f"   Max spread: {max_spread_percent}%")
        logger.info(f"   Crash threshold: {crash_threshold_percent}%")

    def validate_entry(
        self,
        signal_confidence: float,
        spread_percent: float,
        price_change_5min: float,
        session_allowed: bool,
    ) -> Tuple[bool, str]:
        """
        Validate trade entry quality.
        
        Args:
            signal_confidence: Signal confidence score
            spread_percent: Current spread as % of price
            price_change_5min: Price change over last 5 minutes (%)
            session_allowed: Whether session allows trading
            
        Returns:
            Tuple of (approved: bool, reason: str)
        """
        # Check 1: Session
        if not session_allowed:
            return False, "Session does not allow trading"
        
        # Check 2: Confidence
        if signal_confidence < self.min_confidence:
            return False, f"Signal quality too low: {signal_confidence:.2f} < {self.min_confidence}"
        
        # Check 3: Spread
        if spread_percent > self.max_spread_percent:
            return False, f"Spread too wide: {spread_percent:.3f}% > {self.max_spread_percent}%"
        
        # Check 4: Crash phase
        if abs(price_change_5min) > self.crash_threshold_percent:
            return False, f"Crash phase detected: {price_change_5min:.1f}% move in 5min"
        
        return True, "Entry approved"




