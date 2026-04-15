"""
Data Engine V3 (State-Synchronization)
CEO: Qwen Code | Created: 2026-04-14

Acts as the "Sensory Nervous System". It collects ticks directly from MT5,
formats them instantly into a rolling Pandas DataFrame (mimicking backtest batching),
and publishes MARKET_SNAPSHOT events over the Event Bus for zero-latency reactions.
"""

import sys
import os
import pandas as pd
from typing import Dict, Any, Deque
from collections import deque
from loguru import logger

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from live_trading.mt5_bridge import MT5Bridge, TickData
from live_v3.event_bus import EventBus, Event, EventType

class DataEngineV3:
    def __init__(self, bridge: MT5Bridge, event_bus: EventBus, max_bars: int = 250):
        """
        Args:
            bridge: An active MT5Bridge.
            event_bus: The global event bus.
            max_bars: Number of candles required for backtest parity (EMA200 needs at least 200).
        """
        self.bridge = bridge
        self.event_bus = event_bus
        self.max_bars = max_bars
        self.logger = logger.bind(name="DataEngineV3")
        
        # High-performance circular buffers (deques) for O(1) appends
        self._open: Deque[float] = deque(maxlen=max_bars)
        self._high: Deque[float] = deque(maxlen=max_bars)
        self._low: Deque[float] = deque(maxlen=max_bars)
        self._close: Deque[float] = deque(maxlen=max_bars)
        self._volume: Deque[float] = deque(maxlen=max_bars)
        
        # Indicator Buffers
        self._ema9: Deque[float] = deque(maxlen=max_bars)
        self._ema21: Deque[float] = deque(maxlen=max_bars)
        self._ema50: Deque[float] = deque(maxlen=max_bars)
        self._ema200: Deque[float] = deque(maxlen=max_bars)
        self._rsi: Deque[float] = deque(maxlen=max_bars)
        self._atr: Deque[float] = deque(maxlen=max_bars)
        self._macd: Deque[float] = deque(maxlen=max_bars)
        self._macd_signal: Deque[float] = deque(maxlen=max_bars)
        
        self.ticks_processed = 0

    def start(self):
        """Bind directly to the MT5Bridge tick event"""
        self.logger.info("[DATA_V3] Connecting to MT5Bridge stream...")
        self.bridge.on_tick(self._on_tick_received)
        self.logger.info("[DATA_V3] Stream connected. Waiting for tick data.")

    def _on_tick_received(self, tick: TickData):
        """Triggered synchronously by MT5Bridge every time a TICK is parsed."""
        try:
            # We construct a synthetic 'candle' out of the tick data for backtest compatibility.
            # In a true bar-based MQL5 EA, this would be actual bar data.
            # Here we map tick bid/ask to open/close/high/low for the snapshot.
            mid_price = (tick.bid + tick.ask) / 2.0
            
            self._open.append(tick.ask) # Using ask as open proxy
            self._high.append(tick.ask)
            self._low.append(tick.bid)
            self._close.append(mid_price)
            self._volume.append(float(tick.volume))
            
            # Map native MT5 indicators sent via the bridge
            self._ema9.append(tick.ema9)
            self._ema21.append(tick.ema21)
            self._ema50.append(tick.ema50)
            self._ema200.append(tick.ema200)
            self._rsi.append(tick.rsi)
            self._atr.append(tick.atr)
            self._macd.append(tick.macd)
            self._macd_signal.append(tick.macd_signal)
            
            self.ticks_processed += 1
            
            # Broadcast raw tick for Trailing Stops / Position Manager
            self.event_bus.publish(Event(EventType.TICK_RECEIVED, tick))
            
            # If we have enough data, broadcast a complete snapshot
            if len(self._close) >= 50:
                self._broadcast_snapshot(tick)
                
        except Exception as e:
            self.logger.error(f"[DATA_V3] Error parsing tick into snapshot: {e}")

    def _broadcast_snapshot(self, latest_tick: TickData):
        """Constructs a DataFrame and pushes it to the core intelligence."""
        df = pd.DataFrame({
            'open': list(self._open),
            'high': list(self._high),
            'low': list(self._low),
            'close': list(self._close),
            'volume': list(self._volume),
            'ema9': list(self._ema9),
            'ema21': list(self._ema21),
            'ema50': list(self._ema50),
            'ema200': list(self._ema200),
            'rsi': list(self._rsi),
            'atr': list(self._atr),
            'macd': list(self._macd),
            'macd_signal': list(self._macd_signal),
        })
        
        # Publish to the EventBus. CoreIntelligenceV3 will intercept this instantly.
        self.event_bus.publish(Event(
            EventType.MARKET_SNAPSHOT,
            payload={
                "dataframe": df,
                "latest_tick": latest_tick
            }
        ))
