"""
Run Live Trading V2 - Entry Point Principal para Live Trading

Este é o ponto de entrada principal para o sistema de live trading completo.
Integra todos os módulos da FASE 0 e FASE 1:
- MT5 Bridge (TCP Socket)
- Data Engine (Background worker)
- Logger (5 handlers)
- Terminal Dashboard

FASE 2 irá adicionar:
- Neural Chain (cadeia neural completa)
- RegimeDetector
- NeuralSwarm (140+ agentes)
- QuantumThought
- TrinityCore
- SniperExecutor

Uso:
    python run_live_trading_v2.py
"""

import sys
import os
import time
import signal
import argparse
import logging
from datetime import datetime
from typing import Optional

# Configurar logging padrão do Python ANTES de importar outros módulos
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s.%(msecs)03d | %(name)-15s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/live_trading.log', mode='w')
    ]
)

# Adicionar projeto ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from live_trading.mt5_bridge import MT5Bridge, TickData, ConnectionState
from live_trading.data_engine import DataEngine, IndicatorData, MarketState
from live_trading.logger import get_logger, get_recent_logs, get_logger_stats
from live_trading.terminal_dashboard import TerminalDashboard
from live_trading.neural_chain import LiveNeuralChain, LiveSignal
from live_trading.trade_executor import TradeExecutor, Position


class LiveTradingSystem:
    """
    Sistema principal de live trading
    
    Orquestra todos os módulos:
    - MT5 Bridge
    - Data Engine
    - Neural Chain (FASE 2)
    - Risk Management (FASE 3)
    - Dashboard
    """
    
    def __init__(self, config: Optional[dict] = None):
        # Configuração
        self.config = config or self._load_default_config()
        
        # Logger
        self.logger = get_logger("LiveTradingSystem")
        
        # Componentes
        self.bridge: Optional[MT5Bridge] = None
        self.data_engine: Optional[DataEngine] = None
        self.dashboard: Optional[TerminalDashboard] = None
        self.neural_chain: Optional[LiveNeuralChain] = None
        self.trade_executor: Optional[TradeExecutor] = None
        
        # Estado
        self.running = False
        self.start_time = None
        
        # Estatísticas
        self.stats = {
            "ticks_processed": 0,
            "trades_executed": 0,
            "errors": 0,
            "last_tick_time": None
        }
        
        # Registrar signal handlers para shutdown gracioso
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _load_default_config(self) -> dict:
        """Carrega configuração padrão"""
        return {
            "socket": {
                "host": "127.0.0.1",
                "port": 5555,
                "timeout_ms": 3000,
                "max_reconnect_attempts": 10,
                "reconnect_delay_seconds": 1.0,
                "heartbeat_interval_seconds": 1.0
            },
            "mt5": {
                "symbol": "BTCUSD",
                "timeframe": "M5",
                "magic_number": 20260413,
                "max_positions": 1,
                "auto_trade": True
            },
            "dashboard": {
                "enabled": True,
                "refresh_interval": 1.0
            },
            "logging": {
                "level": "DEBUG",
                "log_dir": "logs"
            }
        }
    
    def start(self):
        """Inicia o sistema de live trading completo"""
        self.logger.info("=" * 80)
        self.logger.info("LIVE TRADING SYSTEM - STARTING")
        self.logger.info("=" * 80)
        
        try:
            # 1. Iniciar MT5 Bridge
            self.logger.info("[LIVE] Step 1: Starting MT5 Bridge...")
            self._start_mt5_bridge()
            
            # 2. Iniciar Data Engine
            self.logger.info("[LIVE] Step 2: Starting Data Engine...")
            self._start_data_engine()
            
            # 3. Iniciar Dashboard
            self.logger.info("[LIVE] Step 3: Starting Terminal Dashboard...")
            self._start_dashboard()
            
            # 4. Setup completo (FASE 2 adicionará neural chain aqui)
            self.logger.info("[LIVE] Step 4: Setting up neural chain (FASE 2)...")
            self._setup_neural_chain()
            
            # 5. Marcar como rodando
            self.running = True
            self.start_time = datetime.now()
            
            self.logger.info("=" * 80)
            self.logger.info("✅ LIVE TRADING SYSTEM STARTED SUCCESSFULLY")
            self.logger.info("=" * 80)
            self.logger.info(f"Symbol: {self.config['mt5']['symbol']}")
            self.logger.info(f"Socket: {self.config['socket']['host']}:{self.config['socket']['port']}")
            self.logger.info(f"Dashboard: {'Enabled' if self.config['dashboard']['enabled'] else 'Disabled'}")
            self.logger.info("=" * 80)
            
            # 6. Loop principal
            self._main_loop()
            
        except Exception as e:
            self.logger.error(f"[LIVE] Failed to start live trading system: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            self.stop()
            raise
    
    def stop(self):
        """Para o sistema graciously"""
        self.logger.info("=" * 80)
        self.logger.info("LIVE TRADING SYSTEM - STOPPING")
        self.logger.info("=" * 80)
        
        self.running = False
        
        # Parar componentes
        if self.trade_executor:
            self.logger.info("[LIVE] Stopping trade executor...")
            self.trade_executor.stop()
        
        if self.dashboard:
            self.logger.info("[LIVE] Stopping dashboard...")
            self.dashboard.stop()
        
        if self.data_engine:
            self.logger.info("[LIVE] Stopping data engine...")
            self.data_engine.stop()
        
        if self.bridge:
            self.logger.info("[LIVE] Stopping MT5 bridge...")
            self.bridge.stop()
        
        # Estatísticas finais
        self._print_final_stats()
        
        self.logger.info("=" * 80)
        self.logger.info("✅ LIVE TRADING SYSTEM STOPPED")
        self.logger.info("=" * 80)
    
    def _start_mt5_bridge(self):
        """Inicia MT5 Bridge - APENAS criar, NÃO startar ainda"""
        socket_config = self.config['socket']

        # Criar bridge sem iniciar (callbacks serão registrados antes do start)
        self.bridge = MT5Bridge(
            host=socket_config['host'],
            port=socket_config['port']
        )

        self.logger.info("[LIVE] ✅ MT5 Bridge created")
    
    def _start_data_engine(self):
        """Inicia Data Engine - registrar TODOS callbacks ANTES de start"""
        symbol = self.config['mt5']['symbol']

        self.data_engine = DataEngine(
            bridge=self.bridge,
            symbol=symbol,
            buffer_size=1000
        )

        # Registrar callbacks do data engine
        self.data_engine.on_indicators_ready(self._on_indicators_ready)
        self.data_engine.on_market_state_updated(self._on_market_state_updated)
        self.data_engine.on_regime_change(self._on_regime_change)

        # =====================================================
        # CRITICAL: Registrar TODOS callbacks no bridge ANTES de start
        # =====================================================
        # Data Engine (processa ticks)
        self.bridge.on_tick(self.data_engine._on_tick_received)
        self.bridge.on_account(self.data_engine._on_account_received)
        self.bridge.on_position(self.data_engine._on_position_received)
        
        # Live Trading System (dashboard/stats)
        self.bridge.on_connected(self._on_mt5_connected)
        self.bridge.on_disconnected(self._on_mt5_disconnected)
        self.bridge.on_error(self._on_mt5_error)
        # =====================================================

        # AGORA sim, iniciar bridge (todos callbacks já registrados)
        self.bridge.start()
        self.data_engine.start()

        self.logger.info("[LIVE] ✅ Data Engine started")
    
    def _start_dashboard(self):
        """Inicia Dashboard"""
        if not self.config['dashboard']['enabled']:
            self.logger.info("[LIVE] Dashboard disabled")
            return
        
        self.dashboard = TerminalDashboard(bridge=self.bridge)
        self.dashboard.start()
        
        self.logger.info("[LIVE] ✅ Terminal Dashboard started")
    
    def _setup_neural_chain(self):
        """Setup da cadeia neural completa + Trade Executor"""
        self.logger.info("[LIVE] Initializing Live Neural Chain...")
        
        initial_capital = 100000.0  # Pode vir do config
        symbol = self.config['mt5']['symbol']
        
        self.neural_chain = LiveNeuralChain(
            symbol=symbol,
            initial_capital=initial_capital
        )
        
        self.logger.info("[LIVE] ✅ Live Neural Chain initialized")
        self.logger.info("[LIVE]   Modules loaded: 33+")
        self.logger.info("[LIVE]   Strategies: 13")
        self.logger.info("[LIVE]   Veto systems: 10+")
        self.logger.info("[LIVE]   Analysis modules: 10+")
        
        # Setup Trade Executor
        self.logger.info("[LIVE] Initializing Trade Executor...")
        
        magic_number = self.config['mt5'].get('magic_number', 20260413)
        auto_trade = self.config['mt5'].get('auto_trade', True)
        
        self.trade_executor = TradeExecutor(
            bridge=self.bridge,
            neural_chain=self.neural_chain,
            symbol=symbol,
            magic_number=magic_number,
            auto_execute=auto_trade
        )
        
        # Registrar callbacks
        self.trade_executor.on_order_executed(self._on_order_executed)
        self.trade_executor.on_position_closed(self._on_position_closed)
        
        # Iniciar trade executor
        self.trade_executor.start()
        
        self.logger.info("[LIVE] ✅ Trade Executor initialized")
    
    def _main_loop(self):
        """Loop principal do sistema"""
        self.logger.info("[LIVE] Main loop started")
        
        try:
            while self.running:
                # Verificar estado do sistema
                if self.bridge and self.bridge.is_connected():
                    # Sistema rodando normalmente
                    time.sleep(1)
                else:
                    # Aguardando conexão
                    self.logger.debug("[LIVE] Waiting for MT5 connection...")
                    time.sleep(2)
                
                # Verificar se precisa fazer algo
                self._check_system_health()
        
        except KeyboardInterrupt:
            self.logger.info("[LIVE] Keyboard interrupt received")
        except Exception as e:
            self.logger.error(f"[LIVE] Main loop error: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
        
        finally:
            self.stop()
    
    def _check_system_health(self):
        """Verifica saúde do sistema"""
        # Verificar bridge
        if self.bridge:
            stats = self.bridge.get_stats()
            
            # Verificar erros
            if stats['errors'] > 10:
                self.logger.warning(f"[LIVE] High error count: {stats['errors']}")
            
            # Verificar latência
            if stats['avg_latency_ms'] > 100:
                self.logger.warning(f"[LIVE] High latency: {stats['avg_latency_ms']:.2f}ms")
        
        # Verificar data engine
        if self.data_engine:
            de_stats = self.data_engine.get_stats()
            
            # Verificar erros
            if de_stats['errors'] > 5:
                self.logger.warning(f"[LIVE] Data engine errors: {de_stats['errors']}")
    
    # ===== CALLBACKS =====
    
    def _on_tick_received(self, tick: TickData):
        """Callback quando recebe tick"""
        self.stats['ticks_processed'] += 1
        self.stats['last_tick_time'] = datetime.now()
        
        self.logger.debug(f"[LIVE] Tick received: {tick.symbol} bid={tick.bid:.2f} ask={tick.ask:.2f}")
        
        # Atualizar dashboard
        if self.dashboard and self.data_engine:
            market_state = self.data_engine.get_market_state()
            if market_state:
                self.dashboard.update_market_state(market_state)
    
    def _on_bar_received(self, bar: dict):
        """Callback quando recebe bar"""
        self.logger.debug(f"[LIVE] Bar received: {bar.get('symbol')} {bar.get('timeframe')}")
    
    def _on_account_received(self, account):
        """Callback quando recebe dados da conta"""
        self.logger.debug(f"[LIVE] Account updated: balance={account.balance:.2f}")
    
    def _on_position_received(self, position):
        """Callback quando recebe dados de posição"""
        self.logger.debug(f"[LIVE] Position updated: ticket={position.ticket}")
    
    def _on_mt5_connected(self):
        """Callback quando MT5 conecta"""
        self.logger.info("[LIVE] ✅ MT5 CONNECTED - Data flow starting")
    
    def _on_mt5_disconnected(self):
        """Callback quando MT5 desconecta"""
        self.logger.warning("[LIVE] ⚠️ MT5 DISCONNECTED - Attempting reconnection...")
    
    def _on_mt5_error(self, error: str):
        """Callback quando recebe erro do MT5"""
        self.logger.error(f"[LIVE] ❌ MT5 Error: {error}")
        self.stats['errors'] += 1
    
    def _on_indicators_ready(self, indicators: IndicatorData):
        """Callback quando indicadores estão prontos"""
        self.logger.debug(f"[LIVE] Indicators ready: RSI={indicators.rsi:.2f} ATR={indicators.atr:.5f}")
        
        # Atualizar dashboard
        if self.dashboard:
            self.dashboard.update_indicators(indicators)
        
        # Processar através da neural chain
        if self.neural_chain and self.data_engine:
            tick = self.bridge.get_latest_tick()
            market_state = self.data_engine.get_market_state()
            
            if tick and market_state:
                # Atualizar neural chain com dados frescos
                self.neural_chain.update_market_data(tick, indicators)
                
                # Processar através da cadeia neural
                signal = self.neural_chain.process_tick(tick, indicators, market_state)
                
                if signal:
                    self.logger.info(f"[LIVE] 🎯 NEURAL CHAIN SIGNAL: {signal.direction} {signal.symbol} @ {signal.entry_price:.2f} (conf={signal.confidence:.2f})")
                    
                    # Executar trade!
                    if self.trade_executor:
                        order_ticket = self.trade_executor.execute_signal(signal)
                        
                        if order_ticket:
                            self.logger.info(f"[LIVE] ✅ Trade executed: Order #{order_ticket}")
                        else:
                            self.logger.warning(f"[LIVE] ⚠️ Trade execution failed or rejected")
                    
                    # Atualizar estatísticas
                    self.stats['trades_executed'] = self.neural_chain.stats['trades_executed']
    
    def _on_market_state_updated(self, market_state: MarketState):
        """Callback quando estado do mercado é atualizado"""
        self.logger.debug(f"[LIVE] Market state updated: regime={market_state.regime}")
        
        # Atualizar dashboard
        if self.dashboard:
            self.dashboard.update_market_state(market_state)
    
    def _on_regime_change(self, regime: str):
        """Callback quando regime muda"""
        self.logger.info(f"[LIVE] 🔄 Regime changed to: {regime.upper()}")
    
    def _on_order_executed(self, position: Position):
        """Callback quando ordem é executada"""
        self.logger.info(f"[LIVE] 🎯 ORDER EXECUTED: {position.direction} {position.volume} {position.symbol} @ {position.entry_price:.2f}")
        self.logger.info(f"[LIVE]    SL: {position.stop_loss:.2f} | TP: {position.take_profit:.2f}")
        
        # Atualizar dashboard
        if self.dashboard:
            self.dashboard.update_system_status("Trade Executor", "OK")
    
    def _on_position_closed(self, position: Position):
        """Callback quando posição é fechada"""
        self.logger.info(f"[LIVE] 📊 POSITION CLOSED: Ticket {position.ticket} | PnL: ${position.net_pnl:.2f} | Reason: {position.close_reason}")
        
        # Atualizar dashboard
        if self.dashboard:
            self.dashboard.update_trading_stats({
                "total_pnl": self.trade_executor.stats['total_pnl'] if self.trade_executor else 0.0,
                "positions_closed": self.trade_executor.stats['positions_closed'] if self.trade_executor else 0,
            })
    
    def _signal_handler(self, signum, frame):
        """Handler para signals (Ctrl+C, etc)"""
        self.logger.info(f"[LIVE] Signal {signum} received")
        self.stop()
    
    def _print_final_stats(self):
        """Imprime estatísticas finais"""
        if not self.start_time:
            return
        
        uptime = (datetime.now() - self.start_time).total_seconds()
        
        self.logger.info("[LIVE] FINAL STATISTICS:")
        self.logger.info(f"[LIVE]   Uptime: {uptime:.0f}s")
        self.logger.info(f"[LIVE]   Ticks processed: {self.stats['ticks_processed']}")
        self.logger.info(f"[LIVE]   Trades executed: {self.stats['trades_executed']}")
        self.logger.info(f"[LIVE]   Errors: {self.stats['errors']}")
        
        if self.bridge:
            bridge_stats = self.bridge.get_stats()
            self.logger.info(f"[LIVE]   Bridge ticks received: {bridge_stats['ticks_received']}")
            self.logger.info(f"[LIVE]   Bridge signals sent: {bridge_stats['signals_sent']}")
            self.logger.info(f"[LIVE]   Bridge errors: {bridge_stats['errors']}")
            self.logger.info(f"[LIVE]   Bridge avg latency: {bridge_stats['avg_latency_ms']:.2f}ms")
        
        if self.data_engine:
            de_stats = self.data_engine.get_stats()
            self.logger.info(f"[LIVE]   Data engine ticks processed: {de_stats['ticks_processed']}")
            self.logger.info(f"[LIVE]   Data engine errors: {de_stats['errors']}")
            self.logger.info(f"[LIVE]   Current regime: {de_stats['current_regime']}")
        
        if self.neural_chain:
            nc_stats = self.neural_chain.get_stats()
            self.logger.info(f"[LIVE]   Neural chain signals: {nc_stats['signals_generated']}")
            self.logger.info(f"[LIVE]   Neural chain trades: {nc_stats['trades_executed']}")
            self.logger.info(f"[LIVE]   Neural chain vetoes: {nc_stats['total_vetoes']}")
            self.logger.info(f"[LIVE]   Neural chain vetoes breakdown: {nc_stats['vetoes']}")
        
        if self.trade_executor:
            te_stats = self.trade_executor.get_stats()
            self.logger.info(f"[LIVE]   Trade executor orders sent: {te_stats['orders_sent']}")
            self.logger.info(f"[LIVE]   Trade executor orders executed: {te_stats['orders_executed']}")
            self.logger.info(f"[LIVE]   Trade executor positions closed: {te_stats['positions_closed']}")
            self.logger.info(f"[LIVE]   Trade executor total PnL: ${te_stats['total_pnl']:.2f}")
            self.logger.info(f"[LIVE]   Trade executor open positions: {te_stats['open_positions']}")
        
        # Log statistics
        log_stats = get_logger_stats()
        self.logger.info(f"[LIVE]   Total logs: {log_stats['total']}")


def main():
    """Entry point principal"""
    parser = argparse.ArgumentParser(description="Forex Quantum Bot - Live Trading V2")
    parser.add_argument("--config", type=str, help="Path to config file", default=None)
    parser.add_argument("--symbol", type=str, help="Trading symbol", default=None)
    parser.add_argument("--no-dashboard", action="store_true", help="Disable dashboard")
    
    args = parser.parse_args()
    
    # Carregar config
    config = None
    if args.config:
        import json
        with open(args.config, 'r') as f:
            config = json.load(f)
    
    # Override com args
    if config is None:
        try:
            from live_trading.config import socket_config
            config = {
                "socket": {
                    "host": socket_config.SOCKET_CONFIG["host"],
                    "port": socket_config.SOCKET_CONFIG["port"],
                    "timeout_ms": socket_config.SOCKET_CONFIG["timeout_ms"],
                    "max_reconnect_attempts": socket_config.SOCKET_CONFIG["max_reconnect_attempts"],
                    "reconnect_delay_seconds": socket_config.SOCKET_CONFIG["reconnect_delay_seconds"],
                    "heartbeat_interval_seconds": socket_config.SOCKET_CONFIG["heartbeat_interval_seconds"]
                },
                "mt5": {
                    "symbol": socket_config.MT5_CONFIG["symbol"],
                    "timeframe": socket_config.MT5_CONFIG["timeframe"],
                    "magic_number": socket_config.MT5_CONFIG["magic_number"],
                    "max_positions": socket_config.MT5_CONFIG["max_positions"],
                    "auto_trade": socket_config.MT5_CONFIG["auto_trade"]
                },
                "dashboard": {
                    "enabled": True,
                    "refresh_interval": 1.0
                },
                "logging": {
                    "level": "DEBUG",
                    "log_dir": "logs"
                }
            }
        except ImportError:
            config = None
    
    if args.symbol and config:
        config['mt5']['symbol'] = args.symbol
    
    if args.no_dashboard and config:
        config['dashboard']['enabled'] = False
    
    # Criar e iniciar sistema
    system = LiveTradingSystem(config=config)
    
    try:
        system.start()
    except KeyboardInterrupt:
        print("\n\nLive trading stopped by user")
    except Exception as e:
        print(f"\n\nLive trading failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
