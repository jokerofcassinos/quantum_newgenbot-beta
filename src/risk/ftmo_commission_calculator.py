"""
FTMO Commission Calculator - CORRECTED Real cost analysis
CEO: Qwen Code | Created: 2026-04-10

BTCUSD Contract Specifications (FTMO):
- 1 lot = 1 BTC
- 0.01 lot = 0.01 BTC
- Point = $0.01 price movement
- 0.01 lot: $1 price move = $0.01 P&L
- 1.00 lot: $1 price move = $1.00 P&L

Commission: $0.45 per 0.01 lot per side = $45 per 1.0 lot per side
"""

from typing import Dict, Any
from loguru import logger


class FTMOCommissionCalculator:
    """Corrected commission calculator for BTCUSD"""
    
    COMMISSION_PER_LOT_PER_SIDE = 45.00  # FTMO: $45 per 1.0 lot per side
    
    def __init__(self):
        logger.info(" FTMO Commission Calculator initialized (BTCUSD)")
    
    def calculate_commission(self, volume: float) -> Dict[str, float]:
        """
        Calculate FTMO commission
        
        Args:
            volume: Lot size
        
        Returns:
            dict: Commission breakdown
        """
        commission_per_side = volume * self.COMMISSION_PER_LOT_PER_SIDE
        total_commission = commission_per_side * 2.0  # Round trip
        
        return {
            "volume": volume,
            "commission_entry": commission_per_side,
            "commission_exit": commission_per_side,
            "total_commission": total_commission,
        }
    
    def calculate_pnl_per_point(self, volume: float) -> float:
        """
        Calculate P&L per point of price movement
        
        For BTCUSD:
        - 0.01 lot: 1 point ($0.01) = $0.01 P&L
        - 1.00 lot: 1 point ($0.01) = $1.00 P&L
        
        So: P&L per point = volume (in lots)
        
        Args:
            volume: Lot size
        
        Returns:
            float: P&L per point
        """
        return volume  # $1 per point per 1.0 lot
    
    def analyze_trade(self,
                     volume: float,
                     entry_price: float,
                     stop_loss_price: float,
                     take_profit_price: float,
                     spread_points: float = 100.0) -> Dict[str, Any]:
        """
        Complete trade analysis with realistic costs
        
        Args:
            volume: Lot size
            entry_price: Entry price
            stop_loss_price: Stop loss price
            take_profit_price: Take profit price
            spread_points: Spread in points
        
        Returns:
            dict: Complete analysis
        """
        # Calculate distances
        stop_distance = abs(entry_price - stop_loss_price)
        tp_distance = abs(take_profit_price - entry_price)
        
        # Convert to points ($0.01 = 1 point)
        stop_points = stop_distance / 0.01
        tp_points = tp_distance / 0.01
        
        # Gross P&L
        pnl_per_point = self.calculate_pnl_per_point(volume)
        gross_profit = tp_points * pnl_per_point
        gross_loss = stop_points * pnl_per_point
        
        # Costs
        commission = self.calculate_commission(volume)
        spread_cost = spread_points * pnl_per_point
        
        total_costs = commission["total_commission"] + spread_cost
        
        # Net P&L
        net_profit = gross_profit - total_costs
        net_loss = gross_loss + total_costs
        
        # R:R ratios
        gross_rr = gross_profit / gross_loss if gross_loss > 0 else 0
        net_rr = net_profit / net_loss if net_loss > 0 else 0
        
        # Break-even
        break_even_points = total_costs / pnl_per_point
        break_even_price = break_even_points * 0.01
        
        # Costs as % of profit
        cost_percent = (total_costs / gross_profit * 100) if gross_profit > 0 else 100
        
        return {
            "volume": volume,
            "entry": entry_price,
            "stop_loss": stop_loss_price,
            "take_profit": take_profit_price,
            "stop_distance_points": stop_points,
            "tp_distance_points": tp_points,
            "gross_profit": gross_profit,
            "gross_loss": gross_loss,
            "commission_total": commission["total_commission"],
            "spread_cost": spread_cost,
            "total_costs": total_costs,
            "net_profit": net_profit,
            "net_loss": net_loss,
            "gross_rr": gross_rr,
            "net_rr": net_rr,
            "break_even_points": break_even_points,
            "break_even_dollars": break_even_price,
            "costs_eat_profit_percent": cost_percent,
            "commission_dominance": commission["total_commission"] / total_costs * 100 if total_costs > 0 else 0
        }
    
    def print_analysis(self, analysis: Dict[str, Any]):
        """Print formatted analysis"""
        print("\n" + "="*80)
        print(f" TRADE ANALYSIS - {analysis['volume']:.2f} lots")
        print("="*80)
        
        print(f"\n Entry: ${analysis['entry']:.2f}")
        print(f" Stop Loss: ${analysis['stop_loss']:.2f} ({analysis['stop_distance_points']:.0f} points)")
        print(f" Take Profit: ${analysis['take_profit']:.2f} ({analysis['tp_distance_points']:.0f} points)")
        
        print(f"\n GROSS PROFIT: ${analysis['gross_profit']:.2f}")
        print(f" GROSS LOSS: ${analysis['gross_loss']:.2f}")
        print(f" GROSS R:R: 1:{analysis['gross_rr']:.2f}")
        
        print(f"\n COMMISSION: ${analysis['commission_total']:.2f}")
        print(f" SPREAD COST: ${analysis['spread_cost']:.2f}")
        print(f" TOTAL COSTS: ${analysis['total_costs']:.2f}")
        
        print(f"\n NET PROFIT: ${analysis['net_profit']:.2f}")
        print(f" NET LOSS: ${analysis['net_loss']:.2f}")
        print(f" NET R:R: 1:{analysis['net_rr']:.2f}")
        
        print(f"\n Break-even: {analysis['break_even_points']:.0f} points (${analysis['break_even_dollars']:.2f})")
        print(f" Costs eat {analysis['costs_eat_profit_percent']:.1f}% of profit")
        print(f" Commission is {analysis['commission_dominance']:.1f}% of total costs")
        
        print("\n" + "="*80)




