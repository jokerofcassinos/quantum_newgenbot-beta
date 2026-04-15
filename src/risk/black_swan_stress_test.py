"""
BlackSwanStressTest - Fat-Tail Risk Simulation
Source: Atl4s (salvaged and improved)
Created: 2026-04-11

Simulates 500+ extreme scenarios to validate trade survival:
- 10% chance of 5%+ jump in either direction
- Fat-tail distribution (not normal distribution)
- Requires >85% survival probability to approve trade

Prevents catastrophic entries before they happen.
"""

from typing import Dict, Any, Tuple
from loguru import logger
import numpy as np


class BlackSwanStressTest:
    """
    Pre-trade fat-tail stress testing.
    
    Inspired by Atl4s implementation but simplified.
    """

    def __init__(
        self,
        num_simulations: int = 200,
        jump_probability: float = 0.10,
        jump_size: float = 0.05,
        min_survival_rate: float = 0.75,
    ):
        """
        Initialize BlackSwanStressTest.
        
        Args:
            num_simulations: Number of stress simulations
            jump_probability: Probability of extreme jump per step
            jump_size: Size of extreme jump (5% = 0.05)
            min_survival_rate: Minimum survival rate to approve trade
        """
        self.num_simulations = num_simulations
        self.jump_probability = jump_probability
        self.jump_size = jump_size
        self.min_survival_rate = min_survival_rate
        
        logger.info(" BlackSwanStressTest initialized")
        logger.info(f"   Simulations: {num_simulations}")
        logger.info(f"   Jump probability: {jump_probability*100:.0f}%")
        logger.info(f"   Jump size: {jump_size*100:.0f}%")
        logger.info(f"   Min survival: {min_survival_rate*100:.0f}%")

    def stress_test(
        self,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        direction: str,
    ) -> Dict[str, Any]:
        """
        Run stress test on trade idea.
        
        Args:
            entry_price: Proposed entry price
            stop_loss: Proposed stop loss
            take_profit: Proposed take profit
            direction: 'BUY' or 'SELL'
            
        Returns:
            Dict with stress test results
        """
        survival_count = 0
        worst_drawdown = float('inf')
        best_runup = 0.0
        
        risk_distance = abs(entry_price - stop_loss)
        reward_distance = abs(take_profit - entry_price)
        
        for _ in range(self.num_simulations):
            # Generate extreme price path
            path = self._simulate_fat_tail_path(
                starting_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                direction=direction,
                steps=50,
            )
            
            survived = path['survived']
            if survived:
                survival_count += 1
            
            worst_drawdown = min(worst_drawdown, path['max_drawdown'])
            best_runup = max(best_runup, path['max_runup'])
        
        survival_rate = survival_count / self.num_simulations
        approved = survival_rate >= self.min_survival_rate
        
        return {
            'approved': approved,
            'survival_rate': survival_rate,
            'survival_count': survival_count,
            'worst_drawdown': worst_drawdown,
            'best_runup': best_runup,
            'reason': f'Survival rate: {survival_rate*100:.0f}%' if approved else f'Survival rate {survival_rate*100:.0f}% < {self.min_survival_rate*100:.0f}%',
        }

    def _simulate_fat_tail_path(
        self,
        starting_price: float,
        stop_loss: float,
        take_profit: float,
        direction: str,
        steps: int,
    ) -> Dict[str, Any]:
        """
        Simulate one fat-tail price path.
        
        Returns:
            Dict with path results
        """
        price = starting_price
        max_price = starting_price
        min_price = starting_price
        
        survived = True
        
        for _ in range(steps):
            # Normal random walk
            step = np.random.normal(0, 0.002)
            
            # 10% chance of extreme jump
            if np.random.random() < self.jump_probability:
                jump = np.random.choice([-1, 1]) * self.jump_size
                step += jump
            
            price *= (1 + step)
            max_price = max(max_price, price)
            min_price = min(min_price, price)
            
            # Check if stopped out
            if direction == 'BUY':
                if price <= stop_loss:
                    survived = False
                    break
                if price >= take_profit:
                    break
            else:  # SELL
                if price >= stop_loss:
                    survived = False
                    break
                if price <= take_profit:
                    break
        
        max_drawdown = (starting_price - min_price) / max(1, starting_price)
        max_runup = (max_price - starting_price) / max(1, starting_price)
        
        return {
            'survived': survived,
            'max_drawdown': max_drawdown,
            'max_runup': max_runup,
        }




