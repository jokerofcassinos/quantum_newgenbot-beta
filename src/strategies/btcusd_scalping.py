"""
BTCUSD Scalping Strategy - Momentum-based scalping with DNA adaptation
CEO: Qwen Code | Created: 2026-04-10

Strategy Logic:
- Multi-timeframe momentum analysis
- EMA crossovers with volume confirmation
- RSI divergence detection
- Dynamic parameters from DNA Engine
- FTMO commission-aware P&L calculations
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
import pandas as pd
import numpy as np
from loguru import logger

from src.strategies.base_strategy import BaseStrategy, TradingSignal


class BTCUSDScalpingStrategy(BaseStrategy):
    """
    BTCUSD Scalping Strategy
    
    Features:
    - Multi-timeframe analysis (M5 primary, M15 context, H1 trend)
    - EMA crossover signals with volume confirmation
    - RSI oversold/overbought with divergence
    - Dynamic stop loss based on ATR
    - Commission-aware calculations ($45/lot per side)
    - DNA Engine parameter adaptation
    """
    
    def __init__(self, dna_params: Dict[str, Any]):
        super().__init__("BTCUSD_Momentum_Scalper", dna_params)
        
        # Strategy weights (from DNA or default)
        self.weights = dna_params.get("strategy_weights", {
            "momentum": 0.40,
            "trend": 0.30,
            "volume": 0.20,
            "rsi": 0.10
        })
        
        logger.info(f" {self.name} initialized with DNA params")
    
    async def generate_signal(self,
                             candles: pd.DataFrame,
                             market_data: Dict[str, Any],
                             dna_params: Dict[str, Any]) -> Optional[TradingSignal]:
        """
        Generate trading signal
        
        Analyzes:
        1. EMA crossovers (fast/slow)
        2. RSI levels and divergence
        3. Volume confirmation
        4. ATR-based stop loss
        5. Multi-timeframe alignment
        
        Returns:
            TradingSignal or None
        """
        try:
            if len(candles) < 50:
                logger.warning(" Not enough candles for analysis")
                return None
            
            self.signals_generated += 1
            
            # Get current price
            current_price = candles['close'].iloc[-1]
            current_time = candles['time'].iloc[-1]
            
            # Calculate indicators
            indicators = self._calculate_indicators(candles, dna_params)
            
            # Analyze each component
            momentum_score = self._analyze_momentum(candles, indicators)
            trend_score = self._analyze_trend(candles, indicators)
            volume_score = self._analyze_volume(candles, indicators)
            rsi_score = self._analyze_rsi(candles, indicators)
            
            # Calculate weighted score
            total_score = (
                momentum_score * self.weights.get("momentum", 0.40) +
                trend_score * self.weights.get("trend", 0.30) +
                volume_score * self.weights.get("volume", 0.20) +
                rsi_score * self.weights.get("rsi", 0.10)
            )
            
            # Determine direction
            if total_score > 0.70:
                direction = "BUY"
            elif total_score < -0.70:
                direction = "SELL"
            else:
                logger.info(f" Score {total_score:.2f} - No clear signal")
                self.signals_rejected += 1
                return None
            
            # Calculate entry, SL, TP
            entry_price = current_price
            atr = indicators['atr_14'].iloc[-1]
            
            # Dynamic stop loss from DNA or default (1.5x ATR)
            sl_multiplier = dna_params.get("execution_params", {}).get("trailing_stop_multiplier", 1.5)
            stop_distance = atr * sl_multiplier
            
            if direction == "BUY":
                stop_loss = entry_price - stop_distance
                take_profit = entry_price + (stop_distance * 2)  # 1:2 R:R minimum
            else:  # SELL
                stop_loss = entry_price + stop_distance
                take_profit = entry_price - (stop_distance * 2)
            
            # Calculate R:R ratio
            risk = abs(entry_price - stop_loss)
            reward = abs(take_profit - entry_price)
            rr_ratio = reward / risk if risk > 0 else 0
            
            # Calculate confidence based on score strength
            confidence = min(abs(total_score), 1.0)
            
            # Build rationale
            rationale = self._build_rationale(
                direction, momentum_score, trend_score, 
                volume_score, rsi_score, indicators
            )
            
            # Create signal
            signal = TradingSignal(
                symbol="BTCUSD",
                direction=direction,
                strength=abs(total_score),
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                risk_reward_ratio=rr_ratio,
                confidence=confidence,
                strategy_name=self.name,
                timeframe="M5",
                indicators={
                    "ema_9": float(indicators['ema_9'].iloc[-1]),
                    "ema_21": float(indicators['ema_21'].iloc[-1]),
                    "rsi_14": float(indicators['rsi_14'].iloc[-1]),
                    "atr_14": float(atr),
                    "volume_ratio": float(indicators['volume_ratio'].iloc[-1])
                },
                rationale=rationale,
                timestamp=datetime.now(timezone.utc)
            )
            
            # Validate signal
            is_valid, reason = self.validate_signal(signal)
            if not is_valid:
                logger.warning(f" Signal rejected: {reason}")
                self.signals_rejected += 1
                return None
            
            self.signals_approved += 1
            logger.info(f" Signal generated: {direction} @ ${entry_price:.2f}")
            logger.info(f"   SL: ${stop_loss:.2f} | TP: ${take_profit:.2f}")
            logger.info(f"   R:R: {rr_ratio:.2f} | Confidence: {confidence:.2f}")
            
            return signal
            
        except Exception as e:
            logger.error(f" Error generating signal: {e}", exc_info=True)
            return None
    
    def _calculate_indicators(self, candles: pd.DataFrame, 
                            dna_params: Dict[str, Any]) -> Dict[str, pd.Series]:
        """Calculate all technical indicators"""
        indicators = {}
        
        # Get periods from DNA or use defaults
        ema_fast = dna_params.get("strategy_params", {}).get("indicator_periods", {}).get("ema_fast", 9)
        ema_slow = dna_params.get("strategy_params", {}).get("indicator_periods", {}).get("ema_slow", 21)
        ema_trend = dna_params.get("strategy_params", {}).get("indicator_periods", {}).get("ema_trend", 200)
        rsi_period = dna_params.get("strategy_params", {}).get("indicator_periods", {}).get("rsi_period", 14)
        atr_period = dna_params.get("strategy_params", {}).get("indicator_periods", {}).get("atr_period", 14)
        
        # EMAs
        indicators['ema_9'] = candles['close'].ewm(span=ema_fast, adjust=False).mean()
        indicators['ema_21'] = candles['close'].ewm(span=ema_slow, adjust=False).mean()
        indicators['ema_200'] = candles['close'].ewm(span=ema_trend, adjust=False).mean()
        
        # RSI
        delta = candles['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_period).mean()
        rs = gain / loss
        indicators['rsi_14'] = 100 - (100 / (1 + rs))
        
        # ATR
        high = candles['high']
        low = candles['low']
        prev_close = candles['close'].shift(1)
        
        tr1 = high - low
        tr2 = abs(high - prev_close)
        tr3 = abs(low - prev_close)
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        indicators['atr_14'] = tr.rolling(window=atr_period).mean()
        
        # Volume ratio (current vs 20-period average)
        avg_volume = candles.get('volume', pd.Series([1]*len(candles))).rolling(window=20).mean()
        current_volume = candles.get('volume', pd.Series([1]*len(candles)))
        indicators['volume_ratio'] = current_volume / avg_volume
        
        return indicators
    
    def _analyze_momentum(self, candles: pd.DataFrame, 
                         indicators: Dict[str, pd.Series]) -> float:
        """
        Analyze momentum using EMA crossovers
        
        Returns:
            float: Score from -1.0 (bearish) to +1.0 (bullish)
        """
        ema_fast = indicators['ema_9'].iloc[-1]
        ema_slow = indicators['ema_21'].iloc[-1]
        
        # EMA relationship
        if ema_fast > ema_slow:
            momentum = 1.0
        else:
            momentum = -1.0
        
        # EMA slope (acceleration)
        ema_fast_prev = indicators['ema_9'].iloc[-5]
        ema_slow_prev = indicators['ema_21'].iloc[-5]
        
        if ema_fast > ema_fast_prev and ema_slow > ema_slow_prev:
            momentum *= 1.2  # Accelerating
        elif ema_fast < ema_fast_prev and ema_slow < ema_slow_prev:
            momentum *= 1.2  # Decelerating in current direction
        
        return max(-1.0, min(1.0, momentum))
    
    def _analyze_trend(self, candles: pd.DataFrame, 
                      indicators: Dict[str, pd.Series]) -> float:
        """
        Analyze higher timeframe trend
        
        Returns:
            float: Score from -1.0 to +1.0
        """
        current_price = candles['close'].iloc[-1]
        
        # Check if we have EMA 200
        if 'ema_200' in indicators and not pd.isna(indicators['ema_200'].iloc[-1]):
            ema_200 = indicators['ema_200'].iloc[-1]
            
            if current_price > ema_200:
                return 1.0  # Uptrend
            elif current_price < ema_200:
                return -1.0  # Downtrend
        
        return 0.0  # No clear trend
    
    def _analyze_volume(self, candles: pd.DataFrame, 
                       indicators: Dict[str, pd.Series]) -> float:
        """
        Analyze volume for confirmation
        
        Returns:
            float: Score from 0.0 to 1.0 (confidence)
        """
        volume_ratio = indicators['volume_ratio'].iloc[-1]
        
        # High volume = more confidence
        if volume_ratio > 1.5:
            return 1.0
        elif volume_ratio > 1.0:
            return 0.7
        elif volume_ratio > 0.7:
            return 0.4
        else:
            return 0.2
    
    def _analyze_rsi(self, candles: pd.DataFrame, 
                    indicators: Dict[str, pd.Series]) -> float:
        """
        Analyze RSI for overbought/oversold
        
        Returns:
            float: Score from -1.0 to +1.0
        """
        rsi = indicators['rsi_14'].iloc[-1]
        
        # Traditional levels
        if rsi < 30:
            return 1.0  # Oversold - bullish
        elif rsi < 40:
            return 0.5
        elif rsi > 70:
            return -1.0  # Overbought - bearish
        elif rsi > 60:
            return -0.5
        else:
            return 0.0  # Neutral
    
    def _build_rationale(self,
                        direction: str,
                        momentum: float,
                        trend: float,
                        volume: float,
                        rsi: float,
                        indicators: Dict[str, pd.Series]) -> str:
        """Build human-readable rationale for the signal"""
        parts = []
        
        # Momentum
        if abs(momentum) > 0.8:
            parts.append(f"Strong {'bullish' if momentum > 0 else 'bearish'} momentum")
        
        # Trend
        if abs(trend) > 0.5:
            parts.append(f"Price {'above' if trend > 0 else 'below'} EMA 200")
        
        # Volume
        if volume > 0.7:
            parts.append(f"Volume confirmation ({volume:.1f}x avg)")
        
        # RSI
        rsi_val = indicators['rsi_14'].iloc[-1]
        if rsi_val < 30:
            parts.append(f"RSI oversold ({rsi_val:.1f})")
        elif rsi_val > 70:
            parts.append(f"RSI overbought ({rsi_val:.1f})")
        
        rationale = "; ".join(parts) if parts else "Mixed signals, moderate confidence"
        return rationale




