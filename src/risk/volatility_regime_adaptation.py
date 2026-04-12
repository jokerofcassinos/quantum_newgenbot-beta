"""
VolatilityRegimeAdaptation - Dynamic Strategy Adjustment by Volatility
Source: DubaiMatrixASI (salvaged and improved)
Created: 2026-04-12

Adapts trading parameters based on current volatility regime:
- Low Volatility: Wider stops, higher targets, more trades
- Normal Volatility: Standard parameters
- High Volatility: Tighter stops, lower targets, fewer trades
- Extreme Volatility: Pause trading or minimal risk
"""

from typing import Dict, Any, List, Tuple
from loguru import logger
import numpy as np


class VolatilityRegimeAdaptation:
    """
    Volatility regime adaptation system.
    
    Inspired by DubaiMatrixASI implementation but simplified.
    """

    def __init__(
        self,
        low_vol_threshold: float = 0.005,
        high_vol_threshold: float = 0.02,
        extreme_vol_threshold: float = 0.04,
        lookback: int = 50,
    ):
        """
        Initialize VolatilityRegimeAdaptation.
        
        Args:
            low_vol_threshold: Below this = low volatility
            high_vol_threshold: Above this = high volatility
            extreme_vol_threshold: Above this = extreme volatility
            lookback: Period for volatility calculation
        """
        self.low_vol_threshold = low_vol_threshold
        self.high_vol_threshold = high_vol_threshold
        self.extreme_vol_threshold = extreme_vol_threshold
        self.lookback = lookback
        
        logger.info("🌊 VolatilityRegimeAdaptation initialized")
        logger.info(f"   Low vol: < {low_vol_threshold*100:.1f}%")
        logger.info(f"   High vol: > {high_vol_threshold*100:.1f}%")
        logger.info(f"   Extreme vol: > {extreme_vol_threshold*100:.1f}%")

    def classify_volatility(self, closes: List[float]) -> Dict[str, Any]:
        """
        Classify current volatility regime.
        
        Args:
            closes: Recent price closes
            
        Returns:
            Dict with regime classification
        """
        if len(closes) < 20:
            return {
                'regime': 'unknown',
                'volatility': 0.01,
                'adjustment': {'risk_multiplier': 1.0, 'stop_multiplier': 1.0, 'tp_multiplier': 1.0},
            }
        
        closes = np.array(closes[-self.lookback:])
        returns = np.diff(np.log(closes))
        current_vol = np.std(returns[-20:])
        avg_vol = np.std(returns)
        
        if avg_vol == 0:
            avg_vol = 0.01
        
        vol_ratio = current_vol / avg_vol
        
        # Classify regime
        if current_vol < self.low_vol_threshold:
            regime = 'low'
            adjustment = {
                'risk_multiplier': 1.2,
                'stop_multiplier': 1.5,
                'tp_multiplier': 2.0,
                'max_trades_multiplier': 1.5,
            }
        elif current_vol < self.high_vol_threshold:
            regime = 'normal'
            adjustment = {
                'risk_multiplier': 1.0,
                'stop_multiplier': 1.0,
                'tp_multiplier': 1.0,
                'max_trades_multiplier': 1.0,
            }
        elif current_vol < self.extreme_vol_threshold:
            regime = 'high'
            adjustment = {
                'risk_multiplier': 0.7,
                'stop_multiplier': 1.3,
                'tp_multiplier': 0.8,
                'max_trades_multiplier': 0.6,
            }
        else:
            regime = 'extreme'
            adjustment = {
                'risk_multiplier': 0.3,
                'stop_multiplier': 2.0,
                'tp_multiplier': 0.5,
                'max_trades_multiplier': 0.2,
            }
        
        return {
            'regime': regime,
            'volatility': current_vol,
            'avg_volatility': avg_vol,
            'vol_ratio': vol_ratio,
            'adjustment': adjustment,
        }

    def should_trade(self, closes: List[float]) -> Tuple[bool, str]:
        """
        Determine if trading should be allowed based on volatility.
        
        Args:
            closes: Recent price closes
            
        Returns:
            Tuple of (allowed: bool, reason: str)
        """
        classification = self.classify_volatility(closes)
        regime = classification['regime']
        
        if regime == 'extreme':
            return False, f"Extreme volatility ({classification['volatility']*100:.2f}%) - trading paused"
        else:
            return True, f"Volatility {regime} ({classification['volatility']*100:.2f}%) - trading allowed"
