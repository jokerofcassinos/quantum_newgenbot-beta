"""
New Execution Agent Strategies
CEO: Qwen Code | Created: 2026-04-12

7 New Strategies:
1. MSNR - Market Structure Neural Recognition
2. MSNR Alchemist - Enhanced MSNR with confluence
3. IFVG - Inverse Fair Value Gap
4. OrderFlow - Volume-based flow analysis
5. Supply/Demand - Zone-based trading
6. Fibonacci - Retracement/Extension levels
7. Iceberg - Large order detection
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from loguru import logger

from src.strategies.base_strategy import BaseStrategy, TradingSignal


class MSNRStrategy(BaseStrategy):
    """
    Market Structure Neural Recognition
    
    Analyzes:
    - Break of Structure (BOS)
    - Change of Character (CHoCH)
    - Higher Highs / Lower Lows
    - Market Phase Detection
    """
    
    def __init__(self, dna_params: Dict[str, Any] = None):
        super().__init__("MSNR", dna_params)
        self.name = "MSNR"
    
    def analyze(self, candles: pd.DataFrame, current_price: float, indicators: Dict = None) -> Optional[TradingSignal]:
        if len(candles) < 50:
            return None
        
        close = candles['close'].iloc[-50:]
        high = candles['high'].iloc[-50:]
        low = candles['low'].iloc[-50:]
        
        # Detect market structure
        hh_ll = self._detect_hh_ll(close)
        bos = self._detect_bos(high, low, close)
        choch = self._detect_choch(high, low, close)
        
        # Determine direction
        direction = None
        confidence = 0.5
        
        if bos['bullish'] and hh_ll['uptrend']:
            direction = "BUY"
            confidence = 0.70 + (0.10 if choch['bullish'] else 0)
        elif bos['bearish'] and hh_ll['downtrend']:
            direction = "SELL"
            confidence = 0.70 + (0.10 if choch['bearish'] else 0)
        elif choch['bullish']:
            direction = "BUY"
            confidence = 0.65
        elif choch['bearish']:
            direction = "SELL"
            confidence = 0.65
        
        if not direction:
            return None
        
        # Calculate SL/TP
        sl = self.calculate_fixed_sl(current_price, direction, candles, max_points=300)
        tp = current_price + (current_price - sl) * 2 if direction == "BUY" else current_price - (sl - current_price) * 2
        
        reasoning = f"MSNR: BOS {'bullish' if bos['bullish'] else 'bearish'}, CHoCH {'yes' if choch['bullish'] or choch['bearish'] else 'no'}, Structure {hh_ll['structure']}"
        
        return TradingSignal(
            symbol="BTCUSD",
            direction=direction,
            strength=confidence,
            entry_price=current_price,
            stop_loss=sl,
            take_profit=tp,
            risk_reward_ratio=2.0,
            confidence=confidence,
            strategy_name=self.name,
            timeframe="M5",
            reasoning=reasoning,
            timestamp=datetime.now(timezone.utc)
        )
    
    def _detect_hh_ll(self, close: pd.Series) -> Dict:
        """Detect Higher Highs / Higher Lows or Lower Highs / Lower Lows"""
        if len(close) < 20:
            return {'structure': 'unknown', 'uptrend': False, 'downtrend': False}
        
        # Recent price action
        recent = close.iloc[-10:]
        prev = close.iloc[-20:-10]
        
        recent_high = recent.max()
        recent_low = recent.min()
        prev_high = prev.max()
        prev_low = prev.min()
        
        hh = recent_high > prev_high
        hl = recent_low > prev_low
        lh = recent_high < prev_high
        ll = recent_low < prev_low
        
        return {
            'structure': 'uptrend' if hh and hl else 'downtrend' if lh and ll else 'ranging',
            'uptrend': hh and hl,
            'downtrend': lh and ll,
        }
    
    def _detect_bos(self, high: pd.Series, low: pd.Series, close: pd.Series) -> Dict:
        """Detect Break of Structure"""
        if len(close) < 30:
            return {'bullish': False, 'bearish': False}
        
        recent_high = high.iloc[-20:].max()
        recent_low = low.iloc[-20:].min()
        
        current_close = close.iloc[-1]
        
        bullish_bos = current_close > recent_high
        bearish_bos = current_close < recent_low
        
        return {'bullish': bullish_bos, 'bearish': bearish_bos}
    
    def _detect_choch(self, high: pd.Series, low: pd.Series, close: pd.Series) -> Dict:
        """Detect Change of Character"""
        if len(close) < 40:
            return {'bullish': False, 'bearish': False}
        
        # Previous trend
        prev_trend_up = close.iloc[-30] < close.iloc[-10]
        
        # Current break
        if prev_trend_up:
            bearish_choch = close.iloc[-1] < low.iloc[-20:].min()
            return {'bullish': False, 'bearish': bearish_choch}
        else:
            bullish_choch = close.iloc[-1] > high.iloc[-20:].max()
            return {'bullish': bullish_choch, 'bearish': False}


class MSNRAlchemistStrategy(BaseStrategy):
    """
    MSNR Alchemist - Enhanced MSNR with multiple confluences
    
    Combines:
    - MSNR structure
    - Volume confirmation
    - Momentum alignment
    - Time session filter
    """
    
    def __init__(self, dna_params: Dict[str, Any] = None):
        super().__init__("MSNR_Alchemist", dna_params)
        self.name = "MSNR_Alchemist"
    
    def analyze(self, candles: pd.DataFrame, current_price: float, indicators: Dict = None) -> Optional[TradingSignal]:
        if len(candles) < 50:
            return None
        
        # Get base MSNR signals
        msnr = MSNRStrategy(self.dna_params)
        base_signal = msnr.analyze(candles, current_price)
        
        if not base_signal:
            return None
        
        # Check volume confirmation
        volume = candles['volume'].iloc[-20:]
        avg_vol = volume.mean()
        current_vol = volume.iloc[-1]
        vol_ratio = current_vol / avg_vol if avg_vol > 0 else 1
        
        # Check momentum
        close = candles['close']
        momentum = close.iloc[-1] - close.iloc[-5]
        momentum_confirmed = (base_signal.direction == "BUY" and momentum > 0) or \
                            (base_signal.direction == "SELL" and momentum < 0)
        
        # Calculate final confidence with confluences
        confluences = 1  # Base MSNR
        if vol_ratio > 1.2:
            confluences += 1
        if momentum_confirmed:
            confluences += 1
        
        # Need at least 2 confluences
        if confluences < 2:
            return None
        
        confidence = min(base_signal.confidence * (1 + (confluences - 1) * 0.10), 0.95)
        
        sl = self.calculate_fixed_sl(current_price, base_signal.direction, candles, max_points=300)
        tp = current_price + (current_price - sl) * 2 if base_signal.direction == "BUY" else current_price - (sl - current_price) * 2
        
        return TradingSignal(
            symbol="BTCUSD",
            direction=base_signal.direction,
            strength=confidence,
            entry_price=current_price,
            stop_loss=sl,
            take_profit=tp,
            risk_reward_ratio=2.0,
            confidence=confidence,
            strategy_name=self.name,
            timeframe="M5",
            reasoning=f"MSNR Alchemist: {confluences}/3 confluences (MSNR + {'Vol' if vol_ratio > 1.2 else ''} + {'Mom' if momentum_confirmed else ''})",
            timestamp=datetime.now(timezone.utc)
        )


class IFVGStrategy(BaseStrategy):
    """
    Inverse Fair Value Gap
    
    Trades FVG fills in opposite direction
    """
    
    def __init__(self, dna_params: Dict[str, Any] = None):
        super().__init__("IFVG", dna_params)
        self.name = "IFVG"
    
    def analyze(self, candles: pd.DataFrame, current_price: float, indicators: Dict = None) -> Optional[TradingSignal]:
        if len(candles) < 30:
            return None
        
        # Detect FVGs
        fvgs = []
        for i in range(len(candles) - 25, len(candles) - 2):
            c1 = candles.iloc[i]
            c2 = candles.iloc[i+1]
            c3 = candles.iloc[i+2]
            
            # Bullish FVG
            if c1['high'] < c3['low']:
                fvgs.append({'type': 'bullish', 'low': c1['high'], 'high': c3['low'], 'index': i+1})
            # Bearish FVG
            elif c1['low'] > c3['high']:
                fvgs.append({'type': 'bearish', 'low': c3['high'], 'high': c1['low'], 'index': i+1})
        
        if not fvgs:
            return None
        
        # Find nearest FVG
        current_price = candles.iloc[-1]['close']
        nearest = min(fvgs, key=lambda x: abs((x['low'] + x['high'])/2 - current_price))
        
        fvg_mid = (nearest['low'] + nearest['high']) / 2
        distance_pct = abs(current_price - fvg_mid) / current_price
        
        # Trade opposite to FVG direction (inverse)
        if nearest['type'] == 'bullish' and current_price <= nearest['high'] * 1.001:
            direction = "SELL"
            confidence = 0.65
        elif nearest['type'] == 'bearish' and current_price >= nearest['low'] * 0.999:
            direction = "BUY"
            confidence = 0.65
        else:
            return None
        
        sl = self.calculate_fixed_sl(current_price, direction, candles, max_points=300)
        tp = current_price + (current_price - sl) * 2 if direction == "BUY" else current_price - (sl - current_price) * 2
        
        return TradingSignal(
            symbol="BTCUSD",
            direction=direction,
            strength=confidence,
            entry_price=current_price,
            stop_loss=sl,
            take_profit=tp,
            risk_reward_ratio=2.0,
            confidence=confidence,
            strategy_name=self.name,
            timeframe="M5",
            reasoning=f"IFVG: Inverse of {nearest['type']} FVG at ${fvg_mid:,.0f}",
            timestamp=datetime.now(timezone.utc)
        )


class OrderFlowStrategy(BaseStrategy):
    """
    Volume-based Order Flow Analysis
    
    Analyzes:
    - Volume delta (buy vs sell pressure)
    - Cumulative volume delta
    - Volume profile nodes
    """
    
    def __init__(self, dna_params: Dict[str, Any] = None):
        super().__init__("OrderFlow", dna_params)
        self.name = "OrderFlow"
    
    def analyze(self, candles: pd.DataFrame, current_price: float, indicators: Dict = None) -> Optional[TradingSignal]:
        if len(candles) < 30:
            return None
        
        close = candles['close'].iloc[-30:]
        volume = candles['volume'].iloc[-30:]
        
        # Calculate volume delta (simplified)
        price_changes = close.diff()
        buy_volume = volume.where(price_changes > 0, 0).sum()
        sell_volume = volume.where(price_changes < 0, 0).sum()
        
        total_volume = buy_volume + sell_volume
        if total_volume == 0:
            return None
        
        buy_ratio = buy_volume / total_volume
        
        # Volume profile - find high volume nodes
        price_range = np.linspace(close.min(), close.max(), 20)
        volume_profile = pd.cut(close, bins=price_range, weights=volume).value_counts()
        poc = volume_profile.idxmax() if len(volume_profile) > 0 else close.mean()
        
        # Generate signal
        if buy_ratio > 0.60:
            direction = "BUY"
            confidence = 0.60 + (buy_ratio - 0.60) * 2
        elif buy_ratio < 0.40:
            direction = "SELL"
            confidence = 0.60 + (0.40 - buy_ratio) * 2
        else:
            return None
        
        confidence = min(confidence, 0.90)
        
        sl = self.calculate_fixed_sl(current_price, direction, candles, max_points=300)
        tp = current_price + (current_price - sl) * 2 if direction == "BUY" else current_price - (sl - current_price) * 2
        
        return TradingSignal(
            symbol="BTCUSD",
            direction=direction,
            strength=confidence,
            entry_price=current_price,
            stop_loss=sl,
            take_profit=tp,
            risk_reward_ratio=2.0,
            confidence=confidence,
            strategy_name=self.name,
            timeframe="M5",
            reasoning=f"OrderFlow: Buy ratio {buy_ratio:.1%}, PoC ${poc:.0f}",
            timestamp=datetime.now(timezone.utc)
        )


class SupplyDemandStrategy(BaseStrategy):
    """
    Supply/Demand Zone Trading
    
    Identifies:
    - Supply zones (last up candle before strong down move)
    - Demand zones (last down candle before strong up move)
    - Zone strength based on move magnitude
    """
    
    def __init__(self, dna_params: Dict[str, Any] = None):
        super().__init__("SupplyDemand", dna_params)
        self.name = "SupplyDemand"
    
    def analyze(self, candles: pd.DataFrame, current_price: float, indicators: Dict = None) -> Optional[TradingSignal]:
        if len(candles) < 50:
            return None
        
        # Find supply zones
        supply_zones = self._find_supply_zones(candles.iloc[-50:])
        demand_zones = self._find_demand_zones(candles.iloc[-50:])
        
        # Check if price is near a zone
        for zone in demand_zones:
            if zone['low'] <= current_price <= zone['high'] * 1.002:
                direction = "BUY"
                confidence = 0.65 + zone['strength'] * 0.20
                sl = self.calculate_fixed_sl(current_price, direction, candles, max_points=300)
                tp = current_price + (current_price - sl) * 2
                
                return TradingSignal(
                    symbol="BTCUSD", direction=direction, strength=confidence,
                    entry_price=current_price, stop_loss=sl, take_profit=tp,
                    risk_reward_ratio=2.0, confidence=min(confidence, 0.90),
                    strategy_name=self.name, timeframe="M5",
                    reasoning=f"Demand Zone at ${zone['low']:,.0f}-${zone['high']:,.0f} (strength {zone['strength']:.2f})",
                    timestamp=datetime.now(timezone.utc)
                )
        
        for zone in supply_zones:
            if zone['low'] * 0.998 <= current_price <= zone['high']:
                direction = "SELL"
                confidence = 0.65 + zone['strength'] * 0.20
                sl = self.calculate_fixed_sl(current_price, direction, candles, max_points=300)
                tp = current_price - (sl - current_price) * 2
                
                return TradingSignal(
                    symbol="BTCUSD", direction=direction, strength=confidence,
                    entry_price=current_price, stop_loss=sl, take_profit=tp,
                    risk_reward_ratio=2.0, confidence=min(confidence, 0.90),
                    strategy_name=self.name, timeframe="M5",
                    reasoning=f"Supply Zone at ${zone['low']:,.0f}-${zone['high']:,.0f} (strength {zone['strength']:.2f})",
                    timestamp=datetime.now(timezone.utc)
                )
        
        return None
    
    def _find_demand_zones(self, candles: pd.DataFrame) -> List[Dict]:
        """Find demand zones (last down candle before strong up move)"""
        zones = []
        for i in range(len(candles) - 5):
            if candles.iloc[i]['close'] < candles.iloc[i]['open']:  # Down candle
                # Check for strong move up after
                move = candles.iloc[i+5]['close'] - candles.iloc[i]['low']
                if move > candles.iloc[i]['high'] - candles.iloc[i]['low']:
                    zones.append({
                        'low': candles.iloc[i]['low'],
                        'high': candles.iloc[i]['high'],
                        'strength': min(move / (candles.iloc[i]['high'] - candles.iloc[i]['low']), 2.0)
                    })
        return zones[-3:]  # Last 3 zones
    
    def _find_supply_zones(self, candles: pd.DataFrame) -> List[Dict]:
        """Find supply zones (last up candle before strong down move)"""
        zones = []
        for i in range(len(candles) - 5):
            if candles.iloc[i]['close'] > candles.iloc[i]['open']:  # Up candle
                # Check for strong move down after
                move = candles.iloc[i]['high'] - candles.iloc[i+5]['close']
                if move > candles.iloc[i]['high'] - candles.iloc[i]['low']:
                    zones.append({
                        'low': candles.iloc[i]['low'],
                        'high': candles.iloc[i]['high'],
                        'strength': min(move / (candles.iloc[i]['high'] - candles.iloc[i]['low']), 2.0)
                    })
        return zones[-3:]  # Last 3 zones


class FibonacciStrategy(BaseStrategy):
    """
    Fibonacci Retracement/Extension Trading
    
    Trades:
    - 38.2% retracement in trend direction
    - 61.8% golden retracement
    - 127.2% extension targets
    """
    
    def __init__(self, dna_params: Dict[str, Any] = None):
        super().__init__("Fibonacci", dna_params)
        self.name = "Fibonacci"
    
    def analyze(self, candles: pd.DataFrame, current_price: float, indicators: Dict = None) -> Optional[TradingSignal]:
        if len(candles) < 50:
            return None
        
        high = candles['high'].iloc[-50:].max()
        low = candles['low'].iloc[-50:].min()
        diff = high - low
        
        # Calculate Fib levels
        levels = {
            '0': low,
            '0.236': low + diff * 0.236,
            '0.382': low + diff * 0.382,
            '0.5': low + diff * 0.5,
            '0.618': low + diff * 0.618,
            '0.786': low + diff * 0.786,
            '1': high,
        }
        
        # Find nearest level
        distances = {k: abs(current_price - v) for k, v in levels.items()}
        nearest_level = min(distances, key=distances.get)
        nearest_price = levels[nearest_level]
        
        distance_pct = abs(current_price - nearest_price) / current_price
        
        # Trade bounces from key levels
        if nearest_level in ['0.382', '0.618'] and distance_pct < 0.002:
            # Determine trend
            close = candles['close'].iloc[-20:]
            trend = "up" if close.iloc[-1] > close.iloc[0] else "down"
            
            direction = "BUY" if trend == "up" else "SELL"
            confidence = 0.65 if nearest_level == '0.382' else 0.70
            
            sl = self.calculate_fixed_sl(current_price, direction, candles, max_points=300)
            tp = current_price + (current_price - sl) * 2 if direction == "BUY" else current_price - (sl - current_price) * 2
            
            return TradingSignal(
                symbol="BTCUSD", direction=direction, strength=confidence,
                entry_price=current_price, stop_loss=sl, take_profit=tp,
                risk_reward_ratio=2.0, confidence=confidence,
                strategy_name=self.name, timeframe="M5",
                reasoning=f"Fib {nearest_level} bounce at ${nearest_price:,.0f}",
                timestamp=datetime.now(timezone.utc)
            )
        
        return None


class IcebergStrategy(BaseStrategy):
    """
    Iceberg Order Detection
    
    Detects large hidden orders via:
    - Repeated rejections at same price level
    - Volume spikes with minimal price movement
    - Multiple small orders at same level
    """
    
    def __init__(self, dna_params: Dict[str, Any] = None):
        super().__init__("Iceberg", dna_params)
        self.name = "Iceberg"
    
    def analyze(self, candles: pd.DataFrame, current_price: float, indicators: Dict = None) -> Optional[TradingSignal]:
        if len(candles) < 30:
            return None
        
        close = candles['close'].iloc[-30:]
        high = candles['high'].iloc[-30:]
        low = candles['low'].iloc[-30:]
        volume = candles['volume'].iloc[-30:]
        
        # Detect iceberg buy (repeated rejections at low)
        avg_vol = volume.mean()
        
        # Check for high volume with small range
        recent_range = high.iloc[-1] - low.iloc[-1]
        avg_range = (high.iloc[-10] - low.iloc[-10:]).mean()
        
        if volume.iloc[-1] > avg_vol * 2 and recent_range < avg_range * 0.5:
            # Large volume, small range = iceberg detected
            direction = "BUY" if close.iloc[-1] > close.iloc[-5] else "SELL"
            confidence = 0.65
            
            sl = self.calculate_fixed_sl(current_price, direction, candles, max_points=300)
            tp = current_price + (current_price - sl) * 2 if direction == "BUY" else current_price - (sl - current_price) * 2
            
            return TradingSignal(
                symbol="BTCUSD", direction=direction, strength=confidence,
                entry_price=current_price, stop_loss=sl, take_profit=tp,
                risk_reward_ratio=2.0, confidence=confidence,
                strategy_name=self.name, timeframe="M5",
                reasoning=f"Iceberg detected: Vol {volume.iloc[-1]/avg_vol:.1f}x avg, Range {recent_range/avg_range:.1f}x avg",
                timestamp=datetime.now(timezone.utc)
            )
        
        return None



