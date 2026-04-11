"""
Coherence Engine - Complex agreement analysis
CEO: Wren Code | Created: 2026-04-10

Analyzes ALL machine analyses for agreement strength.
More agreement = higher coherence = stronger signal.
Influences DNA mutation and confidence thresholds.
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from dataclasses import dataclass
from loguru import logger


@dataclass
class CoherenceResult:
    """Result of coherence analysis"""
    overall_coherence: float  # 0-1
    directional_coherence: float  # -1 to 1
    strategy_agreement: float  # 0-1
    indicator_agreement: float  # 0-1
    timeframe_agreement: float  # 0-1
    regime_alignment: float  # 0-1
    risk_alignment: float  # 0-1
    confidence_score: float  # 0-1 overall confidence
    should_trade: bool
    recommended_action: str  # "strong_buy", "buy", "neutral", "sell", "strong_sell"
    reasoning: str


class CoherenceEngine:
    """
    Coherence Analysis Engine
    
    Analyzes agreement between:
    1. All strategies (orchestration result)
    2. All indicators (EMA, RSI, MACD, etc)
    3. All timeframes (M1, M5, M15, H1, H4)
    4. Market regime analysis
    5. Risk parameters
    6. Neural profile selection
    
    Higher coherence = stronger signal = higher DNA confidence
    """
    
    def __init__(self, dna_params: Dict[str, Any]):
        self.dna_params = dna_params
        self.coherence_history: List[float] = []
        
        logger.info("🔬 Coherence Engine initialized")
    
    def analyze(self, orchestration_result: Any, candles: pd.DataFrame,
               regime: str, profile: Any, risk_context: Dict[str, Any]) -> CoherenceResult:
        """
        Analyze coherence across all systems
        
        Args:
            orchestration_result: Result from StrategyOrchestrator
            candles: Market data
            regime: Current market regime
            profile: Current neural profile
            risk_context: Risk context data
        
        Returns:
            CoherenceResult with overall coherence score
        """
        if len(candles) < 100:
            return CoherenceResult(
                overall_coherence=0.3,
                directional_coherence=0.0,
                strategy_agreement=0.3,
                indicator_agreement=0.3,
                timeframe_agreement=0.3,
                regime_alignment=0.3,
                risk_alignment=0.5,
                confidence_score=0.3,
                should_trade=False,
                recommended_action="neutral",
                reasoning="Insufficient data for coherence analysis",
            )
        
        # 1. Strategy agreement (from orchestration)
        strategy_agreement = orchestration_result.coherence
        
        # 2. Indicator agreement
        indicator_agreement = self._analyze_indicator_agreement(candles, orchestration_result.final_direction)
        
        # 3. Timeframe agreement
        timeframe_agreement = self._analyze_timeframe_agreement(candles, orchestration_result.final_direction)
        
        # 4. Regime alignment
        regime_alignment = self._analyze_regime_alignment(regime, orchestration_result.final_direction, profile)
        
        # 5. Risk alignment
        risk_alignment = self._analyze_risk_alignment(risk_context, orchestration_result.final_direction)
        
        # Calculate overall coherence (weighted average)
        overall_coherence = (
            strategy_agreement * 0.25 +
            indicator_agreement * 0.25 +
            timeframe_agreement * 0.20 +
            regime_alignment * 0.15 +
            risk_alignment * 0.15
        )
        
        # Directional coherence (-1 to 1)
        directional_coherence = orchestration_result.weighted_consensus * overall_coherence
        
        # Overall confidence score
        confidence_score = overall_coherence * (0.5 + abs(directional_coherence) * 0.5)
        
        # Determine if should trade (lowered threshold)
        threshold = self.dna_params.get('trading_params', {}).get('entry_threshold', 0.65)
        should_trade = confidence_score > (threshold * 0.7)  # 70% of threshold for more trades
        
        # Recommended action
        if directional_coherence > 0.5:
            action = "strong_buy"
        elif directional_coherence > 0.2:
            action = "buy"
        elif directional_coherence < -0.5:
            action = "strong_sell"
        elif directional_coherence < -0.2:
            action = "sell"
        else:
            action = "neutral"
        
        # Build reasoning
        reasoning = f"Coherence: {overall_coherence:.2f}, "
        reasoning += f"Strategy: {strategy_agreement:.2f}, "
        reasoning += f"Indicators: {indicator_agreement:.2f}, "
        reasoning += f"Timeframes: {timeframe_agreement:.2f}, "
        reasoning += f"Regime: {regime_alignment:.2f}, "
        reasoning += f"Risk: {risk_alignment:.2f}"
        
        # Record in history
        self.coherence_history.append(overall_coherence)
        if len(self.coherence_history) > 1000:
            self.coherence_history = self.coherence_history[-1000:]
        
        return CoherenceResult(
            overall_coherence=overall_coherence,
            directional_coherence=directional_coherence,
            strategy_agreement=strategy_agreement,
            indicator_agreement=indicator_agreement,
            timeframe_agreement=timeframe_agreement,
            regime_alignment=regime_alignment,
            risk_alignment=risk_alignment,
            confidence_score=confidence_score,
            should_trade=should_trade,
            recommended_action=action,
            reasoning=reasoning,
        )
    
    def _analyze_indicator_agreement(self, candles: pd.DataFrame, direction: str) -> float:
        """Analyze how much indicators agree with direction"""
        close = candles['close'].iloc[-50:]
        
        # Calculate indicators
        ema_9 = close.ewm(span=9).mean().iloc[-1]
        ema_21 = close.ewm(span=21).mean().iloc[-1]
        
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = (100 - (100 / (1 + rs))).iloc[-1]
        
        # Check agreement
        agreements = 0
        total = 3
        
        # EMA alignment
        if direction == "BUY" and ema_9 > ema_21:
            agreements += 1
        elif direction == "SELL" and ema_9 < ema_21:
            agreements += 1
        elif direction == "NEUTRAL":
            agreements += 0.5
        
        # RSI alignment
        if direction == "BUY" and rsi < 70:
            agreements += 1
        elif direction == "SELL" and rsi > 30:
            agreements += 1
        elif direction == "NEUTRAL":
            agreements += 0.5
        
        # Momentum alignment
        momentum = close.iloc[-1] - close.iloc[-10]
        if direction == "BUY" and momentum > 0:
            agreements += 1
        elif direction == "SELL" and momentum < 0:
            agreements += 1
        elif direction == "NEUTRAL":
            agreements += 0.5
        
        return agreements / total
    
    def _analyze_timeframe_agreement(self, candles: pd.DataFrame, direction: str) -> float:
        """Analyze how much timeframes agree"""
        if len(candles) < 200:
            return 0.5
        
        close = candles['close']
        
        # Check different "timeframes" via EMAs
        ema_9 = close.ewm(span=9).mean().iloc[-1]
        ema_21 = close.ewm(span=21).mean().iloc[-1]
        ema_50 = close.ewm(span=50).mean().iloc[-1]
        
        agreements = 0
        total = 3
        
        # Short-term
        if direction == "BUY" and ema_9 > ema_21:
            agreements += 1
        elif direction == "SELL" and ema_9 < ema_21:
            agreements += 1
        elif direction == "NEUTRAL":
            agreements += 0.5
        
        # Medium-term
        if direction == "BUY" and ema_21 > ema_50:
            agreements += 1
        elif direction == "SELL" and ema_21 < ema_50:
            agreements += 1
        elif direction == "NEUTRAL":
            agreements += 0.5
        
        # Long-term
        current_price = close.iloc[-1]
        if direction == "BUY" and current_price > ema_50:
            agreements += 1
        elif direction == "SELL" and current_price < ema_50:
            agreements += 1
        elif direction == "NEUTRAL":
            agreements += 0.5
        
        return agreements / total
    
    def _analyze_regime_alignment(self, regime: str, direction: str, profile: Any) -> float:
        """Analyze if direction aligns with regime"""
        # Certain regimes favor certain directions
        regime_direction_bias = {
            "trending_strong_bull": ("BUY", 0.8),
            "trending_strong_bear": ("SELL", 0.8),
            "trending_moderate_bull": ("BUY", 0.6),
            "trending_moderate_bear": ("SELL", 0.6),
            "ranging": ("NEUTRAL", 0.5),
            "high_volatility": ("NEUTRAL", 0.4),
            "crashing": ("SELL", 0.7),
            "chop": ("NEUTRAL", 0.4),
        }
        
        if regime in regime_direction_bias:
            biased_dir, strength = regime_direction_bias[regime]
            
            if direction == biased_dir:
                return strength
            elif direction == "NEUTRAL":
                return 0.5
            else:
                return 1.0 - strength
        
        return 0.5
    
    def _analyze_risk_alignment(self, risk_context: Dict[str, Any], direction: str) -> float:
        """Analyze if risk context supports trading"""
        consecutive_losses = risk_context.get('consecutive_losses', 0)
        drawdown = risk_context.get('current_drawdown', 0)
        daily_loss_pct = risk_context.get('daily_loss_used_percent', 0)
        
        # If high losses, risk alignment is low
        if consecutive_losses >= 5:
            return 0.2
        elif consecutive_losses >= 3:
            return 0.4
        elif drawdown > 5:
            return 0.3
        elif daily_loss_pct > 3:
            return 0.4
        
        return 0.8  # Risk context supports trading
    
    def get_average_coherence(self) -> float:
        """Get average coherence over history"""
        if not self.coherence_history:
            return 0.5
        return np.mean(self.coherence_history)
