"""
VPIN Microstructure - Volume-Synchronized Probability of Informed Trading
Source: Atl4s (salvaged and improved)
Created: 2026-04-11

Measures the imbalance between buy and sell volume to detect institutional activity.
Based on research by Easley, Lopez de Prado, O'Hara (2012).

High VPIN = Informed trading (institutional activity)
Low VPIN = Noise trading (retail activity)
"""

from typing import Dict, Any, List, Tuple
from loguru import logger
import numpy as np


class VPINMicrostructure:
    """
    Volume-Synchronized Probability of Informed Trading.
    
    Inspired by Atl4s implementation based on academic research.
    """

    def __init__(
        self,
        bucket_size: int = 50,
        num_buckets: int = 10,
    ):
        """
        Initialize VPIN Microstructure.
        
        Args:
            bucket_size: Number of ticks per volume bucket
            num_buckets: Number of recent buckets to average
        """
        self.bucket_size = bucket_size
        self.num_buckets = num_buckets
        self.tick_buffer: List[Dict[str, float]] = []
        self.vpin_history: List[float] = []
        
        logger.info(" VPINMicrostructure initialized")
        logger.info(f"   Bucket size: {bucket_size} ticks")
        logger.info(f"   Num buckets: {num_buckets}")

    def update(
        self,
        bid: float,
        ask: float,
        price: float,
        volume: float,
    ) -> float:
        """
        Process new tick and update VPIN.
        
        Args:
            bid: Current bid price
            ask: Current ask price
            price: Last trade price
            volume: Trade volume
            
        Returns:
            Current VPIN value (0.0 to 1.0)
        """
        # Classify tick as buy or sell
        mid_price = (bid + ask) / 2
        if price > mid_price:
            buy_volume = volume
            sell_volume = 0.0
        else:
            buy_volume = 0.0
            sell_volume = volume
        
        self.tick_buffer.append({
            'buy_volume': buy_volume,
            'sell_volume': sell_volume,
            'total_volume': volume,
        })
        
        # Calculate VPIN when we have enough data
        if len(self.tick_buffer) >= self.bucket_size * self.num_buckets:
            vpin = self._calculate_vpin()
            self.vpin_history.append(vpin)
            return vpin
        
        return 0.5  # Default neutral value

    def _calculate_vpin(self) -> float:
        """
        Calculate VPIN from recent tick buckets.
        
        Returns:
            VPIN value (0.0 to 1.0)
        """
        if len(self.tick_buffer) < self.bucket_size * 2:
            return 0.5
        
        # Process most recent buckets
        total_vpin = 0.0
        bucket_count = 0
        
        for i in range(0, min(len(self.tick_buffer), self.bucket_size * self.num_buckets), self.bucket_size):
            bucket = self.tick_buffer[i:i+self.bucket_size]
            if len(bucket) < self.bucket_size:
                continue
            
            buy_vol = sum(t['buy_volume'] for t in bucket)
            sell_vol = sum(t['sell_volume'] for t in bucket)
            total_vol = buy_vol + sell_vol
            
            if total_vol > 0:
                vpin = abs(buy_vol - sell_vol) / total_vol
                total_vpin += vpin
                bucket_count += 1
        
        if bucket_count == 0:
            return 0.5
        
        return total_vpin / bucket_count

    def get_regime(self) -> str:
        """
        Get current trading regime based on VPIN.
        
        Returns:
            Regime classification
        """
        if not self.vpin_history:
            return 'unknown'
        
        current_vpin = self.vpin_history[-1]
        
        if current_vpin > 0.7:
            return 'informed_strong'  # Strong institutional activity
        elif current_vpin > 0.5:
            return 'informed_moderate'  # Moderate institutional activity
        elif current_vpin > 0.3:
            return 'mixed'  # Mixed retail/institutional
        else:
            return 'noise'  # Mostly retail noise

    def should_trade(self) -> bool:
        """
        Determine if current conditions are suitable for trading.

        Returns:
            True if institutional activity detected (good trading conditions)
        """
        if not self.vpin_history:
            return True  # Default allow

        # Trade when VPIN shows institutional activity (not just noise)
        return self.vpin_history[-1] > 0.3

    def calculate_vpin_from_candles(
        self,
        highs: List[float],
        lows: List[float],
        closes: List[float],
        volumes: List[float],
        lookback: int = 20,
    ) -> float:
        """
        Calculate VPIN approximation from OHLCV candle data.
        
        Since we don't have tick data in backtest, we estimate buy/sell volume
        based on where the close is within the candle range.
        
        Args:
            highs: Candle highs
            lows: Candle lows
            closes: Candle closes
            volumes: Candle volumes
            lookback: Number of candles to analyze
            
        Returns:
            VPIN value (0.0 to 1.0)
        """
        if len(closes) < lookback:
            return 0.5  # Not enough data
        
        h = np.array(highs[-lookback:])
        l = np.array(lows[-lookback:])
        c = np.array(closes[-lookback:])
        v = np.array(volumes[-lookback:])
        
        # Estimate buy/sell volume based on close position within candle
        # Close near high = buying pressure, close near low = selling pressure
        candle_range = h - l
        candle_range = np.where(candle_range == 0, 1e-10, candle_range)  # Avoid division by zero
        
        buy_pressure = (c - l) / candle_range  # 0 = sold at low, 1 = bought at high
        sell_pressure = 1 - buy_pressure
        
        buy_volume = v * buy_pressure
        sell_volume = v * sell_pressure
        
        total_buy = np.sum(buy_volume)
        total_sell = np.sum(sell_volume)
        total_volume = total_buy + total_sell
        
        if total_volume == 0:
            return 0.5
        
        vpin = abs(total_buy - total_sell) / total_volume
        
        return vpin




