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
from dataclasses import dataclass, field
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
    strategy: str = "unknown"
    indicators: Dict[str, Any] = field(default_factory=dict)
    reasoning: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
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
        
        logger.info(f" Strategy '{name}' initialized")
    
    @abstractmethod
    def analyze(self, 
               candles: pd.DataFrame,
               current_price: float) -> Optional[TradingSignal]:
        """
        Generate trading signal based on market data
        
        Args:
            candles: Historical candle data
            current_price: Current market price
        
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

    def calculate_fixed_sl(self, entry_price: float, direction: str, 
                          candle_data: pd.DataFrame = None, 
                          max_points: int = 300) -> float:
        """
        Calculate FIXED stop loss capped at max_points
        
        Uses technical analysis to find optimal level within 200-300 point range.
        SL NEVER widens after entry - only trails when in profit.
        
        Args:
            entry_price: Entry price
            direction: BUY or SELL
            candle_data: Recent candles for ATR/EMA analysis
            max_points: Maximum SL distance in points (default 300)
        
        Returns:
            Fixed stop loss price
        """
        if candle_data is not None and len(candle_data) >= 20:
            # Calculate ATR for context
            high = candle_data['high']
            low = candle_data['low']
            close = candle_data['close']
            
            tr1 = high - low
            tr2 = abs(high - close.shift(1))
            tr3 = abs(low - close.shift(1))
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = tr.rolling(14).mean().iloc[-1]
            
            # Find recent swing points
            lookback = 10
            recent_lows = low.iloc[-lookback:]
            recent_highs = high.iloc[-lookback:]
            
            swing_low = recent_lows.min()
            swing_high = recent_highs.max()
            
            # Calculate EMA levels
            ema_9 = close.ewm(span=9).mean().iloc[-1]
            
            if direction == "BUY":
                # For BUY: SL below entry, use best technical level
                sl_candidates = []
                
                # 1. Below swing low (if close enough)
                if swing_low < entry_price:
                    dist = entry_price - swing_low
                    if dist <= max_points:
                        sl_candidates.append(swing_low)
                
                # 2. Below EMA 9 (if close enough)
                if ema_9 < entry_price:
                    dist = entry_price - ema_9
                    if dist <= max_points:
                        sl_candidates.append(ema_9)
                
                # 3. ATR-based (capped)
                if atr:
                    atr_sl = entry_price - min(atr * 1.5, max_points)
                    sl_candidates.append(atr_sl)
                
                # 4. Default: max_points below entry
                sl_candidates.append(entry_price - max_points)
                
                # Choose tightest SL (highest value for BUY)
                stop_loss = max(sl_candidates)
                stop_loss = max(stop_loss, entry_price - max_points)
                
            else:  # SELL
                sl_candidates = []
                
                # 1. Above swing high (if close enough)
                if swing_high > entry_price:
                    dist = swing_high - entry_price
                    if dist <= max_points:
                        sl_candidates.append(swing_high)
                
                # 2. Above EMA 9 (if close enough)
                if ema_9 > entry_price:
                    dist = ema_9 - entry_price
                    if dist <= max_points:
                        sl_candidates.append(ema_9)
                
                # 3. ATR-based (capped)
                if atr:
                    atr_sl = entry_price + min(atr * 1.5, max_points)
                    sl_candidates.append(atr_sl)
                
                # 4. Default: max_points above entry
                sl_candidates.append(entry_price + max_points)
                
                # Choose tightest SL (lowest value for SELL)
                stop_loss = min(sl_candidates)
                stop_loss = min(stop_loss, entry_price + max_points)
        else:
            # No candle data - use fixed distance
            if direction == "BUY":
                stop_loss = entry_price - max_points
            else:
                stop_loss = entry_price + max_points
        
        return round(stop_loss, 2)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get strategy statistics"""
        return {
            "name": self.name,
            "signals_generated": self.signals_generated,
            "signals_approved": self.signals_approved,
            "signals_rejected": self.signals_rejected,
            "approval_rate": self.signals_approved / max(1, self.signals_generated)
        }




