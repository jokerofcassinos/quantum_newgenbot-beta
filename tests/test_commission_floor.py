"""
Tests for CommissionFloor Protocol
Tests the commission floor logic to ensure trades don't close prematurely
"""

import pytest
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.execution.commission_floor import CommissionFloor


class TestCommissionFloor:
    """Test CommissionFloor protocol"""

    def setup_method(self):
        """Setup test fixtures"""
        self.floor = CommissionFloor(
            commission_per_lot_per_side=45.0,
            spread_cost_per_lot=1.0,
            safety_margin_percent=0.20,
        )

    def test_initialization(self):
        """Test CommissionFloor initializes correctly"""
        assert self.floor.commission_per_lot_per_side == 45.0
        assert self.floor.spread_cost_per_lot == 1.0
        assert self.floor.safety_margin_percent == 0.20
        # Round-trip cost = (45 * 2) + 1 = $91 per lot
        assert self.floor.round_trip_per_lot == 91.0
        # Min profit = 91 * 1.20 = $109.20 per lot
        assert abs(self.floor.min_profit_per_lot - 109.20) < 0.01

    def test_calculate_minimum_profit(self):
        """Test minimum profit calculation for different position sizes"""
        # 0.01 lot should need $1.092 minimum
        min_profit_001 = self.floor.calculate_minimum_profit(0.01)
        assert abs(min_profit_001 - 1.092) < 0.01

        # 0.10 lot should need $10.92 minimum
        min_profit_010 = self.floor.calculate_minimum_profit(0.10)
        assert abs(min_profit_010 - 10.92) < 0.01

        # 1.00 lot should need $109.20 minimum
        min_profit_100 = self.floor.calculate_minimum_profit(1.00)
        assert abs(min_profit_100 - 109.20) < 0.01

    def test_should_allow_closure_below_floor(self):
        """Test that closure is blocked when PnL is below floor"""
        # 0.10 lot position needs $10.92 minimum
        min_profit = self.floor.calculate_minimum_profit(0.10)

        # PnL below floor should be rejected
        allowed, reason = self.floor.should_allow_closure(
            current_pnl=min_profit - 5.0,  # $5 below floor
            position_volume=0.10,
            closure_reason='trailing',
        )
        assert allowed == False
        assert 'shortfall' in reason.lower() or 'pnl' in reason.lower()

    def test_should_allow_closure_above_floor(self):
        """Test that closure is allowed when PnL is above floor"""
        # 0.10 lot position needs $10.92 minimum
        min_profit = self.floor.calculate_minimum_profit(0.10)

        # PnL above floor should be accepted
        allowed, reason = self.floor.should_allow_closure(
            current_pnl=min_profit + 10.0,  # $10 above floor
            position_volume=0.10,
            closure_reason='trailing',
        )
        assert allowed == True

    def test_stop_loss_always_allowed(self):
        """Test that stop loss hits are always allowed regardless of PnL"""
        # Even with negative PnL, SL should be allowed
        allowed, reason = self.floor.should_allow_closure(
            current_pnl=-50.0,  # Losing trade
            position_volume=0.10,
            closure_reason='SL hit',
        )
        assert allowed == True
        assert 'stop' in reason.lower() or 'risk' in reason.lower()

    def test_get_status(self):
        """Test status reporting"""
        status = self.floor.get_status(
            current_pnl=15.0,
            position_volume=0.10,
        )
        assert 'current_pnl' in status
        assert 'min_profit' in status
        assert 'shortfall' in status
        assert 'covered' in status
        assert 'coverage_percent' in status

        # $15 PnL vs $10.92 min = covered
        assert status['covered'] == True
        assert status['coverage_percent'] > 100.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
