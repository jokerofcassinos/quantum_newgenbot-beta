"""
KinematicsPhaseSpace - Price Motion Analysis in Phase Space
Source: Atl4s (salvaged and improved)
Created: 2026-04-11

Treats price as a particle in phase space with:
- Velocity: First derivative of price (rate of change)
- Acceleration: Second derivative of price (change in velocity)
- Angle: Direction of movement in phase space
- Speed: Magnitude of velocity vector

Unique feature space that captures market dynamics traditional indicators miss.
"""

from typing import Dict, Any, List, Tuple
from loguru import logger
import numpy as np


class KinematicsPhaseSpace:
    """
    Phase space analysis of price motion.
    
    Inspired by Atl4s implementation but simplified and improved.
    """

    def __init__(self, lookback: int = 20):
        """
        Initialize KinematicsPhaseSpace.
        
        Args:
            lookback: Period for kinematics calculation
        """
        self.lookback = lookback
        
        logger.info("🎯 KinematicsPhaseSpace initialized")
        logger.info(f"   Lookback: {lookback}")

    def calculate_kinematics(
        self,
        prices: List[float],
    ) -> Dict[str, Any]:
        """
        Calculate phase space kinematics.
        
        Args:
            prices: Recent price history
            
        Returns:
            Dict with velocity, acceleration, angle, speed
        """
        if len(prices) < 5:
            return self._default_kinematics()
        
        prices = np.array(prices[-self.lookback:])
        
        # Position (normalized price)
        position = prices - prices[0]
        
        # Velocity (first derivative)
        velocity = np.diff(position, prepend=position[0])
        current_velocity = velocity[-1]
        avg_velocity = np.mean(velocity[-5:])
        
        # Acceleration (second derivative)
        acceleration = np.diff(velocity, prepend=velocity[0])
        current_acceleration = acceleration[-1]
        
        # Phase angle (direction in phase space)
        if abs(current_velocity) > 0.001 or abs(current_acceleration) > 0.001:
            phase_angle = np.arctan2(current_velocity, current_acceleration)
        else:
            phase_angle = 0.0
        
        # Speed (magnitude of velocity)
        speed = np.sqrt(current_velocity**2 + current_acceleration**2)
        
        # Regime classification
        regime = self._classify_regime(current_velocity, current_acceleration)
        
        return {
            'velocity': current_velocity,
            'avg_velocity': avg_velocity,
            'acceleration': current_acceleration,
            'phase_angle': phase_angle,
            'phase_angle_degrees': np.degrees(phase_angle),
            'speed': speed,
            'regime': regime,
            'position': position[-1],
        }

    def _classify_regime(
        self,
        velocity: float,
        acceleration: float,
    ) -> str:
        """
        Classify market regime from kinematics.
        
        Returns:
            Regime classification
        """
        vel_threshold = 0.001
        acc_threshold = 0.0005
        
        high_velocity = abs(velocity) > vel_threshold
        high_acceleration = abs(acceleration) > acc_threshold
        
        if high_velocity and high_acceleration:
            if velocity > 0:
                return 'strong_uptrend'
            else:
                return 'strong_downtrend'
        elif high_velocity and not high_acceleration:
            if velocity > 0:
                return 'established_uptrend'
            else:
                return 'established_downtrend'
        elif not high_velocity and high_acceleration:
            if acceleration > 0:
                return 'trend_initiation_bullish'
            else:
                return 'trend_initiation_bearish'
        else:
            return 'consolidation'

    def _default_kinematics(self) -> Dict[str, Any]:
        """Return default kinematics when insufficient data."""
        return {
            'velocity': 0.0,
            'avg_velocity': 0.0,
            'acceleration': 0.0,
            'phase_angle': 0.0,
            'phase_angle_degrees': 0.0,
            'speed': 0.0,
            'regime': 'unknown',
            'position': 0.0,
        }

    def get_signal_strength(
        self,
        kinematics: Dict[str, Any],
        signal_direction: str,
    ) -> float:
        """
        Calculate signal strength based on kinematics alignment.
        
        Args:
            kinematics: Kinematics dict from calculate_kinematics()
            signal_direction: 'BUY' or 'SELL'
            
        Returns:
            Signal strength (0.0 to 1.0)
        """
        regime = kinematics.get('regime', 'unknown')
        
        # Bullish regimes
        bullish_regimes = ['strong_uptrend', 'established_uptrend', 'trend_initiation_bullish']
        bearish_regimes = ['strong_downtrend', 'established_downtrend', 'trend_initiation_bearish']
        
        if signal_direction == 'BUY':
            if regime in bullish_regimes:
                return 0.8 if 'strong' in regime else 0.6
            elif regime == 'consolidation':
                return 0.4
            else:
                return 0.2
        else:  # SELL
            if regime in bearish_regimes:
                return 0.8 if 'strong' in regime else 0.6
            elif regime == 'consolidation':
                return 0.4
            else:
                return 0.2
