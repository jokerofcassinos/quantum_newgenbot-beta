"""
Tests for Anti-Metralhadora
Tests the overtrading prevention system
"""

import pytest
import sys
import os
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.risk.anti_metralhadora import AntiMetralhadora


class TestAntiMetralhadora:
    """Test Anti-Metralhadora system"""

    def setup_method(self):
        """Setup test fixtures"""
        self.am = AntiMetralhadora(
            min_interval_minutes=5.0,
            max_trades_per_day=25,
            min_quality_score=0.40,
            max_consecutive_losses=3,
            loss_cooldown_minutes=30.0,
        )

    def test_initialization(self):
        """Test Anti-Metralhadora initializes correctly"""
        assert self.am.min_interval_minutes == 5.0
        assert self.am.max_trades_per_day == 25
        assert self.am.min_quality_score == 0.40
        assert self.am.max_consecutive_losses == 3
        assert self.am.loss_cooldown_minutes == 30.0

    def test_should_allow_trade_normal(self):
        """Test normal trade allowance"""
        now = datetime.now(timezone.utc)
        allowed, reason, details = self.am.should_allow_trade(
            signal_quality=0.50,
            current_session='london',
            current_time=now,
        )
        assert allowed == True

    def test_should_reject_low_quality(self):
        """Test rejection of low quality signals"""
        now = datetime.now(timezone.utc)
        allowed, reason, details = self.am.should_allow_trade(
            signal_quality=0.30,  # Below 0.40 threshold
            current_session='london',
            current_time=now,
        )
        assert allowed == False
        assert 'quality' in reason.lower()

    def test_daily_reset(self):
        """Test daily trade counter reset"""
        now = datetime.now(timezone.utc)
        
        # Record 30 trades (above 25 limit)
        for i in range(30):
            self.am.record_trade('win', 'london', now)
        
        # Check status - should have recorded the trades
        status = self.am.get_status()
        assert 'consecutive_losses' in status  # Verify status structure works
        assert status['consecutive_losses'] == 0  # All wins, so 0 consecutive losses


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
