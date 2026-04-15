"""
Zero-Latency Event Bus - Live V3
CEO: Qwen Code | Created: 2026-04-14

Replaces the inefficient `while True` polling loops with a pure Event-Driven Architecture (EDA).
Components subscribe to specific event types and react instantly when data is pushed from MT5.
"""

from typing import Callable, Dict, List, Any
import threading
from enum import Enum, auto
from loguru import logger

class EventType(Enum):
    MARKET_SNAPSHOT = auto()  # Emitted when a complete OHLCV + Indicators snapshot arrives
    TICK_RECEIVED = auto()    # Emitted on every tick (for trailing stops/management)
    SIGNAL_GENERATED = auto() # Emitted by Core Intelligence when a trade is approved
    ORDER_REQUEST = auto()    # Emitted to TradeExecutor to send to MT5
    ORDER_FILLED = auto()     # Emitted when MT5 confirms execution
    POSITION_CLOSED = auto()  # Emitted when MT5 confirms closure
    ERROR = auto()

class Event:
    def __init__(self, event_type: EventType, payload: Any):
        self.type = event_type
        self.payload = payload

class EventBus:
    def __init__(self):
        self.subscribers: Dict[EventType, List[Callable]] = {
            event_type: [] for event_type in EventType
        }
        self.lock = threading.Lock()
        self.logger = logger.bind(name="EventBus")

    def subscribe(self, event_type: EventType, callback: Callable):
        """Register a callback for a specific event type."""
        with self.lock:
            if callback not in self.subscribers[event_type]:
                self.subscribers[event_type].append(callback)

    def unsubscribe(self, event_type: EventType, callback: Callable):
        """Remove a callback for a specific event type."""
        with self.lock:
            if callback in self.subscribers[event_type]:
                self.subscribers[event_type].remove(callback)

    def publish(self, event: Event):
        """
        Instantly push an event to all subscribers.
        Executes synchronously to guarantee zero-latency sequential processing 
        in HFT environments, avoiding thread-switching overhead.
        """
        with self.lock:
            callbacks = self.subscribers[event.type].copy()
            
        for callback in callbacks:
            try:
                callback(event)
            except Exception as e:
                self.logger.error(f"[EVENT_BUS] Error in subscriber {callback.__name__} for {event.type.name}: {e}")
