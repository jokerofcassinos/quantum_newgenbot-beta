"""
Data Engine - Background worker para extrao contnua de dados do MT5

Este mdulo processa dados recebidos do MT5 em background, calcula indicadores
em streaming e mantm buffers atualizados para a cadeia neural.

Herana do projeto legacy DubaiMatrixASI:
- data_engine.py: Background worker para processamento contnuo
- Clculo incremental de indicadores (s atualiza ltimo valor)
- Buffers circulares para auditoria
- Fallback para MT5 API se socket falhar
"""

import threading
import time
import logging
from typing import Optional, Dict, List, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import deque
import numpy as np
import traceback

from live_trading.mt5_bridge import MT5Bridge, TickData, AccountData, PositionData
from live_trading.logger import get_logger


@dataclass
class IndicatorData:
    """Dados de indicadores calculados"""
    timestamp: datetime
    atr: float = 0.0
    rsi: float = 0.0
    ema9: float = 0.0
    ema21: float = 0.0
    ema50: float = 0.0
    ema200: float = 0.0
    macd: float = 0.0
    macd_signal: float = 0.0
    macd_histogram: float = 0.0
    bb_upper: float = 0.0
    bb_middle: float = 0.0
    bb_lower: float = 0.0
    vwap: float = 0.0
    volume_profile: Dict[str, float] = field(default_factory=dict)
    momentum: float = 0.0
    volatility: float = 0.0


@dataclass
class MarketState:
    """Estado atual do mercado"""
    timestamp: datetime
    symbol: str = ""
    price: float = 0.0
    bid: float = 0.0
    ask: float = 0.0
    spread: float = 0.0
    volume: int = 0
    indicators: IndicatorData = field(default_factory=lambda: IndicatorData(timestamp=datetime.now()))
    regime: str = "unknown"  # trending_up, trending_down, ranging, volatile
    trend_strength: float = 0.0
    volatility_regime: str = "normal"  # low, normal, high, extreme


class IncrementalIndicatorCalculator:
    """
    Calculadora incremental de indicadores
    
    Ao invs de recalcular tudo a cada tick, atualiza apenas o ltimo valor.
    Isso reduz drasticamente a latncia.
    """
    
    def __init__(self, buffer_size: int = 500):
        self.buffer_size = buffer_size
        
        # Buffers de preos
        self.prices = deque(maxlen=buffer_size)
        self.highs = deque(maxlen=buffer_size)
        self.lows = deque(maxlen=buffer_size)
        self.volumes = deque(maxlen=buffer_size)
        
        # Estado dos indicadores
        self.ema_values = {}  # {period: last_ema}
        self.atr_value = 0.0
        self.rsi_value = 0.0
        self.macd_value = 0.0
        self.macd_signal_value = 0.0
        
        # Para VWAP
        self.vwap_cumulative_pv = 0.0
        self.vwap_cumulative_v = 0.0
        self.vwap_session_start = None
    
    def update(self, tick: TickData):
        """Atualiza buffers com novo tick"""
        mid_price = (tick.bid + tick.ask) / 2
        self.prices.append(mid_price)
        self.highs.append(tick.ask)
        self.lows.append(tick.bid)
        self.volumes.append(tick.volume)
    
    def calculate_all(self) -> IndicatorData:
        """Calcula todos os indicadores incrementalmente"""
        if len(self.prices) < 2:
            return IndicatorData(timestamp=datetime.now())
        
        indicators = IndicatorData(timestamp=datetime.now())
        
        # Calcular cada indicador
        indicators.atr = self._calculate_atr()
        indicators.rsi = self._calculate_rsi()
        indicators.ema9 = self._calculate_ema(9)
        indicators.ema21 = self._calculate_ema(21)
        indicators.ema50 = self._calculate_ema(50)
        indicators.ema200 = self._calculate_ema(200)
        
        macd_result = self._calculate_macd()
        indicators.macd = macd_result[0]
        indicators.macd_signal = macd_result[1]
        indicators.macd_histogram = macd_result[2]
        
        bb = self._calculate_bollinger_bands()
        indicators.bb_upper = bb[0]
        indicators.bb_middle = bb[1]
        indicators.bb_lower = bb[2]
        
        indicators.vwap = self._calculate_vwap()
        indicators.momentum = self._calculate_momentum()
        indicators.volatility = self._calculate_volatility()
        
        return indicators
    
    def _calculate_ema(self, period: int) -> float:
        """Calcula EMA incremental"""
        if len(self.prices) < period:
            return self.prices[-1] if self.prices else 0.0
        
        # Se  o primeiro clculo ou no tem valor armazenado
        if period not in self.ema_values:
            # Calcular SMA como inicializao
            ema = sum(list(self.prices)[-period:]) / period
        else:
            # Clculo incremental
            multiplier = 2 / (period + 1)
            ema = (self.prices[-1] - self.ema_values[period]) * multiplier + self.ema_values[period]
        
        self.ema_values[period] = ema
        return ema
    
    def _calculate_atr(self, period: int = 14) -> float:
        """Calcula ATR incremental"""
        if len(self.highs) < 2:
            return 0.0
        
        # True Range atual
        current_high = self.highs[-1]
        current_low = self.lows[-1]
        previous_close = self.prices[-2] if len(self.prices) >= 2 else current_high
        
        true_range = max(
            current_high - current_low,
            abs(current_high - previous_close),
            abs(current_low - previous_close)
        )
        
        # ATR incremental (Wilder's smoothing)
        if self.atr_value == 0.0:
            # Primeiro clculo: mdia simples
            tr_values = []
            for i in range(1, min(period, len(self.highs))):
                high = self.highs[-i]
                low = self.lows[-i]
                prev_close = self.prices[-i-1] if i+1 <= len(self.prices) else high
                tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
                tr_values.append(tr)
            
            self.atr_value = sum(tr_values) / len(tr_values) if tr_values else true_range
        else:
            # Incremental
            self.atr_value = (self.atr_value * (period - 1) + true_range) / period
        
        return self.atr_value
    
    def _calculate_rsi(self, period: int = 14) -> float:
        """Calcula RSI incremental"""
        if len(self.prices) < period + 1:
            return 50.0  # Neutro
        
        # Calcular mudanas de preo
        gains = []
        losses = []
        
        prices_list = list(self.prices)
        for i in range(-period, 0):
            change = prices_list[i] - prices_list[i-1]
            gains.append(max(0, change))
            losses.append(max(0, -change))
        
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        self.rsi_value = rsi
        return rsi
    
    def _calculate_macd(self, fast: int = 12, slow: int = 26, signal: int = 9) -> tuple:
        """Calcula MACD"""
        ema_fast = self._calculate_ema_fast_for_macd(fast)
        ema_slow = self._calculate_ema_slow_for_macd(slow)
        
        macd_line = ema_fast - ema_slow
        
        # Signal line (EMA do MACD)
        if self.macd_signal_value == 0.0:
            self.macd_signal_value = macd_line
        else:
            multiplier = 2 / (signal + 1)
            self.macd_signal_value = (macd_line - self.macd_signal_value) * multiplier + self.macd_signal_value
        
        histogram = macd_line - self.macd_signal_value
        self.macd_value = macd_line
        
        return (macd_line, self.macd_signal_value, histogram)
    
    def _calculate_ema_fast_for_macd(self, period: int) -> float:
        """EMA fast para MACD"""
        key = f"macd_fast_{period}"
        if len(self.prices) < period:
            return self.prices[-1] if self.prices else 0.0
        
        if key not in self.ema_values:
            ema = sum(list(self.prices)[-period:]) / period
        else:
            multiplier = 2 / (period + 1)
            ema = (self.prices[-1] - self.ema_values[key]) * multiplier + self.ema_values[key]
        
        self.ema_values[key] = ema
        return ema
    
    def _calculate_ema_slow_for_macd(self, period: int) -> float:
        """EMA slow para MACD"""
        key = f"macd_slow_{period}"
        if len(self.prices) < period:
            return self.prices[-1] if self.prices else 0.0
        
        if key not in self.ema_values:
            ema = sum(list(self.prices)[-period:]) / period
        else:
            multiplier = 2 / (period + 1)
            ema = (self.prices[-1] - self.ema_values[key]) * multiplier + self.ema_values[key]
        
        self.ema_values[key] = ema
        return ema
    
    def _calculate_bollinger_bands(self, period: int = 20, num_std: float = 2.0) -> tuple:
        """Calcula Bollinger Bands"""
        if len(self.prices) < period:
            price = self.prices[-1] if self.prices else 0.0
            return (price, price, price)
        
        prices_slice = list(self.prices)[-period:]
        middle = sum(prices_slice) / period
        
        variance = sum((p - middle) ** 2 for p in prices_slice) / period
        std = variance ** 0.5
        
        upper = middle + num_std * std
        lower = middle - num_std * std
        
        return (upper, middle, lower)
    
    def _calculate_vwap(self) -> float:
        """Calcula VWAP"""
        if not self.prices or not self.volumes:
            return 0.0
        
        # Reset no incio de nova sesso (simplificado: a cada 24h)
        now = datetime.now()
        if self.vwap_session_start is None or (now - self.vwap_session_start).days > 0:
            self.vwap_cumulative_pv = 0.0
            self.vwap_cumulative_v = 0.0
            self.vwap_session_start = now
        
        # Atualizar com ltimo tick
        price = self.prices[-1]
        volume = self.volumes[-1]
        
        self.vwap_cumulative_pv += price * volume
        self.vwap_cumulative_v += volume
        
        if self.vwap_cumulative_v == 0:
            return price
        
        return self.vwap_cumulative_pv / self.vwap_cumulative_v
    
    def _calculate_momentum(self, period: int = 10) -> float:
        """Calcula momentum (rate of change)"""
        if len(self.prices) < period + 1:
            return 0.0
        
        current_price = self.prices[-1]
        past_price = self.prices[-period-1]
        
        if past_price == 0:
            return 0.0
        
        return ((current_price - past_price) / past_price) * 100
    
    def _calculate_volatility(self, period: int = 20) -> float:
        """Calcula volatilidade (std dev dos retornos)"""
        if len(self.prices) < period + 1:
            return 0.0
        
        # Calcular retornos
        returns = []
        prices_list = list(self.prices)
        for i in range(-period, 0):
            if prices_list[i-1] != 0:
                ret = (prices_list[i] - prices_list[i-1]) / prices_list[i-1]
                returns.append(ret)
        
        if not returns:
            return 0.0
        
        # Std dev
        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
        std = variance ** 0.5
        
        return std * 100  # Em porcentagem


class DataEngine:
    """
    Background worker para processamento contnuo de dados
    
    Este mdulo:
    1. Recebe ticks do MT5 Bridge
    2. Calcula indicadores em streaming
    3. Detecta regime de mercado
    4. Mantm buffers atualizados
    5. Fornece dados para a cadeia neural
    
    Herana do legacy:
    - Background worker pattern
    - Processamento contnuo em thread separada
    - Buffers circulares para auditoria
    - Fallback para MT5 API
    """
    
    def __init__(
        self,
        bridge: MT5Bridge,
        symbol: str = "BTCUSD",
        buffer_size: int = 1000,
        enable_fallback: bool = True
    ):
        self.bridge = bridge
        self.symbol = symbol
        self.buffer_size = buffer_size
        self.enable_fallback = enable_fallback
        
        # Calculadora de indicadores
        self.calculator = IncrementalIndicatorCalculator(buffer_size=buffer_size)
        
        # Estado atual do mercado
        self.market_state = MarketState(timestamp=datetime.now(), symbol=symbol)
        
        # Buffers para histrico
        self.indicators_history = deque(maxlen=500)
        self.market_state_history = deque(maxlen=500)
        self.ticks_processed = 0
        self.errors = 0
        
        # Thread de processamento
        self.processing_thread: Optional[threading.Thread] = None
        self._running = False
        
        # Callbacks - usar nomes com underscore para evitar conflito
        self._on_indicators_ready: Optional[Callable[[IndicatorData], None]] = None
        self._on_market_state_updated: Optional[Callable[[MarketState], None]] = None
        self._on_regime_change: Optional[Callable[[str], None]] = None

        # Logger - usar sistema de logs do projeto
        self.logger = get_logger("DataEngine")

    # Callback registration methods (chainable)
    def on_indicators_ready(self, callback):
        self._on_indicators_ready = callback
        return self

    def on_market_state_updated(self, callback):
        self._on_market_state_updated = callback
        return self

    def on_regime_change(self, callback):
        self._on_regime_change = callback
        return self
    
    def start(self):
        """Inicia o data engine"""
        self.logger.info(f"[DATA_ENGINE] Starting data engine for {self.symbol}")

        # Registrar callbacks no bridge (nova API simplificada)
        self.bridge.on_tick(self._on_tick_received)
        self.bridge.on_account(self._on_account_received)
        self.bridge.on_position(self._on_position_received)
        self.bridge.on_connected(self._on_mt5_connected)
        self.bridge.on_disconnected(self._on_mt5_disconnected)
        
        # Iniciar thread de processamento
        self._running = True
        self.processing_thread = threading.Thread(target=self._processing_loop, daemon=True)
        self.processing_thread.start()
        
        self.logger.info("[DATA_ENGINE] Data engine started")
    
    def stop(self):
        """Para o data engine"""
        self.logger.info("[DATA_ENGINE] Stopping data engine")
        self._running = False
        
        if self.processing_thread:
            self.processing_thread.join(timeout=5)
        
        self.logger.info("[DATA_ENGINE] Data engine stopped")
    
    def _on_tick_received(self, tick: TickData):
        """Callback quando recebe tick do MT5 - Dispara processamento imediato"""
        try:
            self.ticks_processed += 1
            
            # Atualizar estado de mercado
            self.market_state.timestamp = tick.timestamp
            self.market_state.indicators.atr = tick.atr
            self.market_state.indicators.rsi = tick.rsi
            self.market_state.indicators.ema9 = tick.ema9
            self.market_state.indicators.ema21 = tick.ema21
            self.market_state.indicators.ema50 = tick.ema50
            self.market_state.indicators.ema200 = tick.ema200
            
            # Disparar callback para a Neural Chain imediatamente
            if self._on_indicators_ready:
                self._on_indicators_ready(self.market_state.indicators)
                
            if self.ticks_processed % 10 == 0:
                self.logger.debug(f"[DATA_ENGINE] Tick #{self.ticks_processed} processed (RSI: {tick.rsi:.2f})")
            
        except Exception as e:
            self.logger.error(f"[DATA_ENGINE] Error processing tick: {e}")
            self.errors += 1
    
    def _on_account_received(self, account: AccountData):
        """Callback quando recebe dados da conta"""
        self.logger.debug(f"[DATA_ENGINE] Account updated: balance={account.balance:.2f}")
    
    def _on_position_received(self, position: PositionData):
        """Callback quando recebe dados de posio"""
        self.logger.debug(f"[DATA_ENGINE] Position updated: ticket={position.ticket}")
    
    def _on_mt5_connected(self):
        """Callback de conexão - Warm-up de histórico (temporariamente desativado para testes)"""
        self.logger.info("[DATA_ENGINE] MT5 connected. (History request skipped for stability test)")
        # self.bridge.request_history(self.symbol, "M5", 200)
        # self.bridge.request_history(self.symbol, "M15", 100)
        # self.bridge.request_history(self.symbol, "H1", 50)
    
    def _on_mt5_disconnected(self):
        """Callback quando MT5 desconecta"""
        self.logger.warning("[DATA_ENGINE] MT5 disconnected")
    
    def _processing_loop(self):
        """Loop principal de processamento em background com telemetria"""
        self.logger.info("[DATA_ENGINE] Processing loop started")
        
        while self._running:
            try:
                if len(self.calculator.prices) >= 2:
                    indicators = self.calculator.calculate_all()
                    
                    regime = self._detect_regime(indicators)
                    
                    self.market_state.indicators = indicators
                    self.market_state.regime = regime[0]
                    self.market_state.trend_strength = regime[1]
                    self.market_state.volatility_regime = regime[2]
                    
                    self.indicators_history.append(indicators)
                    self.market_state_history.append(self.market_state)
                    
                    # Log de Telemetria de Ciclo
                    self.logger.debug(f"[DATA_ENGINE] CICLO: Regime={regime[0]} | ATR={indicators.atr:.2f} | RSI={indicators.rsi:.2f}")

                    if self._on_indicators_ready:
                        self._on_indicators_ready(indicators)
                
                time.sleep(0.5) # Ajustado para 500ms para evitar sobrecarga de log
                
            except Exception as e:
                self.logger.error(f"[DATA_ENGINE] Processing error: {e}")
                time.sleep(1)
        
        self.logger.info("[DATA_ENGINE] Processing loop stopped")
    
    def _detect_regime(self, indicators: IndicatorData) -> tuple:
        """
        Detecta regime de mercado baseado em indicadores
        
        Returns:
            (regime, trend_strength, volatility_regime)
        """
        # Tendncia baseada em EMAs
        ema9 = indicators.ema9
        ema21 = indicators.ema21
        ema50 = indicators.ema50
        ema200 = indicators.ema200
        
        # Fora da tendncia
        if ema9 > 0 and ema21 > 0 and ema50 > 0:
            trend_strength = min(1.0, (ema9 - ema21) / ema21 + (ema21 - ema50) / ema50)
        else:
            trend_strength = 0.0
        
        # Regime de tendncia
        if ema9 > ema21 > ema50 and ema50 > ema200:
            regime = "trending_up"
            trend_strength = min(1.0, trend_strength)
        elif ema9 < ema21 < ema50 and ema50 < ema200:
            regime = "trending_down"
            trend_strength = min(1.0, trend_strength)
        else:
            regime = "ranging"
            trend_strength = 1.0 - trend_strength  # Inverter para ranging
        
        # Regime de volatilidade
        volatility = indicators.volatility
        if volatility > 5.0:
            volatility_regime = "extreme"
        elif volatility > 3.0:
            volatility_regime = "high"
        elif volatility > 1.5:
            volatility_regime = "normal"
        else:
            volatility_regime = "low"
        
        return (regime, trend_strength, volatility_regime)
    
    def get_latest_indicators(self) -> Optional[IndicatorData]:
        """Retorna indicadores mais recentes"""
        if self.indicators_history:
            return self.indicators_history[-1]
        return None
    
    def get_market_state(self) -> MarketState:
        """Retorna estado atual do mercado"""
        return self.market_state
    
    def get_indicators_history(self, n: int = 100) -> list:
        """Retorna histrico de indicadores"""
        return list(self.indicators_history)[-n:]
    
    def get_stats(self) -> dict:
        """Retorna estatsticas do data engine"""
        return {
            "ticks_processed": self.ticks_processed,
            "errors": self.errors,
            "buffer_sizes": {
                "prices": len(self.calculator.prices),
                "indicators_history": len(self.indicators_history),
                "market_state_history": len(self.market_state_history)
            },
            "current_regime": self.market_state.regime,
            "current_volatility_regime": self.market_state.volatility_regime,
            "trend_strength": self.market_state.trend_strength
        }
    
    def register_callbacks(
        self,
        on_indicators_ready: Optional[Callable[[IndicatorData], None]] = None,
        on_market_state_updated: Optional[Callable[[MarketState], None]] = None,
        on_regime_change: Optional[Callable[[str], None]] = None
    ):
        """Registra callbacks para eventos do data engine"""
        if on_indicators_ready:
            self._on_indicators_ready = on_indicators_ready
        if on_market_state_updated:
            self._on_market_state_updated = on_market_state_updated
        if on_regime_change:
            self._on_regime_change = on_regime_change




