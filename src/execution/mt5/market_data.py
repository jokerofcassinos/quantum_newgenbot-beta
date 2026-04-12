"""
Market Data - BTCUSD market data collection and analysis
CEO: Qwen Code | Created: 2026-04-10

Handles:
- Real-time price data (ticks, candles)
- Historical data retrieval
- Volume analysis
- Spread monitoring
- Order book data (if available)
"""

import asyncio
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone, timedelta
from loguru import logger

from src.core.config_manager import ConfigManager


class MarketDataFetcher:
    """
    Fetches and processes market data from MT5 for BTCUSD
    
    Provides:
    - Real-time ticks
    - Historical candlesticks
    - Volume data
    - Spread calculations
    - Technical indicators (basic)
    """
    
    def __init__(self, config: ConfigManager):
        self.config = config
        self.symbol = "BTCUSD"
        self.last_price_data = None
        
        logger.info("📊 Market Data Fetcher initialized")
    
    async def get_current_price(self) -> Optional[Dict[str, Any]]:
        """
        Get current BTCUSD price (bid/ask)
        
        Returns:
            dict: Current price data
        """
        try:
            tick = mt5.symbol_info_tick(self.symbol)
            if tick is None:
                logger.error("❌ Failed to get current price")
                return None
            
            return {
                "bid": tick.bid,
                "ask": tick.ask,
                "last": tick.last,
                "volume": tick.volume,
                "spread": tick.ask - tick.bid,
                "spread_points": (tick.ask - tick.bid) / tick.point,
                "time": datetime.fromtimestamp(tick.time),
                "flags": tick.flags
            }
        except Exception as e:
            logger.error(f"❌ Error getting current price: {e}")
            return None
    
    async def get_candles(self, 
                         timeframe: str = "M5",
                         count: int = 100,
                         start_date: Optional[datetime] = None) -> Optional[pd.DataFrame]:
        """
        Get historical candlestick data
        
        Args:
            timeframe: Timeframe (M1, M5, M15, H1, H4, D1)
            count: Number of candles to retrieve
            start_date: Start date (optional, uses latest if None)
        
        Returns:
            DataFrame: OHLCV data
        """
        try:
            # Map timeframe string to MT5 constant
            tf_map = {
                "M1": mt5.TIMEFRAME_M1,
                "M5": mt5.TIMEFRAME_M5,
                "M15": mt5.TIMEFRAME_M15,
                "M30": mt5.TIMEFRAME_M30,
                "H1": mt5.TIMEFRAME_H1,
                "H4": mt5.TIMEFRAME_H4,
                "D1": mt5.TIMEFRAME_D1,
                "W1": mt5.TIMEFRAME_W1,
                "MN1": mt5.TIMEFRAME_MN1
            }
            
            if timeframe not in tf_map:
                logger.error(f"❌ Invalid timeframe: {timeframe}")
                return None
            
            tf = tf_map[timeframe]
            
            # Get candles
            if start_date:
                rates = mt5.copy_rates_from(self.symbol, tf, start_date, count)
            else:
                rates = mt5.copy_rates_from_pos(self.symbol, tf, 0, count)
            
            if rates is None or len(rates) == 0:
                logger.error(f"❌ No candle data retrieved for {timeframe}")
                return None
            
            # Convert to DataFrame
            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            
            # Rename columns for clarity
            df = df.rename(columns={
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'tick_volume': 'volume'
            })
            
            logger.info(f"📊 Retrieved {len(df)} {timeframe} candles")
            logger.info(f"   Range: {df['time'].iloc[0]} to {df['time'].iloc[-1]}")
            logger.info(f"   Price range: ${df['low'].min():.2f} - ${df['high'].max():.2f}")
            
            self.last_price_data = df
            return df
            
        except Exception as e:
            logger.error(f"❌ Error getting candles: {e}", exc_info=True)
            return None
    
    async def get_multi_timeframe_analysis(self) -> Optional[Dict[str, Any]]:
        """
        Get analysis across multiple timeframes for regime detection
        
        Returns:
            dict: Multi-timeframe analysis results
        """
        try:
            timeframes = ["M1", "M5", "M15", "H1", "H4", "D1"]
            analysis = {}
            
            for tf in timeframes:
                candles = await self.get_candles(timeframe=tf, count=100)
                if candles is None or len(candles) == 0:
                    continue
                
                # Calculate basic metrics
                current_price = candles['close'].iloc[-1]
                price_change = ((current_price - candles['open'].iloc[0]) / candles['open'].iloc[0]) * 100
                
                # Calculate EMAs
                ema_9 = candles['close'].ewm(span=9, adjust=False).mean().iloc[-1]
                ema_21 = candles['close'].ewm(span=21, adjust=False).mean().iloc[-1]
                ema_50 = candles['close'].ewm(span=50, adjust=False).mean().iloc[-1]
                ema_200 = candles['close'].ewm(span=200, adjust=False).mean().iloc[-1] if len(candles) >= 200 else None
                
                # Calculate ATR
                tr = pd.DataFrame()
                tr['h-l'] = candles['high'] - candles['low']
                tr['h-pc'] = abs(candles['high'] - candles['close'].shift(1))
                tr['l-pc'] = abs(candles['low'] - candles['close'].shift(1))
                tr['tr'] = tr[['h-l', 'h-pc', 'l-pc']].max(axis=1)
                atr = tr['tr'].rolling(window=14).mean().iloc[-1]
                
                # Calculate volume average
                avg_volume = candles['volume'].rolling(window=20).mean().iloc[-1]
                current_volume = candles['volume'].iloc[-1]
                volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
                
                # Determine trend
                if ema_9 > ema_21 > ema_50:
                    trend = "bullish"
                elif ema_9 < ema_21 < ema_50:
                    trend = "bearish"
                else:
                    trend = "ranging"
                
                analysis[tf] = {
                    "current_price": current_price,
                    "price_change_percent": price_change,
                    "ema_9": ema_9,
                    "ema_21": ema_21,
                    "ema_50": ema_50,
                    "ema_200": ema_200,
                    "atr_14": atr,
                    "avg_volume_20": avg_volume,
                    "current_volume": current_volume,
                    "volume_ratio": volume_ratio,
                    "trend": trend,
                    "candle_count": len(candles)
                }
            
            logger.info(f"📊 Multi-timeframe analysis complete: {len(analysis)} timeframes")
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Error in multi-timeframe analysis: {e}", exc_info=True)
            return None
    
    async def calculate_spread_stats(self, samples: int = 100) -> Dict[str, Any]:
        """
        Calculate spread statistics
        
        Args:
            samples: Number of spread samples
        
        Returns:
            dict: Spread statistics
        """
        try:
            spreads = []
            
            for _ in range(samples):
                price = await self.get_current_price()
                if price:
                    spreads.append(price["spread_points"])
                await asyncio.sleep(0.1)  # Small delay
            
            if not spreads:
                return {}
            
            spread_array = np.array(spreads)
            
            return {
                "avg_spread": float(np.mean(spread_array)),
                "median_spread": float(np.median(spread_array)),
                "min_spread": float(np.min(spread_array)),
                "max_spread": float(np.max(spread_array)),
                "std_spread": float(np.std(spread_array)),
                "samples": len(spreads)
            }
        except Exception as e:
            logger.error(f"❌ Error calculating spread stats: {e}")
            return {}
    
    async def get_market_hours_analysis(self) -> Dict[str, Any]:
        """
        Analyze volume and volatility by market hour
        
        Returns:
            dict: Market hours analysis
        """
        try:
            # Get recent M5 candles
            candles = await self.get_candles(timeframe="M5", count=1000)
            if candles is None:
                return {}
            
            # Add hour column
            candles['hour'] = candles['time'].dt.hour
            
            # Calculate stats by hour
            hourly_stats = candles.groupby('hour').agg({
                'volume': 'mean',
                'high': 'max',
                'low': 'min',
                'close': 'last'
            }).reset_index()
            
            # Calculate range (volatility proxy)
            hourly_stats['range'] = hourly_stats['high'] - hourly_stats['low']
            
            # Convert to dict
            result = {}
            for _, row in hourly_stats.iterrows():
                hour = int(row['hour'])
                result[hour] = {
                    "avg_volume": row['volume'],
                    "avg_range": row['range'],
                    "volatility_score": row['range'] / candles['close'].mean() * 10000
                }
            
            # Identify best trading hours (high volume + volatility)
            best_hours = sorted(result.items(), 
                              key=lambda x: x[1]['avg_volume'] * x[1]['avg_range'],
                              reverse=True)[:5]
            
            return {
                "hourly_stats": result,
                "best_trading_hours": [h[0] for h in best_hours],
                "analysis_period": f"{candles['time'].iloc[0]} to {candles['time'].iloc[-1]}"
            }
        except Exception as e:
            logger.error(f"❌ Error in market hours analysis: {e}")
            return {}
    
    async def detect_price_patterns(self, candles: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Detect common candlestick patterns
        
        Args:
            candles: DataFrame with OHLCV data
        
        Returns:
            list: Detected patterns
        """
        try:
            patterns = []
            
            if len(candles) < 3:
                return patterns
            
            # Doji pattern (very small body relative to range)
            for i in range(-3, -1):
                candle = candles.iloc[i]
                body = abs(candle['close'] - candle['open'])
                range_size = candle['high'] - candle['low']
                
                if range_size > 0 and body / range_size < 0.1:
                    patterns.append({
                        "pattern": "doji",
                        "index": i,
                        "time": candle['time'],
                        "price": candle['close'],
                        "significance": "indecision"
                    })
            
            # Engulfing pattern
            for i in range(-3, -2):
                prev = candles.iloc[i]
                curr = candles.iloc[i + 1]
                
                prev_body = abs(prev['close'] - prev['open'])
                curr_body = abs(curr['close'] - curr['open'])
                
                # Bullish engulfing
                if (prev['close'] < prev['open'] and 
                    curr['close'] > curr['open'] and
                    curr['open'] <= prev['close'] and
                    curr['close'] >= prev['open']):
                    patterns.append({
                        "pattern": "bullish_engulfing",
                        "index": i + 1,
                        "time": curr['time'],
                        "price": curr['close'],
                        "significance": "bullish_reversal"
                    })
                
                # Bearish engulfing
                elif (prev['close'] > prev['open'] and 
                      curr['close'] < curr['open'] and
                      curr['open'] >= prev['close'] and
                      curr['close'] <= prev['open']):
                    patterns.append({
                        "pattern": "bearish_engulfing",
                        "index": i + 1,
                        "time": curr['time'],
                        "price": curr['close'],
                        "significance": "bearish_reversal"
                    })
            
            if patterns:
                logger.info(f"🔍 Detected {len(patterns)} pattern(s)")
            
            return patterns
            
        except Exception as e:
            logger.error(f"❌ Error detecting patterns: {e}")
            return []
    
    async def get_orderbook_depth(self) -> Optional[Dict[str, Any]]:
        """
        Get order book depth (if available from broker)
        
        Returns:
            dict: Order book data
        """
        try:
            # Try to get order book
            book = mt5.market_book_get(self.symbol)
            
            if book is None:
                logger.info("ℹ️ Order book not available")
                return None
            
            # Parse order book
            bids = []
            asks = []
            
            for entry in book:
                if entry.type == mt5.MARKET_BOOK_TYPE_BUY:
                    bids.append({
                        "price": entry.price,
                        "volume": entry.volume
                    })
                elif entry.type == mt5.MARKET_BOOK_TYPE_SELL:
                    asks.append({
                        "price": entry.price,
                        "volume": entry.volume
                    })
            
            return {
                "bids": bids,
                "asks": asks,
                "bid_volume": sum(b['volume'] for b in bids),
                "ask_volume": sum(a['volume'] for a in asks),
                "total_volume": sum(b['volume'] for b in bids) + sum(a['volume'] for a in asks)
            }
        except Exception as e:
            logger.error(f"❌ Error getting order book: {e}")
            return None
