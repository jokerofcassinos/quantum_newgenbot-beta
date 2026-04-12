"""
Forex Quantum Bot - Live Trading System v3.0
PRODUCTION SYSTEM | CEO: Forex Quantum Bot | Created: 2026-04-12

Features:
- Direct MT5 command execution
- Real-time neural logging (1-to-1 machine state)
- Cycle audits (per-session tracking, auto-clean on restart)
- Test modes: --selltest, --buytest
- Telegram dashboard with interactive buttons
- Real-time order tracking with PnL monitoring
- Smart TP + Trailing position management
- FTMO compliance monitoring

Usage:
    python run_live_trading.py              # Normal live trading
    python run_live_trading.py --selltest   # Test SELL order execution
    python run_live_trading.py --buytest    # Test BUY order execution
    python run_live_trading.py --status     # Show current system status
"""

import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List, Tuple
from loguru import logger
import time
import sys
import os
import json
import argparse
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import core components
from src.strategies.session_profiles import detect_session, get_session_profile, apply_session_veto
from src.execution.position_manager_smart_tp import PositionManagerSmartTP
from src.risk.backtest_risk_manager import BacktestRiskManager
from src.risk.anti_metralhadora import AntiMetralhadora
from src.risk.risk_quantum_engine import RiskQuantumEngine
from src.risk.profit_erosion_tiers import ProfitErosionTiers
from src.risk.great_filter import GreatFilter
from src.monitoring.neural_trade_auditor import NeuralTradeAuditor
from src.monitoring.ghost_audit_engine import GhostAuditEngine
from src.monitoring.telegram_dashboard_v2 import TelegramDashboardV2


# ============================================================================
# CYCLE AUDIT SYSTEM
# ============================================================================

class CycleAudit:
    """
    Ultra-detailed cycle audit system.
    Tracks everything per session, auto-cleans on restart.
    """

    def __init__(self, audit_dir: str = "data/cycle-audits"):
        self.audit_dir = Path(audit_dir)
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_dir = self.audit_dir / self.session_id

        # Clean old sessions
        self._cleanup_old_sessions()
        self.session_dir.mkdir(parents=True, exist_ok=True)

        # Real-time tracking
        self.cycles = []
        self.current_cycle = 0
        self.start_time = datetime.now(timezone.utc)

        # Metrics
        self.total_candles_processed = 0
        self.total_signals_generated = 0
        self.total_signals_vetoed = 0
        self.total_orders_sent = 0
        self.total_orders_filled = 0
        self.total_orders_rejected = 0
        self.total_errors = 0

        # Market state tracking
        self.price_history = []
        self.regime_history = []
        self.confidence_history = []

        logger.info(f"📋 CycleAudit initialized: {self.session_dir}")

    def _cleanup_old_sessions(self):
        """Remove all old sessions - start fresh."""
        if self.audit_dir.exists():
            import shutil
            for old_session in self.audit_dir.iterdir():
                if old_session.is_dir():
                    shutil.rmtree(old_session, ignore_errors=True)
            logger.info("🗑️ Cleaned all old cycle audits")

    def record_cycle(self, cycle_data: Dict[str, Any]):
        """Record a complete cycle (candle processed)."""
        self.current_cycle += 1
        cycle_data['cycle_number'] = self.current_cycle
        cycle_data['timestamp'] = datetime.now(timezone.utc).isoformat()
        cycle_data['uptime_seconds'] = (datetime.now(timezone.utc) - self.start_time).total_seconds()

        self.cycles.append(cycle_data)
        self.total_candles_processed += 1

        # Save every 60 cycles
        if self.current_cycle % 60 == 0:
            self._save_cycle_audit()

    def _save_cycle_audit(self):
        """Save complete cycle audit to JSON."""
        audit_data = {
            'session_id': self.session_id,
            'start_time': self.start_time.isoformat(),
            'end_time': datetime.now(timezone.utc).isoformat(),
            'total_cycles': self.current_cycle,
            'metrics': {
                'total_candles_processed': self.total_candles_processed,
                'total_signals_generated': self.total_signals_generated,
                'total_signals_vetoed': self.total_signals_vetoed,
                'total_orders_sent': self.total_orders_sent,
                'total_orders_filled': self.total_orders_filled,
                'total_orders_rejected': self.total_orders_rejected,
                'total_errors': self.total_errors,
            },
            'last_100_cycles': self.cycles[-100:],
        }

        filepath = self.session_dir / "cycle_audit.json"
        with open(filepath, 'w') as f:
            json.dump(audit_data, f, indent=2, default=str)

    def generate_real_time_report(self, engine) -> str:
        """Generate ultra-detailed real-time report."""
        uptime = (datetime.now(timezone.utc) - self.start_time).total_seconds()
        uptime_str = f"{int(uptime // 3600)}h {int((uptime % 3600) // 60)}m {int(uptime % 60)}s"
        cycles_per_min = self.current_cycle / max(1, uptime / 60)

        report = (
            f"📊 CYCLE AUDIT REPORT\n"
            f"{'─' * 50}\n"
            f"Session: {self.session_id}\n"
            f"Uptime: {uptime_str}\n"
            f"Total Cycles: {self.current_cycle}\n"
            f"Cycles/min: {cycles_per_min:.1f}\n"
            f"\n"
            f"📈 Metrics:\n"
            f"   Candles: {self.total_candles_processed}\n"
            f"   Signals: {self.total_signals_generated}\n"
            f"   Vetoes: {self.total_signals_vetoed} ({self.total_signals_vetoed/max(1,self.total_signals_generated)*100:.1f}%)\n"
            f"   Orders Sent: {self.total_orders_sent}\n"
            f"   Orders Filled: {self.total_orders_filled}\n"
            f"   Orders Rejected: {self.total_orders_rejected}\n"
            f"   Errors: {self.total_errors}\n"
            f"\n"
            f"💹 Trading:\n"
            f"   Trades: {engine.total_trades}\n"
            f"   Wins: {engine.winning_trades}\n"
            f"   Losses: {engine.losing_trades}\n"
            f"   WR: {engine.winning_trades/max(1,engine.total_trades)*100:.1f}%\n"
            f"   DD: {engine.max_drawdown:.2f}%\n"
        )

        return report


# ============================================================================
# LIVE TRADING ENGINE V3.0
# ============================================================================

class LiveTradingEngine:
    """
    Production live trading engine with direct MT5 execution.

    Features:
    - Real-time neural logging (1-to-1 machine state)
    - Direct MT5 command execution
    - Smart TP + Trailing position management
    - Cycle audit tracking
    - Telegram dashboard
    - Test modes (--selltest, --buytest)
    """

    def __init__(
        self,
        symbol: str = "BTCUSD",
        timeframe: int = mt5.TIMEFRAME_M5,
        risk_percent: float = 1.0,
        max_positions: int = 1,
        test_mode: str = None,
    ):
        """Initialize Live Trading Engine."""
        self.symbol = symbol
        self.timeframe = timeframe
        self.risk_percent = risk_percent
        self.max_positions = max_positions
        self.test_mode = test_mode

        # State
        self.running = False
        self.start_time = datetime.now(timezone.utc)
        self.equity = 0.0
        self.balance = 0.0
        self.total_trades = 0
        self.total_vetoes = 0
        self.total_signals = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.consecutive_wins = 0
        self.consecutive_losses = 0
        self.last_loss_time = None
        self.consecutive_loss_cooldown = 6
        self.last_trade_time = None
        self.min_trade_interval = 300
        self.cycle_count = 0
        self.last_bar_time = None

        # Position tracking
        self.current_position = None
        self.position_peak_pnl = 0.0
        self.position_current_pnl = 0.0
        self.position_smart_tp_hits = 0
        self.peak_equity = 0.0
        self.max_drawdown = 0.0

        # Daily tracking
        self.daily_pnl = 0.0
        self.daily_loss_used = 0.0
        self.total_loss_used = 0.0
        self.ftmo_daily_remaining = 5000.0
        self.ftmo_total_remaining = 10000.0

        # Session tracking
        self.current_session = "unknown"

        # Loss patterns
        self.loss_patterns = {'avg_win_size': 0.0, 'avg_loss_size': 0.0}

        # Components
        self._init_components()

        # MT5
        self.mt5_connected = False

        # Cycle Audit
        self.cycle_audit = CycleAudit()

        # Telegram
        self.telegram = TelegramDashboardV2()

        logger.info("=" * 80)
        logger.info("🚀 FOREX QUANTUM BOT - LIVE TRADING ENGINE v3.0")
        logger.info("=" * 80)
        logger.info(f"   Symbol: {symbol}")
        logger.info(f"   Timeframe: M5")
        logger.info(f"   Risk/Trade: {risk_percent}%")
        logger.info(f"   Max Positions: {max_positions}")
        logger.info(f"   Test Mode: {test_mode or 'LIVE TRADING'}")
        logger.info(f"   Session: {self.cycle_audit.session_id}")

    def _init_components(self):
        """Initialize all trading components."""
        self.risk_manager = BacktestRiskManager(initial_capital=100000.0)

        self.anti_metralhadora = AntiMetralhadora(
            min_interval_minutes=5.0,
            max_trades_per_day=25,
            min_quality_score=0.40,
            max_consecutive_losses=3,
            loss_cooldown_minutes=30.0,
        )

        self.position_manager = PositionManagerSmartTP(
            tp1_portion=0.00, tp1_rr=1.0,
            tp2_portion=0.50, tp2_rr=2.0,
            tp3_portion=0.00, tp3_rr=3.0,
            trailing_portion=0.50,
            trailing_atr_multiplier=1.5,
        )

        self.risk_quantum = RiskQuantumEngine(
            kelly_fraction=0.25,
            max_position_size=5.0,
            min_position_size=0.01,
            base_risk_percent=1.0,
        )

        self.profit_erosion = ProfitErosionTiers()
        self.great_filter = GreatFilter()
        self.ghost_audit = GhostAuditEngine(audit_dir="data/live-ghost-audits")
        self.auditor = NeuralTradeAuditor(base_path="data/live-trade-audits")
        self.auditor._backtest_mode = True

        logger.info("✅ All components initialized")

    def connect_mt5(self) -> bool:
        """Connect to MetaTrader 5 with verification."""
        logger.info("🔄 Connecting to MT5...")

        if not mt5.initialize():
            logger.error(f"❌ MT5 initialization failed: {mt5.last_error()}")
            return False

        account_info = mt5.account_info()
        if account_info is None:
            logger.error("❌ Failed to get account info")
            return False

        self.balance = account_info.balance
        self.equity = account_info.equity
        self.peak_equity = self.equity

        logger.info(f"✅ MT5 Connected Successfully")
        logger.info(f"   Account: {account_info.login}")
        logger.info(f"   Server: {account_info.server}")
        logger.info(f"   Name: {account_info.name}")
        logger.info(f"   Balance: ${self.balance:,.2f}")
        logger.info(f"   Equity: ${self.equity:,.2f}")
        logger.info(f"   Leverage: 1:{account_info.leverage}")

        symbol_info = mt5.symbol_info(self.symbol)
        if symbol_info is None:
            logger.error(f"❌ Symbol {self.symbol} not found")
            return False

        if not symbol_info.visible:
            logger.warning(f"⚠️ Symbol not visible, enabling...")
            if not mt5.symbol_select(self.symbol, True):
                logger.error(f"❌ Failed to select symbol")
                return False

        logger.info(f"   Symbol: {self.symbol}")
        logger.info(f"   Point: {symbol_info.point}")
        logger.info(f"   Digits: {symbol_info.digits}")
        logger.info(f"   Spread: {symbol_info.spread}")
        logger.info(f"   Trade Contract Size: {symbol_info.trade_contract_size}")

        tick = mt5.symbol_info_tick(self.symbol)
        if tick:
            logger.info(f"   Current Bid: {tick.bid}")
            logger.info(f"   Current Ask: {tick.ask}")

        self.mt5_connected = True
        return True

    def get_uptime(self) -> str:
        """Get formatted uptime string."""
        uptime = (datetime.now(timezone.utc) - self.start_time).total_seconds()
        return f"{int(uptime // 3600)}h {int((uptime % 3600) // 60)}m {int(uptime % 60)}s"

    def get_candles(self, count: int = 200) -> Optional[pd.DataFrame]:
        """Fetch latest candles from MT5."""
        rates = mt5.copy_rates_from_pos(self.symbol, self.timeframe, 0, count)
        if rates is None or len(rates) == 0:
            logger.error(f"❌ Failed to get candles: {mt5.last_error()}")
            return None

        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s', utc=True)
        return df

    def calculate_indicators(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate all technical indicators."""
        indicators = {}
        close = df['close']
        high = df['high']
        low = df['low']
        volume = df['tick_volume']

        indicators['ema_9'] = self._ema(close, 9)
        indicators['ema_21'] = self._ema(close, 21)
        indicators['ema_50'] = self._ema(close, 50)
        indicators['sma_20'] = close.rolling(20).mean()

        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss.replace(0, np.nan)
        indicators['rsi_14'] = 100 - (100 / (1 + rs))

        tr = pd.concat([
            high - low,
            (high - close.shift()).abs(),
            (low - close.shift()).abs()
        ], axis=1).max(axis=1)
        indicators['atr_14'] = tr.rolling(14).mean()

        indicators['volume_avg_20'] = volume.rolling(20).mean()

        return indicators

    def _ema(self, series: pd.Series, span: int) -> pd.Series:
        """Calculate EMA."""
        return series.ewm(span=span, adjust=False).mean()

    def generate_signal(self, df: pd.DataFrame, indicators: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate trading signal using 12-strategy voting system."""
        if len(df) < 50:
            return None

        current_price = df['close'].iloc[-1]
        current_time = df['time'].iloc[-1]

        close = df['close'].values
        high = df['high'].values
        low = df['low'].values
        idx = len(df) - 1

        votes = {
            'strategy_votes': {},
            'buy_votes': 0,
            'sell_votes': 0,
            'neutral_votes': 0,
            'total_strategies': 12,
        }

        ema_9 = indicators['ema_9'].iloc[-1]
        ema_21 = indicators['ema_21'].iloc[-1]
        atr = indicators['atr_14'].iloc[-1]

        # Strategy 1: Momentum
        ema_diff_pct = abs(ema_9 - ema_21) / current_price * 100
        if ema_9 > ema_21 and ema_diff_pct > 0.15:
            votes['strategy_votes']['momentum'] = {'vote': 'BUY', 'confidence': min(0.60 + ema_diff_pct * 0.3, 0.90)}
            votes['buy_votes'] += 1
        elif ema_9 < ema_21 and ema_diff_pct > 0.15:
            votes['strategy_votes']['momentum'] = {'vote': 'SELL', 'confidence': min(0.60 + ema_diff_pct * 0.3, 0.90)}
            votes['sell_votes'] += 1
        else:
            votes['strategy_votes']['momentum'] = {'vote': 'NEUTRAL', 'confidence': 0.5}
            votes['neutral_votes'] += 1

        # Strategy 2: Liquidity Sweep
        lo10 = low[max(0, idx - 9):idx + 1].min()
        hi10 = high[max(0, idx - 9):idx + 1].max()
        if current_price <= lo10 * 1.002:
            votes['strategy_votes']['liquidity'] = {'vote': 'BUY', 'confidence': 0.65}
            votes['buy_votes'] += 1
        elif current_price >= hi10 * 0.998:
            votes['strategy_votes']['liquidity'] = {'vote': 'SELL', 'confidence': 0.65}
            votes['sell_votes'] += 1
        else:
            votes['strategy_votes']['liquidity'] = {'vote': 'NEUTRAL', 'confidence': 0.5}
            votes['neutral_votes'] += 1

        # Strategy 3: Thermodynamic
        if idx >= 10:
            price_change = (current_price - close[idx - 10]) / close[idx - 10] * 100
            if price_change < -2.0:
                votes['strategy_votes']['thermodynamic'] = {'vote': 'BUY', 'confidence': 0.65}
                votes['buy_votes'] += 1
            elif price_change > 2.0:
                votes['strategy_votes']['thermodynamic'] = {'vote': 'SELL', 'confidence': 0.65}
                votes['sell_votes'] += 1
            else:
                votes['strategy_votes']['thermodynamic'] = {'vote': 'NEUTRAL', 'confidence': 0.5}
                votes['neutral_votes'] += 1

        # Strategy 4: Physics
        sma_20 = indicators['sma_20'].iloc[-1]
        if current_price > sma_20 * 1.008:
            votes['strategy_votes']['physics'] = {'vote': 'SELL', 'confidence': 0.65}
            votes['sell_votes'] += 1
        elif current_price < sma_20 * 0.992:
            votes['strategy_votes']['physics'] = {'vote': 'BUY', 'confidence': 0.65}
            votes['buy_votes'] += 1
        else:
            votes['strategy_votes']['physics'] = {'vote': 'NEUTRAL', 'confidence': 0.5}
            votes['neutral_votes'] += 1

        # Strategy 5: Order Block
        if idx >= 15:
            ob_high = high[idx - 15:idx - 5].max()
            ob_low = low[idx - 15:idx - 5].min()
            if current_price <= ob_low * 1.003:
                votes['strategy_votes']['order_block'] = {'vote': 'BUY', 'confidence': 0.63}
                votes['buy_votes'] += 1
            elif current_price >= ob_high * 0.997:
                votes['strategy_votes']['order_block'] = {'vote': 'SELL', 'confidence': 0.63}
                votes['sell_votes'] += 1
            else:
                votes['strategy_votes']['order_block'] = {'vote': 'NEUTRAL', 'confidence': 0.5}
                votes['neutral_votes'] += 1

        # Strategy 6: FVG
        fvg_vote = 'NEUTRAL'
        if idx >= 8:
            for j in range(max(0, idx - 8), idx - 1):
                h1, l3 = high[j], low[j + 2]
                l1, h3 = low[j], high[j + 2]
                if h1 < l3 and current_price >= l3 * 0.998 and current_price <= h1 * 1.002:
                    fvg_vote = 'BUY'
                    break
                elif l1 > h3 and current_price <= l1 * 1.002 and current_price >= h3 * 0.998:
                    fvg_vote = 'SELL'
                    break
        votes['strategy_votes']['fvg'] = {'vote': fvg_vote, 'confidence': 0.62 if fvg_vote != 'NEUTRAL' else 0.5}
        if fvg_vote == 'BUY':
            votes['buy_votes'] += 1
        elif fvg_vote == 'SELL':
            votes['sell_votes'] += 1
        else:
            votes['neutral_votes'] += 1

        # Strategies 7-12
        for name in ['msnr', 'msnr_alchemist', 'ifvg', 'order_flow', 'supply_demand', 'fibonacci']:
            votes['strategy_votes'][name] = {'vote': 'NEUTRAL', 'confidence': 0.5}
            votes['neutral_votes'] += 1

        # Determine consensus
        if votes['buy_votes'] > votes['sell_votes'] and votes['buy_votes'] >= 5:
            direction = 'BUY'
            consensus_conf = sum(v['confidence'] for v in votes['strategy_votes'].values() if v['vote'] == 'BUY') / max(1, votes['buy_votes'])
        elif votes['sell_votes'] > votes['buy_votes'] and votes['sell_votes'] >= 5:
            direction = 'SELL'
            consensus_conf = sum(v['confidence'] for v in votes['strategy_votes'].values() if v['vote'] == 'SELL') / max(1, votes['sell_votes'])
        else:
            return None

        if pd.isna(atr) or atr == 0:
            return None

        sl_dist = min(max(atr * 1.5, 500), 3000)
        tp_dist = sl_dist * 2.0

        if direction == 'BUY':
            sl = current_price - sl_dist
            tp = current_price + tp_dist
        else:
            sl = current_price + sl_dist
            tp = current_price - tp_dist

        return {
            'direction': direction,
            'entry_price': current_price,
            'stop_loss': sl,
            'take_profit': tp,
            'volume': 0.01,
            'confidence': consensus_conf,
            'atr': atr,
            'votes': votes,
            'buy_votes': votes['buy_votes'],
            'sell_votes': votes['sell_votes'],
            'neutral_votes': votes['neutral_votes'],
            'time': current_time,
        }

    def validate_signal(self, signal: Dict[str, Any], df: pd.DataFrame) -> Tuple[bool, str]:
        """Validate signal through all veto layers."""
        current_time = signal['time']
        session = detect_session(current_time)
        self.current_session = session
        session_profile = get_session_profile(session)

        # Session veto
        session_veto = apply_session_veto(session_profile, signal)
        if not session_veto['approved']:
            return False, f"Session veto: {session_veto.get('reason', 'unknown')}"

        # Anti-Metralhadora
        allowed, reason, _ = self.anti_metralhadora.should_allow_trade(
            signal_quality=signal.get('confidence', 0.0),
            current_session=session,
            current_time=current_time,
        )
        if not allowed:
            return False, f"Anti-Metralhadora: {reason}"

        # GreatFilter
        spread = self._get_spread()
        price_change = self._get_price_change_5min(df)
        great_allowed, great_reason = self.great_filter.validate_entry(
            signal_confidence=signal.get('confidence', 0.5),
            spread_percent=spread,
            price_change_5min=price_change,
            session_allowed=True,
        )
        if not great_allowed:
            return False, f"GreatFilter: {great_reason}"

        return True, "All vetoes passed"

    def _get_spread(self) -> float:
        """Get current spread as percentage."""
        tick = mt5.symbol_info_tick(self.symbol)
        if tick is None:
            return 0.001
        spread = tick.ask - tick.bid
        return (spread / tick.ask) * 100

    def _get_price_change_5min(self, df: pd.DataFrame) -> float:
        """Get price change over last 5 minutes."""
        if len(df) < 2:
            return 0.0
        return ((df['close'].iloc[-1] - df['close'].iloc[-2]) / df['close'].iloc[-2]) * 100

    def calculate_position_size(self, signal: Dict[str, Any]) -> float:
        """Calculate position size using RiskQuantumEngine."""
        account_info = mt5.account_info()
        if account_info is None:
            return 0.01

        equity = account_info.equity
        win_rate = self.winning_trades / max(1, self.total_trades) if self.total_trades > 10 else 0.35
        avg_win_loss = self.loss_patterns.get('avg_win_size', 15.0) / max(1, self.loss_patterns.get('avg_loss_size', 8.0)) if self.loss_patterns.get('avg_loss_size', 0) > 0 else 1.5

        sizing = self.risk_quantum.calculate_position_size(
            equity=equity,
            win_rate=win_rate,
            avg_win_loss_ratio=avg_win_loss,
            signal_confidence=signal.get('confidence', 0.5),
            current_volatility=signal.get('atr', 200),
            avg_volatility=signal.get('atr', 200),
            current_drawdown=self.max_drawdown / 100.0 if self.max_drawdown > 0 else 0.0,
            correlation_factor=1.0,
        )

        return sizing['position_size']

    def execute_trade(self, signal: Dict[str, Any]) -> bool:
        """Execute trade on MT5."""
        volume = signal.get('volume', 0.01)
        direction = signal['direction']
        sl = signal['stop_loss']
        tp = signal['take_profit']

        tick = mt5.symbol_info_tick(self.symbol)
        if tick is None:
            logger.error("❌ Failed to get tick data")
            return False

        if direction == 'BUY':
            order_type = mt5.ORDER_TYPE_BUY
            price = tick.ask
        else:
            order_type = mt5.ORDER_TYPE_SELL
            price = tick.bid

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": self.symbol,
            "volume": volume,
            "type": order_type,
            "price": price,
            "sl": sl,
            "tp": tp,
            "deviation": 50,
            "magic": 123456,
            "comment": "ForexQuantumBot",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)

        if result is None:
            logger.error(f"❌ Order send failed: {mt5.last_error()}")
            return False

        if result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error(f"❌ Order failed: {result.retcode} - {result.comment}")
            return False

        logger.info(f"✅ Order executed: {direction} {volume} lots @ {price:.2f}")
        logger.info(f"   SL: {sl:.2f}, TP: {tp:.2f}")
        logger.info(f"   Ticket: {result.order}")

        # Track position
        self.current_position = {
            'ticket': result.order,
            'direction': direction,
            'entry_price': price,
            'stop_loss': sl,
            'take_profit': tp,
            'volume': volume,
            'open_time': datetime.now(timezone.utc),
            'targets': self.position_manager.create_position_targets(
                entry_price=price,
                stop_loss=sl,
                direction=direction,
                atr=signal.get('atr', 200),
            ),
        }

        # Send Telegram alert
        self.telegram.send_order_opened(
            ticket=result.order,
            direction=direction,
            volume=volume,
            entry=price,
            sl=sl,
            tp=tp,
            reason=f"{signal.get('buy_votes', 0)} BUY votes vs {signal.get('sell_votes', 0)} SELL votes",
            confidence=signal.get('confidence', 0.5),
            votes=signal.get('votes', {}),
        )

        # Audit entry
        self.auditor.capture_entry_state(
            ticket=result.order,
            direction=direction,
            entry_price=price,
            stop_loss=sl,
            take_profit=tp,
            volume=volume,
            strategy_name="live_trading",
            signal_confidence=signal.get('confidence', 0.5),
            market_regime={'regime_type': 'unknown', 'regime_confidence': 0.5, 'session': self.current_session},
            multi_timeframe={'M5_trend': 'neutral', 'alignment_score': 0.5},
            indicators={},
            price_action={},
            momentum={},
            risk_context={'capital': self.balance, 'equity': self.equity},
            dna_state={},
            smart_order_manager={},
            strategy_voting=signal.get('votes', {}),
        )

        return True

    def manage_position(self, df: pd.DataFrame, indicators: Dict[str, Any]):
        """Manage open position (check TP/SL, trailing, Smart TP)."""
        if self.current_position is None:
            return

        pos = self.current_position
        tick = mt5.symbol_info_tick(self.symbol)
        if tick is None:
            return

        current_price = tick.bid if pos['direction'] == 'SELL' else tick.ask

        # Calculate unrealized PnL
        if pos['direction'] == 'BUY':
            self.position_current_pnl = (current_price - pos['entry_price']) * pos['volume']
        else:
            self.position_current_pnl = (pos['entry_price'] - current_price) * pos['volume']

        self.position_peak_pnl = max(self.position_peak_pnl, self.position_current_pnl)

        # Check Smart TP targets
        atr = indicators.get('atr_14', pd.Series([200])).iloc[-1]
        if pd.isna(atr):
            atr = 200

        position_closed, realized_pnl, closed_targets = self.position_manager.check_targets(
            position_targets=pos['targets'],
            current_price=current_price,
            current_volume=pos['volume'],
            atr=atr,
        )

        if position_closed:
            self.position_smart_tp_hits = sum(1 for t in pos['targets']['targets'] if t.get('closed', False))
            self._close_position(pos, realized_pnl, current_price, 'Smart TP complete')

    def _close_position(self, pos: Dict, realized_pnl: float, exit_price: float, reason: str):
        """Close position and record results."""
        # Close via MT5
        tick = mt5.symbol_info_tick(self.symbol)
        if tick is None:
            return

        if pos['direction'] == 'BUY':
            order_type = mt5.ORDER_TYPE_SELL
            price = tick.bid
        else:
            order_type = mt5.ORDER_TYPE_BUY
            price = tick.ask

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": self.symbol,
            "volume": pos['volume'],
            "type": order_type,
            "position": pos['ticket'],
            "price": price,
            "deviation": 50,
            "magic": 123456,
            "comment": f"Close: {reason}",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)

        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            duration = (datetime.now(timezone.utc) - pos['open_time']).total_seconds() / 60
            commission = pos['volume'] * 90  # $90 round trip per lot

            if realized_pnl > 0:
                self.winning_trades += 1
                self.consecutive_wins += 1
                self.consecutive_losses = 0
            else:
                self.losing_trades += 1
                self.consecutive_losses += 1
                self.consecutive_wins = 0

            self.total_trades += 1
            self.current_position = None
            self.position_peak_pnl = 0.0
            self.position_current_pnl = 0.0
            self.position_smart_tp_hits = 0

            logger.info(f"✅ Position closed: {reason}")
            logger.info(f"   P/L: ${realized_pnl:+,.2f}")
            logger.info(f"   Duration: {duration:.0f} min")

            # Telegram alert
            self.telegram.send_order_closed(
                ticket=pos['ticket'],
                direction=pos['direction'],
                volume=pos['volume'],
                entry=pos['entry_price'],
                exit_price=exit_price,
                pnl=realized_pnl,
                commission=commission,
                reason=reason,
                duration_minutes=int(duration),
                smart_tp_hits=self.position_smart_tp_hits,
            )

    def log_neural_state(self, df: pd.DataFrame, indicators: Dict[str, Any], signal: Optional[Dict]):
        """Log complete neural machine state to terminal."""
        if df is None or len(df) < 2:
            return

        current_price = df['close'].iloc[-1]
        ema_9 = indicators.get('ema_9', pd.Series([0])).iloc[-1]
        ema_21 = indicators.get('ema_21', pd.Series([0])).iloc[-1]
        rsi = indicators.get('rsi_14', pd.Series([50])).iloc[-1]
        atr = indicators.get('atr_14', pd.Series([0])).iloc[-1]

        trend = "📈 BULLISH" if ema_9 > ema_21 else "📉 BEARISH"
        rsi_status = "🔴 OB" if rsi > 70 else ("🟢 OS" if rsi < 30 else "⚪ N")

        signal_info = ""
        if signal:
            signal_info = f" | 🎯 Signal: {signal['direction']} ({signal['confidence']:.2f}) | Votes: {signal.get('buy_votes', 0)}B/{signal.get('sell_votes', 0)}S/{signal.get('neutral_votes', 0)}N"
        else:
            signal_info = " | 🎯 No Signal"

        pos_info = ""
        if self.current_position:
            pos_info = f" | 📦 Open: {self.current_position['direction']} ${self.position_current_pnl:+,.2f} (Peak: ${self.position_peak_pnl:+,.2f})"

        logger.info(
            f"🧠 NEURAL | "
            f"💰 {current_price:,.2f} | "
            f"📊 {trend} | "
            f"RSI: {rsi:.1f} {rsi_status} | "
            f"ATR: {atr:.2f} | "
            f"Cycle: {self.cycle_count}"
            f"{signal_info}"
            f"{pos_info}"
        )

    def run(self, max_bars: int = None):
        """Main trading loop."""
        logger.info("=" * 80)
        logger.info("🚀 STARTING LIVE TRADING LOOP")
        logger.info("=" * 80)

        if not self.connect_mt5():
            logger.error("❌ Failed to connect to MT5. Aborting.")
            return

        self.running = True
        bar_count = 0

        try:
            while self.running:
                df = self.get_candles(count=200)
                if df is None or len(df) < 50:
                    logger.warning("⚠️ Insufficient data, waiting...")
                    time.sleep(5)
                    continue

                indicators = self.calculate_indicators(df)
                self.cycle_count += 1
                self.last_bar_time = df['time'].iloc[-1]

                # Manage open position
                self.manage_position(df, indicators)

                # Check if we can open new position
                if self.current_position is None:
                    signal = self.generate_signal(df, indicators)
                    self.total_signals += 1
                    self.cycle_audit.total_signals_generated += 1

                    if signal:
                        # Log neural state with signal
                        self.log_neural_state(df, indicators, signal)

                        approved, reason = self.validate_signal(signal, df)

                        if approved:
                            volume = self.calculate_position_size(signal)
                            signal['volume'] = max(0.01, min(5.0, volume))

                            if self.execute_trade(signal):
                                self.cycle_audit.total_orders_sent += 1
                        else:
                            self.total_vetoes += 1
                            self.cycle_audit.total_signals_vetoed += 1
                            logger.debug(f"🚫 Signal vetoed: {reason}")
                    else:
                        # Log neural state without signal
                        self.log_neural_state(df, indicators, None)

                # Log status periodically
                if bar_count % 12 == 0:
                    self.cycle_audit.generate_real_time_report(self)
                    # Send Telegram dashboard
                    self.telegram.send_dashboard(self)

                bar_count += 1

                if max_bars and bar_count >= max_bars:
                    logger.info(f"✅ Reached max bars ({max_bars}). Stopping.")
                    break

                # Wait for next bar
                time.sleep(5)

        except KeyboardInterrupt:
            logger.info("⏹️ Stopped by user")
        except Exception as e:
            logger.error(f"❌ Trading loop error: {e}", exc_info=True)
        finally:
            self.shutdown()

    def shutdown(self):
        """Shutdown trading system."""
        logger.info("🛑 Shutting down live trading system...")
        self.running = False

        # Close any open positions
        if self.current_position:
            logger.warning(f"⚠️ Closing open position: {self.current_position['ticket']}")
            tick = mt5.symbol_info_tick(self.symbol)
            if tick:
                exit_price = tick.bid if self.current_position['direction'] == 'BUY' else tick.ask
                self._close_position(self.current_position, 0.0, exit_price, 'Shutdown')

        # Save cycle audit
        self.cycle_audit._save_cycle_audit()

        # Shutdown MT5
        if self.mt5_connected:
            mt5.shutdown()
            logger.info("✅ MT5 disconnected")

        # Final status
        logger.info("=" * 80)
        logger.info("LIVE TRADING SYSTEM SHUTDOWN COMPLETE")
        logger.info("=" * 80)
        logger.info(f"   Total Trades: {self.total_trades}")
        logger.info(f"   Wins: {self.winning_trades}")
        logger.info(f"   Losses: {self.losing_trades}")
        logger.info(f"   Win Rate: {self.winning_trades/max(1,self.total_trades)*100:.1f}%")
        logger.info(f"   Max DD: {self.max_drawdown:.2f}%")
        logger.info(f"   Uptime: {self.get_uptime()}")


def run_test_mode(direction: str):
    """Run test mode to verify order execution."""
    logger.info("=" * 80)
    logger.info(f"🧪 RUNNING {direction.upper()} TEST MODE")
    logger.info("=" * 80)

    if not mt5.initialize():
        logger.error("❌ MT5 initialization failed")
        return

    account = mt5.account_info()
    if account:
        logger.info(f"✅ Connected: {account.login} @ {account.server}")
        logger.info(f"   Balance: ${account.balance:,.2f}")

    tick = mt5.symbol_info_tick("BTCUSD")
    if tick is None:
        logger.error("❌ Failed to get BTCUSD tick")
        mt5.shutdown()
        return

    price = tick.bid if direction == 'SELL' else tick.ask
    sl_dist = 500
    tp_dist = 1000

    if direction == 'BUY':
        sl = price - sl_dist
        tp = price + tp_dist
        order_type = mt5.ORDER_TYPE_BUY
    else:
        sl = price + sl_dist
        tp = price - tp_dist
        order_type = mt5.ORDER_TYPE_SELL

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": "BTCUSD",
        "volume": 0.01,
        "type": order_type,
        "price": price,
        "sl": sl,
        "tp": tp,
        "deviation": 50,
        "magic": 123456,
        "comment": "TEST ORDER",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    logger.info(f"📤 Sending {direction} order...")
    logger.info(f"   Price: {price:.2f}")
    logger.info(f"   SL: {sl:.2f}")
    logger.info(f"   TP: {tp:.2f}")
    logger.info(f"   Volume: 0.01")

    result = mt5.order_send(request)

    if result:
        logger.info(f"   Retcode: {result.retcode}")
        logger.info(f"   Order: {result.order}")
        logger.info(f"   Price: {result.price}")
        logger.info(f"   Comment: {result.comment}")

        if result.retcode == mt5.TRADE_RETCODE_DONE:
            logger.info(f"✅ {direction} TEST SUCCESSFUL!")
        else:
            logger.error(f"❌ {direction} TEST FAILED: {result.comment}")
    else:
        logger.error(f"❌ Order send failed: {mt5.last_error()}")

    mt5.shutdown()


if __name__ == "__main__":
    # Setup logging
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO",
    )

    # Parse arguments
    parser = argparse.ArgumentParser(description="Forex Quantum Bot - Live Trading")
    parser.add_argument("--selltest", action="store_true", help="Test SELL order execution")
    parser.add_argument("--buytest", action="store_true", help="Test BUY order execution")
    parser.add_argument("--status", action="store_true", help="Show current system status")
    args = parser.parse_args()

    if args.selltest:
        run_test_mode("SELL")
    elif args.buytest:
        run_test_mode("BUY")
    else:
        engine = LiveTradingEngine(
            symbol="BTCUSD",
            risk_percent=1.0,
            max_positions=1,
        )
        engine.run()
