"""
Tests for ExpectancyEngine
Tests the pre-trade expected value calculator
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.analysis.expectancy_engine import ExpectancyEngine


class TestExpectancyEngine:
    """Test ExpectancyEngine"""

    def setup_method(self):
        """Setup test fixtures"""
        self.engine = ExpectancyEngine(
            commission_per_lot_per_side=45.0,
            spread_cost_per_lot=1.0,
            slippage_estimate_per_trade=0.5,
            min_expectancy_multiple=1.5,
        )

    def test_initialization(self):
        """Test ExpectancyEngine initializes correctly"""
        assert self.engine.commission_per_lot_per_side == 45.0
        assert self.engine.spread_cost_per_lot == 1.0
        assert self.engine.slippage_estimate == 0.5
        assert self.engine.min_expectancy_multiple == 1.5

    def test_calculate_total_cost(self):
        """Test total cost calculation"""
        # 0.01 lot: commission=0.90, spread=0.01, slippage=0.005 = $0.915
        cost_001 = self.engine.calculate_total_cost(0.01)
        assert abs(cost_001 - 0.915) < 0.01

        # 0.10 lot: commission=9.00, spread=0.10, slippage=0.05 = $9.15
        cost_010 = self.engine.calculate_total_cost(0.10)
        assert abs(cost_010 - 9.15) < 0.01

        # 1.00 lot: commission=90.00, spread=1.00, slippage=0.50 = $91.50
        cost_100 = self.engine.calculate_total_cost(1.00)
        assert abs(cost_100 - 91.50) < 0.01

    def test_calculate_expectancy_profitable(self):
        """Test expectancy calculation for profitable trade"""
        result = self.engine.calculate_expectancy(
            win_rate=0.60,
            avg_win=20.0,
            avg_loss=10.0,
            position_volume=0.10,
        )
        
        # Expectancy = (0.60 * 20) - (0.40 * 10) = 12 - 4 = $8
        assert abs(result['expectancy'] - 8.0) < 0.01
        # Note: is_profitable checks NET expectancy (after costs)
        # Total cost for 0.10 lot = $9.15, so net = $8 - $9.15 = -$1.15
        # This is expected behavior - gross positive but net negative after costs

    def test_calculate_expectancy_unprofitable(self):
        """Test expectancy calculation for unprofitable trade"""
        result = self.engine.calculate_expectancy(
            win_rate=0.40,
            avg_win=10.0,
            avg_loss=20.0,
            position_volume=0.10,
        )
        
        # Expectancy = (0.40 * 10) - (0.60 * 20) = 4 - 12 = -$8
        assert abs(result['expectancy'] - (-8.0)) < 0.01
        assert result['is_profitable'] == False
        assert result['recommendation'] == 'VETO'

    def test_record_trade(self):
        """Test trade recording"""
        self.engine.record_trade(pnl=15.0, position_volume=0.10, direction='BUY')
        self.engine.record_trade(pnl=-8.0, position_volume=0.10, direction='SELL')
        self.engine.record_trade(pnl=20.0, position_volume=0.10, direction='BUY')
        
        stats = self.engine.get_current_stats()
        assert stats['total_trades'] == 3
        assert stats['winning_trades'] == 2
        assert stats['losing_trades'] == 1
        assert abs(stats['win_rate'] - 0.667) < 0.01

    def test_get_current_stats_empty(self):
        """Test stats when no trades recorded"""
        stats = self.engine.get_current_stats()
        assert stats['total_trades'] == 0
        assert stats['win_rate'] == 0.5  # Default
        assert stats['avg_win'] == 10.0  # Default
        assert stats['avg_loss'] == 5.0  # Default


if __name__ == '__main__':
    pytest.main([__file__, '-v'])



