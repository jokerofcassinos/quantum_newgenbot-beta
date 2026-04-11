"""
Strategy Orchestrator - Voting system with dynamic weights
CEO: Qwen Code | Created: 2026-04-10

Features:
1. Strategy debate/voting (BUY vs SELL vs NEUTRAL)
2. Dynamic weights based on regime
3. Profile-based strategy power
4. Coherence measurement
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass
from loguru import logger

from src.strategies.advanced_strategies import (
    LiquidityStrategy, ThermodynamicStrategy, PhysicsStrategy,
    OrderBlockStrategy, FVGStrategy, AdvancedSignal
)


@dataclass
class StrategyVote:
    """Vote from a single strategy"""
    strategy_name: str
    direction: str  # BUY, SELL, NEUTRAL
    confidence: float
    weight: float  # Dynamic weight based on regime/profile
    weighted_vote: float  # confidence * weight
    signal: Optional[AdvancedSignal] = None


@dataclass
class OrchestrationResult:
    """Result of strategy orchestration"""
    final_direction: str  # BUY, SELL, NEUTRAL
    total_buy_votes: float
    total_sell_votes: float
    total_neutral_votes: float
    coherence: float  # 0-1, how much strategies agree
    weighted_consensus: float  # -1 to 1 (negative=bearish, positive=bullish)
    signals: List[AdvancedSignal]
    top_signal: Optional[AdvancedSignal]
    reasoning: str


class StrategyOrchestrator:
    """
    Orchestrates multiple strategies with voting system
    
    Features:
    1. Each strategy votes BUY/SELL/NEUTRAL
    2. Weights adjust based on regime
    3. Profile determines strategy power
    4. Coherence measures agreement
    """
    
    def __init__(self, dna_params: Dict[str, Any]):
        self.dna_params = dna_params
        
        # Initialize all strategies
        self.strategies = {
            "liquidity": LiquidityStrategy(),
            "thermodynamic": ThermodynamicStrategy(),
            "physics": PhysicsStrategy(),
            "order_block": OrderBlockStrategy(),
            "fvg": FVGStrategy(),
        }
        
        # Strategy weights per regime (DNA-adjustable)
        self.regime_weights = {
            "trending_strong_bull": {
                "liquidity": 0.25, "thermodynamic": 0.15, "physics": 0.20,
                "order_block": 0.25, "fvg": 0.15,
            },
            "trending_strong_bear": {
                "liquidity": 0.25, "thermodynamic": 0.15, "physics": 0.20,
                "order_block": 0.25, "fvg": 0.15,
            },
            "trending_moderate_bull": {
                "liquidity": 0.20, "thermodynamic": 0.20, "physics": 0.20,
                "order_block": 0.20, "fvg": 0.20,
            },
            "trending_moderate_bear": {
                "liquidity": 0.20, "thermodynamic": 0.20, "physics": 0.20,
                "order_block": 0.20, "fvg": 0.20,
            },
            "ranging": {
                "liquidity": 0.30, "thermodynamic": 0.25, "physics": 0.15,
                "order_block": 0.20, "fvg": 0.10,
            },
            "high_volatility": {
                "liquidity": 0.35, "thermodynamic": 0.20, "physics": 0.25,
                "order_block": 0.10, "fvg": 0.10,
            },
            "crashing": {
                "liquidity": 0.40, "thermodynamic": 0.20, "physics": 0.30,
                "order_block": 0.05, "fvg": 0.05,
            },
            "chop": {
                "liquidity": 0.30, "thermodynamic": 0.30, "physics": 0.20,
                "order_block": 0.10, "fvg": 0.10,
            },
        }
        
        # Strategy performance tracking
        self.strategy_performance = {name: {"trades": 0, "wins": 0} for name in self.strategies}
        
        logger.info("🎭 Strategy Orchestrator initialized")
        logger.info(f"   5 Strategies: Liquidity, Thermodynamic, Physics, Order Block, FVG")
    
    def orchestrate(self, candles: pd.DataFrame, current_price: float, 
                   regime: str, profile_weights: Dict[str, float] = None) -> OrchestrationResult:
        """
        Run orchestration - all strategies vote
        
        Args:
            candles: Market data
            current_price: Current price
            regime: Current market regime
            profile_weights: Optional weights from neural profile
        
        Returns:
            OrchestrationResult with consensus
        """
        votes = []
        signals = []
        
        # Get regime weights
        weights = self.regime_weights.get(regime, self.regime_weights["ranging"])
        
        # If profile weights provided, blend them
        if profile_weights:
            for strat_name in weights:
                if strat_name in profile_weights:
                    weights[strat_name] = weights[strat_name] * 0.7 + profile_weights.get(strat_name, 0) * 0.3
        
        # Normalize weights
        total_weight = sum(weights.values())
        if total_weight > 0:
            weights = {k: v / total_weight for k, v in weights.items()}
        
        # Each strategy votes
        for name, strategy in self.strategies.items():
            try:
                signal = strategy.analyze(candles, current_price)
                
                if signal:
                    weight = weights.get(name, 0.2)
                    vote = StrategyVote(
                        strategy_name=name,
                        direction=signal.direction,
                        confidence=signal.confidence,
                        weight=weight,
                        weighted_vote=signal.confidence * weight,
                        signal=signal,
                    )
                    votes.append(vote)
                    signals.append(signal)
                else:
                    # Strategy votes NEUTRAL
                    votes.append(StrategyVote(
                        strategy_name=name,
                        direction="NEUTRAL",
                        confidence=0.5,
                        weight=weights.get(name, 0.2),
                        weighted_vote=0.0,
                    ))
            except Exception as e:
                logger.warning(f"Strategy {name} error: {e}")
                votes.append(StrategyVote(
                    strategy_name=name,
                    direction="NEUTRAL",
                    confidence=0.0,
                    weight=0.0,
                    weighted_vote=0.0,
                ))
        
        # Calculate consensus
        total_buy = sum(v.weighted_vote for v in votes if v.direction == "BUY")
        total_sell = sum(v.weighted_vote for v in votes if v.direction == "SELL")
        total_neutral = sum(v.weighted_vote for v in votes if v.direction == "NEUTRAL")
        
        # Weighted consensus (-1 to 1)
        total_votes = total_buy + total_sell + max(0.01, total_neutral)
        weighted_consensus = (total_buy - total_sell) / total_votes
        
        # Determine direction
        if weighted_consensus > 0.2:
            final_direction = "BUY"
        elif weighted_consensus < -0.2:
            final_direction = "SELL"
        else:
            final_direction = "NEUTRAL"
        
        # Calculate coherence (how much strategies agree)
        directions = [v.direction for v in votes]
        if len(directions) > 0:
            buy_count = directions.count("BUY")
            sell_count = directions.count("SELL")
            neutral_count = directions.count("NEUTRAL")
            max_agreement = max(buy_count, sell_count, neutral_count)
            coherence = max_agreement / len(directions)
        else:
            coherence = 0.0
        
        # Get top signal
        top_signal = None
        if signals:
            top_signal = max(signals, key=lambda s: s.confidence * weights.get(s.strategy, 0.2))
        
        # Build reasoning
        reasoning = f"Consensus: {final_direction} ({weighted_consensus:+.2f}), "
        reasoning += f"Coherence: {coherence:.2f}, "
        reasoning += f"Buy: {total_buy:.2f}, Sell: {total_sell:.2f}, Neutral: {total_neutral:.2f}"
        
        result = OrchestrationResult(
            final_direction=final_direction,
            total_buy_votes=total_buy,
            total_sell_votes=total_sell,
            total_neutral_votes=total_neutral,
            coherence=coherence,
            weighted_consensus=weighted_consensus,
            signals=signals,
            top_signal=top_signal,
            reasoning=reasoning,
        )
        
        logger.info(f"🎭 Orchestration Result: {final_direction}")
        logger.info(f"   Consensus: {weighted_consensus:+.2f}")
        logger.info(f"   Coherence: {coherence:.2f}")
        logger.info(f"   Buy: {total_buy:.2f} | Sell: {total_sell:.2f} | Neutral: {total_neutral:.2f}")
        
        return result
    
    def update_strategy_performance(self, strategy_name: str, pnl: float):
        """Update strategy performance after trade"""
        if strategy_name in self.strategy_performance:
            self.strategy_performance[strategy_name]["trades"] += 1
            if pnl > 0:
                self.strategy_performance[strategy_name]["wins"] += 1
    
    def get_strategy_weights_for_regime(self, regime: str) -> Dict[str, float]:
        """Get current strategy weights for regime"""
        return self.regime_weights.get(regime, {})
