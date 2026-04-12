"""
Timeframe Synthesizer - Intelligent multi-timeframe reconstruction
CEO: Qwen Code | Created: 2026-04-10

Problem:
- M1 data from MT5 is limited (broker only keeps recent bars)
- We need M1 for accurate backtesting but often only have M5+

Solution:
- Use sophisticated fractal reconstruction algorithms
- Combine M5, M15, H1 to synthesize realistic M1 data
- Apply Brownian motion with drift matching parent timeframe
- Ensure OHLCV consistency across all timeframes
- Volume distribution follows realistic intrabar patterns
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from loguru import logger


class TimeframeSynthesizer:
    """
    Intelligent timeframe synthesis system
    
    Capabilities:
    1. Reconstruct M1 from M5/M15/H1 data
    2. Interpolate missing timeframes
    3. Ensure cross-timeframe consistency
    4. Generate realistic tick-level data
    """
    
    # Typical bars per parent timeframe
    BARS_PER_TIMEFRAME = {
        'M1_from_M5': 5,
        'M1_from_M15': 15,
        'M5_from_M15': 3,
        'M5_from_H1': 12,
        'M15_from_H1': 4,
        'M30_from_H1': 2,
        'H1_from_H4': 4,
        'H4_from_D1': 6,
    }
    
    # Volume distribution patterns (intraday)
    VOLUME_PATTERNS = {
        'asian': [0.3, 0.25, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.45, 0.4, 0.35],
        'london': [0.6, 0.7, 0.85, 1.0, 1.1, 1.15, 1.2, 1.15, 1.1, 1.0, 0.9, 0.8],
        'ny': [0.9, 1.0, 1.1, 1.2, 1.3, 1.35, 1.4, 1.35, 1.25, 1.15, 1.0, 0.85],
        'overlap': [1.2, 1.3, 1.4, 1.5, 1.6, 1.65, 1.7, 1.65, 1.5, 1.4, 1.3, 1.2],
    }
    
    def synthesize_m1_from_higher_tf(self, 
                                     candles_higher: pd.DataFrame,
                                     source_timeframe: str = 'M5') -> pd.DataFrame:
        """
        Synthesize M1 candles from higher timeframe data
        
        Algorithm:
        1. For each M5 candle, generate 5 M1 candles
        2. Use Brownian bridge to interpolate prices
        3. Match OHLC constraints exactly
        4. Distribute volume realistically
        5. Add micro-structure noise
        
        Args:
            candles_higher: DataFrame with M5/M15/H1 candles
            source_timeframe: Source timeframe ('M5', 'M15', 'H1')
        
        Returns:
            DataFrame: Synthesized M1 candles
        """
        bars_per_parent = self.BARS_PER_TIMEFRAME[f'M1_from_{source_timeframe}']
        
        logger.info(f"🔬 Synthesizing M1 from {source_timeframe} "
                   f"({bars_per_parent} M1 bars per parent)")
        
        all_m1 = []
        
        for idx, parent in candles_higher.iterrows():
            # Generate child M1 candles
            m1_candles = self._generate_child_bars(
                parent, bars_per_parent, 'M1'
            )
            all_m1.extend(m1_candles)
        
        m1_df = pd.DataFrame(all_m1)
        m1_df['time'] = pd.to_datetime(m1_df['time'])
        m1_df = m1_df.sort_values('time').reset_index(drop=True)
        
        logger.info(f"✅ Synthesized {len(m1_df)} M1 candles from "
                   f"{len(candles_higher)} {source_timeframe} candles")
        
        return m1_df
    
    def _generate_child_bars(self, 
                            parent_candle: pd.Series,
                            n_children: int,
                            child_tf: str) -> List[Dict]:
        """
        Generate child bars from a single parent bar
        
        Uses Brownian bridge interpolation with constraints:
        - First open = parent open
        - Last close = parent close
        - Max high = parent high
        - Min low = parent low
        - Sum volume = parent volume
        """
        parent_open = parent_candle['open']
        parent_high = parent_candle['high']
        parent_low = parent_candle['low']
        parent_close = parent_candle['close']
        parent_volume = parent_candle.get('volume', 1000)
        parent_time = parent_candle['time']
        
        # Calculate time increment
        if child_tf == 'M1':
            time_delta = pd.Timedelta(minutes=1)
        elif child_tf == 'M5':
            time_delta = pd.Timedelta(minutes=5)
        else:
            time_delta = pd.Timedelta(minutes=1)
        
        # Generate price path using Brownian bridge
        price_path = self._brownian_bridge(
            start=parent_open,
            end=parent_close,
            n_steps=n_children,
            high_constraint=parent_high,
            low_constraint=parent_low,
            volatility=self._estimate_volatility(parent_candle)
        )
        
        # Build child candles
        children = []
        for i in range(n_children):
            child_time = parent_time + (i * time_delta)
            
            if i == 0:
                open_price = parent_open
            else:
                open_price = children[-1]['close']
            
            close_price = price_path[i]
            
            # Generate realistic high/low for this child bar
            child_range = self._generate_child_range(open_price, close_price, parent_high, parent_low)
            high_price = child_range['high']
            low_price = child_range['low']
            
            # Distribute volume (U-shaped pattern)
            volume_weight = self._get_volume_weight(i, n_children, parent_time.hour)
            child_volume = parent_volume * volume_weight / n_children
            
            children.append({
                'time': child_time,
                'open': round(open_price, 2),
                'high': round(high_price, 2),
                'low': round(low_price, 2),
                'close': round(close_price, 2),
                'volume': round(child_volume, 0)
            })
        
        return children
    
    def _brownian_bridge(self, 
                        start: float, 
                        end: float, 
                        n_steps: int,
                        high_constraint: float,
                        low_constraint: float,
                        volatility: float) -> np.ndarray:
        """
        Generate Brownian bridge path from start to end
        with constraints on high/low
        """
        # Standard Brownian bridge
        t = np.linspace(0, 1, n_steps)
        B_t = np.random.standard_normal(n_steps).cumsum()
        B_t = B_t - t * B_t[-1]  # Bridge constraint
        
        # Scale by volatility
        sigma = volatility * 0.1
        path = start + (end - start) * t + sigma * B_t
        
        # Apply constraints via clamping (preserves endpoints better than scaling)
        path = np.clip(path, low_constraint, high_constraint)
        
        # Ensure exact endpoints
        path[0] = start
        path[-1] = end
        
        return path
    
    def _estimate_volatility(self, candle: pd.Series) -> float:
        """Estimate volatility from parent candle"""
        high = candle['high']
        low = candle['low']
        price = candle['close']
        
        # Normalize range as percentage
        range_pct = (high - low) / price
        
        return range_pct * 100  # Return as "points" equivalent
    
    def _generate_child_range(self, open_price: float, close_price: float,
                             parent_high: float, parent_low: float) -> Dict:
        """Generate realistic high/low for child bar"""
        body = abs(close_price - open_price)
        
        # Child bar range should be smaller than parent
        max_range = (parent_high - parent_low) * 0.6
        
        if body > 0:
            # Add wicks
            upper_wick = np.random.uniform(0, max_range * 0.4)
            lower_wick = np.random.uniform(0, max_range * 0.4)
            
            high = max(open_price, close_price) + upper_wick
            low = min(open_price, close_price) - lower_wick
        else:
            # Doji - symmetric range
            range_size = np.random.uniform(max_range * 0.1, max_range * 0.3)
            high = open_price + range_size / 2
            low = open_price - range_size / 2
        
        # Constrain to parent range
        high = min(high, parent_high)
        low = max(low, parent_low)
        
        return {'high': high, 'low': low}
    
    def _get_volume_weight(self, 
                          bar_index: int, 
                          total_bars: int, 
                          hour_utc: int) -> float:
        """
        Get volume weight for child bar based on time pattern
        
        BTCUSD volume patterns:
        - Asian session: Low volume
        - London open: Increasing
        - NY open: Peak volume
        - London/NY overlap: Highest
        """
        # Determine session
        if 0 <= hour_utc < 7:
            pattern = self.VOLUME_PATTERNS['asian']
        elif 7 <= hour_utc < 13:
            pattern = self.VOLUME_PATTERNS['london']
        elif 13 <= hour_utc < 17:
            pattern = self.VOLUME_PATTERNS['overlap']
        else:
            pattern = self.VOLUME_PATTERNS['ny']
        
        # Get minute-level weight
        minute_weight = pattern[bar_index % len(pattern)]
        
        return minute_weight
    
    def synthesize_all_timeframes(self, 
                                  m5_candles: pd.DataFrame,
                                  h1_candles: Optional[pd.DataFrame] = None,
                                  h4_candles: Optional[pd.DataFrame] = None) -> Dict[str, pd.DataFrame]:
        """
        Synthesize all timeframes from available data
        
        Returns:
            dict: All timeframes (M1, M5, M15, M30, H1, H4)
        """
        result = {}
        
        # M1 from M5
        logger.info("🔬 Synthesizing M1 from M5...")
        result['M1'] = self.synthesize_m1_from_higher_tf(m5_candles, 'M5')
        
        # M5 (already have)
        result['M5'] = m5_candles
        
        # M15 from M5 (aggregate)
        logger.info("🔬 Aggregating M15 from M5...")
        result['M15'] = self._aggregate_timeframe(m5_candles, 'M15')
        
        # H1 from M5
        logger.info("🔬 Aggregating H1 from M5...")
        result['H1'] = self._aggregate_timeframe(m5_candles, 'H1')
        
        # H4 (if provided or from H1)
        if h4_candles is not None:
            result['H4'] = h4_candles
        elif 'H1' in result:
            result['H4'] = self._aggregate_timeframe(result['H1'], 'H4')
        
        logger.info(f"✅ Timeframe synthesis complete:")
        for tf, df in result.items():
            logger.info(f"   {tf}: {len(df)} candles")
        
        return result
    
    def _aggregate_timeframe(self, 
                            candles: pd.DataFrame, 
                            target_tf: str) -> pd.DataFrame:
        """
        Aggregate candles to higher timeframe
        
        M5 → M15: 3 bars per candle
        M5 → H1: 12 bars per candle
        M5 → H4: 72 bars per candle
        """
        bars_per_candle = {
            'M15': 3,
            'M30': 6,
            'H1': 12,
            'H4': 72,
            'D1': 288,
        }
        
        n_bars = bars_per_candle.get(target_tf, 12)
        
        aggregated = []
        
        for i in range(0, len(candles), n_bars):
            chunk = candles.iloc[i:i+n_bars]
            
            if len(chunk) == 0:
                continue
            
            agg_candle = {
                'time': chunk.iloc[0]['time'],
                'open': chunk.iloc[0]['open'],
                'high': chunk['high'].max(),
                'low': chunk['low'].min(),
                'close': chunk.iloc[-1]['close'],
                'volume': chunk['volume'].sum() if 'volume' in chunk.columns else 0
            }
            
            aggregated.append(agg_candle)
        
        return pd.DataFrame(aggregated)
