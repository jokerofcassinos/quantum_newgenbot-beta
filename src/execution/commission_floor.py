"""
CommissionFloor Protocol - Minimum Profit Threshold
CEO: User Suggestion | Created: 2026-04-12

Prevents premature trade closure until commission costs are covered.

Commission structure (FTMO BTCUSD):
- $45.0 per lot per side (entry + exit = $90 per lot round trip)
- For 0.01 lot: $0.45 entry + $0.45 exit = $0.90 total
- For 0.10 lot: $4.50 entry + $4.50 exit = $9.00 total

This protocol ensures trades stay open until minimum profit threshold is reached.
"""

from typing import Dict, Any, Tuple
from loguru import logger


class CommissionFloor:
    """
    Commission floor protocol for preventing premature trade closure.
    """

    def __init__(
        self,
        commission_per_lot_per_side: float = 45.0,
        spread_cost_per_lot: float = 1.0,
        safety_margin_percent: float = 0.20,
    ):
        """
        Initialize CommissionFloor.
        
        Args:
            commission_per_lot_per_side: Commission cost per lot per side ($45 FTMO)
            spread_cost_per_lot: Estimated spread cost per lot ($1 BTCUSD)
            safety_margin_percent: Extra margin above commission (20% recommended)
        """
        self.commission_per_lot_per_side = commission_per_lot_per_side
        self.spread_cost_per_lot = spread_cost_per_lot
        self.safety_margin_percent = safety_margin_percent
        
        # Total round-trip cost per lot (entry + exit + spread)
        self.round_trip_per_lot = (commission_per_lot_per_side * 2) + spread_cost_per_lot
        
        # Minimum profit threshold (commission + safety margin)
        self.min_profit_per_lot = self.round_trip_per_lot * (1 + safety_margin_percent)
        
        logger.info("💰 CommissionFloor initialized")
        logger.info(f"   Commission/lot/side: ${commission_per_lot_per_side:.2f}")
        logger.info(f"   Spread/lot: ${spread_cost_per_lot:.2f}")
        logger.info(f"   Round-trip cost/lot: ${self.round_trip_per_lot:.2f}")
        logger.info(f"   Min profit/lot: ${self.min_profit_per_lot:.2f}")

    def calculate_minimum_profit(
        self,
        position_volume: float,
    ) -> float:
        """
        Calculate minimum profit needed to cover commissions for a position.
        
        Args:
            position_volume: Position size in lots
            
        Returns:
            Minimum profit in USD to cover commissions
        """
        return self.min_profit_per_lot * position_volume

    def should_allow_closure(
        self,
        current_pnl: float,
        position_volume: float,
        closure_reason: str,
    ) -> Tuple[bool, str]:
        """
        Check if trade closure should be allowed based on commission floor.
        
        Args:
            current_pnl: Current unrealized PnL
            position_volume: Position size in lots
            closure_reason: Reason for closure (e.g., 'trailing', 'TP1', 'erosion')
            
        Returns:
            Tuple of (allowed: bool, reason: str)
        """
        min_profit = self.calculate_minimum_profit(position_volume)
        
        # Always allow stop loss hits (risk management)
        if 'SL' in closure_reason or 'stop' in closure_reason.lower():
            return True, "Stop loss hit - risk management"
        
        # Check if PnL covers commissions
        if current_pnl >= min_profit:
            return True, f"PnL ${current_pnl:.2f} >= min ${min_profit:.2f}"
        
        # Not enough profit to cover commissions
        shortfall = min_profit - current_pnl
        return False, f"PnL ${current_pnl:.2f} < min ${min_profit:.2f} (shortfall ${shortfall:.2f})"

    def get_status(
        self,
        current_pnl: float,
        position_volume: float,
    ) -> Dict[str, Any]:
        """Get commission floor status for monitoring."""
        min_profit = self.calculate_minimum_profit(position_volume)
        shortfall = max(0, min_profit - current_pnl)
        covered = current_pnl >= min_profit
        
        return {
            'current_pnl': current_pnl,
            'min_profit': min_profit,
            'shortfall': shortfall,
            'covered': covered,
            'coverage_percent': (current_pnl / max(0.01, min_profit)) * 100,
        }
