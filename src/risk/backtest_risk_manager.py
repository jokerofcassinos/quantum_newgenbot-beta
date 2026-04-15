"""
Simplified Risk Manager for Backtest Integration
CEO: Qwen Code | Created: 2026-04-11

This is a synchronous version of RiskManager designed specifically for backtesting.
The original RiskManager uses async which doesn't work well in the backtest loop.
"""

from typing import Dict, Any
from loguru import logger


class BacktestRiskManager:
    """
    Simplified risk manager for backtest environment.
    Provides real-time validation without async overhead.
    """

    def __init__(self, initial_capital: float = 100000.0):
        self.initial_capital = initial_capital
        self.daily_start_balance = initial_capital
        self.daily_pnl = 0.0
        self.total_pnl = 0.0
        self.consecutive_losses = 0
        self.consecutive_wins = 0
        self.trades_today = 0

        # FTMO limits (based on INITIAL capital, not current)
        self.daily_loss_limit = initial_capital * 0.05  # 5% of initial
        self.total_loss_limit = initial_capital * 0.10  # 10% of initial

        logger.info(f" Backtest Risk Manager initialized")
        logger.info(f"   Initial Capital: ${initial_capital:,.2f}")
        logger.info(f"   Daily Loss Limit: ${self.daily_loss_limit:,.2f} (5%)")
        logger.info(f"   Total Loss Limit: ${self.total_loss_limit:,.2f} (10%)")

    def validate_trade(self, risk_amount: float, reward_amount: float, current_capital: float) -> Dict[str, Any]:
        """
        Validate if a trade meets risk criteria.
        Returns dict with approved status and reasons.
        """
        result = {
            'approved': True,
            'reasons': [],
            'warnings': []
        }

        # 1. Check daily loss limit
        current_daily_loss = abs(min(0, self.daily_pnl))
        if current_daily_loss + risk_amount > self.daily_loss_limit:
            result['approved'] = False
            result['reasons'].append(f"Daily loss limit would be exceeded: ${current_daily_loss + risk_amount:.2f} > ${self.daily_loss_limit:.2f}")

        # 2. Check total drawdown limit
        current_total_loss = abs(min(0, self.total_pnl))
        if current_total_loss + risk_amount > self.total_loss_limit:
            result['approved'] = False
            result['reasons'].append(f"Total drawdown limit would be exceeded: ${current_total_loss + risk_amount:.2f} > ${self.total_loss_limit:.2f}")

        # 3. Check R:R ratio (minimum 1.5:1)
        if risk_amount > 0 and reward_amount > 0:
            rr_ratio = reward_amount / risk_amount
            if rr_ratio < 1.5:
                result['warnings'].append(f"Low R:R ratio: {rr_ratio:.2f}:1 (minimum 1.5:1)")

        # 4. Warning for consecutive losses
        if self.consecutive_losses >= 3:
            result['warnings'].append(f" {self.consecutive_losses} consecutive losses - risk is elevated")

        # 5. Warning if approaching daily limit
        daily_used_pct = (current_daily_loss / self.daily_loss_limit) * 100
        if daily_used_pct > 60:
            result['warnings'].append(f" Daily loss at {daily_used_pct:.1f}% of limit")

        return result

    def record_trade(self, pnl: float):
        """Record trade PnL and update tracking."""
        self.daily_pnl += pnl
        self.total_pnl += pnl
        self.trades_today += 1

        if pnl > 0:
            self.consecutive_wins += 1
            self.consecutive_losses = 0
        else:
            self.consecutive_losses += 1
            self.consecutive_wins = 0

    def reset_daily_tracking(self, new_balance: float):
        """Reset daily tracking for new day."""
        self.daily_start_balance = new_balance
        self.daily_pnl = 0.0
        self.trades_today = 0

    def should_stop_trading(self) -> tuple:
        """Check if trading should be stopped due to risk limits."""
        # Daily loss check
        daily_loss = abs(min(0, self.daily_pnl))
        if daily_loss >= self.daily_loss_limit:
            return True, f"Daily loss limit reached: ${daily_loss:.2f} / ${self.daily_loss_limit:.2f}"

        # Total loss check
        total_loss = abs(min(0, self.total_pnl))
        if total_loss >= self.total_loss_limit:
            return True, f"Total loss limit reached: ${total_loss:.2f} / ${self.total_loss_limit:.2f}"

        # Consecutive losses check
        if self.consecutive_losses >= 7:
            return True, f"7 consecutive losses - mandatory review"

        return False, "Trading allowed"

    def get_summary(self) -> Dict[str, Any]:
        """Get risk summary for logging."""
        return {
            'daily_pnl': self.daily_pnl,
            'total_pnl': self.total_pnl,
            'daily_loss_used_pct': (abs(min(0, self.daily_pnl)) / self.daily_loss_limit) * 100,
            'total_loss_used_pct': (abs(min(0, self.total_pnl)) / self.total_loss_limit) * 100,
            'consecutive_losses': self.consecutive_losses,
            'consecutive_wins': self.consecutive_wins,
            'should_stop': self.should_stop_trading()[0]
        }




