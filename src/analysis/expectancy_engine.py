"""
ExpectancyEngine - Pre-Trade Expected Value Calculator
Source: Custom (based on forensic analysis recommendations)
Created: 2026-04-12

Calculates expected value BEFORE entering each trade:
expectancy = (win_rate × avg_win) - (loss_rate × avg_loss)

Only enters trades where expectancy > commission_cost × safety_margin

This ensures every trade has positive mathematical expectation
after accounting for all costs.
"""

from typing import Dict, Any, List, Optional, Tuple
from loguru import logger


class ExpectancyEngine:
    """
    Pre-trade expectancy calculator.
    
    Ensures every trade has positive expected value after costs.
    """

    def __init__(
        self,
        commission_per_lot_per_side: float = 45.0,
        spread_cost_per_lot: float = 1.0,
        slippage_estimate_per_trade: float = 0.5,
        min_expectancy_multiple: float = 1.5,
    ):
        """
        Initialize ExpectancyEngine.
        
        Args:
            commission_per_lot_per_side: Commission cost per lot per side ($45 FTMO)
            spread_cost_per_lot: Estimated spread cost per lot ($1 BTCUSD)
            slippage_estimate_per_trade: Estimated slippage per trade ($0.50)
            min_expectancy_multiple: Minimum expectancy must be this × total_cost
        """
        self.commission_per_lot_per_side = commission_per_lot_per_side
        self.spread_cost_per_lot = spread_cost_per_lot
        self.slippage_estimate = slippage_estimate_per_trade
        self.min_expectancy_multiple = min_expectancy_multiple
        
        # Performance tracking
        self.trades = []
        self.winning_trades = []
        self.losing_trades = []
        
        logger.info("📈 ExpectancyEngine initialized")
        logger.info(f"   Commission/lot/side: ${commission_per_lot_per_side:.2f}")
        logger.info(f"   Min expectancy multiple: {min_expectancy_multiple}x")

    def calculate_total_cost(
        self,
        position_volume: float,
    ) -> float:
        """
        Calculate total cost for a trade (commission + spread + slippage).
        
        Args:
            position_volume: Position size in lots
            
        Returns:
            Total cost in USD
        """
        commission = self.commission_per_lot_per_side * position_volume * 2  # entry + exit
        spread = self.spread_cost_per_lot * position_volume
        slippage = self.slippage_estimate * position_volume
        
        return commission + spread + slippage

    def calculate_expectancy(
        self,
        win_rate: float,
        avg_win: float,
        avg_loss: float,
        position_volume: float,
    ) -> Dict[str, Any]:
        """
        Calculate expected value for a potential trade.
        
        Args:
            win_rate: Historical win rate (0.0 to 1.0)
            avg_win: Average winning trade amount
            avg_loss: Average losing trade amount (positive number)
            position_volume: Position size in lots
            
        Returns:
            Dict with expectancy analysis
        """
        loss_rate = 1.0 - win_rate
        
        # Calculate expectancy
        expectancy = (win_rate * avg_win) - (loss_rate * avg_loss)
        
        # Calculate total cost
        total_cost = self.calculate_total_cost(position_volume)
        
        # Calculate net expectancy (after costs)
        net_expectancy = expectancy - total_cost
        
        # Calculate required minimum expectancy
        min_required_expectancy = total_cost * self.min_expectancy_multiple
        
        # Determine if trade should be taken
        is_profitable = net_expectancy > 0
        passes_threshold = expectancy >= min_required_expectancy
        
        return {
            'expectancy': expectancy,
            'total_cost': total_cost,
            'net_expectancy': net_expectancy,
            'min_required_expectancy': min_required_expectancy,
            'is_profitable': is_profitable,
            'passes_threshold': passes_threshold,
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'position_volume': position_volume,
            'risk_reward_ratio': avg_win / max(0.01, avg_loss),
            'recommendation': 'ALLOW' if (is_profitable and passes_threshold) else 'VETO',
            'reason': self._get_reason(is_profitable, passes_threshold, expectancy, min_required_expectancy),
        }

    def _get_reason(
        self,
        is_profitable: bool,
        passes_threshold: bool,
        expectancy: float,
        min_required: float,
    ) -> str:
        """Get human-readable reason for decision."""
        if is_profitable and passes_threshold:
            return f"Expectancy ${expectancy:.2f} >= required ${min_required:.2f} - GOOD TRADE"
        elif is_profitable and not passes_threshold:
            return f"Expectancy ${expectancy:.2f} < required ${min_required:.2f} - marginal"
        else:
            return f"Expectancy ${expectancy:.2f} is NEGATIVE - AVOID TRADE"

    def record_trade(
        self,
        pnl: float,
        position_volume: float,
        direction: str,
    ):
        """Record a trade for expectancy calculation."""
        self.trades.append({
            'pnl': pnl,
            'volume': position_volume,
            'direction': direction,
        })
        
        if pnl > 0:
            self.winning_trades.append(pnl)
        else:
            self.losing_trades.append(abs(pnl))

    def get_current_stats(self) -> Dict[str, Any]:
        """Get current trading statistics."""
        if not self.trades:
            return {
                'win_rate': 0.5,
                'avg_win': 10.0,
                'avg_loss': 5.0,
                'total_trades': 0,
            }
        
        win_rate = len(self.winning_trades) / max(1, len(self.trades))
        avg_win = sum(self.winning_trades) / max(1, len(self.winning_trades))
        avg_loss = sum(self.losing_trades) / max(1, len(self.losing_trades))
        
        return {
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'total_trades': len(self.trades),
            'winning_trades': len(self.winning_trades),
            'losing_trades': len(self.losing_trades),
        }
