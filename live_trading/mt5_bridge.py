"""
MT5 Bridge - TCP Socket Server para comunicação com MetaTrader 5

Baseado na arquitetura legacy DubaiMatrixASI que FUNCIONA:
- Server socket non-blocking desde o início
- TCP_NODELAY aplicado IMEDIATAMENTE no accept
- Handshake não-bloqueante (ou sem handshake formal)
- Receive loop com polling simples (BlockingIOError + sleep 100us)
- Buffer de 32KB
- Thread lifecycle correto na reconexão
"""

import socket
import threading
import select
import time
import logging
from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from live_trading.logger import get_logger


class ConnectionState(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


@dataclass
class TickData:
    timestamp: datetime
    symbol: str
    bid: float
    ask: float
    volume: int = 0
    spread: float = 0.0
    atr: float = 0.0
    rsi: float = 0.0
    ema9: float = 0.0
    ema21: float = 0.0
    ema50: float = 0.0
    ema200: float = 0.0
    macd: float = 0.0
    macd_signal: float = 0.0


@dataclass
class BarData:
    timestamp: datetime
    symbol: str
    timeframe: str
    open: float
    high: float
    low: float
    close: float
    volume: int = 0


@dataclass
class AccountData:
    timestamp: datetime
    balance: float = 0.0
    equity: float = 0.0
    margin: float = 0.0
    free_margin: float = 0.0
    margin_level: float = 0.0
    profit: float = 0.0


@dataclass
class PositionData:
    timestamp: datetime
    ticket: int = 0
    symbol: str = ""
    order_type: str = ""
    volume: float = 0.0
    open_price: float = 0.0
    sl: float = 0.0
    tp: float = 0.0
    current_price: float = 0.0
    profit: float = 0.0
    swap: float = 0.0
    commission: float = 0.0
    magic: int = 0


class CircularBuffer:
    def __init__(self, maxlen=10000):
        self.maxlen = maxlen
        self.buffer = []
        self.lock = threading.Lock()

    def add(self, item):
        with self.lock:
            self.buffer.append(item)
            if len(self.buffer) > self.maxlen:
                self.buffer = self.buffer[-self.maxlen:]

    def get_all(self):
        with self.lock:
            return list(self.buffer)

    def __len__(self):
        return len(self.buffer)


class MT5Bridge:
    """
    Bridge TCP entre MT5 e Python.
    Arquitetura baseada no legacy DubaiMatrixASI que funciona.
    """

    def __init__(self, host="127.0.0.1", port=5555):
        self.host = host
        self.port = port
        self.logger = get_logger("MT5Bridge")

        # Sockets
        self.server_socket = None
        self.client_socket = None
        self.client_address = None

        # Estado
        self.state = ConnectionState.DISCONNECTED
        self._running = False
        self._accept_running = False
        self._receive_running = False

        # Threads
        self.accept_thread = None
        self.receive_thread = None
        self.heartbeat_thread = None

        # Callbacks
        self.on_tick_callback = None
        self.on_bar_callback = None
        self.on_account_callback = None
        self.on_position_callback = None
        self.on_error_callback = None
        self.on_connected_callback = None
        self.on_disconnected_callback = None

        # Dados
        self.ticks_buffer = CircularBuffer(10000)
        self.bars_buffer = CircularBuffer(1000)
        self.account_buffer = CircularBuffer(100)
        self.positions_buffer = CircularBuffer(100)
        self.logs_buffer = CircularBuffer(1000)

        # Stats
        self.stats = {
            "ticks_received": 0,
            "bars_received": 0,
            "signals_sent": 0,
            "errors": 0,
            "reconnections": 0,
            "start_time": None,
            "last_tick_time": None,
            "last_heartbeat": None,
            "latency_samples": [],
            "avg_latency_ms": 0.0,
        }

    def on_tick(self, callback):
        self.on_tick_callback = callback
        return self

    def on_bar(self, callback):
        self.on_bar_callback = callback
        return self

    def on_account(self, callback):
        self.on_account_callback = callback
        return self

    def on_position(self, callback):
        self.on_position_callback = callback
        return self

    def on_error(self, callback):
        self.on_error_callback = callback
        return self

    def on_connected(self, callback):
        self.on_connected_callback = callback
        return self

    def on_disconnected(self, callback):
        self.on_disconnected_callback = callback
        return self

    def start(self):
        """Inicia servidor TCP - Estilo legacy: non-blocking desde início"""
        self.logger.info(f"[MT5_BRIDGE] Starting TCP socket server on {self.host}:{self.port}")

        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(10)  # Backlog 10 como legacy
        self.server_socket.setblocking(False)  # Non-blocking IMEDIATO

        self.logger.info(f"[MT5_BRIDGE] Listening on {self.host}:{self.port}")

        self._running = True
        self._accept_running = True
        self._receive_running = False
        self.stats["start_time"] = datetime.now()

        self.accept_thread = threading.Thread(target=self._accept_loop, daemon=True)
        self.accept_thread.start()

        self.state = ConnectionState.CONNECTING

    def stop(self):
        """Para servidor"""
        self.logger.info("[MT5_BRIDGE] Stopping server...")
        self._running = False
        self._accept_running = False
        self._receive_running = False
        self.state = ConnectionState.DISCONNECTED

        if self.client_socket:
            try:
                self.client_socket.close()
            except:
                pass
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass

        self.logger.info("[MT5_BRIDGE] Server stopped")

    # ========== ACCEPT LOOP (Estilo legacy) ==========

    def _accept_loop(self):
        """
        Loop de aceitação - Estilo legacy bridge.py:
        - Só aceita se NÃO houver conexão ativa
        - Se já existe conexão, apenas dorme
        - Configura socket IMEDIATAMENTE no accept
        """
        while self._accept_running:
            try:
                if self.client_socket is None:
                    # Tentar aceitar nova conexão
                    try:
                        client_sock, addr = self.server_socket.accept()

                        # Configurar IMEDIATAMENTE (como legacy)
                        client_sock.setblocking(False)
                        client_sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

                        self.client_socket = client_sock
                        self.client_address = addr
                        self.stats["reconnections"] += 1
                        self.state = ConnectionState.CONNECTED

                        self.logger.info(f"[MT5_BRIDGE] MT5 Connected: {addr}")

                        # Iniciar receive thread para este client
                        self._receive_running = True
                        self.receive_thread = threading.Thread(
                            target=self._receive_loop,
                            daemon=True
                        )
                        self.receive_thread.start()

                        # Heartbeat thread
                        self.heartbeat_thread = threading.Thread(
                            target=self._heartbeat_loop,
                            daemon=True
                        )
                        self.heartbeat_thread.start()

                        # Callbacks
                        if self.on_connected_callback:
                            self.on_connected_callback()

                        # Handshake não-bloqueante
                        self._handle_handshake()

                    except BlockingIOError:
                        time.sleep(0.1)  # 100ms como legacy
                    except Exception as e:
                        self.logger.error(f"[MT5_BRIDGE] Accept error: {e}")
                        self.stats["errors"] += 1
                        time.sleep(1)
                else:
                    # Já conectado - esperar
                    time.sleep(1)

            except Exception as e:
                self.logger.error(f"[MT5_BRIDGE] Accept loop error: {e}")
                self.stats["errors"] += 1
                time.sleep(1)

    # ========== HANDSHAKE (Não-bloqueante) ==========

    def _handle_handshake(self):
        """
        Handshake não-bloqueante - legado não tem handshake formal.
        Apenas verifica se MT5 enviou HANDSHAKE nos primeiros dados.
        """
        try:
            # Tentar ler handshake sem bloquear
            # MT5 pode enviar HANDSHAKE + dados juntos
            import select
            readable, _, _ = select.select([self.client_socket], [], [], 2.0)

            if readable:
                data = self.client_socket.recv(4096)
                if data:
                    text = data.decode('utf-8', errors='ignore')
                    if 'HANDSHAKE' in text:
                        self.logger.info(f"[MT5_BRIDGE] Handshake received: {text[:100]}")

                        # Enviar ack
                        ack = "HANDSHAKE_OK|ForexQuantumBot_Python|v3.00|20260413\n"
                        try:
                            self.client_socket.send(ack.encode('utf-8'))
                        except:
                            pass

                        # Processar qualquer dado extra após handshake
                        if '\n' in text:
                            lines = text.split('\n')
                            for line in lines[1:]:  # Pular linha do handshake
                                line = line.strip()
                                if line:
                                    self._process_message(line)

                        self.logger.info("[MT5_BRIDGE] Handshake OK sent")
                        return True

            # Se não recebeu handshake, continuar mesmo assim (legacy não exige)
            self.logger.info("[MT5_BRIDGE] No handshake detected, proceeding anyway (legacy mode)")
            return True

        except Exception as e:
            self.logger.warning(f"[MT5_BRIDGE] Handshake error: {e}")
            return True  # Continuar mesmo com erro

    # ========== RECEIVE LOOP (Estilo legacy) ==========

    def _receive_loop(self):
        """
        Loop de recebimento - Estilo legacy zmq_bridge:
        - Polling com BlockingIOError
        - Sleep de 100us quando sem dados
        - Buffer de 32KB
        - Logging mínimo no caminho crítico
        """
        buffer = ""

        while self._receive_running and self._running:
            try:
                try:
                    data = self.client_socket.recv(32768)  # 32KB como legacy
                except BlockingIOError:
                    time.sleep(0.0001)  # 100 MICROSEGUNDOS como legacy!
                    continue
                except Exception:
                    # Socket error - conexão fechada
                    break

                if not data:
                    # MT5 fechou a conexão
                    self.logger.warning("[MT5_BRIDGE] Connection closed by MT5")
                    break

                # Decodificar
                buffer += data.decode('utf-8', errors='ignore')

                # Limitar tamanho do buffer (segurança)
                if len(buffer) > 1_000_000:
                    self.logger.error("[MT5_BRIDGE] Buffer overflow, clearing")
                    buffer = ""
                    self.stats["errors"] += 1
                    continue

                # Processar mensagens completas
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    line = line.strip()
                    if line:
                        self._process_message(line)

            except Exception as e:
                self.logger.error(f"[MT5_BRIDGE] Receive error: {e}")
                self.stats["errors"] += 1
                break

        # Cleanup quando thread termina
        self._handle_disconnect()

    # ========== HEARTBEAT ==========

    def _heartbeat_loop(self):
        """Monitora heartbeat do MT5 - NÃO envia (legacy não envia)"""
        while self._running and self.state == ConnectionState.CONNECTED:
            try:
                # Verificar se MT5 ainda envia heartbeat
                if self.stats.get("last_heartbeat"):
                    time_since = (datetime.now() - self.stats["last_heartbeat"]).total_seconds()
                    if time_since > 30:
                        self.logger.warning(f"[MT5_BRIDGE] No heartbeat for {time_since:.0f}s")

                time.sleep(2)
            except Exception as e:
                self.logger.error(f"[MT5_BRIDGE] Heartbeat monitor error: {e}")
                time.sleep(1)

    # ========== PROCESS MESSAGES ==========

    def _process_message(self, message: str):
        """Processa mensagem do MT5"""
        try:
            parts = message.split('|')
            if len(parts) < 2:
                return

            command = parts[0]

            if command == "TICK":
                self._process_tick_data(parts)
            elif command == "BAR":
                self._process_bar_data(parts)
            elif command == "ACCOUNT":
                self._process_account_data(parts)
            elif command == "POSITIONS":
                self._process_positions_data(parts)
            elif command == "ORDER_FILLED":
                self._process_order_filled(parts)
            elif command == "ERROR":
                self._process_mt5_error(parts)
            elif command == "HEARTBEAT":
                self.stats["last_heartbeat"] = datetime.now()

        except Exception as e:
            self.stats["errors"] += 1

    def _process_tick_data(self, parts: list):
        try:
            tick = TickData(
                timestamp=datetime.now(),
                symbol=parts[1] if len(parts) > 1 else "",
                bid=float(parts[2]) if len(parts) > 2 else 0.0,
                ask=float(parts[3]) if len(parts) > 3 else 0.0,
                volume=int(parts[4]) if len(parts) > 4 else 0,
                spread=float(parts[5]) if len(parts) > 5 else 0.0,
                atr=float(parts[6]) if len(parts) > 6 else 0.0,
                rsi=float(parts[7]) if len(parts) > 7 else 0.0,
                ema9=float(parts[8]) if len(parts) > 8 else 0.0,
                ema21=float(parts[9]) if len(parts) > 9 else 0.0,
                ema50=float(parts[10]) if len(parts) > 10 else 0.0,
                ema200=float(parts[11]) if len(parts) > 11 else 0.0,
                macd=float(parts[12]) if len(parts) > 12 else 0.0,
                macd_signal=float(parts[13]) if len(parts) > 13 else 0.0,
            )

            self.ticks_buffer.add(tick)
            self.stats["ticks_received"] += 1
            self.stats["last_tick_time"] = datetime.now()

            if self.on_tick_callback:
                self.on_tick_callback(tick)

        except Exception as e:
            self.stats["errors"] += 1

    def _process_bar_data(self, parts: list):
        try:
            bar = BarData(
                timestamp=datetime.now(),
                symbol=parts[1] if len(parts) > 1 else "",
                timeframe=parts[2] if len(parts) > 2 else "",
                open=float(parts[3]) if len(parts) > 3 else 0.0,
                high=float(parts[4]) if len(parts) > 4 else 0.0,
                low=float(parts[5]) if len(parts) > 5 else 0.0,
                close=float(parts[6]) if len(parts) > 6 else 0.0,
                volume=int(parts[7]) if len(parts) > 7 else 0,
            )
            self.bars_buffer.add(bar)
            self.stats["bars_received"] += 1

            if self.on_bar_callback:
                self.on_bar_callback(bar)
        except Exception as e:
            self.stats["errors"] += 1

    def _process_account_data(self, parts: list):
        try:
            account = AccountData(
                timestamp=datetime.now(),
                balance=float(parts[1]) if len(parts) > 1 else 0.0,
                equity=float(parts[2]) if len(parts) > 2 else 0.0,
                margin=float(parts[3]) if len(parts) > 3 else 0.0,
                free_margin=float(parts[4]) if len(parts) > 4 else 0.0,
                margin_level=float(parts[5]) if len(parts) > 5 else 0.0,
                profit=float(parts[6]) if len(parts) > 6 else 0.0,
            )
            self.account_buffer.add(account)
            if self.on_account_callback:
                self.on_account_callback(account)
        except Exception as e:
            self.stats["errors"] += 1

    def _process_positions_data(self, parts: list):
        try:
            count = int(parts[1]) if len(parts) > 1 else 0
            idx = 2
            for _ in range(count):
                if idx + 12 > len(parts):
                    break
                position = PositionData(
                    timestamp=datetime.now(),
                    ticket=int(parts[idx]) if len(parts) > idx else 0,
                    symbol=parts[idx+1] if len(parts) > idx+1 else "",
                    order_type=parts[idx+2] if len(parts) > idx+2 else "",
                    volume=float(parts[idx+3]) if len(parts) > idx+3 else 0.0,
                    open_price=float(parts[idx+4]) if len(parts) > idx+4 else 0.0,
                    sl=float(parts[idx+5]) if len(parts) > idx+5 else 0.0,
                    tp=float(parts[idx+6]) if len(parts) > idx+6 else 0.0,
                    current_price=float(parts[idx+7]) if len(parts) > idx+7 else 0.0,
                    profit=float(parts[idx+8]) if len(parts) > idx+8 else 0.0,
                    swap=float(parts[idx+9]) if len(parts) > idx+9 else 0.0,
                    commission=float(parts[idx+10]) if len(parts) > idx+10 else 0.0,
                    magic=int(parts[idx+11]) if len(parts) > idx+11 else 0,
                )
                self.positions_buffer.add(position)
                idx += 12

            if self.on_position_callback:
                self.on_position_callback(position)
        except Exception as e:
            self.stats["errors"] += 1

    def _process_order_filled(self, parts: list):
        pass

    def _process_mt5_error(self, parts: list):
        self.stats["errors"] += 1
        if self.on_error_callback:
            self.on_error_callback(parts[2] if len(parts) > 2 else "Unknown MT5 error")

    # ========== DISCONNECT ==========

    def _handle_disconnect(self):
        """
        Disconnect simples - Estilo legacy:
        Apenas limpa referência, accept thread cuida da reconexão.
        """
        old_state = self.state
        self.state = ConnectionState.DISCONNECTED
        self._receive_running = False

        if self.client_socket:
            try:
                self.client_socket.close()
            except:
                pass
            self.client_socket = None

        if old_state == ConnectionState.CONNECTED:
            self.logger.info("[MT5_BRIDGE] Disconnected, accept thread will handle reconnect")
            if self.on_disconnected_callback:
                self.on_disconnected_callback()

    # ========== UTILS ==========

    def get_stats(self) -> dict:
        stats = dict(self.stats)
        if self.stats.get("start_time"):
            uptime = (datetime.now() - self.stats["start_time"]).total_seconds()
            stats["uptime_seconds"] = int(uptime)
        return stats

    def is_connected(self) -> bool:
        return self.state == ConnectionState.CONNECTED and self.client_socket is not None

    def send_signal(self, signal: str):
        """Envia sinal para MT5"""
        if self.client_socket and self.state == ConnectionState.CONNECTED:
            try:
                self.client_socket.send((signal + "\n").encode('utf-8'))
                self.stats["signals_sent"] += 1
            except Exception as e:
                self.stats["errors"] += 1
                self.logger.error(f"[MT5_BRIDGE] Send error: {e}")
