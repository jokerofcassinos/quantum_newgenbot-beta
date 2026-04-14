"""
Terminal Dashboard - Mostra logs de TODOS os sistemas em tempo real

Este módulo cria um dashboard em tempo real no terminal que mostra:
- Status de conexão MT5
- Métricas de performance (PnL, drawdown, win rate)
- Logs de cada sistema (1 por 1)
- Estado do mercado (regime, indicadores)
- Estatísticas de trading
- Alertas de erros e anomalias

Herança do projeto legacy DubaiMatrixASI:
- Terminal output com logs de todos os sistemas
- Dashboard com métricas de performance
- Status de conexão em tempo real
- Alertas visuais
"""

import os
import sys
import time
import threading
from datetime import datetime
from typing import Optional, Dict, List
import json

from live_trading.logger import get_logger, get_recent_logs, get_logger_stats
from live_trading.mt5_bridge import MT5Bridge, ConnectionState


class Colors:
    """Cores ANSI para terminal"""
    RESET = '\033[0m'
    BOLD = '\033[1m'
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    BG_BLUE = '\033[44m'
    BG_GREEN = '\033[42m'
    BG_RED = '\033[41m'
    BG_YELLOW = '\033[43m'


class TerminalDashboard:
    """
    Dashboard em tempo real no terminal
    
    Mostra:
    - Header com status geral
    - Seção MT5 Bridge
    - Seção Data Engine
    - Logs de cada sistema (rolling)
    - Métricas de performance
    - Alertas
    """
    
    def __init__(self, bridge: Optional[MT5Bridge] = None):
        self.bridge = bridge
        self.logger = get_logger("Dashboard")
        
        # Estado do dashboard
        self.running = False
        self.refresh_interval = 1.0  # Atualizar a cada 1 segundo
        
        # Thread de atualização
        self.refresh_thread: Optional[threading.Thread] = None
        
        # Dados para display
        self.market_state = None
        self.indicators = None
        self.trading_stats = {}
        self.system_status = {}
        
        # Estatísticas de logs
        self.last_log_count = 0
        
        # Clear screen
        self.clear_screen()
    
    def start(self):
        """Inicia o dashboard"""
        self.logger.info("[DASHBOARD] Starting terminal dashboard")
        self.running = True
        
        # Iniciar thread de refresh
        self.refresh_thread = threading.Thread(target=self._refresh_loop, daemon=True)
        self.refresh_thread.start()
        
        self.logger.info("[DASHBOARD] Dashboard started")
    
    def stop(self):
        """Para o dashboard"""
        self.logger.info("[DASHBOARD] Stopping terminal dashboard")
        self.running = False
        
        if self.refresh_thread:
            self.refresh_thread.join(timeout=3)
        
        self.logger.info("[DASHBOARD] Dashboard stopped")
    
    def update_market_state(self, market_state):
        """Atualiza estado do mercado para display"""
        self.market_state = market_state
    
    def update_indicators(self, indicators):
        """Atualiza indicadores para display"""
        self.indicators = indicators
    
    def update_trading_stats(self, stats: Dict):
        """Atualiza estatísticas de trading"""
        self.trading_stats = stats
    
    def update_system_status(self, system: str, status: str):
        """Atualiza status de um sistema"""
        self.system_status[system] = status
    
    def clear_screen(self):
        """Limpa a tela"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def _refresh_loop(self):
        """Loop de refresh do dashboard"""
        while self.running:
            try:
                self._render()
                time.sleep(self.refresh_interval)
            except Exception as e:
                self.logger.error(f"[DASHBOARD] Error refreshing: {e}")
                time.sleep(2)
    
    def _render(self):
        """Renderiza o dashboard completo"""
        # Limpar tela
        self.clear_screen()
        
        # Header
        self._render_header()
        
        # MT5 Bridge Status
        self._render_mt5_status()
        
        # Market State
        self._render_market_state()
        
        # System Logs (últimos logs de cada sistema)
        self._render_system_logs()
        
        # Statistics
        self._render_statistics()
        
        # Footer
        self._render_footer()
    
    def _render_header(self):
        """Renderiza header do dashboard"""
        width = 100
        
        print("=" * width)
        print(f"{Colors.BOLD}{Colors.BG_BLUE}          FOREX QUANTUM BOT - LIVE TRADING DASHBOARD          {Colors.RESET}")
        print("=" * width)
        
        # Data/hora
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"{Colors.CYAN}Time:{Colors.RESET} {now}")
    
    def _render_mt5_status(self):
        """Renderiza status do MT5 Bridge"""
        width = 100
        
        print("\n" + "=" * width)
        print(f"{Colors.BOLD}{Colors.BG_BLUE}  MT5 BRIDGE STATUS  {Colors.RESET}")
        print("=" * width)
        
        if self.bridge:
            stats = self.bridge.get_stats()
            is_connected = self.bridge.is_connected()
            
            # Connection status
            status_icon = "✅ CONNECTED" if is_connected else "❌ DISCONNECTED"
            print(f"{Colors.CYAN}Status:{Colors.RESET} {status_icon}")
            
            # Latency
            latency = stats.get('avg_latency_ms', 0)
            if latency > 0:
                latency_color = Colors.GREEN if latency < 50 else Colors.YELLOW if latency < 100 else Colors.RED
                print(f"{Colors.CYAN}Latency:{Colors.RESET} {latency_color}{latency:.2f}ms{Colors.RESET}")
            else:
                print(f"{Colors.CYAN}Latency:{Colors.RESET} N/A")
            
            # Ticks received
            print(f"{Colors.CYAN}Ticks Received:{Colors.RESET} {stats.get('ticks_received', 0)}")
            
            # Signals sent
            print(f"{Colors.CYAN}Signals Sent:{Colors.RESET} {stats.get('signals_sent', 0)}")
            
            # Errors
            errors = stats.get('errors', 0)
            error_color = Colors.RED if errors > 0 else Colors.GREEN
            print(f"{Colors.CYAN}Errors:{Colors.RESET} {error_color}{errors}{Colors.RESET}")
            
            # Reconnections
            reconnections = stats.get('reconnections', 0)
            print(f"{Colors.CYAN}Reconnections:{Colors.RESET} {reconnections}")
            
            # Buffer sizes
            buffer_sizes = stats.get('buffer_sizes', {})
            print(f"\n{Colors.CYAN}Buffers:{Colors.RESET}")
            print(f"  Ticks: {buffer_sizes.get('ticks', 0):<10} | Bars: {buffer_sizes.get('bars', 0):<10} | Logs: {buffer_sizes.get('logs', 0)}")
            
            # Uptime
            uptime = stats.get('uptime_seconds', 0)
            if uptime > 0:
                hours = int(uptime // 3600)
                minutes = int((uptime % 3600) // 60)
                seconds = int(uptime % 60)
                print(f"{Colors.CYAN}Uptime:{Colors.RESET} {hours}h {minutes}m {seconds}s")
        else:
            print(f"{Colors.RED}MT5 Bridge not initialized{Colors.RESET}")
    
    def _render_market_state(self):
        """Renderiza estado do mercado"""
        width = 100
        
        print("\n" + "=" * width)
        print(f"{Colors.BOLD}{Colors.BG_BLUE}  MARKET STATE  {Colors.RESET}")
        print("=" * width)
        
        if self.market_state:
            ms = self.market_state
            
            # Symbol and price
            print(f"{Colors.CYAN}Symbol:{Colors.RESET} {ms.symbol}")
            print(f"{Colors.CYAN}Price:{Colors.RESET} {ms.price:.2f}")
            
            # Bid/Ask/Spread
            print(f"{Colors.CYAN}Bid/Ask:{Colors.RESET} {ms.bid:.2f} / {ms.ask:.2f} (Spread: {ms.spread:.2f})")
            
            # Regime
            regime_icons = {
                "trending_up": "📈 TRENDING UP",
                "trending_down": "📉 TRENDING DOWN",
                "ranging": "➡️ RANGING",
                "volatile": "⚡ VOLATILE"
            }
            regime_display = regime_icons.get(ms.regime, f"❓ {ms.regime.upper()}")
            print(f"{Colors.CYAN}Regime:{Colors.RESET} {regime_display} (Strength: {ms.trend_strength:.2f})")
            
            # Volatility regime
            vol_colors_map = {
                "low": Colors.GREEN,
                "normal": Colors.CYAN,
                "high": Colors.YELLOW,
                "extreme": Colors.RED
            }
            vol_color = vol_colors_map.get(ms.volatility_regime, Colors.RESET)
            print(f"{Colors.CYAN}Volatility:{Colors.RESET} {vol_color}{ms.volatility_regime.upper()}{Colors.RESET}")
            
            # Indicators
            if self.indicators:
                ind = self.indicators
                print(f"\n{Colors.CYAN}Indicators:{Colors.RESET}")
                print(f"  ATR: {ind.atr:.5f}  |  RSI: {ind.rsi:.2f}")
                print(f"  EMA9: {ind.ema9:.2f}  |  EMA21: {ind.ema21:.2f}  |  EMA50: {ind.ema50:.2f}  |  EMA200: {ind.ema200:.2f}")
                print(f"  MACD: {ind.macd:.5f}  |  Signal: {ind.macd_signal:.5f}  |  Histogram: {ind.macd_histogram:.5f}")
                print(f"  BB Upper: {ind.bb_upper:.2f}  |  Middle: {ind.bb_middle:.2f}  |  Lower: {ind.bb_lower:.2f}")
                print(f"  VWAP: {ind.vwap:.2f}  |  Momentum: {ind.momentum:.2f}%  |  Volatility: {ind.volatility:.2f}%")
        else:
            print(f"{Colors.YELLOW}Waiting for market data...{Colors.RESET}")
    
    def _render_system_logs(self):
        """Renderiza logs recentes de cada sistema"""
        width = 100
        
        print("\n" + "=" * width)
        print(f"{Colors.BOLD}{Colors.BG_BLUE}  SYSTEM LOGS (Latest)  {Colors.RESET}")
        print("=" * width)
        
        # Obter logs recentes
        recent_logs = get_recent_logs(n=15)
        
        if recent_logs:
            for log in recent_logs[-15:]:
                # Formatar log
                timestamp = logasctime if hasattr(log, 'asctime') else datetime.now().strftime('%H:%M:%S')
                name = log.name if hasattr(log, 'name') else "Unknown"
                levelname = log.levelname if hasattr(log, 'levelname') else "INFO"
                message = log.getMessage() if hasattr(log, 'getMessage') else str(log)
                
                # Colorir por nível
                level_colors = {
                    "DEBUG": Colors.CYAN,
                    "INFO": Colors.GREEN,
                    "WARNING": Colors.YELLOW,
                    "ERROR": Colors.RED,
                    "CRITICAL": Colors.RED + Colors.BOLD
                }
                level_color = level_colors.get(levelname, Colors.RESET)
                
                # Truncar nome do sistema
                system_name = name[:15].ljust(15)
                
                # Truncar mensagem se muito longa
                if len(message) > 80:
                    message = message[:77] + "..."
                
                print(f"{Colors.CYAN}{timestamp}{Colors.RESET} | {Colors.BOLD}{system_name}{Colors.RESET} | {level_color}{levelname:<8}{Colors.RESET} | {message}")
        else:
            print(f"{Colors.YELLOW}No logs yet...{Colors.RESET}")
    
    def _render_statistics(self):
        """Renderiza estatísticas gerais"""
        width = 100
        
        print("\n" + "=" * width)
        print(f"{Colors.BOLD}{Colors.BG_BLUE}  STATISTICS  {Colors.RESET}")
        print("=" * width)
        
        # Log statistics
        log_stats = get_logger_stats()
        print(f"{Colors.CYAN}Log Counts:{Colors.RESET}")
        print(f"  DEBUG: {log_stats['counts'].get(10, 0):<10} | INFO: {log_stats['counts'].get(20, 0):<10} | WARNING: {log_stats['counts'].get(30, 0)}")
        print(f"  ERROR: {log_stats['counts'].get(40, 0):<10} | CRITICAL: {log_stats['counts'].get(50, 0):<10} | TOTAL: {log_stats['total']}")
        
        # Trading statistics
        if self.trading_stats:
            print(f"\n{Colors.CYAN}Trading Stats:{Colors.RESET}")
            for key, value in self.trading_stats.items():
                print(f"  {key}: {value}")
        
        # System status
        if self.system_status:
            print(f"\n{Colors.CYAN}System Status:{Colors.RESET}")
            for system, status in self.system_status.items():
                status_icon = "✅" if status == "OK" else "❌" if status == "ERROR" else "⏳"
                print(f"  {status_icon} {system}: {status}")
    
    def _render_footer(self):
        """Renderiza footer do dashboard"""
        width = 100
        
        print("\n" + "=" * width)
        print(f"{Colors.CYAN}Press Ctrl+C to stop{Colors.RESET}")
        print("=" * width)


class SimpleTerminalOutput:
    """
    Output simplificado para terminal (sem refresh completo)
    Útil para mostrar status em tempo real sem limpar a tela
    """
    
    def __init__(self):
        self.logger = get_logger("TerminalOutput")
        self.last_update = None
    
    def print_status_line(self, system: str, status: str, message: str = ""):
        """Imprime uma linha de status"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        status_icons = {
            "OK": "✅",
            "ERROR": "❌",
            "WARNING": "⚠️",
            "INFO": "ℹ️",
            "RUNNING": "🔄"
        }
        icon = status_icons.get(status, "•")
        
        print(f"[{timestamp}] {icon} {system}: {message}")
    
    def print_separator(self, title: str = ""):
        """Imprime separador"""
        width = 80
        if title:
            print(f"\n{'=' * width}")
            print(f"  {title}")
            print(f"{'=' * width}")
        else:
            print(f"\n{'-' * width}")
    
    def print_market_data(self, market_state, indicators=None):
        """Imprime dados de mercado"""
        if not market_state:
            return
        
        ms = market_state
        self.print_separator("MARKET DATA")
        
        print(f"Symbol: {ms.symbol}")
        print(f"Price: {ms.price:.2f} (Bid: {ms.bid:.2f} / Ask: {ms.ask:.2f})")
        print(f"Spread: {ms.spread:.2f}")
        print(f"Regime: {ms.regime.upper()} (Strength: {ms.trend_strength:.2f})")
        print(f"Volatility: {ms.volatility_regime.upper()}")
        
        if indicators:
            ind = indicators
            print(f"\nIndicators:")
            print(f"  ATR: {ind.atr:.5f}")
            print(f"  RSI: {ind.rsi:.2f}")
            print(f"  EMA: 9={ind.ema9:.2f}, 21={ind.ema21:.2f}, 50={ind.ema50:.2f}, 200={ind.ema200:.2f}")
            print(f"  MACD: {ind.macd:.5f} / Signal: {ind.macd_signal:.5f}")
