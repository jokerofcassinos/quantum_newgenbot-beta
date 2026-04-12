"""
Anti-Metralhadora - Overtrading Prevention System
Source: DubaiMatrixASI (salvaged and improved)
Created: 2026-04-11

Prevents overtrading by enforcing:
1. Minimum time between trades
2. Maximum trades per day
3. Minimum signal quality threshold
4. Cooldown after consecutive losses
5. Session-based trade limits
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, Tuple
from loguru import logger


class AntiMetralhadora:
    """
    Prevents machine-gun overtrading that kills accounts.
    
    Inspired by DubaiMatrixASI's implementation but simplified and improved.
    """

    def __init__(
        self,
        min_interval_minutes: float = 5.0,
        max_trades_per_day: int = 25,
        min_quality_score: float = 0.40,
        max_consecutive_losses: int = 3,
        loss_cooldown_minutes: float = 30.0,
        max_trades_per_session: Dict[str, int] = None,
    ):
        """
        Initialize Anti-Metralhadora.
        
        Args:
            min_interval_minutes: Minimum time between trades
            max_trades_per_day: Maximum trades per calendar day
            min_quality_score: Minimum signal confidence to allow trade
            max_consecutive_losses: Max losses before cooldown
            loss_cooldown_minutes: Cooldown period after max losses
            max_trades_per_session: Per-session trade limits
        """
        self.min_interval_minutes = min_interval_minutes
        self.max_trades_per_day = max_trades_per_day
        self.min_quality_score = min_quality_score
        self.max_consecutive_losses = max_consecutive_losses
        self.loss_cooldown_minutes = loss_cooldown_minutes
        
        # Default session limits (Asian gets lower limit due to low liquidity)
        self.max_trades_per_session = max_trades_per_session or {
            'asian': 5,
            'london': 10,
            'ny': 10,
            'ny_overlap': 12,
            'weekend': 0,  # No trading on weekend
        }
        
        # State tracking
        self.last_trade_time: Optional[datetime] = None
        self.last_loss_time: Optional[datetime] = None
        self.trade_count_today: int = 0
        self.consecutive_losses: int = 0
        self.trade_count_per_session: Dict[str, int] = {
            'asian': 0,
            'london': 0,
            'ny': 0,
            'ny_overlap': 0,
            'weekend': 0,
        }
        self.current_session: str = 'unknown'
        self.last_reset_date: Optional[datetime.date] = None
        
        logger.info("🛡️ Anti-Metralhadora initialized")
        logger.info(f"   Min interval: {min_interval_minutes} min")
        logger.info(f"   Max trades/day: {max_trades_per_day}")
        logger.info(f"   Min quality: {min_quality_score}")
        logger.info(f"   Loss cooldown: {loss_cooldown_minutes} min after {max_consecutive_losses} losses")

    def should_allow_trade(
        self,
        signal_quality: float,
        current_session: str,
        current_time: Optional[datetime] = None,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Check if trade should be allowed based on anti-overtrading rules.
        
        Args:
            signal_quality: Signal confidence score (0.0 to 1.0)
            current_session: Current market session (asian/london/ny/ny_overlap/weekend)
            current_time: Current time (defaults to now)
            
        Returns:
            Tuple of (allowed: bool, reason: str, details: dict)
        """
        if current_time is None:
            current_time = datetime.now(timezone.utc)
        
        # Reset daily counters if new day
        self._check_daily_reset(current_time)
        
        # Update current session
        self.current_session = current_session
        
        checks = []
        details = {
            'signal_quality': signal_quality,
            'session': current_session,
            'trades_today': self.trade_count_today,
            'consecutive_losses': self.consecutive_losses,
            'time_since_last_trade': None,
            'time_since_last_loss': None,
        }
        
        # Check 1: Signal quality threshold
        if signal_quality < self.min_quality_score:
            checks.append(('FAIL', f'Signal quality {signal_quality:.2f} < {self.min_quality_score:.2f}'))
            return False, 'low_quality', details
        
        # Check 2: Weekend trading
        if self.max_trades_per_session.get(current_session, 0) == 0:
            checks.append(('FAIL', f'Trading disabled for {current_session} session'))
            return False, 'session_blocked', details
        
        # Check 3: Session trade limit
        session_count = self.trade_count_per_session.get(current_session, 0)
        session_limit = self.max_trades_per_session.get(current_session, 999)
        if session_count >= session_limit:
            checks.append(('FAIL', f'Session limit reached: {session_count}/{session_limit}'))
            return False, 'session_limit', details
        
        # Check 4: Daily trade limit
        if self.trade_count_today >= self.max_trades_per_day:
            checks.append(('FAIL', f'Daily limit reached: {self.trade_count_today}/{self.max_trades_per_day}'))
            return False, 'daily_limit', details
        
        # Check 5: Minimum interval between trades
        if self.last_trade_time is not None:
            elapsed_minutes = (current_time - self.last_trade_time).total_seconds() / 60.0
            details['time_since_last_trade'] = elapsed_minutes
            
            if elapsed_minutes < self.min_interval_minutes:
                remaining = self.min_interval_minutes - elapsed_minutes
                checks.append(('FAIL', f'Too soon: {remaining:.1f} min remaining'))
                return False, 'cooldown', details
        
        # Check 6: Consecutive loss cooldown
        if self.consecutive_losses >= self.max_consecutive_losses and self.last_loss_time is not None:
            elapsed_minutes = (current_time - self.last_loss_time).total_seconds() / 60.0
            details['time_since_last_loss'] = elapsed_minutes
            
            if elapsed_minutes < self.loss_cooldown_minutes:
                remaining = self.loss_cooldown_minutes - elapsed_minutes
                checks.append(('FAIL', f'Loss cooldown: {remaining:.1f} min remaining'))
                return False, 'loss_cooldown', details
        
        # All checks passed
        return True, 'approved', details

    def record_trade(
        self,
        result: str,  # 'win' or 'loss'
        current_session: str,
        current_time: Optional[datetime] = None,
    ) -> None:
        """
        Record a trade for tracking purposes.
        
        Args:
            result: 'win' or 'loss'
            current_session: Current market session
            current_time: Trade time (defaults to now)
        """
        if current_time is None:
            current_time = datetime.now(timezone.utc)
        
        # Update last trade time
        self.last_trade_time = current_time
        
        # Update session count
        if current_session in self.trade_count_per_session:
            self.trade_count_per_session[current_session] += 1
        
        # Update daily count
        self.trade_count_today += 1
        
        # Update consecutive losses/wins
        if result == 'loss':
            self.consecutive_losses += 1
            self.last_loss_time = current_time
            logger.warning(f"⚠️ Loss recorded. Consecutive losses: {self.consecutive_losses}")
            
            if self.consecutive_losses >= self.max_consecutive_losses:
                logger.warning(f"🛑 Loss cooldown activated: {self.loss_cooldown_minutes} min cooldown")
        else:
            self.consecutive_losses = 0
            logger.info(f"✅ Win recorded. Consecutive losses reset.")

    def _check_daily_reset(self, current_time: datetime) -> None:
        """Reset daily counters if new day."""
        current_date = current_time.date()
        
        if self.last_reset_date is None or current_date != self.last_reset_date:
            logger.info(f"🔄 Daily reset: Resetting trade counters")
            self.trade_count_today = 0
            self.trade_count_per_session = {
                'asian': 0,
                'london': 0,
                'ny': 0,
                'ny_overlap': 0,
                'weekend': 0,
            }
            self.last_reset_date = current_date

    def get_status(self) -> Dict[str, Any]:
        """Get current status for monitoring."""
        return {
            'last_trade_time': self.last_trade_time.isoformat() if self.last_trade_time else None,
            'last_loss_time': self.last_loss_time.isoformat() if self.last_loss_time else None,
            'trades_today': self.trade_count_today,
            'consecutive_losses': self.consecutive_losses,
            'current_session': self.current_session,
            'session_counts': dict(self.trade_count_per_session),
            'time_since_last_trade_min': (
                (datetime.now(timezone.utc) - self.last_trade_time).total_seconds() / 60.0
                if self.last_trade_time else None
            ),
        }

    def reset(self) -> None:
        """Reset all state (for testing or manual reset)."""
        self.last_trade_time = None
        self.last_loss_time = None
        self.trade_count_today = 0
        self.consecutive_losses = 0
        self.trade_count_per_session = {
            'asian': 0,
            'london': 0,
            'ny': 0,
            'ny_overlap': 0,
            'weekend': 0,
        }
        self.last_reset_date = None
        logger.info("🔄 Anti-Metralhadora state reset")
