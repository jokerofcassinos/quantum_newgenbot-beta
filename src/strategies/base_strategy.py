"""
Strategy Engine - Base strategy class and signal generation
CEO: Qwen Code | Created: 2026-04-10

Handles:
- Base strategy architecture
- Signal generation
- Entry/exit logic
- Integration with DNA Engine
- Commission and spread awareness
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from dataclasses import dataclass
from loguru import logger

import pandas as pd
import numpy as np


@dataclass
class TradingSignal:
    """Represents a trading signal with all necessary parameters"""
    symbol: str
    direction: str  # "BUY" or "SELL"
    strength: float  # 0.0 to 1.0
    entry_price: float
    stop_loss: float
    take_profit: float
    risk_reward_ratio: float
    confidence: float  # 0.0 to 1.0
    strategy_name: str
    timeframe: str
    indicators: Dict[str, Any]
    rationale: str
    timestamp: datetime
    estimated_commission: float = 0.0
    estimated_spread_cost: float = 0.0
    net_expected_profit: float = 0.0


class BaseStrategy(ABC):
    """
    Abstract base class for all trading strategies
    
    Each strategy must:
    - Implement generate_signal() method
    - Work with DNA Engine parameters
    - Calculate realistic P&L (including commissions)
    - Provide clear rationale
    """
    
    def __init__(self, name: str, dna_params: Dict[str, Any]):
        self.name = name
        self.dna_params = dna_params
        self.signals_generated = 0
        self.signals_approved = 0
        self.signals_rejected = 0
        
        logger.info(f"📊 Strategy '{name}' initialized")
    
    @abstractmethod
    async def generate_signal(self, 
                             candles: pd.DataFrame,
                             market_data: Dict[str, Any],
                             dna_params: Dict[str, Any]) -> Optional[TradingSignal]:
        """
        Generate trading signal based on market data
        
        Args:
            candles: Historical candle data
            market_data: Current market conditions
            dna_params: Dynamic DNA parameters
        
        Returns:
            TradingSignal or None
        """
        pass
    
    def calculate_costs(self, 
                       volume: float, 
                       spread_points: float,
                       point_value: float) -> Dict[str, float]:
        """
        Calculate all trading costs (FTMO-specific)
        
        FTMO Commission Structure:
        - $0.45 per 0.01 lot = $45 per 1.0 lot
        - This is PER SIDE (entry + exit = 2x)
        
        Args:
            volume: Lot size
            spread_points: Current spread in points
            point_value: Value per point
        
        Returns:
            dict: Cost breakdown
        """
        # FTMO Commission: $45 per 1.0 lot per side
        commission_per_lot = 45.0
        commission_per_side = volume * commission_per_lot
        
        # Round trip (entry + exit)
        total_commission = commission_per_side * 2
        
        # Spread cost
        spread_cost = spread_points * point_value * volume
        
        # Total costs
        total_costs = total_commission + spread_cost
        
        return {
            "commission_entry": commission_per_side,
            "commission_exit": commission_per_side,
            "total_commission": total_commission,
            "spread_cost": spread_cost,
            "total_costs": total_costs,
            "cost_per_lot": commission_per_lot,
            "volume": volume
        }
    
    def calculate_realistic_rr(self,
                              gross_profit: float,
                              gross_loss: float,
                              costs: Dict[str, float]) -> Dict[str, float]:
        """
        Calculate realistic risk:reward including all costs
        
        Args:
            gross_profit: Gross profit (before costs)
            gross_loss: Gross loss (before costs)
            costs: Cost breakdown from calculate_costs()
        
        Returns:
            dict: Realistic P&L analysis
        """
        total_costs = costs["total_costs"]
        
        # Net profit/loss
        net_profit = gross_profit - total_costs
        net_loss = gross_loss + total_costs
        
        # Realistic R:R
        if net_loss > 0:
            realistic_rr = net_profit / net_loss
        else:
            realistic_rr = 0.0
        
        # Break-even analysis
        break_even_rr = total_costs / gross_loss if gross_loss > 0 else float('inf')
        
        return {
            "gross_profit": gross_profit,
            "gross_loss": gross_loss,
            "total_costs": total_costs,
            "net_profit": net_profit,
            "net_loss": net_loss,
            "realistic_rr": realistic_rr,
            "break_even_rr": break_even_rr,
            "costs_eat_percent": (total_costs / gross_profit * 100) if gross_profit > 0 else 100
        }
    
    def validate_signal(self, signal: TradingSignal) -> tuple[bool, str]:
        """
        Validate trading signal before returning
        
        Args:
            signal: TradingSignal to validate
        
        Returns:
            tuple: (is_valid, reason)
        """
        # Check R:R ratio
        if signal.risk_reward_ratio < 1.5:
            return False, f"R:R {signal.risk_reward_ratio:.2f} too low (min 1.5)"
        
        # Check confidence
        if signal.confidence < 0.65:
            return False, f"Confidence {signal.confidence:.2f} too low (min 0.65)"
        
        # Check stop loss distance
        sl_distance = abs(signal.entry_price - signal.stop_loss)
        if sl_distance < 50:  # Minimum $50 stop for BTCUSD
            return False, f"Stop loss too tight: ${sl_distance:.2f}"
        
        # Check take profit
        tp_distance = abs(signal.entry_price - signal.take_profit)
        if tp_distance < 100:  # Minimum $100 target
            return False, f"Take profit too close: ${tp_distance:.2f}"
        
        return True, "Signal validated"
    
    def get_stats(self) -> Dict[str, Any]:
        """Get strategy statistics"""
        return {
            "name": self.name,
            "signals_generated": self.signals_generated,
            "signals_approved": self.signals_approved,
            "signals_rejected": self.signals_rejected,
            "approval_rate": self.signals_approved / max(1, self.signals_generated)
        }
