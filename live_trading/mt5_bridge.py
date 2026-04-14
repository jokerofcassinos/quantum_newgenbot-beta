"""
MT5 Bridge - TCP Socket Server para comunicação ultra-rápida com MetaTrader 5

Este módulo implementa um servidor TCP socket que se comunica com o Expert Advisor
no MetaTrader 5. Substitui o antigo sistema de polling por arquivos JSON/CSV.

Protocolo: Pipe-delimited
Latência alvo: <50ms
Porta padrão: 5555

Herança do projeto legacy DubaiMatrixASI:
- TCP socket nativo (herdado de mt5_bridge.py legacy)
- Protocolo pipe-delimited
- Reconexão automática com fallback
- Heartbeat para keep-alive
- Buffers circulares para auditoria
"""

import socket
import threading
import queue
import time
import logging
from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
import traceback

# Importar sistema de logs do projeto
from live_trading.logger import get_logger


class ConnectionState(Enum):
    """Estados possíveis da conexão com MT5"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    HANDSHAKING = "handshaking"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    ERROR = "error"


@dataclass
class TickData:
    """Dados de tick recebidos do MT5"""
    timestamp: datetime
    symbol: str
    bid: float
    ask: float
    volume: int
    spread: float
    atr: float = 0.0
    rsi: float = 0.0
    ema9: float = 0.0
    ema21: float = 0.0
    ema50: float = 0.0
    ema200: float = 0.0
    macd: float = 0.0
    macd_signal: float = 0.0
    raw_data: str = ""


@dataclass
class AccountData:
    """Dados da conta recebidos do MT5"""
    timestamp: datetime
    balance: float = 0.0
    equity: float = 0.0
    margin: float = 0.0
    free_margin: float = 0.0
    margin_level: float = 0.0
    profit: float = 0.0


@dataclass
class PositionData:
    """Dados de posição recebidos do MT5"""
    timestamp: datetime
    ticket: int = 0
    symbol: str = ""
    order_type: str = ""  # BUY ou SELL
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
    """Buffer circular para armazen dados de mercado"""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.buffer = []
        self.lock = threading.Lock()
    
    def add(self, item: Any):
        """Adiciona item ao buffer"""
        with self.lock:
            self.buffer.append(item)
            if len(self.buffer) > self.max_size:
                self.buffer.pop(0)
    
    def get_latest(self, n: int = 1) -> list:
        """Retorna os n itens mais recentes"""
        with self.lock:
            return self.buffer[-n:] if n <= len(self.buffer) else self.buffer[:]
    
    def get_all(self) -> list:
        """Retorna todos os itens"""
        with self.lock:
            return self.buffer[:]
    
    def size(self) -> int:
        """Retorna tamanho atual do buffer"""
        with self.lock:
            return len(self.buffer)
    
    def clear(self):
        """Limpa o buffer"""
        with self.lock:
            self.buffer.clear()


class MT5Bridge:
    """
    TCP Socket Bridge para comunicação bidirecional com MT5
    
    Este é o coração da comunicação entre o bot Python e o MetaTrader 5.
    Usa TCP sockets nativos para comunicação ultra-rápida (sub-50ms).
    
    Herança do legacy:
    - TCP socket server (porta 5555)
    - Protocolo pipe-delimited
    - Handshake de conexão
    - Heartbeat automático
    - Reconexão com fallback
    - Buffers circulares
    """
    
    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 5555,
        timeout: int = 3000,
        max_reconnect_attempts: int = 5,
        reconnect_delay: float = 1.0,
        heartbeat_interval: float = 1.0,
        buffer_size: int = 1000
    ):
        # Configuração do socket
        self.host = host
        self.port = port
        self.timeout = timeout  # ms
        self.max_reconnect_attempts = max_reconnect_attempts
        self.reconnect_delay = reconnect_delay  # segundos
        self.heartbeat_interval = heartbeat_interval  # segundos
        
        # Estado da conexão
        self.state = ConnectionState.DISCONNECTED
        self.server_socket: Optional[socket.socket] = None
        self.client_socket: Optional[socket.socket] = None
        self.client_address: Optional[tuple] = None
        
        # Threads
        self.accept_thread: Optional[threading.Thread] = None
        self.receive_thread: Optional[threading.Thread] = None
        self.heartbeat_thread: Optional[threading.Thread] = None
        self._running = False
        
        # Buffers circulares
        self.ticks_buffer = CircularBuffer(buffer_size)
        self.bars_buffer = CircularBuffer(500)
        self.account_buffer = CircularBuffer(100)
        self.positions_buffer = CircularBuffer(50)
        self.logs_buffer = CircularBuffer(5000)
        
        # Queues para comunicação entre threads
        self.data_queue = queue.Queue()
        self.signal_queue = queue.Queue()
        
        # Última atualização
        self.last_heartbeat: Optional[datetime] = None
        self.last_tick: Optional[datetime] = None
        self.last_signal_sent: Optional[datetime] = None
        
        # Callbacks
        self.on_tick_callback: Optional[Callable[[TickData], None]] = None
        self.on_bar_callback: Optional[Callable[[dict], None]] = None
        self.on_account_callback: Optional[Callable[[AccountData], None]] = None
        self.on_position_callback: Optional[Callable[[PositionData], None]] = None
        self.on_error_callback: Optional[Callable[[str], None]] = None
        self.on_connected_callback: Optional[Callable[[], None]] = None
        self.on_disconnected_callback: Optional[Callable[[], None]] = None
        
        # Estatísticas
        self.stats = {
            "ticks_received": 0,
            "signals_sent": 0,
            "errors": 0,
            "reconnections": 0,
            "start_time": None,
            "last_error": None,
            "avg_latency_ms": 0.0,
            "latency_samples": []
        }
        
        # Logger - usar sistema de logs do projeto
        self.logger = get_logger("MT5Bridge")
        
        # Buffer inicial para dados recebidos durante handshake
        self._initial_buffer = ""
    
    def register_callbacks(
        self,
        on_tick: Optional[Callable[[TickData], None]] = None,
        on_bar: Optional[Callable[[dict], None]] = None,
        on_account: Optional[Callable[[AccountData], None]] = None,
        on_position: Optional[Callable[[PositionData], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
        on_connected: Optional[Callable[[], None]] = None,
        on_disconnected: Optional[Callable[[], None]] = None
    ):
        """Registra callbacks para eventos do MT5"""
        if on_tick:
            self.on_tick_callback = on_tick
        if on_bar:
            self.on_bar_callback = on_bar
        if on_account:
            self.on_account_callback = on_account
        if on_position:
            self.on_position_callback = on_position
        if on_error:
            self.on_error_callback = on_error
        if on_connected:
            self.on_connected_callback = on_connected
        if on_disconnected:
            self.on_disconnected_callback = on_disconnected
    
    def start(self):
        """Inicia o servidor TCP socket"""
        self.logger.info(f"[MT5_BRIDGE] Starting TCP socket server on {self.host}:{self.port}")
        
        try:
            # Criar socket server
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            # Removido TCP_NODELAY do server socket - causa problemas com MQL5
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(1)
            self.server_socket.settimeout(1.0)  # Timeout para permitir shutdown
            
            self.logger.info(f"[MT5_BRIDGE] Listening on {self.host}:{self.port}")
            
            # Iniciar thread de aceitação
            self._running = True
            self.stats["start_time"] = datetime.now()
            self.accept_thread = threading.Thread(target=self._accept_loop, daemon=True)
            self.accept_thread.start()
            
            self.state = ConnectionState.CONNECTING
            
        except Exception as e:
            self.logger.error(f"[MT5_BRIDGE] Failed to start server: {e}")
            self.state = ConnectionState.ERROR
            if self.on_error_callback:
                self.on_error_callback(f"Failed to start server: {e}")
            raise
    
    def stop(self):
        """Para o servidor e desconecta"""
        self.logger.info("[MT5_BRIDGE] Stopping server...")
        self._running = False
        self.state = ConnectionState.DISCONNECTED
        
        # Fechar sockets
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
    
    def _accept_loop(self):
        """Loop para aceitar conexões do MT5"""
        while self._running:
            try:
                client_socket, client_address = self.server_socket.accept()

                # Se já existe conexão, fechar ANTES de aceitar nova (como o legacy)
                if self.client_socket is not None:
                    self.logger.info(f"[MT5_BRIDGE] Closing old connection to accept new from {client_address}")
                    try:
                        self.client_socket.close()
                    except:
                        pass
                    self.client_socket = None
                    self.state = ConnectionState.CONNECTING

                self.logger.info(f"[MT5_BRIDGE] MT5 connected from {client_address}")
                self.client_socket = client_socket
                self.client_address = client_address

                # Enable keepalive on client socket
                self.client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                
                # Configurar socket do cliente com timeout para handshake
                self.client_socket.settimeout(5.0)

                # Iniciar handshake
                self.state = ConnectionState.HANDSHAKING
                if self._handle_handshake():
                    self.state = ConnectionState.CONNECTED
                    self.logger.info("[MT5_BRIDGE] Handshake successful - CONNECTED")

                    # Enable keepalive + nodelay on client socket AFTER handshake
                    try:
                        self.client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                        self.client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                    except:
                        pass

                    # Set socket to non-blocking (select() handles timeout)
                    self.client_socket.setblocking(False)

                    # Iniciar threads
                    self.receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
                    self.receive_thread.start()

                    self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
                    self.heartbeat_thread.start()

                    if self.on_connected_callback:
                        self.on_connected_callback()
                else:
                    self.logger.error("[MT5_BRIDGE] Handshake failed")
                    self.client_socket.close()
                    self.client_socket = None
                    self.state = ConnectionState.CONNECTING

            except socket.timeout:
                continue
            except Exception as e:
                if self._running:
                    self.logger.error(f"[MT5_BRIDGE] Accept error: {e}")
                    self.stats["errors"] += 1
                    time.sleep(1)

    def _handle_handshake(self) -> bool:
        """Processa handshake com MT5"""
        try:
            self.logger.info("[MT5_BRIDGE] Waiting for handshake...")
            data = self.client_socket.recv(4096).decode('utf-8', errors='ignore')

            if not data:
                self.logger.error("[MT5_BRIDGE] Empty handshake")
                return False

            self.logger.info(f"[MT5_BRIDGE] Handshake received: {data}")

            # Verificar se é handshake válido
            if "HANDSHAKE" in data:
                # Enviar ack
                ack = "HANDSHAKE_OK|ForexQuantumBot_Python|v3.00|20260413"
                self.client_socket.send(ack.encode('utf-8'))
                self.logger.info(f"[MT5_BRIDGE] Handshake ack sent: {ack}")
                
                # Salvar qualquer dado extra recebido após handshake para o receive loop
                if '\n' in data:
                    # Pegar dados após o handshake
                    parts = data.split('\n', 1)
                    if len(parts) > 1 and parts[1].strip():
                        self._initial_buffer = parts[1]
                        self.logger.info(f"[MT5_BRIDGE] Saved initial buffer: {self._initial_buffer[:50]}")
                    else:
                        self._initial_buffer = ""
                else:
                    self._initial_buffer = ""
                
                return True
            else:
                self.logger.error(f"[MT5_BRIDGE] Invalid handshake: {data}")
                return False

        except Exception as e:
            self.logger.error(f"[MT5_BRIDGE] Handshake error: {e}")
            return False
    
    def _receive_loop(self):
        """Loop para receber dados do MT5 continuamente"""
        # Começar com buffer inicial do handshake (se houver)
        buffer = self._initial_buffer
        empty_count = 0
        
        self.logger.info(f"[MT5_BRIDGE] Receive loop started, initial buffer: {len(buffer)} bytes")
        
        # Processar buffer inicial ANTES de chamar recv()
        if buffer:
            self.logger.info(f"[MT5_BRIDGE] Processing initial buffer: {buffer[:100]}...")
            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                line = line.strip()
                if line:
                    self.logger.debug(f"[MT5_BRIDGE] Processing initial message: {line[:50]}...")
                    self._process_message(line)
        
        self.logger.info("[MT5_BRIDGE] Starting receive loop - calling recv()...")

        while self._running and self.state == ConnectionState.CONNECTED:
            try:
                # Usar select() para verificar se há dados (1s timeout)
                import select
                readable, _, _ = select.select([self.client_socket], [], [], 1.0)

                if not readable:
                    # Timeout do select - sem dados disponíveis
                    continue

                # Socket pronto para leitura
                try:
                    data = self.client_socket.recv(8192)
                except BlockingIOError:
                    # Non-blocking socket sem dados - esperado
                    continue
                    
                if len(data) > 0:
                    self.logger.info(f"[MT5_BRIDGE] recv() got {len(data)} bytes: {data[:100]}")
                else:
                    self.logger.warning("[MT5_BRIDGE] recv() got 0 bytes")

                if not data:
                    # recv() retorna 0 bytes quando o peer FECHOU a conexao
                    self.logger.warning("[MT5_BRIDGE] Connection closed by MT5 (recv returned 0)")
                    self._handle_disconnect()
                    break

                # Decodificar
                buffer += data.decode('utf-8', errors='ignore')

                # Processar mensagens (delimitadas por newline)
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    line = line.strip()

                    if line:
                        self._process_message(line)

            except socket.timeout:
                # Timeout é esperado, continuar
                continue
            except ConnectionResetError:
                self.logger.error("[MT5_BRIDGE] Connection reset by MT5")
                self._handle_disconnect()
                break
            except Exception as e:
                if self._running:
                    self.logger.error(f"[MT5_BRIDGE] Receive error: {e}")
                    self.stats["errors"] += 1
                    time.sleep(0.1)
                    time.sleep(0.1)
    
    def _process_message(self, message: str):
        """Processa uma mensagem recebida do MT5"""
        try:
            # Log da mensagem recebida
            self.logs_buffer.add({
                "timestamp": datetime.now(),
                "direction": "RECV",
                "message": message[:200]  # Limitar tamanho
            })
            
            # Parse do protocolo pipe-delimited
            parts = message.split('|')
            
            if len(parts) < 2:
                self.logger.warning(f"[MT5_BRIDGE] Invalid message format: {message}")
                return
            
            command = parts[0]
            
            # Medir latência (se tiver timestamp na mensagem)
            receive_time = time.time()
            
            if command == "TICK":
                # TICK|symbol|bid|ask|volume|spread|atr|rsi|ema9|ema21|ema50|ema200|macd|macd_signal|timestamp
                self._process_tick_data(parts, receive_time)
                
            elif command == "BAR":
                # BAR|symbol|timeframe|open|high|low|close|volume|timestamp
                self._process_bar_data(parts)
                
            elif command == "ACCOUNT":
                # ACCOUNT|balance|equity|margin|free_margin|margin_level|profit|timestamp
                self._process_account_data(parts)
                
            elif command == "POSITIONS":
                # POSITIONS|count|ticket|symbol|type|volume|open_price|sl|tp|current_price|profit|swap|commission|magic|...
                self._process_positions_data(parts)
                
            elif command == "ORDER_FILLED":
                # ORDER_FILLED|ticket|symbol|type|volume|price|sl|tp|timestamp
                self._process_order_filled(parts)
                
            elif command == "ERROR":
                # ERROR|error_code|error_message|timestamp
                self._process_mt5_error(parts)
                
            elif command == "HEARTBEAT":
                # HEARTBEAT|timestamp
                self.last_heartbeat = datetime.now()
                
            else:
                self.logger.warning(f"[MT5_BRIDGE] Unknown command: {command}")
                
        except Exception as e:
            self.logger.error(f"[MT5_BRIDGE] Error processing message: {e}")
            self.logger.error(f"[MT5_BRIDGE] Message: {message}")
            self.stats["errors"] += 1
    
    def _process_tick_data(self, parts: list, receive_time: float):
        """Processa dados de tick"""
        try:
            self.logger.info(f"[MT5_BRIDGE] Processing tick data: {len(parts)} fields")
            
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
            
            self.logger.info(f"[MT5_BRIDGE] Tick parsed: {tick.symbol} bid={tick.bid:.2f} ask={tick.ask:.2f}")
            
            # Adicionar ao buffer
            self.ticks_buffer.add(tick)
            self.last_tick = tick.timestamp
            
            # Estatísticas
            self.stats["ticks_received"] += 1
            
            # Calcular latência se tiver timestamp
            if len(parts) > 14:
                try:
                    send_time = datetime.fromisoformat(parts[14])
                    latency_ms = (tick.timestamp - send_time).total_seconds() * 1000
                    self.stats["latency_samples"].append(latency_ms)
                    # Manter apenas últimos 100 samples
                    if len(self.stats["latency_samples"]) > 100:
                        self.stats["latency_samples"] = self.stats["latency_samples"][-100:]
                    self.stats["avg_latency_ms"] = sum(self.stats["latency_samples"]) / len(self.stats["latency_samples"])
                    self.logger.info(f"[MT5_BRIDGE] Latency: {latency_ms:.2f}ms")
                except Exception as e:
                    self.logger.warning(f"[MT5_BRIDGE] Failed to parse timestamp: {e}")
            
            # Callback
            if self.on_tick_callback:
                self.logger.info("[MT5_BRIDGE] Calling on_tick callback...")
                self.on_tick_callback(tick)
                self.logger.info("[MT5_BRIDGE] on_tick callback completed")
            
            self.logger.info(f"[MT5_BRIDGE] Tick processing complete. Total ticks: {self.stats['ticks_received']}")
            
        except Exception as e:
            self.logger.error(f"[MT5_BRIDGE] Error processing tick: {e}")
            import traceback
            self.logger.error(f"[MT5_BRIDGE] Traceback: {traceback.format_exc()}")
            self.stats["errors"] += 1
    
    def _process_bar_data(self, parts: list):
        """Processa dados de barra"""
        try:
            bar = {
                "timestamp": datetime.now(),
                "symbol": parts[1] if len(parts) > 1 else "",
                "timeframe": parts[2] if len(parts) > 2 else "",
                "open": float(parts[3]) if len(parts) > 3 else 0.0,
                "high": float(parts[4]) if len(parts) > 4 else 0.0,
                "low": float(parts[5]) if len(parts) > 5 else 0.0,
                "close": float(parts[6]) if len(parts) > 6 else 0.0,
                "volume": int(parts[7]) if len(parts) > 7 else 0,
            }
            
            self.bars_buffer.add(bar)
            
            if self.on_bar_callback:
                self.on_bar_callback(bar)
                
        except Exception as e:
            self.logger.error(f"[MT5_BRIDGE] Error processing bar: {e}")
            self.stats["errors"] += 1
    
    def _process_account_data(self, parts: list):
        """Processa dados da conta"""
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
            self.logger.error(f"[MT5_BRIDGE] Error processing account: {e}")
            self.stats["errors"] += 1
    
    def _process_positions_data(self, parts: list):
        """Processa dados de posições"""
        try:
            # Formato: POSITIONS|count|ticket|symbol|type|volume|open_price|sl|tp|current_price|profit|swap|commission|magic|...
            count = int(parts[1]) if len(parts) > 1 else 0
            
            # Posições podem ter múltiplos conjuntos de dados
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
            self.logger.error(f"[MT5_BRIDGE] Error processing positions: {e}")
            self.stats["errors"] += 1
    
    def _process_order_filled(self, parts: list):
        """Processa confirmação de ordem executada"""
        try:
            ticket = parts[1] if len(parts) > 1 else "unknown"
            symbol = parts[2] if len(parts) > 2 else ""
            order_type = parts[3] if len(parts) > 3 else ""
            volume = parts[4] if len(parts) > 4 else "0"
            price = parts[5] if len(parts) > 5 else "0"
            
            self.logger.info(f"[MT5_BRIDGE] ORDER FILLED: {order_type} {volume} {symbol} @ {price} (ticket={ticket})")
            
            # Log no buffer
            self.logs_buffer.add({
                "timestamp": datetime.now(),
                "type": "ORDER_FILLED",
                "ticket": ticket,
                "symbol": symbol,
                "type": order_type,
                "volume": volume,
                "price": price
            })
            
        except Exception as e:
            self.logger.error(f"[MT5_BRIDGE] Error processing order filled: {e}")
            self.stats["errors"] += 1
    
    def _process_mt5_error(self, parts: list):
        """Processa erro do MT5"""
        try:
            error_code = parts[1] if len(parts) > 1 else "unknown"
            error_message = parts[2] if len(parts) > 2 else "unknown error"
            
            self.logger.error(f"[MT5_BRIDGE] MT5 Error {error_code}: {error_message}")
            self.stats["errors"] += 1
            
            if self.on_error_callback:
                self.on_error_callback(f"MT5 Error {error_code}: {error_message}")
                
        except Exception as e:
            self.logger.error(f"[MT5_BRIDGE] Error processing MT5 error: {e}")
    
    def _heartbeat_loop(self):
        """Envia heartbeat periódico para MT5 - DESABILITADO pois MT5 já envia"""
        # MT5 envia heartbeat a cada 1 segundo, não precisamos enviar também
        # Isso evita race condition no socket
        self.logger.info("[MT5_BRIDGE] Heartbeat loop started - monitoring only (no send)")
        
        while self._running and self.state == ConnectionState.CONNECTED:
            try:
                # Apenas verificar se MT5 está enviando heartbeat
                if self.last_heartbeat:
                    time_since_hb = (datetime.now() - self.last_heartbeat).total_seconds()
                    if time_since_hb > 15:
                        self.logger.warning(f"[MT5_BRIDGE] No heartbeat from MT5 for {time_since_hb:.0f}s")
                
                time.sleep(self.heartbeat_interval)
                
            except Exception as e:
                self.logger.error(f"[MT5_BRIDGE] Heartbeat monitor error: {e}")
                time.sleep(1)
    
    def _handle_disconnect(self):
        """Trata desconexão e tenta reconectar"""
        self.state = ConnectionState.DISCONNECTED
        
        if self.on_disconnected_callback:
            self.on_disconnected_callback()
        
        # Tentar reconectar
        self._reconnect()
    
    def _reconnect(self):
        """Tenta reconectar ao MT5"""
        if not self._running:
            return
        
        self.state = ConnectionState.RECONNECTING
        self.logger.info("[MT5_BRIDGE] Attempting to reconnect...")
        
        for attempt in range(1, self.max_reconnect_attempts + 1):
            try:
                self.logger.info(f"[MT5_BRIDGE] Reconnection attempt {attempt}/{self.max_reconnect_attempts}")
                
                # Fechar socket antigo
                if self.client_socket:
                    self.client_socket.close()
                    self.client_socket = None
                
                # Aguardar antes de tentar
                time.sleep(self.reconnect_delay)
                
                # Notificar reconexão
                self.stats["reconnections"] += 1
                
                # Voltar ao estado de conexão
                self.state = ConnectionState.CONNECTING
                
                # O accept_loop vai cuidar de aceitar nova conexão
                return
                
            except Exception as e:
                self.logger.error(f"[MT5_BRIDGE] Reconnection attempt {attempt} failed: {e}")
                time.sleep(self.reconnect_delay)
        
        self.logger.error("[MT5_BRIDGE] All reconnection attempts failed")
        self.state = ConnectionState.ERROR
        
        if self.on_error_callback:
            self.on_error_callback("All reconnection attempts failed")
    
    def send_signal(self, signal_type: str, **kwargs) -> bool:
        """
        Envia sinal de trading para o MT5
        
        Args:
            signal_type: BUY, SELL, CLOSE, MODIFY
            **kwargs: Parâmetros do sinal (lote, SL, TP, etc)
        
        Returns:
            True se enviado com sucesso, False caso contrário
        """
        if self.state != ConnectionState.CONNECTED or not self.client_socket:
            self.logger.error("[MT5_BRIDGE] Cannot send signal: not connected")
            return False
        
        try:
            # Montar mensagem
            if signal_type == "BUY":
                # BUY|symbol|lot|sl|tp|magic|timestamp
                msg = (
                    f"BUY|"
                    f"{kwargs.get('symbol', 'BTCUSD')}|"
                    f"{kwargs.get('lot', 0.01)}|"
                    f"{kwargs.get('sl', 0.0)}|"
                    f"{kwargs.get('tp', 0.0)}|"
                    f"{kwargs.get('magic', 20260412)}|"
                    f"{datetime.now().isoformat()}"
                )
            
            elif signal_type == "SELL":
                # SELL|symbol|lot|sl|tp|magic|timestamp
                msg = (
                    f"SELL|"
                    f"{kwargs.get('symbol', 'BTCUSD')}|"
                    f"{kwargs.get('lot', 0.01)}|"
                    f"{kwargs.get('sl', 0.0)}|"
                    f"{kwargs.get('tp', 0.0)}|"
                    f"{kwargs.get('magic', 20260412)}|"
                    f"{datetime.now().isoformat()}"
                )
            
            elif signal_type == "CLOSE":
                # CLOSE|ticket|timestamp
                msg = (
                    f"CLOSE|"
                    f"{kwargs.get('ticket', 0)}|"
                    f"{datetime.now().isoformat()}"
                )
            
            elif signal_type == "MODIFY":
                # MODIFY|ticket|new_sl|new_tp|timestamp
                msg = (
                    f"MODIFY|"
                    f"{kwargs.get('ticket', 0)}|"
                    f"{kwargs.get('sl', 0.0)}|"
                    f"{kwargs.get('tp', 0.0)}|"
                    f"{datetime.now().isoformat()}"
                )
            
            elif signal_type == "GET_DATA":
                # GET_DATA|data_type|timestamp
                msg = (
                    f"GET_DATA|"
                    f"{kwargs.get('data_type', 'all')}|"
                    f"{datetime.now().isoformat()}"
                )
            
            else:
                self.logger.error(f"[MT5_BRIDGE] Unknown signal type: {signal_type}")
                return False
            
            # Enviar
            msg_with_newline = msg + "\n"
            self.client_socket.send(msg_with_newline.encode('utf-8'))
            
            # Estatísticas
            self.stats["signals_sent"] += 1
            self.last_signal_sent = datetime.now()
            
            # Log
            self.logger.info(f"[MT5_BRIDGE] Signal sent: {signal_type} -> {msg[:100]}...")
            self.logs_buffer.add({
                "timestamp": datetime.now(),
                "direction": "SEND",
                "signal_type": signal_type,
                "message": msg
            })
            
            return True
            
        except Exception as e:
            self.logger.error(f"[MT5_BRIDGE] Failed to send signal: {e}")
            self.stats["errors"] += 1
            return False
    
    def get_latest_tick(self) -> Optional[TickData]:
        """Retorna o tick mais recente"""
        ticks = self.ticks_buffer.get_latest(1)
        return ticks[0] if ticks else None
    
    def get_latest_account(self) -> Optional[AccountData]:
        """Retorna os dados mais recentes da conta"""
        accounts = self.account_buffer.get_latest(1)
        return accounts[0] if accounts else None
    
    def get_positions(self) -> list:
        """Retorna todas as posições no buffer"""
        return self.positions_buffer.get_all()
    
    def get_stats(self) -> dict:
        """Retorna estatísticas da conexão"""
        stats = self.stats.copy()
        stats["state"] = self.state.value
        stats["buffer_sizes"] = {
            "ticks": self.ticks_buffer.size(),
            "bars": self.bars_buffer.size(),
            "account": self.account_buffer.size(),
            "positions": self.positions_buffer.size(),
            "logs": self.logs_buffer.size()
        }
        
        if self.stats["start_time"]:
            uptime = (datetime.now() - self.stats["start_time"]).total_seconds()
            stats["uptime_seconds"] = uptime
        
        return stats
    
    def is_connected(self) -> bool:
        """Verifica se está conectado ao MT5"""
        return self.state == ConnectionState.CONNECTED
    
    def get_connection_status(self) -> str:
        """Retorna status detalhado da conexão"""
        status = {
            "state": self.state.value,
            "host": self.host,
            "port": self.port,
            "last_heartbeat": self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            "last_tick": self.last_tick.isoformat() if self.last_tick else None,
            "last_signal_sent": self.last_signal_sent.isoformat() if self.last_signal_sent else None,
            "stats": self.get_stats()
        }
        return json.dumps(status, indent=2)
