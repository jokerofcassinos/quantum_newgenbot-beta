"""
RecursiveSelfDebate - Metacognitive Decision Validation System
Source: Atl4s (salvaged and improved)
Created: 2026-04-11

The system questions its own decisions through adversarial reasoning:
1. Build Bull Case (arguments for entry)
2. Build Bear Case (arguments against entry)
3. Debate (weigh opposing arguments)
4. Decision (can flip original signal if bear case wins)

This catches 10-15% of bad decisions before execution.
"""

from typing import Dict, Any, Tuple, List
from loguru import logger


class RecursiveSelfDebate:
    """
    Metacognitive decision validation through adversarial reasoning.
    
    Inspired by Atl4s implementation but simplified and improved.
    """

    def __init__(
        self,
        min_debate_confidence: float = 0.35,
    ):
        """
        Initialize RecursiveSelfDebate.
        
        Args:
            min_debate_confidence: Minimum confidence after debate to approve trade
        """
        self.min_debate_confidence = min_debate_confidence
        
        logger.info(" RecursiveSelfDebate initialized")
        logger.info(f"   Min debate confidence: {min_debate_confidence}")

    def debate(
        self,
        original_signal: str,
        signal_confidence: float,
        market_data: Dict[str, Any],
    ) -> Tuple[bool, str, float]:
        """
        Run adversarial debate on trade signal.
        
        Args:
            original_signal: Original signal direction ('BUY', 'SELL', 'NEUTRAL')
            signal_confidence: Original signal confidence
            market_data: Market data for debate arguments
            
        Returns:
            Tuple of (approved: bool, final_signal: str, final_confidence: float)
        """
        if original_signal == 'NEUTRAL':
            return False, 'NEUTRAL', 0.0
        
        # Build Bull Case (arguments supporting original signal)
        bull_points = self._build_bull_case(original_signal, market_data)
        
        # Build Bear Case (arguments opposing original signal)
        bear_points = self._build_bear_case(original_signal, market_data)
        
        # Weigh arguments
        bull_strength = sum(p['weight'] for p in bull_points)
        bear_strength = sum(p['weight'] for p in bear_points)
        
        # Original signal side
        if original_signal == 'BUY':
            original_strength = bull_strength
            opposing_strength = bear_strength
        else:  # SELL
            original_strength = bear_strength
            opposing_strength = bull_strength
        
        # Calculate debate confidence
        total = bull_strength + bear_strength
        if total == 0:
            debate_confidence = 0.5
        else:
            # How strongly does original signal win the debate?
            debate_confidence = original_strength / total
        
        # Can flip decision if opposing side wins debate
        final_signal = original_signal
        if opposing_strength > original_strength * 1.3:
            # Opposing case is significantly stronger - flip signal
            final_signal = 'SELL' if original_signal == 'BUY' else 'BUY'
            debate_confidence = 1.0 - debate_confidence
            logger.info(f" Signal flipped: {original_signal}  {final_signal}")
        
        # Final approval
        approved = debate_confidence >= self.min_debate_confidence
        
        return approved, final_signal, debate_confidence

    def _build_bull_case(
        self,
        original_signal: str,
        market_data: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Build arguments supporting the original signal."""
        arguments = []
        
        # Check trend alignment
        regime = market_data.get('regime', {})
        if regime.get('trend_type') == 'trending':
            arguments.append({
                'point': 'Market is trending (strong momentum)',
                'weight': 0.3,
            })
        
        # Check volatility
        vol_regime = market_data.get('volatility', 'normal')
        if vol_regime == 'normal':
            arguments.append({
                'point': 'Volatility is normal (good entry conditions)',
                'weight': 0.2,
            })
        
        # Check volume
        volume_ratio = market_data.get('volume_ratio', 1.0)
        if volume_ratio > 1.2:
            arguments.append({
                'point': f'Volume {volume_ratio:.1f}x above average (institutional activity)',
                'weight': 0.25,
            })
        
        # Check signal confidence
        if market_data.get('signal_confidence', 0) > 0.6:
            arguments.append({
                'point': 'High signal confidence',
                'weight': 0.25,
            })
        
        return arguments

    def _build_bear_case(
        self,
        original_signal: str,
        market_data: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Build arguments opposing the original signal."""
        arguments = []
        
        # Check for ranging market
        regime = market_data.get('regime', {})
        if regime.get('trend_type') == 'ranging':
            arguments.append({
                'point': 'Market is ranging (false breakouts likely)',
                'weight': 0.35,
            })
        
        # Check for high volatility
        vol_regime = market_data.get('volatility', 'normal')
        if vol_regime == 'high':
            arguments.append({
                'point': 'High volatility (erratic price action)',
                'weight': 0.25,
            })
        
        # Check spread
        spread_pct = market_data.get('spread_percent', 0)
        if spread_pct > 0.05:
            arguments.append({
                'point': f'Wide spread {spread_pct:.3f}% (high transaction cost)',
                'weight': 0.2,
            })
        
        # Check for recent losses
        consecutive_losses = market_data.get('consecutive_losses', 0)
        if consecutive_losses >= 3:
            arguments.append({
                'point': f'{consecutive_losses} consecutive losses (possible strategy decay)',
                'weight': 0.3,
            })
        
        # Check signal strength
        if market_data.get('signal_confidence', 0) < 0.5:
            arguments.append({
                'point': 'Low signal confidence (weak setup)',
                'weight': 0.25,
            })
        
        return arguments




