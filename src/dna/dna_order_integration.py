"""
DNA Integration with Smart Order Manager
CEO: Qwen Code | Created: 2026-04-10

Allows DNA Engine to auto-adjust:
- Profit profile parameters
- TP adjustment weights
- SL behavior per target
- Velocity thresholds
- Trailing distances
"""

from typing import Dict, Any, List
from loguru import logger

from src.execution.smart_order_manager import SmartOrderManager, ProfitTarget


class DNAOrderManagerIntegration:
    """
    Integrates DNA Engine with Smart Order Manager
    
    DNA mutates order management parameters based on:
    - Historical performance
    - Market regime
    - Win rate at different targets
    - Average slippage per velocity level
    """
    
    def __init__(self, dna_params: Dict[str, Any]):
        self.dna_params = dna_params
        self.order_manager = SmartOrderManager(dna_params=dna_params)
        
        logger.info(" DNA-Order Manager Integration initialized")
    
    def adjust_profit_profiles(self, performance_data: Dict[str, Any]) -> None:
        """
        Adjust profit profiles based on performance data
        
        Args:
            performance_data: Historical performance by target level
        """
        logger.info(" Adjusting profit profiles based on performance...")
        
        for target in ProfitTarget:
            target_key = f"target_{int(target.value * 100)}"
            
            if target_key in performance_data:
                perf = performance_data[target_key]
                profile = self.order_manager.profit_profiles[target]
                
                # Adjust SL distance based on win rate at this target
                win_rate = perf.get('win_rate', 0.5)
                
                if win_rate > 0.7:
                    # High win rate - can afford tighter SL
                    profile.sl_distance_points *= 0.9
                    logger.info(f"    {target.value*100:.0f}%: High WR ({win_rate:.1%})  Tightening SL")
                
                elif win_rate < 0.4:
                    # Low win rate - need wider SL
                    profile.sl_distance_points *= 1.1
                    logger.info(f"    {target.value*100:.0f}%: Low WR ({win_rate:.1%})  Widening SL")
                
                # Adjust velocity threshold based on average velocity at target
                avg_velocity = perf.get('avg_velocity', 1.0)
                profile.velocity_threshold = avg_velocity * 0.8  # 80% of avg
                
                # Adjust min profit lock based on average profit
                avg_profit = perf.get('avg_profit', 20.0)
                profile.min_profit_lock = avg_profit * 0.5  # Lock 50% of avg
                
                profile.dna_adjusted = True
        
        logger.info(" Profit profiles adjusted by DNA")
    
    def adjust_tp_settings(self, market_regime: str) -> None:
        """
        Adjust TP settings based on market regime
        
        Args:
            market_regime: Current market regime
        """
        settings = self.order_manager.tp_adjustment_settings
        
        regime_adjustments = {
            'trending_bullish': {
                'gravity_weight': 0.20,
                'velocity_weight': 0.30,
                'oscillation_weight': 0.30,
                'volume_weight': 0.20,
            },
            'trending_bearish': {
                'gravity_weight': 0.25,
                'velocity_weight': 0.35,
                'oscillation_weight': 0.20,
                'volume_weight': 0.20,
            },
            'ranging_high_vol': {
                'gravity_weight': 0.40,
                'velocity_weight': 0.20,
                'oscillation_weight': 0.20,
                'volume_weight': 0.20,
            },
            'ranging_low_vol': {
                'gravity_weight': 0.15,
                'velocity_weight': 0.15,
                'oscillation_weight': 0.50,
                'volume_weight': 0.20,
            },
        }
        
        if market_regime in regime_adjustments:
            adjustment = regime_adjustments[market_regime]
            settings.update(adjustment)
            
            logger.info(f" TP settings adjusted for regime: {market_regime}")
            logger.info(f"   Gravity: {settings['gravity_weight']:.2f}")
            logger.info(f"   Velocity: {settings['velocity_weight']:.2f}")
            logger.info(f"   Oscillation: {settings['oscillation_weight']:.2f}")
            logger.info(f"   Volume: {settings['volume_weight']:.2f}")
    
    def get_optimized_state(self) -> Dict[str, Any]:
        """Get current optimized state for reporting"""
        profiles_summary = {}
        
        for target, profile in self.order_manager.profit_profiles.items():
            profiles_summary[f"{int(target.value*100)}%"] = {
                'sl_behavior': profile.sl_behavior,
                'velocity_threshold': profile.velocity_threshold,
                'sl_distance_points': profile.sl_distance_points,
                'min_profit_lock': profile.min_profit_lock,
                'dna_adjusted': profile.dna_adjusted,
            }
        
        return {
            'tp_settings': self.order_manager.tp_adjustment_settings,
            'profit_profiles': profiles_summary,
        }




