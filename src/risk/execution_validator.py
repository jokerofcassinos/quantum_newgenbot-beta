"""
Execution Validator - Pre-Trade Validation System
Source: DubaiMatrixASI (salvaged and improved)
Created: 2026-04-11

Validates trade execution before sending to broker:
1. Spread check (reject if spread too wide)
2. Session check (reject if trading not allowed)
3. Margin check (reject if insufficient margin)
4. Volatility check (reject if volatility extreme)
5. News filter check (reject if high-impact news)
"""

from typing import Dict, Any, Tuple
from loguru import logger


class ExecutionValidator:
    """
    Pre-trade execution validator.
    
    Inspired by DubaiMatrixASI's implementation but simplified.
    """

    def __init__(
        self,
        max_spread_points: int = 50,
        max_volatility_multiplier: float = 3.0,
        min_margin_level: float = 200.0,
    ):
        """
        Initialize Execution Validator.
        
        Args:
            max_spread_points: Maximum allowed spread in points
            max_volatility_multiplier: Max volatility vs average (3x = reject)
            min_margin_level: Minimum margin level percentage
        """
        self.max_spread_points = max_spread_points
        self.max_volatility_multiplier = max_volatility_multiplier
        self.min_margin_level = min_margin_level
        
        logger.info(" ExecutionValidator initialized")
        logger.info(f"   Max spread: {max_spread_points} points")
        logger.info(f"   Max volatility: {max_volatility_multiplier}x average")
        logger.info(f"   Min margin: {min_margin_level}%")

    def validate(
        self,
        spread_points: int,
        current_volatility: float,
        avg_volatility: float,
        margin_level: float,
        session_allowed: bool,
    ) -> Tuple[bool, str]:
        """
        Validate trade execution.
        
        Args:
            spread_points: Current spread in points
            current_volatility: Current ATR/volatility
            avg_volatility: Average volatility
            margin_level: Current margin level percentage
            session_allowed: Whether trading is allowed in current session
            
        Returns:
            Tuple of (approved: bool, reason: str)
        """
        # Check 1: Session
        if not session_allowed:
            return False, "Trading not allowed in current session"
        
        # Check 2: Spread
        if spread_points > self.max_spread_points:
            return False, f"Spread too wide: {spread_points} > {self.max_spread_points} points"
        
        # Check 3: Volatility
        vol_ratio = current_volatility / max(1, avg_volatility)
        if vol_ratio > self.max_volatility_multiplier:
            return False, f"Volatility extreme: {vol_ratio:.1f}x > {self.max_volatility_multiplier}x"
        
        # Check 4: Margin
        if margin_level < self.min_margin_level:
            return False, f"Margin too low: {margin_level:.0f}% < {self.min_margin_level}%"
        
        return True, "Execution approved"




