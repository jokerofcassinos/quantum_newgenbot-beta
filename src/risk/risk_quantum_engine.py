"""
RiskQuantumEngine - Advanced 5-Factor Position Sizing
Source: DubaiMatrixASI (salvaged and improved)
Created: 2026-04-11

Calculates optimal position size based on 5 risk factors:
1. Kelly Criterion (base fraction)
2. Volatility Adjustment (ATR-based)
3. Confidence Scaling (signal quality)
4. Drawdown Protection (current DD level)
5. Correlation Check (open positions)

This replaces simple risk% sizing with sophisticated multi-factor approach.
"""

from typing import Dict, Any, Optional
from loguru import logger
import math


class RiskQuantumEngine:
    """
    Advanced position sizing with 5 risk factors.
    
    Inspired by DubaiMatrixASI's RiskQuantumEngine but simplified and improved.
    """

    def __init__(
        self,
        kelly_fraction: float = 0.25,
        max_position_size: float = 1.0,
        min_position_size: float = 0.01,
        base_risk_percent: float = 1.0,
        volatility_lookback: int = 20,
        dd_protection_threshold: float = 0.05,
        max_dd_limit: float = 0.10,
    ):
        """
        Initialize RiskQuantumEngine.
        
        Args:
            kelly_fraction: Fraction of Kelly to use (0.25 = quarter Kelly)
            max_position_size: Maximum lots allowed
            min_position_size: Minimum lots allowed
            base_risk_percent: Base risk per trade (%)
            volatility_lookback: Period for volatility calculation
            dd_protection_threshold: DD level to start reducing size
            max_dd_limit: Maximum DD before stopping trades
        """
        self.kelly_fraction = kelly_fraction
        self.max_position_size = max_position_size
        self.min_position_size = min_position_size
        self.base_risk_percent = base_risk_percent
        self.volatility_lookback = volatility_lookback
        self.dd_protection_threshold = dd_protection_threshold
        self.max_dd_limit = max_dd_limit
        
        logger.info("⚛️ RiskQuantumEngine initialized")
        logger.info(f"   Kelly fraction: {kelly_fraction}")
        logger.info(f"   Max position: {max_position_size} lots")
        logger.info(f"   Base risk: {base_risk_percent}%")
        logger.info(f"   DD protection: {dd_protection_threshold*100:.0f}%")

    def calculate_position_size(
        self,
        equity: float,
        win_rate: float,
        avg_win_loss_ratio: float,
        signal_confidence: float,
        current_volatility: float,
        avg_volatility: float,
        current_drawdown: float,
        correlation_factor: float = 1.0,
    ) -> Dict[str, Any]:
        """
        Calculate optimal position size with 5 risk factors.
        
        Args:
            equity: Current account equity
            win_rate: Historical win rate (0.0 to 1.0)
            avg_win_loss_ratio: Average win / average loss ratio
            signal_confidence: Current signal confidence (0.0 to 1.0)
            current_volatility: Current ATR or volatility measure
            avg_volatility: Average volatility over lookback period
            current_drawdown: Current drawdown from peak (0.0 to 1.0)
            correlation_factor: Correlation with open positions (1.0 = no correlation)
            
        Returns:
            Dict with position size and factor breakdown
        """
        factors = {}
        
        # Factor 1: Kelly Criterion (base fraction)
        # Kelly % = W - [(1-W)/R] where W=win rate, R=win/loss ratio
        kelly_percent = win_rate - ((1 - win_rate) / max(0.1, avg_win_loss_ratio))
        kelly_percent = max(0, kelly_percent) * self.kelly_fraction
        factors['kelly'] = kelly_percent
        
        # Factor 2: Volatility Adjustment
        # Reduce size when volatility is higher than average
        vol_ratio = current_volatility / max(1, avg_volatility)
        if vol_ratio > 1.5:
            vol_adjustment = 0.5  # Cut size in half for extreme volatility
        elif vol_ratio > 1.2:
            vol_adjustment = 0.75  # Reduce 25%
        elif vol_ratio < 0.8:
            vol_adjustment = 1.2  # Increase 20% for low volatility
        else:
            vol_adjustment = 1.0  # Normal
        factors['volatility'] = vol_adjustment
        
        # Factor 3: Confidence Scaling
        # Scale position by signal confidence
        confidence_scaling = signal_confidence / 0.5  # Normalize around 0.5
        confidence_scaling = max(0.5, min(1.5, confidence_scaling))  # Cap between 0.5-1.5
        factors['confidence'] = confidence_scaling
        
        # Factor 4: Drawdown Protection
        # Reduce size as drawdown increases
        if current_drawdown >= self.max_dd_limit:
            dd_protection = 0.0  # Stop trading
        elif current_drawdown >= self.dd_protection_threshold:
            # Linear reduction from 100% to 0% between threshold and limit
            dd_protection = 1.0 - ((current_drawdown - self.dd_protection_threshold) / 
                                  (self.max_dd_limit - self.dd_protection_threshold))
        else:
            dd_protection = 1.0  # No reduction
        factors['drawdown'] = dd_protection
        
        # Factor 5: Correlation Check
        # Reduce size if correlated with open positions
        correlation_adjustment = max(0.5, min(1.0, correlation_factor))
        factors['correlation'] = correlation_adjustment
        
        # Calculate final position size
        # Base risk amount
        base_risk_amount = equity * (self.base_risk_percent / 100.0)
        
        # Apply all factors
        adjusted_risk_percent = kelly_percent * vol_adjustment * confidence_scaling * dd_protection * correlation_adjustment
        adjusted_risk_amount = equity * (adjusted_risk_percent / 100.0)
        
        # BOOSTED position sizing for BTCUSD
        # Instead of dividing by ATR (which produces tiny lots), use risk-based sizing
        # For BTCUSD: 1 lot = $1 per point, so volume = risk_amount / stop_distance
        # We assume typical stop distance of ~1.5x ATR for position sizing purposes
        typical_stop_distance = current_volatility * 1.5  # 1.5x ATR stop
        lot_size = adjusted_risk_amount / max(100, typical_stop_distance)  # Min $100 stop distance
        
        # BOOST: Multiply by risk multiplier to utilize available margin
        # With only 0.07% DD, we can safely use larger positions
        # Scale up to use more of the available max_position_size
        risk_multiplier = 5.0  # BOOST: 5x multiplier for larger positions
        lot_size *= risk_multiplier
        
        # Apply limits
        lot_size = max(self.min_position_size, min(self.max_position_size, lot_size))
        
        return {
            'position_size': lot_size,
            'risk_percent': adjusted_risk_percent,
            'risk_amount': adjusted_risk_amount,
            'factors': factors,
            'kelly_percent': kelly_percent,
            'approved': dd_protection > 0,
            'reason': 'Approved' if dd_protection > 0 else 'Max drawdown reached',
        }

    def get_recommendation(self, calculation: Dict[str, Any]) -> str:
        """Get human-readable recommendation from calculation."""
        size = calculation['position_size']
        risk = calculation['risk_percent']
        factors = calculation['factors']
        
        if not calculation['approved']:
            return f"🛑 TRADE REJECTED: {calculation['reason']}"
        
        rec = f"📊 Position Size: {size:.3f} lots ({risk:.2f}% risk)\n"
        rec += f"   Kelly: {factors['kelly']:.2f}%\n"
        rec += f"   Volatility: {factors['volatility']:.2f}x\n"
        rec += f"   Confidence: {factors['confidence']:.2f}x\n"
        rec += f"   Drawdown: {factors['drawdown']:.2f}x\n"
        rec += f"   Correlation: {factors['correlation']:.2f}x"
        
        return rec
