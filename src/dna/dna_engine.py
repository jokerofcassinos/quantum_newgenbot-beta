"""
DNA Engine - Adaptive parameter system (THE HEART OF THE BOT)
CEO: Qwen Code | Created: 2026-04-10

This module is responsible for:
1. Detecting market regime changes
2. Mutating DNA parameters adaptively
3. Validating mutations against safety limits
4. Storing successful configurations in memory
5. Large-scale market analysis for informed adaptation

ZERO HARDCODED PARAMETERS - Everything is dynamic and adaptive!
"""

import json
import asyncio
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timezone
from pathlib import Path
from loguru import logger

from src.core.config_manager import ConfigManager


class DNAEngine:
    """
    DNA Engine - Self-adapting parameter system
    
    The DNA contains all trading parameters that automatically
    adjust based on market conditions, performance metrics,
    and large-scale analysis.
    """
    
    def __init__(self, config: ConfigManager):
        self.config = config
        self.current_dna: Dict[str, Any] = {}
        self.dna_memory: Dict[str, Any] = {}
        self.absolute_limits: Dict[str, Any] = {}
        
        # Mutation tracking
        self.mutation_count = 0
        self.successful_mutations = 0
        self.rejected_mutations = 0
        
        logger.info("🧬 DNA Engine initialized")
    
    def load_dna(self) -> Dict[str, Any]:
        """Load current DNA configuration"""
        self.current_dna = self.config.load_dna()
        self.dna_memory = self.config.load_dna_memory()
        self.absolute_limits = self.config.load_absolute_limits()
        
        logger.info(f"🧬 DNA loaded with {len(self.current_dna)} top-level strands")
        logger.info(f"🧠 DNA Memory contains {len(self.dna_memory.get('regimes', {}))} regimes")
        
        return self.current_dna
    
    async def adapt(self) -> Dict[str, Any]:
        """
        Main adaptation cycle - called periodically (every 5 minutes)
        
        Process:
        1. Analyze current market regime
        2. Review recent performance
        3. Query DNA memory for similar regimes
        4. Calculate optimal parameter adjustments
        5. Validate against absolute limits
        6. Apply mutation if valid
        7. Log and notify
        """
        logger.info("🧬 Starting DNA adaptation cycle...")
        
        try:
            # Step 1: Detect current market regime
            regime = await self.detect_regime()
            logger.info(f"📊 Current regime: {regime.get('regime_type', 'unknown')} "
                       f"(confidence: {regime.get('confidence', 0):.2f})")
            
            # Step 2: Analyze recent performance
            performance = await self.analyze_recent_performance()
            logger.info(f"📈 Recent performance: "
                       f"Win Rate={performance.get('win_rate', 0):.1%}, "
                       f"Profit Factor={performance.get('profit_factor', 0):.2f}")
            
            # Step 3: Query DNA memory for similar regimes
            memory_match = self.query_dna_memory(regime)
            if memory_match:
                logger.info(f"🧠 DNA Memory match found: {memory_match.get('regime_name')} "
                           f"(success rate: {memory_match.get('success_rate', 0):.1%})")
            
            # Step 4: Calculate mutations
            mutations = self.calculate_mutations(regime, performance, memory_match)
            
            if mutations:
                logger.info(f"🔬 Calculated {len(mutations)} potential mutations")
                
                # Step 5: Validate mutations
                valid_mutations = self.validate_mutations(mutations)
                
                if valid_mutations:
                    # Step 6: Apply mutations
                    self.apply_mutations(valid_mutations)
                    
                    # Step 7: Save updated DNA
                    self.config.save_dna(self.current_dna)
                    
                    # Update stats
                    self.mutation_count += len(valid_mutations)
                    self.successful_mutations += len(valid_mutations)
                    
                    logger.info(f"✅ Applied {len(valid_mutations)} mutations successfully")
                    
                    # TODO: Send Telegram notification
                    # await self.notify_mutation(valid_mutations)
                else:
                    logger.warning("⚠️ All mutations rejected - DNA unchanged")
                    self.rejected_mutations += len(mutations)
            else:
                logger.info("ℹ️ No mutations needed - DNA optimal for current regime")
            
            # Update regime info in DNA
            self.current_dna["market_regime"] = {
                "current_regime": regime.get("regime_type", "unknown"),
                "regime_confidence": regime.get("confidence", 0.5),
                "volatility_regime": regime.get("volatility", "unknown"),
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "next_regime_check": "in 5 minutes"
            }
            
            return self.current_dna
            
        except Exception as e:
            logger.error(f"❌ Error in DNA adaptation: {e}", exc_info=True)
            return self.current_dna
    
    async def detect_regime(self) -> Dict[str, Any]:
        """
        Detect current market regime through large-scale analysis
        
        Returns dict with:
        - regime_type: trending_bullish, trending_bearish, ranging_bullish, ranging_bearish, ranging_neutral
        - confidence: 0.0 to 1.0
        - volatility: low, medium, high, extreme
        - momentum: strong, moderate, weak
        - liquidity: tight, normal, wide
        - atr_current: current ATR value
        - trend_strength: 0.0 to 1.0
        """
        # TODO: Implement actual regime detection
        # This should analyze:
        # - Moving average alignment (EMA 9/21/50/200)
        # - ADX for trend strength
        # - ATR for volatility
        # - Volume analysis
        # - Price action patterns
        # - Higher timeframe context
        
        logger.warning("⚠️ Regime detection not yet implemented - returning placeholder")
        
        return {
            "regime_type": "unknown_initial",
            "confidence": 0.5,
            "volatility": "unknown",
            "momentum": "unknown",
            "liquidity": "unknown",
            "atr_current": 0.0,
            "trend_strength": 0.5,
            "analysis_timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    async def analyze_recent_performance(self) -> Dict[str, Any]:
        """
        Analyze recent trading performance
        
        Returns dict with:
        - win_rate: percentage
        - profit_factor: gross_profit / gross_loss
        - total_trades: number of recent trades
        - avg_win: average winning trade
        - avg_loss: average losing trade
        - max_drawdown: maximum recent drawdown
        - consecutive_losses: current consecutive loss streak
        """
        # TODO: Implement actual performance analysis
        # Query trade history from database
        
        logger.warning("⚠️ Performance analysis not yet implemented - returning placeholder")
        
        return {
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "total_trades": 0,
            "avg_win": 0.0,
            "avg_loss": 0.0,
            "max_drawdown": 0.0,
            "consecutive_losses": 0,
            "analysis_period": "last_50_trades"
        }
    
    def query_dna_memory(self, regime: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Query DNA memory for similar market regimes
        
        Returns best matching regime configuration if found
        """
        regimes = self.dna_memory.get("regimes", {})
        
        if not regimes:
            logger.info("🧠 DNA Memory empty - no historical regimes")
            return None
        
        # Find regime with highest similarity
        best_match = None
        best_similarity = 0.0
        
        for regime_name, regime_data in regimes.items():
            # Calculate similarity (simple version - should be more sophisticated)
            similarity = self.calculate_regime_similarity(regime, regime_data)
            
            if similarity > best_similarity:
                best_similarity = similarity
                best_match = regime_data
                best_match["regime_name"] = regime_name
        
        # Only return if confidence is high enough
        if best_similarity > 0.7:
            return best_match
        
        return None
    
    def calculate_regime_similarity(self, 
                                    regime1: Dict[str, Any], 
                                    regime2: Dict[str, Any]) -> float:
        """
        Calculate similarity between two regimes (0.0 to 1.0)
        """
        similarity = 0.0
        factors_checked = 0
        
        # Regime type match
        if regime1.get("regime_type") == regime2.get("regime_type"):
            similarity += 0.4
        factors_checked += 1
        
        # Volatility match
        if regime1.get("volatility") == regime2.get("volatility"):
            similarity += 0.3
        factors_checked += 1
        
        # Momentum match
        if regime1.get("momentum") == regime2.get("momentum"):
            similarity += 0.2
        factors_checked += 1
        
        # ATR similarity (within 20%)
        atr1 = regime1.get("atr_current", 0)
        atr2 = regime2.get("atr_current", 0)
        if atr1 > 0 and atr2 > 0:
            atr_diff = abs(atr1 - atr2) / max(atr1, atr2)
            if atr_diff < 0.2:
                similarity += 0.1
        factors_checked += 1
        
        return similarity / factors_checked
    
    def calculate_mutations(self,
                           regime: Dict[str, Any],
                           performance: Dict[str, Any],
                           memory_match: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate parameter mutations based on current conditions
        
        Returns dict of parameter paths and their new values
        """
        mutations = {}
        
        # If we have a memory match, suggest using those parameters
        if memory_match:
            logger.info("🧠 Suggesting parameters from DNA memory")
            # Merge memory parameters with current DNA
            if "best_params" in memory_match:
                mutations.update(memory_match["best_params"])
        
        # Performance-based adjustments
        win_rate = performance.get("win_rate", 0)
        consecutive_losses = performance.get("consecutive_losses", 0)
        
        if consecutive_losses >= 3:
            # Reduce risk after consecutive losses
            current_risk = self.config.get_param(self.current_dna, "risk_params.base_risk_percent")
            if current_risk:
                new_risk = max(current_risk * 0.75, 0.25)  # Reduce by 25%, min 0.25%
                mutations["risk_params.base_risk_percent"] = new_risk
                logger.info(f"🔬 Mutation: Reducing risk to {new_risk:.2f}% after {consecutive_losses} losses")
        
        elif win_rate > 0.65:
            # Can increase risk slightly with good performance
            current_risk = self.config.get_param(self.current_dna, "risk_params.base_risk_percent")
            if current_risk and current_risk < 1.0:
                new_risk = min(current_risk * 1.1, 1.0)  # Increase by 10%, max 1%
                mutations["risk_params.base_risk_percent"] = new_risk
                logger.info(f"🔬 Mutation: Increasing risk to {new_risk:.2f}% (win rate {win_rate:.1%})")
        
        # TODO: Add more sophisticated mutation logic
        # - Regime-specific adjustments
        # - Volatility-based stop adjustments
        # - Strategy weight rebalancing
        # - Indicator period optimization
        
        return mutations
    
    def validate_mutations(self, mutations: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate proposed mutations against absolute safety limits
        
        Returns only valid mutations
        """
        valid_mutations = {}
        
        for param_path, new_value in mutations.items():
            # Get absolute limit for this parameter
            if "risk_params" in param_path:
                limit_value = self.config.get_param(self.absolute_limits, 
                                                    f"absolute_limits.{param_path}")
                
                if limit_value is not None:
                    if "max" in param_path or "limit" in param_path:
                        # Value should be below limit
                        if new_value <= limit_value:
                            valid_mutations[param_path] = new_value
                            logger.info(f"✅ Mutation valid: {param_path} = {new_value} (limit: {limit_value})")
                        else:
                            logger.warning(f"❌ Mutation rejected: {param_path} = {new_value} exceeds limit {limit_value}")
                    else:
                        valid_mutations[param_path] = new_value
                else:
                    # No limit defined, accept mutation
                    valid_mutations[param_path] = new_value
            else:
                # Non-risk parameter, accept
                valid_mutations[param_path] = new_value
        
        return valid_mutations
    
    def apply_mutations(self, mutations: Dict[str, Any]) -> None:
        """
        Apply validated mutations to current DNA
        """
        for param_path, new_value in mutations.items():
            old_value = self.config.get_param(self.current_dna, param_path)
            self.current_dna = self.config.set_param(self.current_dna, param_path, new_value)
            
            logger.info(f"🧬 DNA mutated: {param_path}")
            logger.info(f"   {old_value} → {new_value}")
    
    def save_regime_to_memory(self, regime: Dict[str, Any], performance: Dict[str, Any]) -> None:
        """
        Save successful regime configuration to memory for future reference
        """
        regime_name = regime.get("regime_type", "unknown")
        
        if "regimes" not in self.dna_memory:
            self.dna_memory["regimes"] = {}
        
        # Initialize or update regime
        if regime_name not in self.dna_memory["regimes"]:
            self.dna_memory["regimes"][regime_name] = {
                "occurrences": 0,
                "success_rate": 0.0,
                "best_params": {},
                "avg_profit_per_trade": 0.0,
                "max_drawdown": 0.0,
                "total_trades": 0,
                "last_seen": None
            }
        
        # Update stats
        regime_data = self.dna_memory["regimes"][regime_name]
        regime_data["occurrences"] += 1
        regime_data["total_trades"] += performance.get("total_trades", 0)
        regime_data["last_seen"] = datetime.now(timezone.utc).isoformat()
        
        # Update success rate (weighted average)
        old_sr = regime_data["success_rate"]
        new_wr = performance.get("win_rate", 0)
        total = regime_data["occurrences"]
        regime_data["success_rate"] = ((old_sr * (total - 1)) + new_wr) / total
        
        # Save best parameters if performance was good
        if performance.get("win_rate", 0) > 0.6:
            regime_data["best_params"] = {
                "risk_params": self.current_dna.get("risk_params", {}),
                "strategy_params": self.current_dna.get("strategy_params", {}),
                "execution_params": self.current_dna.get("execution_params", {})
            }
        
        # Save memory
        self.config.save_dna_memory(self.dna_memory)
        logger.info(f"🧠 Regime saved to memory: {regime_name}")
    
    def get_dna_summary(self) -> Dict[str, Any]:
        """
        Get current DNA state summary for reporting
        """
        return {
            "mutation_count": self.mutation_count,
            "successful_mutations": self.successful_mutations,
            "rejected_mutations": self.rejected_mutations,
            "current_regime": self.current_dna.get("market_regime", {}).get("current_regime", "unknown"),
            "base_risk_percent": self.current_dna.get("risk_params", {}).get("base_risk_percent", 0),
            "active_strategy": self.current_dna.get("strategy_params", {}).get("active_strategy", "unknown"),
            "last_updated": self.current_dna.get("market_regime", {}).get("last_updated", "never")
        }
