"""
Live Trading Logger - Sistema de logs com 5 handlers simultâneos

Este módulo implementa um sistema de logging ultra-detalhado com 5 handlers
simultâneos para garantir visibilidade completa de todos os sistemas em tempo real.

Handlers:
1. Console - Output colorido por nível no terminal
2. File - Arquivo rotativo (10MB max, 10 backups)
3. Audit - Buffer circular para compliance e auditoria
4. Memory - In-memory para acesso rápido pelo dashboard
5. Socket - Envia para dashboard externo (opcional)

Herança do projeto legacy DubaiMatrixASI:
- logger.py: 5 handlers simultâneos
- Rotating files com 10MB max
- Buffer circular para auditoria
- Formatação colorida por nível
- Logs estruturados por sistema
"""

import logging
import sys
import os
from logging.handlers import RotatingFileHandler, MemoryHandler
from datetime import datetime
from typing import Optional, Dict, List
from collections import deque
import threading
import json


# Cores para output no console
class Colors:
    """Cores ANSI para terminal"""
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DEBUG = '\033[36m'      # Ciano
    INFO = '\033[32m'       # Verde
    WARNING = '\033[33m'    # Amarelo
    ERROR = '\033[31m'      # Vermelho
    CRITICAL = '\033[35m'   # Magenta


class ColorFormatter(logging.Formatter):
    """Formatter com cores para console"""
    
    FORMATS = {
        logging.DEBUG: f"{Colors.DEBUG}%(asctime)s.%(msecs)03d{Colors.RESET} | {Colors.BOLD}%(name)-15s{Colors.RESET} | {Colors.DEBUG}%(levelname)-8s{Colors.RESET} | %(message)s",
        logging.INFO: f"{Colors.DEBUG}%(asctime)s.%(msecs)03d{Colors.RESET} | {Colors.BOLD}%(name)-15s{Colors.RESET} | {Colors.INFO}%(levelname)-8s{Colors.RESET} | %(message)s",
        logging.WARNING: f"{Colors.DEBUG}%(asctime)s.%(msecs)03d{Colors.RESET} | {Colors.BOLD}%(name)-15s{Colors.RESET} | {Colors.WARNING}%(levelname)-8s{Colors.RESET} | %(message)s",
        logging.ERROR: f"{Colors.DEBUG}%(asctime)s.%(msecs)03d{Colors.RESET} | {Colors.BOLD}%(name)-15s{Colors.RESET} | {Colors.ERROR}%(levelname)-8s{Colors.RESET} | %(message)s",
        logging.CRITICAL: f"{Colors.DEBUG}%(asctime)s.%(msecs)03d{Colors.RESET} | {Colors.BOLD}%(name)-15s{Colors.RESET} | {Colors.CRITICAL}%(levelname)-8s{Colors.RESET} | %(message)s",
    }
    
    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, datefmt='%Y-%m-%d %H:%M:%S')
        return formatter.format(record)


class SystemLogger:
    """
    Logger para um sistema específico
    
    Cada sistema (MT5Bridge, DataEngine, NeuralChain, etc) tem seu próprio logger
    com nome identificável para fácil filtragem.
    """
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.name = name
    
    def debug(self, message: str, **kwargs):
        """Log debug message"""
        extra = {"system": self.name, **kwargs}
        self.logger.debug(message, extra=extra)
    
    def info(self, message: str, **kwargs):
        """Log info message"""
        extra = {"system": self.name, **kwargs}
        self.logger.info(message, extra=extra)
    
    def warning(self, message: str, **kwargs):
        """Log warning message"""
        extra = {"system": self.name, **kwargs}
        self.logger.warning(message, extra=extra)
    
    def error(self, message: str, **kwargs):
        """Log error message"""
        extra = {"system": self.name, **kwargs}
        self.logger.error(message, extra=extra)
    
    def critical(self, message: str, **kwargs):
        """Log critical message"""
        extra = {"system": self.name, **kwargs}
        self.logger.critical(message, extra=extra)
    
    def trade(self, message: str, trade_data: Dict):
        """Log específico para trades"""
        trade_json = json.dumps(trade_data, default=str)
        self.info(f"[TRADE] {message} | Data: {trade_json}")
    
    def signal(self, message: str, signal_data: Dict):
        """Log específico para sinais de trading"""
        signal_json = json.dumps(signal_data, default=str)
        self.info(f"[SIGNAL] {message} | Data: {signal_json}")
    
    def performance(self, message: str, perf_data: Dict):
        """Log específico para métricas de performance"""
        perf_json = json.dumps(perf_data, default=str)
        self.info(f"[PERF] {message} | Data: {perf_json}")


class LiveTradingLoggerManager:
    """
    Gerenciador central de logs para live trading
    
    Configura e gerencia todos os 5 handlers simultâneos:
    1. Console (colorido por nível)
    2. File (rotating, 10MB max)
    3. Audit (circular buffer para compliance)
    4. Memory (in-memory para acesso rápido)
    5. Socket (dashboard externo - opcional)
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Singleton thread-safe"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        # Evitar reinicialização
        if hasattr(self, '_initialized') and self._initialized:
            return
        
        self._initialized = True
        
        # Configuração
        self.log_level = logging.DEBUG
        self.log_dir = "logs"
        self.max_bytes = 10 * 1024 * 1024  # 10MB
        self.backup_count = 10
        self.memory_buffer_size = 5000
        self.audit_buffer_size = 1000
        
        # Handlers
        self.console_handler = None
        self.file_handler = None
        self.audit_handler = None
        self.memory_handler = None
        self.socket_handler = None
        
        # Memory buffer para acesso rápido
        self.memory_buffer = deque(maxlen=self.memory_buffer_size)
        self.memory_buffer_lock = threading.Lock()
        
        # Estatísticas
        self.log_counts = {
            logging.DEBUG: 0,
            logging.INFO: 0,
            logging.WARNING: 0,
            logging.ERROR: 0,
            logging.CRITICAL: 0
        }
        self.counts_lock = threading.Lock()
        
        # Criar diretório de logs
        os.makedirs(self.log_dir, exist_ok=True)
        
        # Configurar logger principal
        self._setup_logger()
    
    def _setup_logger(self):
        """Configura o logger principal com todos os handlers"""
        # Logger raiz
        self.root_logger = logging.getLogger("LiveTrading")
        self.root_logger.setLevel(self.log_level)
        self.root_logger.handlers = []  # Limpar handlers existentes
        
        # Handler 1: Console (colorido)
        self._setup_console_handler()
        
        # Handler 2: File (rotating)
        self._setup_file_handler()
        
        # Handler 3: Audit (circular buffer)
        self._setup_audit_handler()
        
        # Handler 4: Memory (in-memory)
        self._setup_memory_handler()
        
        # Handler 5: Socket (dashboard externo - opcional)
        # self._setup_socket_handler()  # Desabilitado por padrão
    
    def _setup_console_handler(self):
        """Configura handler de console com cores"""
        self.console_handler = logging.StreamHandler(sys.stdout)
        self.console_handler.setLevel(logging.INFO)
        self.console_handler.setFormatter(ColorFormatter())
        self.root_logger.addHandler(self.console_handler)
    
    def _setup_file_handler(self):
        """Configura handler de arquivo rotativo"""
        log_file = os.path.join(self.log_dir, "live_trading.log")
        
        self.file_handler = RotatingFileHandler(
            log_file,
            maxBytes=self.max_bytes,
            backupCount=self.backup_count,
            encoding='utf-8'
        )
        self.file_handler.setLevel(logging.DEBUG)
        
        # Formatter detalhado para arquivo
        file_formatter = logging.Formatter(
            '%(asctime)s.%(msecs)03d | %(name)-15s | %(levelname)-8s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        self.file_handler.setFormatter(file_formatter)
        self.root_logger.addHandler(self.file_handler)
        
        # Handler separado para erros
        error_file = os.path.join(self.log_dir, "errors.log")
        error_handler = RotatingFileHandler(
            error_file,
            maxBytes=self.max_bytes,
            backupCount=self.backup_count,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(file_formatter)
        self.root_logger.addHandler(error_handler)
    
    def _setup_audit_handler(self):
        """Configura handler de auditoria com buffer circular"""
        audit_file = os.path.join(self.log_dir, "audit.log")
        
        # MemoryHandler com flush para arquivo
        target_handler = logging.FileHandler(audit_file, encoding='utf-8')
        target_handler.setLevel(logging.WARNING)
        
        target_formatter = logging.Formatter(
            '%(asctime)s.%(msecs)03d | %(name)-15s | %(levelname)-8s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        target_handler.setFormatter(target_formatter)
        
        self.audit_handler = MemoryHandler(
            capacity=self.audit_buffer_size,
            target=target_handler
        )
        self.audit_handler.setLevel(logging.WARNING)
        self.root_logger.addHandler(self.audit_handler)
    
    def _setup_memory_handler(self):
        """Configura handler in-memory para acesso rápido"""
        # Usar classe customizada para buffer circular
        self.memory_handler = CircularMemoryHandler(self.memory_buffer_size)
        self.memory_handler.setLevel(logging.DEBUG)
        self.root_logger.addHandler(self.memory_handler)
    
    def _setup_socket_handler(self, host: str = "localhost", port: int = 9020):
        """Configura handler de socket para dashboard externo (opcional)"""
        # Implementação futura: enviar logs para dashboard web
        pass
    
    def get_logger(self, name: str) -> SystemLogger:
        """
        Obtém logger para um sistema específico
        
        Args:
            name: Nome do sistema (ex: "MT5Bridge", "DataEngine", "NeuralChain")
        
        Returns:
            SystemLogger configurado
        """
        return SystemLogger(name)
    
    def get_recent_logs(self, n: int = 100, level: Optional[int] = None) -> list:
        """
        Obtém logs recentes do buffer de memória
        
        Args:
            n: Número de logs a retornar
            level: Filtrar por nível (opcional)
        
        Returns:
            Lista de registros de log
        """
        with self.memory_buffer_lock:
            logs = list(self.memory_handler.buffer)
        
        # Filtrar por nível se especificado
        if level is not None:
            logs = [log for log in logs if log.levelno >= level]
        
        # Retornar últimos n
        return logs[-n:]
    
    def get_stats(self) -> dict:
        """Retorna estatísticas de logging"""
        with self.counts_lock:
            return {
                "counts": self.log_counts.copy(),
                "total": sum(self.log_counts.values()),
                "memory_buffer_size": len(self.memory_buffer)
            }
    
    def increment_count(self, level: int):
        """Incrementa contador de logs por nível"""
        with self.counts_lock:
            if level in self.log_counts:
                self.log_counts[level] += 1
    
    def flush(self):
        """Força flush de todos os handlers"""
        if self.audit_handler:
            self.audit_handler.flush()
        
        if self.file_handler:
            self.file_handler.flush()
        
        if self.memory_handler:
            self.memory_handler.flush()
    
    def shutdown(self):
        """Desliga todos os handlers corretamente"""
        self.flush()
        
        # Fechar handlers
        for handler in [self.console_handler, self.file_handler, self.audit_handler, self.memory_handler]:
            if handler:
                try:
                    handler.close()
                except:
                    pass


class CircularMemoryHandler(logging.Handler):
    """Handler de memória com buffer circular"""
    
    def __init__(self, capacity: int = 5000):
        super().__init__()
        self.buffer = deque(maxlen=capacity)
        self.lock = threading.Lock()
    
    def emit(self, record: logging.LogRecord):
        """Emite registro para o buffer"""
        try:
            with self.lock:
                self.buffer.append(record)
        except Exception:
            self.handleError(record)
    
    def flush(self):
        """Flush (no-op para memory handler)"""
        pass
    
    def close(self):
        """Fecha handler"""
        with self.lock:
            self.buffer.clear()
        super().close()


# Instância global singleton
logger_manager = LiveTradingLoggerManager()


# Funções de conveniência
def get_logger(name: str) -> SystemLogger:
    """Obtém logger para um sistema"""
    return logger_manager.get_logger(name)


def get_recent_logs(n: int = 100, level: Optional[int] = None) -> list:
    """Obtém logs recentes"""
    return logger_manager.get_recent_logs(n, level)


def get_logger_stats() -> dict:
    """Obtém estatísticas de logging"""
    return logger_manager.get_stats()
