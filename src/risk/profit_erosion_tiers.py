"""
Profit Erosion Tiers - Multi-Level Profit Protection System
Source: Atl4s (salvaged and improved)
Created: 2026-04-11

Protects unrealized gains by tightening tolerance as profit increases:
- $0-$30:   No protection (let it breathe)
- $30-$50:  Allow 50% retracement
- $50-$100: Allow 40% retracement
- $100-$200: Allow 30% retracement
- $200-$300: Allow 10% retracement
- $300+:    Allow 5% retracement

This prevents giving back large profits while still giving trades room to develop.
"""

from typing import Dict, Any, List, Tuple, Optional
from loguru import logger


class ProfitErosionTiers:
    """
    Multi-tier profit protection system.
    
    Inspired by Atl4s implementation but simplified and improved.
    """

    def __init__(
        self,
        tiers: List[Tuple[float, float]] = None,
    ):
        """
        Initialize Profit Erosion Tiers.
        
        Args:
            tiers: List of (profit_threshold, max_retrace_pct) tuples
                   Default: [(30, 0.0), (50, 0.50), (100, 0.40), (200, 0.30), (300, 0.10), (999999, 0.05)]
        """
        if tiers is None:
            self.tiers = [
                (30.0, 0.0),     # $0-$30: no protection
                (50.0, 0.50),    # $30-$50: 50% retrace allowed
                (100.0, 0.40),   # $50-$100: 40% allowed
                (200.0, 0.30),   # $100-$200: 30% allowed
                (300.0, 0.10),   # $200-$300: 10% allowed
                (999999.0, 0.05),  # $300+: 5% allowed
            ]
        else:
            self.tiers = tiers
        
        logger.info(" ProfitErosionTiers initialized")
        for threshold, retrace in self.tiers:
            logger.info(f"   ${threshold:>8.0f}: {retrace*100:.0f}% max retrace")

    def check_erosion(
        self,
        current_pnl: float,
        peak_pnl: float,
    ) -> Tuple[bool, str]:
        """
        Check if profit has eroded beyond allowed threshold.
        
        Args:
            current_pnl: Current unrealized PnL
            peak_pnl: Peak unrealized PnL reached
            
        Returns:
            Tuple of (should_exit: bool, reason: str)
        """
        # Only protect profits above minimum threshold
        if peak_pnl < self.tiers[0][0]:
            return False, "Below protection threshold"
        
        # Calculate retracement percentage
        if peak_pnl <= 0:
            return False, "No profit to protect"
        
        retrace_amount = peak_pnl - current_pnl
        retrace_pct = retrace_amount / peak_pnl if peak_pnl > 0 else 0
        
        # Find applicable tier
        for threshold, max_retrace in self.tiers:
            if peak_pnl <= threshold:
                # This is our tier
                if retrace_pct > max_retrace:
                    return True, f"Profit erosion: {retrace_pct*100:.1f}% > {max_retrace*100:.0f}% allowed at ${peak_pnl:.0f} peak"
                break
        
        # If we get here, we're in the highest tier
        _, max_retrace = self.tiers[-1]
        if retrace_pct > max_retrace:
            return True, f"Profit erosion: {retrace_pct*100:.1f}% > {max_retrace*100:.0f}% allowed at ${peak_pnl:.0f} peak"
        
        return False, f"OK: {retrace_pct*100:.1f}% retrace (tier allows {max_retrace*100:.0f}%)"

    def get_protection_level(self, peak_pnl: float) -> Dict[str, Any]:
        """Get current protection level for monitoring."""
        for threshold, max_retrace in self.tiers:
            if peak_pnl <= threshold:
                return {
                    'tier_threshold': threshold,
                    'max_retrace_pct': max_retrace,
                    'description': f"${threshold:.0f} tier: {max_retrace*100:.0f}% max retrace",
                }
        
        # Highest tier
        threshold, max_retrace = self.tiers[-1]
        return {
            'tier_threshold': threshold,
            'max_retrace_pct': max_retrace,
            'description': f"${threshold:.0f}+ tier: {max_retrace*100:.0f}% max retrace",
        }




