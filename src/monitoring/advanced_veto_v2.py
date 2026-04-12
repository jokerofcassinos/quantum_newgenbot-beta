"""
Advanced Veto System v2
CEO: Qwen Code | Created: 2026-04-12

New Veto Protocols:
1. Top/Bottom Detection - Identify local extrema, veto reversals
2. RSI-Based Vetoes - Veto BUY if RSI > 75, SELL if RSI < 25
3. Session-Aware Vetoes - Higher thresholds for Asian/Weekend
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List
from loguru import logger


class AdvancedVetoV2:
    """
    Advanced Veto System with sophisticated rules
    
    Veto Categories:
    - LETHAL: Never override (black swan, margin call, weekend)
    - MAJOR: Strong veto (RSI extremes, top/bottom detection)
    - MINOR: Soft veto (low confidence, session mismatch)
    """
    
    def __init__(self):
        self.veto_rules = []
        self.veto_count = 0
        
    def check_all_vetos(self, signal: Dict[str, Any], candles: pd.DataFrame, 
                       account_state: Dict[str, float]) -> Dict[str, Any]:
        """
        Run all veto checks
        
        Returns:
            dict with approval status and veto details
        """
        vetoes = []
        
        # 1. RSI-Based Vetoes
        rsi_veto = self._check_rsi_extremes(signal, candles)
        if rsi_veto:
            vetoes.append(rsi_veto)
        
        # 2. Top/Bottom Detection
        extrema_veto = self._check_extrema_reversal(signal, candles)
        if extrema_veto:
            vetoes.append(extrema_veto)
        
        # 3. Multi-Timeframe RSI Divergence
        divergence_veto = self._check_rsi_divergence(signal, candles)
        if divergence_veto:
            vetoes.append(divergence_veto)
        
        # 4. Overbought/Oversold + Low Volume
        low_liq_veto = self._check_low_liquidity_extremes(signal, candles)
        if low_liq_veto:
            vetoes.append(low_liq_veto)
        
        # 5. Bollinger Band Extremes
        bb_veto = self._check_bollinger_extremes(signal, candles)
        if bb_veto:
            vetoes.append(bb_veto)
        
        # 6. Session-Aware Checks
        session_veto = self._check_session_compatibility(signal, candles)
        if session_veto:
            vetoes.append(session_veto)
        
        # Determine result
        if not vetoes:
            return {
                'approved': True,
                'vetoed_by': None,
                'veto_severity': None,
                'reason': 'All vetoes passed'
            }
        
        # Find most severe veto
        severity_order = ['lethal', 'major', 'minor']
        most_severe = min(vetoes, key=lambda v: severity_order.index(v.get('severity', 'minor')))
        
        self.veto_count += 1
        
        return {
            'approved': False,
            'vetoed_by': most_severe['rule'],
            'veto_severity': most_severe['severity'],
            'reason': most_severe['reason'],
            'all_vetoes': vetoes
        }
    
    def _check_rsi_extremes(self, signal: Dict[str, Any], candles: pd.DataFrame) -> Dict[str, Any]:
        """
        RSI-Based Veto

        GHOST AUDIT FIX: Relaxed thresholds based on 8,081 ghost trade analysis
        Ghost audit found: 44 RSI veto combinations vetoing 100% winners

        OLD Rules (Too strict):
        - BUY veto if RSI > 75 (overbought)
        - SELL veto if RSI < 25 (oversold)
        - Additional veto if RSI > 70 AND declining momentum

        NEW Rules (Relaxed based on ghost audit data):
        - BUY veto if RSI > 85 (extreme overbought only)
        - SELL veto if RSI < 15 (extreme oversold only)
        - Keep momentum divergence checks but with relaxed thresholds
        """
        if len(candles) < 20:
            return None

        close = candles['close']
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))

        current_rsi = rsi.iloc[-1]
        if pd.isna(current_rsi):
            return None

        direction = signal.get('direction', '')

        # GHOST AUDIT FIX: BUY veto only at extreme overbought (>85, was >75)
        # Ghost audit showed: BUY vetoed at RSI 75-80 had 80-100% WR!
        if direction == 'BUY' and current_rsi > 85:
            return {
                'rule': 'RSI Extreme Overbought',
                'severity': 'major',
                'reason': f"BUY vetoed - RSI {current_rsi:.1f} > 85 (EXTREME overbought)"
            }

        # GHOST AUDIT FIX: SELL veto only at extreme oversold (<15, was <25)
        # Ghost audit showed: SELL vetoed at RSI 15-25 had 60-100% WR!
        if direction == 'SELL' and current_rsi < 15:
            return {
                'rule': 'RSI Extreme Oversold',
                'severity': 'major',
                'reason': f"SELL vetoed - RSI {current_rsi:.1f} < 15 (EXTREME oversold)"
            }

        # GHOST AUDIT FIX: Relaxed momentum check (RSI > 80 AND declining, was >70)
        if direction == 'BUY' and current_rsi > 80:
            rsi_5_ago = rsi.iloc[-5] if len(rsi) >= 5 else current_rsi
            if current_rsi < rsi_5_ago:
                return {
                    'rule': 'RSI Divergence',
                    'severity': 'major',
                    'reason': f"BUY vetoed - RSI {current_rsi:.1f} > 80 AND declining (was {rsi_5_ago:.1f})"
                }

        # GHOST AUDIT FIX: Relaxed momentum check (RSI < 20 AND rising, was <30)
        if direction == 'SELL' and current_rsi < 20:
            rsi_5_ago = rsi.iloc[-5] if len(rsi) >= 5 else current_rsi
            if current_rsi > rsi_5_ago:
                return {
                    'rule': 'RSI Recovery',
                    'severity': 'major',
                    'reason': f"SELL vetoed - RSI {current_rsi:.1f} < 20 AND rising (was {rsi_5_ago:.1f})"
                }
        
        return None
    
    def _check_extrema_reversal(self, signal: Dict[str, Any], candles: pd.DataFrame) -> Dict[str, Any]:
        """
        Top/Bottom Detection
        
        Identify local extrema (swing highs/lows) and veto reversal trades
        that are attempting to pick tops/bottoms without confirmation
        """
        if len(candles) < 50:
            return None
        
        close = candles['close'].iloc[-50:]
        high = candles['high'].iloc[-50:]
        low = candles['low'].iloc[-50:]
        
        direction = signal.get('direction', '')
        current_price = close.iloc[-1]
        
        # Find swing highs and lows
        swing_highs = self._find_swing_points(high, lookback=5, find_max=True)
        swing_lows = self._find_swing_points(low, lookback=5, find_max=False)
        
        if not swing_highs or not swing_lows:
            return None
        
        nearest_high = min(swing_highs, key=lambda x: abs(x['price'] - current_price))
        nearest_low = min(swing_lows, key=lambda x: abs(x['price'] - current_price))
        
        distance_to_high_pct = abs(current_price - nearest_high['price']) / current_price * 100
        distance_to_low_pct = abs(current_price - nearest_low['price']) / current_price * 100
        
        # Veto SELL if at recent swing low (trying to bottom-pick)
        if direction == 'SELL' and distance_to_low_pct < 0.5:
            return {
                'rule': 'Bottom Pick Attempt',
                'severity': 'major',
                'reason': f"SELL vetoed - Price at swing low (${nearest_low['price']:,.0f}, {distance_to_low_pct:.2f}%)"
            }
        
        # Veto BUY if at recent swing high (trying to top-pick)
        if direction == 'BUY' and distance_to_high_pct < 0.5:
            return {
                'rule': 'Top Pick Attempt',
                'severity': 'major',
                'reason': f"BUY vetoed - Price at swing high (${nearest_high['price']:,.0f}, {distance_to_high_pct:.2f}%)"
            }
        
        return None
    
    def _check_rsi_divergence(self, signal: Dict[str, Any], candles: pd.DataFrame) -> Dict[str, Any]:
        """
        Multi-Timeframe RSI Divergence Check
        
        Veto if:
        - M5 RSI says BUY but H1 RSI is overbought
        - M5 RSI says SELL but H1 RSI is oversold
        """
        if len(candles) < 100:
            return None
        
        # Calculate RSI on current timeframe
        close = candles['close']
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        
        current_rsi = rsi.iloc[-1]
        if pd.isna(current_rsi):
            return None
        
        direction = signal.get('direction', '')
        
        # Simulate higher timeframe RSI (using longer lookback as proxy)
        if len(close) >= 50:
            h1_rsi = self._calculate_rsi(close.iloc[-50:], period=14)
        else:
            h1_rsi = current_rsi
        
        # Check divergence
        if direction == 'BUY' and h1_rsi > 70:
            return {
                'rule': 'HTF RSI Overbought',
                'severity': 'major',
                'reason': f"BUY vetoed - M5 RSI {current_rsi:.1f} but H1 RSI {h1_rsi:.1f} > 70"
            }
        
        if direction == 'SELL' and h1_rsi < 30:
            return {
                'rule': 'HTF RSI Oversold',
                'severity': 'major',
                'reason': f"SELL vetoed - M5 RSI {current_rsi:.1f} but H1 RSI {h1_rsi:.1f} < 30"
            }
        
        return None
    
    def _check_low_liquidity_extremes(self, signal: Dict[str, Any], candles: pd.DataFrame) -> Dict[str, Any]:
        """
        Low Liquidity + Extreme Position Veto
        
        Veto if:
        - Volume is very low AND RSI is extreme
        - Session is Asian/Weekend AND position is against trend
        """
        if len(candles) < 20:
            return None
        
        volume = candles['volume'].iloc[-20:]
        avg_volume = volume.mean()
        current_volume = volume.iloc[-1]
        
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
        
        # Check RSI
        close = candles['close']
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        current_rsi = rsi.iloc[-1]
        
        if pd.isna(current_rsi):
            return None
        
        direction = signal.get('direction', '')
        
        # Low volume + extreme RSI
        if volume_ratio < 0.5:  # Very low volume
            if direction == 'BUY' and current_rsi > 70:
                return {
                    'rule': 'Low Liq Overbought',
                    'severity': 'major',
                    'reason': f"BUY vetoed - Low volume ({volume_ratio:.1f}x avg) AND RSI {current_rsi:.1f} > 70"
                }
            if direction == 'SELL' and current_rsi < 30:
                return {
                    'rule': 'Low Liq Oversold',
                    'severity': 'major',
                    'reason': f"SELL vetoed - Low volume ({volume_ratio:.1f}x avg) AND RSI {current_rsi:.1f} < 30"
                }
        
        return None
    
    def _check_bollinger_extremes(self, signal: Dict[str, Any], candles: pd.DataFrame) -> Dict[str, Any]:
        """
        Bollinger Band Extremes Veto
        
        Veto if:
        - BUY at upper band (overextended)
        - SELL at lower band (overextended)
        """
        if len(candles) < 25:
            return None
        
        close = candles['close']
        sma = close.rolling(20).mean()
        std = close.rolling(20).std()
        
        upper_band = sma + 2 * std
        lower_band = sma - 2 * std
        
        current_price = close.iloc[-1]
        current_upper = upper_band.iloc[-1]
        current_lower = lower_band.iloc[-1]
        
        direction = signal.get('direction', '')
        
        # BUY at upper band
        if direction == 'BUY' and current_price >= current_upper * 0.998:
            return {
                'rule': 'BB Upper Band',
                'severity': 'major',
                'reason': f"BUY vetoed - Price at upper BB (${current_upper:,.0f})"
            }
        
        # SELL at lower band
        if direction == 'SELL' and current_price <= current_lower * 1.002:
            return {
                'rule': 'BB Lower Band',
                'severity': 'major',
                'reason': f"SELL vetoed - Price at lower BB (${current_lower:,.0f})"
            }
        
        return None
    
    def _check_session_compatibility(self, signal: Dict[str, Any], candles: pd.DataFrame) -> Dict[str, Any]:
        """
        Session-Aware Veto
        
        Veto if:
        - Asian session and signal confidence < 0.75
        - Weekend and signal confidence < 0.85
        """
        import datetime
        
        current_time = candles.iloc[-1].get('time', datetime.datetime.now(datetime.timezone.utc))
        if hasattr(current_time, 'hour'):
            hour = current_time.hour
            weekday = current_time.weekday()
        else:
            hour = datetime.datetime.now(datetime.timezone.utc).hour
            weekday = datetime.datetime.now(datetime.timezone.utc).weekday()
        
        direction = signal.get('direction', '')
        confidence = signal.get('confidence', 0)
        
        # Weekend veto
        if weekday >= 5:
            if confidence < 0.85:
                return {
                    'rule': 'Weekend Low Confidence',
                    'severity': 'lethal',
                    'reason': f"Weekend trading vetoed - Confidence {confidence:.2f} < 0.85"
                }
        
        # Asian session veto
        if 0 <= hour < 7:
            if confidence < 0.75:
                return {
                    'rule': 'Asian Session Low Confidence',
                    'severity': 'major',
                    'reason': f"Asian session vetoed - Confidence {confidence:.2f} < 0.75"
                }
        
        return None
    
    def _find_swing_points(self, series: pd.Series, lookback: int = 5, find_max: bool = True) -> List[Dict]:
        """Find swing highs or lows"""
        points = []
        for i in range(lookback, len(series) - lookback):
            window = series.iloc[i-lookback:i+lookback+1]
            if find_max:
                if series.iloc[i] == window.max():
                    points.append({'index': i, 'price': series.iloc[i]})
            else:
                if series.iloc[i] == window.min():
                    points.append({'index': i, 'price': series.iloc[i]})
        return points[-5:]  # Last 5 points
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> float:
        """Calculate RSI for a price series"""
        delta = prices.diff()
        gain = delta.where(delta > 0, 0).rolling(period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
        rs = gain / loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        return rsi.iloc[-1] if len(rsi) > 0 else 50
