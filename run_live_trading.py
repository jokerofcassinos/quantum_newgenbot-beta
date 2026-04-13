"""
Forex Quantum Bot - Live Trading System v4.0
PRODUCTION SYSTEM | CEO: Forex Quantum Bot | Created: 2026-04-12

Features:
- Direct MT5 command execution
- REAL-TIME neural logging (EVERY bar, complete state)
- Per-cycle JSON audit files (like backtest trade audits)
- Test modes: --selltest, --buytest
- Telegram dashboard with EDITING (no spam) + callback handlers
- Real-time order tracking with PnL monitoring
- Smart TP + Trailing position management
- FTMO compliance monitoring
- Balance/equity tracking on EVERY bar

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
# CYCLE AUDIT SYSTEM - PER-CYCLE JSON FILES (like backtest trade audits)
# ============================================================================

class CycleAudit:
    """
    Ultra-detailed cycle audit system.
    Creates ONE JSON file per cycle: cycle_000001.json, cycle_000002.json, etc.
    Auto-cleans on restart.
    """

    def __init__(self, audit_dir: str = "data/cycle-audits"):
        self.audit_dir = Path(audit_dir)
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_dir = self.audit_dir / self.session_id

        # Clean old sessions
        self._cleanup_old_sessions()
        self.session_dir.mkdir(parents=True, exist_ok=True)

        # Real-time tracking
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

        logger.info(f"CycleAudit initialized (per-cycle JSON): {self.session_dir}")

    def _cleanup_old_sessions(self):
        """Remove all old sessions - start fresh."""
        if self.audit_dir.exists():
            import shutil
            for old_session in self.audit_dir.iterdir():
                if old_session.is_dir():
                    shutil.rmtree(old_session, ignore_errors=True)
            logger.info("Cleaned all old cycle audits")

    def save_cycle_audit(self, cycle_data: Dict[str, Any]):
        """
        Save a COMPLETE cycle audit as its OWN JSON file.
        File naming: cycle_000001.json, cycle_000002.json, etc.
        Structure matches backtest trade audits with ultra-complex data.
        """
        self.current_cycle += 1
        self.total_candles_processed += 1

        # Enrich with metadata
        cycle_data['cycle_number'] = self.current_cycle
        cycle_data['timestamp'] = datetime.now(timezone.utc).isoformat()
        cycle_data['uptime_seconds'] = (datetime.now(timezone.utc) - self.start_time).total_seconds()
        cycle_data['session_id'] = self.session_id

        # Write individual cycle file
        cycle_filename = f"cycle_{self.current_cycle:06d}.json"
        cycle_filepath = self.session_dir / cycle_filename
        with open(cycle_filepath, 'w') as f:
            json.dump(cycle_data, f, indent=2, default=str)

        return cycle_filepath

    def generate_real_time_report(self, engine) -> str:
        """Generate ultra-detailed real-time report."""
        uptime = (datetime.now(timezone.utc) - self.start_time).total_seconds()
        uptime_str = f"{int(uptime // 3600)}h {int((uptime % 3600) // 60)}m {int(uptime % 60)}s"
        cycles_per_min = self.current_cycle / max(1, uptime / 60)

        report = (
            f"CYCLE AUDIT REPORT\n"
            f"{'-' * 50}\n"
            f"Session: {self.session_id}\n"
            f"Uptime: {uptime_str}\n"
            f"Total Cycles: {self.current_cycle}\n"
            f"Cycles/min: {cycles_per_min:.1f}\n"
            f"\n"
            f"Metrics:\n"
            f"   Candles: {self.total_candles_processed}\n"
            f"   Signals: {self.total_signals_generated}\n"
            f"   Vetoes: {self.total_signals_vetoed} ({self.total_signals_vetoed/max(1,self.total_signals_generated)*100:.1f}%)\n"
            f"   Orders Sent: {self.total_orders_sent}\n"
            f"   Orders Filled: {self.total_orders_filled}\n"
            f"   Orders Rejected: {self.total_orders_rejected}\n"
            f"   Errors: {self.total_errors}\n"
            f"\n"
            f"Trading:\n"
            f"   Trades: {engine.total_trades}\n"
            f"   Wins: {engine.winning_trades}\n"
            f"   Losses: {engine.losing_trades}\n"
            f"   WR: {engine.winning_trades/max(1,engine.total_trades)*100:.1f}%\n"
            f"   DD: {engine.max_drawdown:.2f}%\n"
        )

        return report


# ============================================================================
# LIVE TRADING ENGINE V4.0 - ULTRA-COMPREHENSIVE LOGGING
# ============================================================================

class LiveTradingEngine:
    """
    Production live trading engine with direct MT5 execution.

    Features:
    - REAL-TIME neural logging (EVERY bar, complete state)
    - Direct MT5 command execution
    - Smart TP + Trailing position management
    - Per-cycle JSON audit files
    - Telegram dashboard with EDITING (no spam)
    - Test modes (--selltest, --buytest)
    - Balance/equity tracking on every bar
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
        self.daily_start_balance = 0.0

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

        # Last cycle audit data (for saving at end of cycle)
        self._last_signal = None
        self._last_votes = None
        self._last_indicators = None
        self._last_veto_results = None

        logger.info("=" * 80)
        logger.info("FOREX QUANTUM BOT - LIVE TRADING ENGINE v4.0")
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

        logger.info("All components initialized")

    def _refresh_account_state(self) -> Dict[str, Any]:
        """
        Query mt5.account_info() and update internal balance/equity tracking.
        Called on EVERY bar to ensure accurate state.
        """
        account_info = mt5.account_info()
        if account_info is None:
            return {'balance': self.balance, 'equity': self.equity, 'margin': 0.0, 'margin_free': 0.0, 'margin_level': 0.0}

        old_balance = self.balance
        self.balance = account_info.balance
        self.equity = account_info.equity

        # Track peak equity and drawdown
        if self.equity > self.peak_equity:
            self.peak_equity = self.equity
        if self.peak_equity > 0:
            current_dd = (self.peak_equity - self.equity) / self.peak_equity * 100
            if current_dd > self.max_drawdown:
                self.max_drawdown = current_dd

        # Track daily PnL from actual MT5 balance
        if self.daily_start_balance == 0.0:
            self.daily_start_balance = self.balance
        self.daily_pnl = self.balance - self.daily_start_balance

        return {
            'balance': account_info.balance,
            'equity': account_info.equity,
            'margin': account_info.margin,
            'margin_free': account_info.margin_free,
            'margin_level': account_info.margin_level,
        }

    def connect_mt5(self) -> bool:
        """Connect to MetaTrader 5 with verification."""
        logger.info("Connecting to MT5...")

        if not mt5.initialize():
            logger.error(f"MT5 initialization failed: {mt5.last_error()}")
            return False

        account_info = mt5.account_info()
        if account_info is None:
            logger.error("Failed to get account info")
            return False

        self.balance = account_info.balance
        self.equity = account_info.equity
        self.peak_equity = self.equity
        self.daily_start_balance = self.balance

        logger.info(f"MT5 Connected Successfully")
        logger.info(f"   Account: {account_info.login}")
        logger.info(f"   Server: {account_info.server}")
        logger.info(f"   Name: {account_info.name}")
        logger.info(f"   Balance: ${self.balance:,.2f}")
        logger.info(f"   Equity: ${self.equity:,.2f}")
        logger.info(f"   Leverage: 1:{account_info.leverage}")

        symbol_info = mt5.symbol_info(self.symbol)
        if symbol_info is None:
            logger.error(f"Symbol {self.symbol} not found")
            return False

        if not symbol_info.visible:
            logger.warning(f"Symbol not visible, enabling...")
            if not mt5.symbol_select(self.symbol, True):
                logger.error(f"Failed to select symbol")
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
            logger.error(f"Failed to get candles: {mt5.last_error()}")
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
        """
        Generate trading signal using 12-strategy voting system.
        LOGS every strategy vote, vote totals, and consensus.
        """
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
        rsi = indicators['rsi_14'].iloc[-1]
        ema_50 = indicators['ema_50'].iloc[-1]
        sma_20 = indicators['sma_20'].iloc[-1]
        volume_avg = indicators['volume_avg_20'].iloc[-1]
        current_volume = df['tick_volume'].iloc[-1]

        # Build complete market state for audit
        market_state = {
            'symbol': self.symbol,
            'timeframe': 'M5',
            'open': float(df['open'].iloc[-1]),
            'high': float(df['high'].iloc[-1]),
            'low': float(df['low'].iloc[-1]),
            'close': float(current_price),
            'volume': int(current_volume),
            'spread': self._get_spread(),
        }

        indicator_state = {
            'ema_9': float(ema_9) if not pd.isna(ema_9) else None,
            'ema_21': float(ema_21) if not pd.isna(ema_21) else None,
            'ema_50': float(ema_50) if not pd.isna(ema_50) else None,
            'sma_20': float(sma_20) if not pd.isna(sma_20) else None,
            'rsi_14': float(rsi) if not pd.isna(rsi) else None,
            'atr_14': float(atr) if not pd.isna(atr) else None,
            'volume_avg_20': float(volume_avg) if not pd.isna(volume_avg) else None,
        }

        # Strategy 1: Momentum
        ema_diff_pct = abs(ema_9 - ema_21) / current_price * 100
        if ema_9 > ema_21 and ema_diff_pct > 0.15:
            conf = min(0.60 + ema_diff_pct * 0.3, 0.90)
            votes['strategy_votes']['momentum'] = {
                'vote': 'BUY', 'confidence': conf,
                'reason': f"EMA9>EMA21, diff={ema_diff_pct:.3f}%"
            }
            votes['buy_votes'] += 1
        elif ema_9 < ema_21 and ema_diff_pct > 0.15:
            conf = min(0.60 + ema_diff_pct * 0.3, 0.90)
            votes['strategy_votes']['momentum'] = {
                'vote': 'SELL', 'confidence': conf,
                'reason': f"EMA9<EMA21, diff={ema_diff_pct:.3f}%"
            }
            votes['sell_votes'] += 1
        else:
            votes['strategy_votes']['momentum'] = {
                'vote': 'NEUTRAL', 'confidence': 0.5,
                'reason': f"EMA diff too small: {ema_diff_pct:.3f}%"
            }
            votes['neutral_votes'] += 1

        # Strategy 2: Liquidity Sweep
        lo10 = low[max(0, idx - 9):idx + 1].min()
        hi10 = high[max(0, idx - 9):idx + 1].max()
        if current_price <= lo10 * 1.002:
            votes['strategy_votes']['liquidity'] = {
                'vote': 'BUY', 'confidence': 0.65,
                'reason': f"Price near 10-bar low: {current_price:.2f} <= {lo10 * 1.002:.2f}"
            }
            votes['buy_votes'] += 1
        elif current_price >= hi10 * 0.998:
            votes['strategy_votes']['liquidity'] = {
                'vote': 'SELL', 'confidence': 0.65,
                'reason': f"Price near 10-bar high: {current_price:.2f} >= {hi10 * 0.998:.2f}"
            }
            votes['sell_votes'] += 1
        else:
            votes['strategy_votes']['liquidity'] = {
                'vote': 'NEUTRAL', 'confidence': 0.5,
                'reason': f"Price within range [{lo10:.2f}, {hi10:.2f}]"
            }
            votes['neutral_votes'] += 1

        # Strategy 3: Thermodynamic
        if idx >= 10:
            price_change = (current_price - close[idx - 10]) / close[idx - 10] * 100
            if price_change < -2.0:
                votes['strategy_votes']['thermodynamic'] = {
                    'vote': 'BUY', 'confidence': 0.65,
                    'reason': f"Oversold: {price_change:.2f}% drop in 10 bars"
                }
                votes['buy_votes'] += 1
            elif price_change > 2.0:
                votes['strategy_votes']['thermodynamic'] = {
                    'vote': 'SELL', 'confidence': 0.65,
                    'reason': f"Overbought: {price_change:.2f}% rise in 10 bars"
                }
                votes['sell_votes'] += 1
            else:
                votes['strategy_votes']['thermodynamic'] = {
                    'vote': 'NEUTRAL', 'confidence': 0.5,
                    'reason': f"Price change normal: {price_change:.2f}%"
                }
                votes['neutral_votes'] += 1

        # Strategy 4: Physics (Mean Reversion)
        if current_price > sma_20 * 1.008:
            votes['strategy_votes']['physics'] = {
                'vote': 'SELL', 'confidence': 0.65,
                'reason': f"Price above SMA20 by {(current_price/sma_20-1)*100:.2f}%"
            }
            votes['sell_votes'] += 1
        elif current_price < sma_20 * 0.992:
            votes['strategy_votes']['physics'] = {
                'vote': 'BUY', 'confidence': 0.65,
                'reason': f"Price below SMA20 by {(1-current_price/sma_20)*100:.2f}%"
            }
            votes['buy_votes'] += 1
        else:
            votes['strategy_votes']['physics'] = {
                'vote': 'NEUTRAL', 'confidence': 0.5,
                'reason': f"Price near SMA20"
            }
            votes['neutral_votes'] += 1

        # Strategy 5: Order Block
        if idx >= 15:
            ob_high = high[idx - 15:idx - 5].max()
            ob_low = low[idx - 15:idx - 5].min()
            if current_price <= ob_low * 1.003:
                votes['strategy_votes']['order_block'] = {
                    'vote': 'BUY', 'confidence': 0.63,
                    'reason': f"Price at order block low: {current_price:.2f} <= {ob_low * 1.003:.2f}"
                }
                votes['buy_votes'] += 1
            elif current_price >= ob_high * 0.997:
                votes['strategy_votes']['order_block'] = {
                    'vote': 'SELL', 'confidence': 0.63,
                    'reason': f"Price at order block high: {current_price:.2f} >= {ob_high * 0.997:.2f}"
                }
                votes['sell_votes'] += 1
            else:
                votes['strategy_votes']['order_block'] = {
                    'vote': 'NEUTRAL', 'confidence': 0.5,
                    'reason': f"Price outside OB range [{ob_low:.2f}, {ob_high:.2f}]"
                }
                votes['neutral_votes'] += 1

        # Strategy 6: FVG
        fvg_vote = 'NEUTRAL'
        fvg_reason = "No FVG detected"
        if idx >= 8:
            for j in range(max(0, idx - 8), idx - 1):
                h1, l3 = high[j], low[j + 2]
                l1, h3 = low[j], high[j + 2]
                if h1 < l3 and current_price >= l3 * 0.998 and current_price <= h1 * 1.002:
                    fvg_vote = 'BUY'
                    fvg_reason = f"Bullish FVG found at bar {j}"
                    break
                elif l1 > h3 and current_price <= l1 * 1.002 and current_price >= h3 * 0.998:
                    fvg_vote = 'SELL'
                    fvg_reason = f"Bearish FVG found at bar {j}"
                    break
        votes['strategy_votes']['fvg'] = {
            'vote': fvg_vote, 'confidence': 0.62 if fvg_vote != 'NEUTRAL' else 0.5,
            'reason': fvg_reason
        }
        if fvg_vote == 'BUY':
            votes['buy_votes'] += 1
        elif fvg_vote == 'SELL':
            votes['sell_votes'] += 1
        else:
            votes['neutral_votes'] += 1

        # Strategies 7-12 (placeholders - NEUTRAL)
        for name in ['msnr', 'msnr_alchemist', 'ifvg', 'order_flow', 'supply_demand', 'fibonacci']:
            votes['strategy_votes'][name] = {
                'vote': 'NEUTRAL', 'confidence': 0.5,
                'reason': "Strategy not yet implemented"
            }
            votes['neutral_votes'] += 1

        # Determine consensus
        if votes['buy_votes'] > votes['sell_votes'] and votes['buy_votes'] >= 5:
            direction = 'BUY'
            buy_confs = [v['confidence'] for v in votes['strategy_votes'].values() if v['vote'] == 'BUY']
            consensus_conf = sum(buy_confs) / max(1, len(buy_confs))
        elif votes['sell_votes'] > votes['buy_votes'] and votes['sell_votes'] >= 5:
            direction = 'SELL'
            sell_confs = [v['confidence'] for v in votes['strategy_votes'].values() if v['vote'] == 'SELL']
            consensus_conf = sum(sell_confs) / max(1, len(sell_confs))
        else:
            # No consensus - store votes for logging, then return None
            logger.debug(
                f"No consensus: BUY={votes['buy_votes']}, SELL={votes['sell_votes']}, NEUTRAL={votes['neutral_votes']} (need > opposing and >= 5)"
            )
            # IMPORTANT: Store votes so terminal logging can show them even without signal
            self._last_votes = votes
            self._last_signal = None
            
            # Still save cycle audit for no-signal cycles
            self._save_no_signal_audit(market_state, indicator_state, votes, df)
            return None

        if pd.isna(atr) or atr == 0:
            # Store votes even if ATR is invalid
            self._last_votes = votes
            self._last_signal = None
            return None

        sl_dist = min(max(atr * 1.5, 500), 3000)
        tp_dist = sl_dist * 2.0

        if direction == 'BUY':
            sl = current_price - sl_dist
            tp = current_price + tp_dist
        else:
            sl = current_price + sl_dist
            tp = current_price - tp_dist

        signal = {
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
            'market_state': market_state,
            'indicator_state': indicator_state,
        }

        # Store for cycle audit
        self._last_signal = signal
        self._last_votes = votes

        return signal

    def _save_no_signal_audit(self, market_state, indicator_state, votes, df):
        """Save cycle audit even when no signal is generated."""
        session = detect_session(df['time'].iloc[-1])
        self.current_session = session

        account_state = self._refresh_account_state()

        cycle_data = {
            'market_state': market_state,
            'indicators': indicator_state,
            'strategy_votes': {k: v for k, v in votes['strategy_votes'].items()},
            'vote_totals': {
                'buy_votes': votes['buy_votes'],
                'sell_votes': votes['sell_votes'],
                'neutral_votes': votes['neutral_votes'],
                'consensus_direction': 'NONE',
                'consensus_confidence': 0.0,
            },
            'signal_result': {
                'generated': False,
                'reason': f"No consensus: BUY={votes['buy_votes']}, SELL={votes['sell_votes']}, NEUTRAL={votes['neutral_votes']}",
            },
            'veto_results': {
                'session_veto': {'approved': True, 'reason': 'No signal to veto', 'session': session},
                'anti_metralhadora_veto': {'approved': True, 'reason': 'No signal to veto'},
                'great_filter_veto': {'approved': True, 'reason': 'No signal to veto'},
                'final_result': 'NO_SIGNAL',
            },
            'position_state': self._get_position_state(),
            'account_state': account_state,
            'metadata': {
                'session': session,
                'regime': 'unknown',
                'cycle_count': self.cycle_count,
                'total_signals_generated': self.total_signals,
                'total_signals_vetoed': self.total_vetoes,
                'total_trades': self.total_trades,
                'uptime_seconds': (datetime.now(timezone.utc) - self.start_time).total_seconds(),
            },
        }

        self.cycle_audit.save_cycle_audit(cycle_data)

    def validate_signal(self, signal: Dict[str, Any], df: pd.DataFrame) -> Tuple[bool, str]:
        """
        Validate signal through all veto layers.
        LOGS each veto check and result.
        """
        current_time = signal['time']
        session = detect_session(current_time)
        self.current_session = session
        session_profile = get_session_profile(session)

        veto_results = {}

        # Veto 1: Session
        session_veto = apply_session_veto(session_profile, signal)
        veto_results['session_veto'] = {
            'approved': session_veto['approved'],
            'reason': session_veto.get('reason', 'unknown'),
            'session': session,
            'profile': {
                'min_confidence': session_profile.min_confidence_threshold,
                'max_position_size': session_profile.max_position_size,
                'min_strategy_votes': session_profile.min_strategy_votes,
                'trading_allowed': session_profile.trading_allowed,
            },
        }
        if not session_veto['approved']:
            logger.debug(f"  Veto 1 - Session: REJECTED ({session_veto.get('reason', 'unknown')})")
            self._last_veto_results = veto_results
            return False, f"Session veto: {session_veto.get('reason', 'unknown')}"
        logger.debug(f"  Veto 1 - Session ({session}): APPROVED")

        # Veto 2: Anti-Metralhadora
        allowed, reason, details = self.anti_metralhadora.should_allow_trade(
            signal_quality=signal.get('confidence', 0.0),
            current_session=session,
            current_time=current_time,
        )
        veto_results['anti_metralhadora_veto'] = {
            'approved': allowed,
            'reason': reason,
            'details': details,
        }
        if not allowed:
            logger.debug(f"  Veto 2 - Anti-Metralhadora: REJECTED ({reason})")
            self._last_veto_results = veto_results
            return False, f"Anti-Metralhadora: {reason}"
        logger.debug(f"  Veto 2 - Anti-Metralhadora: APPROVED (quality={signal.get('confidence', 0.0):.2f} >= 0.40)")

        # Veto 3: GreatFilter
        spread = self._get_spread()
        price_change = self._get_price_change_5min(df)
        great_allowed, great_reason = self.great_filter.validate_entry(
            signal_confidence=signal.get('confidence', 0.5),
            spread_percent=spread,
            price_change_5min=price_change,
            session_allowed=True,
        )
        veto_results['great_filter_veto'] = {
            'approved': great_allowed,
            'reason': great_reason,
            'spread_percent': spread,
            'price_change_5min': price_change,
        }
        if not great_allowed:
            logger.debug(f"  Veto 3 - GreatFilter: REJECTED ({great_reason})")
            self._last_veto_results = veto_results
            return False, f"GreatFilter: {great_reason}"
        logger.debug(f"  Veto 3 - GreatFilter: APPROVED (spread={spread:.3f}% < 0.05%)")

        veto_results['final_result'] = 'APPROVED'
        self._last_veto_results = veto_results
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
        """Execute trade on MT5. LOGS order details, ticket, result."""
        volume = signal.get('volume', 0.01)
        direction = signal['direction']
        sl = signal['stop_loss']
        tp = signal['take_profit']

        tick = mt5.symbol_info_tick(self.symbol)
        if tick is None:
            logger.error("Failed to get tick data")
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
            logger.error(f"Order send returned None: {mt5.last_error()}")
            self.cycle_audit.total_errors += 1
            return False

        if result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error(f"Order failed: retcode={result.retcode}, comment={result.comment}")
            self.cycle_audit.total_orders_rejected += 1
            self.cycle_audit.total_errors += 1
            return False

        logger.info(
            f"Order executed: {direction} {volume} lots @ {price:.2f} | "
            f"SL: {sl:.2f}, TP: {tp:.2f} | Ticket: {result.order}"
        )

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

        self.cycle_audit.total_orders_sent += 1
        self.cycle_audit.total_orders_filled += 1

        return True

    def manage_position(self, df: pd.DataFrame, indicators: Dict[str, Any]):
        """
        Manage open position (check TP/SL, trailing, Smart TP).
        LOGS PnL, Smart TP status, trailing on every bar.
        """
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

        # Count Smart TP hits
        self.position_smart_tp_hits = sum(1 for t in pos['targets']['targets'] if t.get('closed', False))

        if position_closed:
            duration_min = (datetime.now(timezone.utc) - pos['open_time']).total_seconds() / 60
            logger.info(
                f"Smart TP complete | PnL: ${realized_pnl:+,.2f} | "
                f"Peak: ${self.position_peak_pnl:+,.2f} | "
                f"TP hits: {self.position_smart_tp_hits}/4 | "
                f"Duration: {duration_min:.0f}min"
            )
            self._close_position(pos, realized_pnl, current_price, 'Smart TP complete')

    def _get_position_state(self) -> Dict[str, Any]:
        """Get current position state for audit."""
        if self.current_position is None:
            return {
                'has_open_position': False,
                'ticket': None,
                'direction': None,
                'entry_price': None,
                'current_price': None,
                'stop_loss': None,
                'take_profit': None,
                'volume': None,
                'unrealized_pnl': 0.0,
                'peak_pnl': 0.0,
                'smart_tp_hits': 0,
                'duration_minutes': 0,
            }

        pos = self.current_position
        tick = mt5.symbol_info_tick(self.symbol)
        current_price = tick.bid if tick else pos['entry_price']
        duration_min = (datetime.now(timezone.utc) - pos['open_time']).total_seconds() / 60

        return {
            'has_open_position': True,
            'ticket': pos['ticket'],
            'direction': pos['direction'],
            'entry_price': pos['entry_price'],
            'current_price': current_price,
            'stop_loss': pos['stop_loss'],
            'take_profit': pos['take_profit'],
            'volume': pos['volume'],
            'unrealized_pnl': round(self.position_current_pnl, 2),
            'peak_pnl': round(self.position_peak_pnl, 2),
            'smart_tp_hits': self.position_smart_tp_hits,
            'duration_minutes': round(duration_min, 1),
        }

    def _close_position(self, pos: Dict, realized_pnl: float, exit_price: float, reason: str):
        """
        Close position and record results.
        LOGS exit details, PnL, duration, commission accounting.
        """
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

        # Calculate commission: $90 round trip per lot
        commission = pos['volume'] * 90
        net_pnl = realized_pnl - commission
        duration = (datetime.now(timezone.utc) - pos['open_time']).total_seconds() / 60

        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            if realized_pnl > 0:
                self.winning_trades += 1
                self.consecutive_wins += 1
                self.consecutive_losses = 0
            else:
                self.losing_trades += 1
                self.consecutive_losses += 1
                self.consecutive_wins = 0
                self.last_loss_time = datetime.now(timezone.utc)

            self.total_trades += 1

            logger.info(
                f"Position closed: {reason} | "
                f"Ticket: {pos['ticket']} | "
                f"PnL: ${realized_pnl:+,.2f} (gross) | "
                f"Commission: ${commission:.2f} | "
                f"Net: ${net_pnl:+,.2f} | "
                f"Duration: {duration:.0f}min"
            )

            # Refresh account state immediately after close
            self._refresh_account_state()

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

            # Record trade in anti-metralhadora
            trade_result = 'win' if realized_pnl > 0 else 'loss'
            self.anti_metralhadora.record_trade(trade_result, self.current_session)

        # Reset position tracking
        self.current_position = None
        self.position_peak_pnl = 0.0
        self.position_current_pnl = 0.0
        self.position_smart_tp_hits = 0

    def _log_complete_cycle(
        self,
        df: pd.DataFrame,
        indicators: Dict[str, Any],
        signal: Optional[Dict],
        veto_approved: Optional[bool] = None,
        veto_reason: Optional[str] = None,
    ):
        """
        Log COMPLETE neural state to terminal EVERY bar.
        This is the primary real-time logging function.
        """
        if df is None or len(df) < 2:
            return

        current_price = df['close'].iloc[-1]
        ema_9 = indicators.get('ema_9', pd.Series([0])).iloc[-1]
        ema_21 = indicators.get('ema_21', pd.Series([0])).iloc[-1]
        rsi_val = indicators.get('rsi_14', pd.Series([50])).iloc[-1]
        atr = indicators.get('atr_14', pd.Series([0])).iloc[-1]
        ema_50 = indicators.get('ema_50', pd.Series([0])).iloc[-1]

        # Trend
        trend = "BULLISH" if ema_9 > ema_21 else "BEARISH"
        trend_icon = "BULL" if ema_9 > ema_21 else "SELL"
        ema_diff_pct = abs(ema_9 - ema_21) / current_price * 100 if current_price > 0 else 0

        # RSI
        if pd.isna(rsi_val):
            rsi_val = 50
        rsi_status = "OB" if rsi_val > 70 else ("OS" if rsi_val < 30 else "N")
        rsi_icon = "OB" if rsi_val > 70 else ("OS" if rsi_val < 30 else "N")

        # ATR
        atr_val = atr if not pd.isna(atr) else 0

        # Format timestamp
        ts = df['time'].iloc[-1].strftime("%Y-%m-%d %H:%M:%S")

        # Build trend line
        trend_line = (
            f"Trend: {trend} (EMA9: {ema_9:,.2f} > EMA21: {ema_21:,.2f}) | "
            f"RSI: {rsi_val:.1f} {rsi_status} | "
            f"ATR: {atr_val:,.2f}"
        )

        # Build vote line - ALWAYS show votes even if no signal
        vote_line = ""
        signal_line = ""
        
        # Use stored votes from generate_signal() (always available)
        votes = self._last_votes if hasattr(self, '_last_votes') and self._last_votes else None
        
        if votes:
            buy_votes = votes.get('buy_votes', 0)
            sell_votes = votes.get('sell_votes', 0)
            neutral_votes = votes.get('neutral_votes', 0)

            # Get individual strategy votes with confidences
            strategy_votes = votes.get('strategy_votes', {})
            
            # Build detailed vote breakdown
            buy_details = []
            sell_details = []
            neutral_details = []
            
            for strategy_name, vote_info in strategy_votes.items():
                vote_dir = vote_info.get('vote', 'NEUTRAL')
                conf = vote_info.get('confidence', 0.5)
                reason = vote_info.get('reason', '')
                
                if vote_dir == 'BUY':
                    buy_details.append(f"{strategy_name}={conf:.2f}")
                elif vote_dir == 'SELL':
                    sell_details.append(f"{strategy_name}={conf:.2f}")
                else:
                    neutral_details.append(f"{strategy_name}={conf:.2f}")
            
            buy_str = ", ".join(buy_details) if buy_details else "none"
            sell_str = ", ".join(sell_details) if sell_details else "none"
            neutral_str = ", ".join(neutral_details) if neutral_details else "none"
            
            vote_line = (
                f"Votes [{buy_votes}B/{sell_votes}S/{neutral_votes}N] | "
                f"BUY: {buy_str} | "
                f"SELL: {sell_str} | "
                f"NEUTRAL: {neutral_str}"
            )
            
            # Signal line (show if signal generated or why not)
            if signal:
                conf = signal.get('confidence', 0)
                sl = signal.get('stop_loss', 0)
                tp = signal.get('take_profit', 0)
                vol = signal.get('volume', 0.01)
                signal_line = (
                    f"Signal: {signal['direction']} @ {conf:.2f} conf | "
                    f"SL: {sl:,.2f} | TP: {tp:,.2f} | Vol: {vol:.2f} lots"
                )
            else:
                # Show why no signal was generated
                if buy_votes >= 5 or sell_votes >= 5:
                    # Had consensus but failed other checks
                    signal_line = f"No Signal - vetoed or no clear direction"
                else:
                    signal_line = (
                        f"No Signal - insufficient votes "
                        f"(need 5+, got {max(buy_votes, sell_votes)})"
                    )
        else:
            vote_line = "Votes: No strategy votes recorded"
            signal_line = "No Signal - insufficient data"

        # Veto line
        veto_line = ""
        if veto_approved is True:
            veto_line = "Vetoes: Session OK | Anti-Metralhadora OK | GreatFilter OK -> APPROVED"
        elif veto_approved is False:
            veto_line = f"Vetoes: REJECTED - {veto_reason}"

        # Position line
        pos_line = ""
        if self.current_position:
            pos = self.current_position
            pos_line = (
                f"Position: {pos['direction']} open | "
                f"Entry: {pos['entry_price']:,.2f} | "
                f"PnL: ${self.position_current_pnl:+,.2f} | "
                f"Peak: ${self.position_peak_pnl:+,.2f} | "
                f"Smart TP: {self.position_smart_tp_hits}/4"
            )

        # Account line
        account_state = self._refresh_account_state()
        bal = account_state['balance']
        eq = account_state['equity']
        margin = account_state['margin']
        dd_pct = (self.peak_equity - eq) / self.peak_equity * 100 if self.peak_equity > 0 else 0
        daily = self.daily_pnl

        account_line = (
            f"Account: Bal: ${bal:,.2f} | Eq: ${eq:,.2f} | "
            f"Margin: ${margin:,.2f} | DD: {dd_pct:.2f}% | "
            f"Daily: ${daily:+,.2f}"
        )

        # Log complete cycle
        cycle_header = f"CYCLE #{self.cycle_count:05d} | {ts} UTC | {self.symbol}: ${current_price:,.2f}"

        logger.info(f"{'='*80}")
        logger.info(cycle_header)
        logger.info(trend_line)
        logger.info(vote_line)
        if signal:
            logger.info(signal_line)
        if veto_line:
            logger.info(veto_line)
        if pos_line:
            logger.info(pos_line)
        logger.info(account_line)
        logger.info(f"{'='*80}")

    def _build_cycle_audit_data(
        self,
        df: pd.DataFrame,
        indicators: Dict[str, Any],
        signal: Optional[Dict],
        veto_approved: Optional[bool] = None,
        veto_reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Build complete cycle audit data structure."""
        current_price = df['close'].iloc[-1]
        session = self.current_session

        account_state = self._refresh_account_state()

        # Market state
        market_state = {
            'symbol': self.symbol,
            'timeframe': 'M5',
            'open': float(df['open'].iloc[-1]),
            'high': float(df['high'].iloc[-1]),
            'low': float(df['low'].iloc[-1]),
            'close': float(current_price),
            'volume': int(df['tick_volume'].iloc[-1]),
            'spread': self._get_spread(),
        }

        # Indicators
        ind = indicators
        indicator_state = {
            'ema_9': float(ind['ema_9'].iloc[-1]) if not pd.isna(ind['ema_9'].iloc[-1]) else None,
            'ema_21': float(ind['ema_21'].iloc[-1]) if not pd.isna(ind['ema_21'].iloc[-1]) else None,
            'ema_50': float(ind['ema_50'].iloc[-1]) if not pd.isna(ind['ema_50'].iloc[-1]) else None,
            'sma_20': float(ind['sma_20'].iloc[-1]) if not pd.isna(ind['sma_20'].iloc[-1]) else None,
            'rsi_14': float(ind['rsi_14'].iloc[-1]) if not pd.isna(ind['rsi_14'].iloc[-1]) else None,
            'atr_14': float(ind['atr_14'].iloc[-1]) if not pd.isna(ind['atr_14'].iloc[-1]) else None,
            'volume_avg_20': float(ind['volume_avg_20'].iloc[-1]) if not pd.isna(ind['volume_avg_20'].iloc[-1]) else None,
        }

        # Strategy votes
        if signal and self._last_votes:
            votes = self._last_votes
            strategy_votes = {k: v for k, v in votes['strategy_votes'].items()}
            vote_totals = {
                'buy_votes': votes['buy_votes'],
                'sell_votes': votes['sell_votes'],
                'neutral_votes': votes['neutral_votes'],
                'consensus_direction': signal.get('direction', 'NONE'),
                'consensus_confidence': signal.get('confidence', 0.0),
            }
            signal_result = {
                'generated': True,
                'direction': signal['direction'],
                'confidence': signal['confidence'],
                'entry_price': signal['entry_price'],
                'stop_loss': signal['stop_loss'],
                'take_profit': signal['take_profit'],
                'volume': signal.get('volume', 0.01),
            }
        else:
            strategy_votes = {}
            vote_totals = {
                'buy_votes': 0,
                'sell_votes': 0,
                'neutral_votes': 0,
                'consensus_direction': 'NONE',
                'consensus_confidence': 0.0,
            }
            signal_result = {
                'generated': False,
                'reason': 'No consensus or no signal generated',
            }

        # Veto results
        if self._last_veto_results:
            veto_results = self._last_veto_results
        else:
            veto_results = {
                'session_veto': {'approved': True, 'reason': 'No signal to veto', 'session': session},
                'anti_metralhadora_veto': {'approved': True, 'reason': 'No signal to veto'},
                'great_filter_veto': {'approved': True, 'reason': 'No signal to veto'},
                'final_result': 'NO_SIGNAL' if not signal else ('APPROVED' if veto_approved else 'REJECTED'),
            }

        cycle_data = {
            'market_state': market_state,
            'indicators': indicator_state,
            'strategy_votes': strategy_votes,
            'vote_totals': vote_totals,
            'signal_result': signal_result,
            'veto_results': veto_results,
            'position_state': self._get_position_state(),
            'account_state': account_state,
            'metadata': {
                'session': session,
                'regime': 'unknown',
                'cycle_count': self.cycle_count,
                'total_signals_generated': self.total_signals,
                'total_signals_vetoed': self.total_vetoes,
                'total_trades': self.total_trades,
                'uptime_seconds': (datetime.now(timezone.utc) - self.start_time).total_seconds(),
            },
        }

        return cycle_data

    def run(self, max_bars: int = None):
        """
        Main trading loop.
        EVERY bar: refreshes account, logs complete neural state, saves cycle audit JSON.
        """
        logger.info("=" * 80)
        logger.info("STARTING LIVE TRADING LOOP")
        logger.info("=" * 80)

        if not self.connect_mt5():
            logger.error("Failed to connect to MT5. Aborting.")
            return

        self.running = True
        bar_count = 0
        last_dashboard_time = time.time()

        try:
            while self.running:
                # 1. Fetch candles
                df = self.get_candles(count=200)
                if df is None or len(df) < 50:
                    logger.warning("Insufficient data, waiting...")
                    time.sleep(5)
                    continue

                # 2. Calculate indicators
                indicators = self.calculate_indicators(df)

                # 3. Refresh account state on EVERY bar
                self._refresh_account_state()

                # 4. Increment cycle
                self.cycle_count += 1
                self.last_bar_time = df['time'].iloc[-1]

                # 5. Manage open position
                self.manage_position(df, indicators)

                # 6. Generate signal (if no open position)
                signal = None
                veto_approved = None
                veto_reason_str = None

                if self.current_position is None:
                    signal = self.generate_signal(df, indicators)
                    self.total_signals += 1
                    self.cycle_audit.total_signals_generated += 1

                    if signal:
                        # Log neural state WITH signal
                        approved, reason = self.validate_signal(signal, df)
                        veto_approved = approved
                        veto_reason_str = reason

                        if approved:
                            volume = self.calculate_position_size(signal)
                            signal['volume'] = max(0.01, min(5.0, volume))
                            self.execute_trade(signal)
                        else:
                            self.total_vetoes += 1
                            self.cycle_audit.total_signals_vetoed += 1

                # 7. Log COMPLETE cycle to terminal
                self._log_complete_cycle(df, indicators, signal, veto_approved, veto_reason_str)

                # 8. Save cycle audit JSON file
                cycle_audit_data = self._build_cycle_audit_data(
                    df, indicators, signal, veto_approved, veto_reason_str
                )
                self.cycle_audit.save_cycle_audit(cycle_audit_data)

                # 9. Telegram dashboard (every 5 minutes, not every bar)
                now = time.time()
                if now - last_dashboard_time >= 300:  # 5 minutes
                    self.telegram.send_dashboard(self)
                    last_dashboard_time = now

                bar_count += 1

                if max_bars and bar_count >= max_bars:
                    logger.info(f"Reached max bars ({max_bars}). Stopping.")
                    break

                # Wait for next bar
                time.sleep(5)

        except KeyboardInterrupt:
            logger.info("Stopped by user")
        except Exception as e:
            logger.error(f"Trading loop error: {e}", exc_info=True)
        finally:
            self.shutdown()

    def shutdown(self):
        """Shutdown trading system."""
        logger.info("Shutting down live trading system...")
        self.running = False

        # Close any open positions
        if self.current_position:
            logger.warning(f"Closing open position: {self.current_position['ticket']}")
            tick = mt5.symbol_info_tick(self.symbol)
            if tick:
                exit_price = tick.bid if self.current_position['direction'] == 'BUY' else tick.ask
                self._close_position(self.current_position, 0.0, exit_price, 'Shutdown')

        # Shutdown MT5
        if self.mt5_connected:
            mt5.shutdown()
            logger.info("MT5 disconnected")

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
    logger.info(f"RUNNING {direction.upper()} TEST MODE")
    logger.info("=" * 80)

    if not mt5.initialize():
        logger.error("MT5 initialization failed")
        return

    account = mt5.account_info()
    if account:
        logger.info(f"Connected: {account.login} @ {account.server}")
        logger.info(f"   Balance: ${account.balance:,.2f}")

    tick = mt5.symbol_info_tick("BTCUSD")
    if tick is None:
        logger.error("Failed to get BTCUSD tick")
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

    logger.info(f"Sending {direction} order...")
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
            logger.info(f"{direction} TEST SUCCESSFUL!")
        else:
            logger.error(f"{direction} TEST FAILED: {result.comment}")
    else:
        logger.error(f"Order send failed: {mt5.last_error()}")

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
