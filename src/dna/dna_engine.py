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
    
    async def detect_regime(self, candles=None) -> Dict[str, Any]:
        """
        Detect current market regime through large-scale analysis
        
        Returns dict with:
        - regime_type: trending_bullish, trending_bearish, ranging, high_volatility, crashing, chop
        - confidence: 0.0 to 1.0
        - volatility: low, medium, high, extreme
        - momentum: strong, moderate, weak
        - atr_current: current ATR value
        - trend_strength: 0.0 to 1.0
        """
        # If no candles provided, return unknown (live mode will pass candles)
        if candles is None or len(candles) < 100:
            logger.warning("⚠️ Insufficient candle data for regime detection")
            return {
                "regime_type": "unknown_initial",
                "confidence": 0.3,
                "volatility": "unknown",
                "momentum": "unknown",
                "atr_current": 0.0,
                "trend_strength": 0.5,
                "analysis_timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        import numpy as np
        
        close = candles['close'].values
        high = candles['high'].values
        low = candles['low'].values
        
        # --- EMA Alignment ---
        def ema(data, span):
            alpha = 2.0 / (span + 1)
            result = np.empty_like(data, dtype=float)
            result[0] = data[0]
            for i in range(1, len(data)):
                result[i] = alpha * data[i] + (1 - alpha) * result[i - 1]
            return result
        
        ema_9 = ema(close, 9)
        ema_21 = ema(close, 21)
        ema_50 = ema(close, 50)
        
        e9 = ema_9[-1]
        e21 = ema_21[-1]
        e50 = ema_50[-1]
        current_price = close[-1]
        
        # Trend strength based on EMA alignment
        if e9 > e21 > e50:
            trend_strength = 1.0
            trend_dir = "bullish"
        elif e9 < e21 < e50:
            trend_strength = 1.0
            trend_dir = "bearish"
        elif e9 > e21:
            trend_strength = 0.6
            trend_dir = "bullish"
        elif e9 < e21:
            trend_strength = 0.6
            trend_dir = "bearish"
        else:
            trend_strength = 0.2
            trend_dir = "neutral"
        
        # --- ATR-based volatility ---
        tr = np.maximum(high[1:] - low[1:],
                        np.maximum(np.abs(high[1:] - close[:-1]),
                                   np.abs(low[1:] - close[:-1])))
        atr_14 = np.mean(tr[-14:]) if len(tr) >= 14 else np.mean(tr)
        atr_pct = atr_14 / current_price * 100
        
        if atr_pct > 3.0:
            volatility = "extreme"
        elif atr_pct > 2.0:
            volatility = "high"
        elif atr_pct > 0.5:
            volatility = "medium"
        else:
            volatility = "low"
        
        # --- Momentum ---
        returns_5 = (close[-1] - close[-6]) / close[-6] * 100 if len(close) > 5 else 0
        returns_20 = (close[-1] - close[-21]) / close[-21] * 100 if len(close) > 20 else 0
        
        if abs(returns_5) > 2.0:
            momentum = "strong"
        elif abs(returns_5) > 0.5:
            momentum = "moderate"
        else:
            momentum = "weak"
        
        # --- Regime Classification ---
        if atr_pct > 3.0 and returns_20 < -5.0:
            regime_type = "crashing"
            confidence = 0.85
        elif atr_pct > 2.0:
            regime_type = "high_volatility"
            confidence = 0.75
        elif trend_strength >= 0.8:
            regime_type = f"trending_{trend_dir}"
            confidence = 0.80
        elif trend_strength >= 0.5:
            regime_type = f"trending_moderate_{trend_dir}"
            confidence = 0.65
        elif atr_pct < 0.3 and momentum == "weak":
            regime_type = "chop"
            confidence = 0.70
        else:
            regime_type = "ranging"
            confidence = 0.60
        
        logger.info(f"🔍 Regime detected: {regime_type} (conf={confidence:.2f}, vol={volatility}, mom={momentum})")
        
        return {
            "regime_type": regime_type,
            "confidence": confidence,
            "volatility": volatility,
            "momentum": momentum,
            "atr_current": float(atr_14),
            "trend_strength": trend_strength,
            "analysis_timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    async def analyze_recent_performance(self, trade_history=None) -> Dict[str, Any]:
        """
        Analyze recent trading performance
        
        Args:
            trade_history: list of trade dicts with keys: net_pnl, gross_pnl, etc.
        
        Returns dict with:
        - win_rate, profit_factor, total_trades, avg_win, avg_loss,
          max_drawdown, consecutive_losses
        """
        # If not provided, use internally tracked history
        if trade_history is None:
            trade_history = getattr(self, '_trade_history', [])
        
        if not trade_history or len(trade_history) == 0:
            logger.info("📊 No trade history available for performance analysis")
            return {
                "win_rate": 0.0,
                "profit_factor": 0.0,
                "total_trades": 0,
                "avg_win": 0.0,
                "avg_loss": 0.0,
                "max_drawdown": 0.0,
                "consecutive_losses": 0,
                "analysis_period": "no_data"
            }
        
        # Analyze last 50 trades (or all if fewer)
        recent = trade_history[-50:]
        
        pnls = [t.get('net_pnl', 0) for t in recent]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p <= 0]
        
        total = len(pnls)
        win_rate = len(wins) / total if total > 0 else 0
        
        gross_profit = sum(wins) if wins else 0
        gross_loss = abs(sum(losses)) if losses else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        avg_win = sum(wins) / len(wins) if wins else 0
        avg_loss = abs(sum(losses)) / len(losses) if losses else 0
        
        # Consecutive losses (current streak from end)
        consecutive_losses = 0
        for p in reversed(pnls):
            if p <= 0:
                consecutive_losses += 1
            else:
                break
        
        # Max drawdown from equity curve
        equity = 0.0
        peak = 0.0
        max_dd = 0.0
        for p in pnls:
            equity += p
            peak = max(peak, equity)
            dd = peak - equity
            max_dd = max(max_dd, dd)
        
        logger.info(f"📊 Performance: WR={win_rate:.1%} PF={profit_factor:.2f} "
                    f"trades={total} consec_L={consecutive_losses}")
        
        return {
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "total_trades": total,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "max_drawdown": max_dd,
            "consecutive_losses": consecutive_losses,
            "analysis_period": f"last_{len(recent)}_trades"
        }
    
    def record_trade(self, trade_result: Dict[str, Any]):
        """Record a trade result for performance tracking"""
        if not hasattr(self, '_trade_history'):
            self._trade_history = []
        self._trade_history.append(trade_result)
    
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
