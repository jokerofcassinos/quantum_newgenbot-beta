"""
ThermodynamicExit - 5-Sensor Intelligent Profit Management System
Source: Laplace-Demon-AGI v3.0 (salvaged and improved)
Created: 2026-04-11

Manages exits using 5 sensors:
1. PVD - Profit Velocity Decay (slowing momentum)
2. MCE - Micro-Ceiling Detection (resistance levels)
3. ATC - Adaptive TP Contraction (tightening targets)
4. PEG - Profit Entropy Gauge (chaos measurement)
5. MEM - Micro-Exhaustion Marker (final push detection)

This is the BEST exit logic found across ALL three legacy projects.
"""

from typing import Dict, Any, Tuple, List, Optional
from loguru import logger
import numpy as np


class ThermodynamicExit:
    """
    5-sensor intelligent profit management system.
    
    Inspired by Laplace-Demon-AGI v3.0 implementation but simplified and improved.
    This was identified as the BEST exit logic across all legacy projects.
    """

    def __init__(
        self,
        velocity_decay_threshold: float = 0.3,
        micro_ceiling_lookback: int = 20,
        tp_contraction_factor: float = 0.8,
        entropy_lookback: int = 10,
        exhaustion_sensitivity: float = 0.7,
    ):
        """
        Initialize Thermodynamic Exit.
        
        Args:
            velocity_decay_threshold: Profit velocity decay threshold (0.3 = 30%)
            micro_ceiling_lookback: Lookback for ceiling detection
            tp_contraction_factor: Factor to contract TP when entropy high
            entropy_lookback: Period for entropy calculation
            exhaustion_sensitivity: Sensitivity for exhaustion detection
        """
        self.velocity_decay_threshold = velocity_decay_threshold
        self.micro_ceiling_lookback = micro_ceiling_lookback
        self.tp_contraction_factor = tp_contraction_factor
        self.entropy_lookback = entropy_lookback
        self.exhaustion_sensitivity = exhaustion_sensitivity
        
        logger.info("🌡️ ThermodynamicExit initialized (5-sensor system)")
        logger.info(f"   PVD threshold: {velocity_decay_threshold}")
        logger.info(f"   MCE lookback: {micro_ceiling_lookback}")
        logger.info(f"   ATC factor: {tp_contraction_factor}")
        logger.info(f"   PEG lookback: {entropy_lookback}")
        logger.info(f"   MEM sensitivity: {exhaustion_sensitivity}")

    def calculate_sensors(
        self,
        prices: List[float],
        entry_price: float,
        direction: str,
    ) -> Dict[str, Any]:
        """
        Calculate all 5 thermodynamic sensors.
        
        Args:
            prices: Recent price history
            entry_price: Trade entry price
            direction: 'BUY' or 'SELL'
            
        Returns:
            Dict with sensor readings
        """
        if len(prices) < 5:
            return self._default_sensors()
        
        prices = np.array(prices)
        
        # Calculate PnL series
        if direction == 'BUY':
            pnl_series = prices - entry_price
        else:
            pnl_series = entry_price - prices
        
        # Sensor 1: PVD - Profit Velocity Decay
        if len(pnl_series) >= 5:
            recent_velocity = np.diff(pnl_series[-5:]).mean()
            earlier_velocity = np.diff(pnl_series[-10:-5]).mean() if len(pnl_series) >= 10 else recent_velocity
            
            if abs(earlier_velocity) > 0.001:
                velocity_decay = 1.0 - (recent_velocity / earlier_velocity)
            else:
                velocity_decay = 0.0
        else:
            velocity_decay = 0.0
            recent_velocity = 0.0
        
        # Sensor 2: MCE - Micro-Ceiling Detection
        if len(prices) >= self.micro_ceiling_lookback:
            recent_high = prices[-self.micro_ceiling_lookback:].max()
            current_price = prices[-1]
            ceiling_distance = (recent_high - current_price) / max(1, current_price)
            at_ceiling = ceiling_distance < 0.001  # Within 0.1% of recent high
        else:
            at_ceiling = False
            ceiling_distance = 1.0
        
        # Sensor 3: ATC - Adaptive TP Contraction (based on entropy)
        if len(pnl_series) >= self.entropy_lookback:
            # Calculate entropy of PnL changes
            pnl_changes = np.diff(pnl_series[-self.entropy_lookback:])
            if len(pnl_changes) > 1 and pnl_changes.std() > 0:
                # Normalized entropy
                sorted_changes = np.sort(np.abs(pnl_changes))
                entropy = -np.sum(sorted_changes * np.log(sorted_changes + 1e-10))
                entropy_normalized = min(1.0, entropy / 5.0)  # Normalize to 0-1
            else:
                entropy_normalized = 0.0
        else:
            entropy_normalized = 0.0
        
        # Sensor 4: PEG - Profit Entropy Gauge (already calculated above)
        profit_entropy = entropy_normalized
        
        # Sensor 5: MEM - Micro-Exhaustion Marker
        if len(pnl_series) >= 10:
            # Check for final push pattern (sharp move followed by stagnation)
            last_move = abs(pnl_series[-1] - pnl_series[-3])
            avg_move = np.abs(np.diff(pnl_series[-10:])).mean()
            
            if avg_move > 0:
                exhaustion_ratio = last_move / avg_move
                is_exhausted = exhaustion_ratio < self.exhaustion_sensitivity
            else:
                exhaustion_ratio = 0.0
                is_exhausted = False
        else:
            exhaustion_ratio = 0.0
            is_exhausted = False
        
        return {
            'pvd': velocity_decay,
            'recent_velocity': recent_velocity,
            'mce_at_ceiling': at_ceiling,
            'mce_ceiling_distance': ceiling_distance,
            'atc_entropy': profit_entropy,
            'peg_entropy': profit_entropy,
            'mem_exhausted': is_exhausted,
            'mem_exhaustion_ratio': exhaustion_ratio,
            'current_pnl': pnl_series[-1] if len(pnl_series) > 0 else 0.0,
        }

    def _default_sensors(self) -> Dict[str, Any]:
        """Return default sensor values when insufficient data."""
        return {
            'pvd': 0.0,
            'recent_velocity': 0.0,
            'mce_at_ceiling': False,
            'mce_ceiling_distance': 1.0,
            'atc_entropy': 0.0,
            'peg_entropy': 0.0,
            'mem_exhausted': False,
            'mem_exhaustion_ratio': 0.0,
            'current_pnl': 0.0,
        }

    def should_exit(
        self,
        sensors: Dict[str, Any],
        current_tp_distance: float,
        current_sl_distance: float,
    ) -> Tuple[bool, str]:
        """
        Determine if trade should be exited based on sensors.
        
        Args:
            sensors: Sensor readings from calculate_sensors()
            current_tp_distance: Distance to take profit
            current_sl_distance: Distance to stop loss
            
        Returns:
            Tuple of (should_exit: bool, reason: str)
        """
        # Check PVD - Profit Velocity Decay
        if sensors['pvd'] > self.velocity_decay_threshold and sensors['current_pnl'] > 0:
            return True, f"PVD: Profit velocity decayed {sensors['pvd']*100:.0f}%"
        
        # Check MCE - Micro-Ceiling
        if sensors['mce_at_ceiling'] and sensors['current_pnl'] > 0:
            return True, f"MCE: At micro-ceiling (distance: {sensors['mce_ceiling_distance']*10000:.1f} pips)"
        
        # Check MEM - Micro-Exhaustion
        if sensors['mem_exhausted'] and sensors['current_pnl'] > 0:
            return True, f"MEM: Exhaustion detected (ratio: {sensors['mem_exhaustion_ratio']:.2f})"
        
        # Check ATC - Adaptive TP Contraction
        if sensors['peg_entropy'] > 0.7 and sensors['current_pnl'] > 0:
            return True, f"ATC: High entropy ({sensors['peg_entropy']:.2f}), contract TP"
        
        return False, "Sensors nominal"

    def get_adjusted_tp(
        self,
        original_tp: float,
        sensors: Dict[str, Any],
        entry_price: float,
        direction: str,
    ) -> float:
        """
        Calculate adjusted take profit based on entropy.
        
        Args:
            original_tp: Original take profit price
            sensors: Sensor readings
            entry_price: Trade entry price
            direction: 'BUY' or 'SELL'
            
        Returns:
            Adjusted take profit price
        """
        if sensors['peg_entropy'] > 0.5:
            # High entropy - contract TP
            if direction == 'BUY':
                contraction = (original_tp - entry_price) * self.tp_contraction_factor
                return entry_price + contraction
            else:
                contraction = (entry_price - original_tp) * self.tp_contraction_factor
                return entry_price - contraction
        
        return original_tp
