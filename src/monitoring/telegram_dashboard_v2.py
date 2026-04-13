"""
Forex Quantum Bot - Telegram Dashboard v3.0
ULTRA-DETAILED interactive dashboard with EDITING (no spam) + callback handlers
CEO: Forex Quantum Bot | Created: 2026-04-12

Features:
- SENDS ONE message and EDITS it (no spam!)
- Interactive buttons with callback handlers
- Real-time market analysis on button click
- Position monitoring with close buttons
- Order lifecycle notifications
- System status and metrics
- Neural state visualization
"""

import requests
import MetaTrader5 as mt5
import pandas as pd
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from loguru import logger
import json
import time


class TelegramDashboardV2:
    """
    Professional Telegram dashboard with EDITING (no spam) and interactive buttons.
    Sends ONE dashboard message and edits it on every update.
    """

    def __init__(self, config_path: str = "config/telegram-config.json"):
        self.config_path = config_path
        self.enabled = False
        self.bot_token = None
        self.chat_id = None
        self.dashboard_message_id = None  # Persistent message ID for editing
        self.last_callback_time = 0
        self.callback_cooldown = 3  # seconds between callback calls

        # Load config
        try:
            from pathlib import Path
            if Path(config_path).exists():
                with open(config_path, 'r') as f:
                    config = json.load(f)
                self.bot_token = config.get('bot_token')
                self.chat_id = config.get('chat_id')
                if self.bot_token and self.chat_id:
                    self.enabled = True
                    logger.info("Telegram Dashboard V3 enabled (EDIT mode, no spam)")
        except Exception as e:
            logger.warning(f"Telegram not configured: {e}")

    def _api_url(self, method: str) -> str:
        """Build Telegram API URL."""
        return f"https://api.telegram.org/bot{self.bot_token}/{method}"

    def _api_call(self, method: str, payload: Dict) -> Optional[Dict]:
        """Make Telegram API call with error handling."""
        if not self.enabled:
            return None

        try:
            url = self._api_url(method)
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Telegram API {method} failed: {response.status_code} - {response.text[:200]}")
                return None
        except Exception as e:
            logger.error(f"Telegram API error ({method}): {e}")
            return None

    def send_message(self, text: str, parse_mode: str = "HTML", reply_markup: Dict = None) -> Optional[int]:
        """Send a NEW message and return message_id. Only use for events (trades, alerts)."""
        if not self.enabled:
            return None

        payload = {
            'chat_id': self.chat_id,
            'text': text,
            'parse_mode': parse_mode,
            'disable_web_page_preview': True,
        }
        if reply_markup:
            payload['reply_markup'] = json.dumps(reply_markup)

        result = self._api_call("sendMessage", payload)
        if result:
            msg_id = result.get('result', {}).get('message_id')
            return msg_id
        return None

    def edit_message(self, message_id: int, text: str, reply_markup: Dict = None) -> bool:
        """Edit an EXISTING message. This is the PRIMARY update method for dashboard."""
        if not self.enabled or not message_id:
            return False

        payload = {
            'chat_id': self.chat_id,
            'message_id': message_id,
            'text': text,
            'parse_mode': 'HTML',
            'disable_web_page_preview': True,
        }
        if reply_markup:
            payload['reply_markup'] = json.dumps(reply_markup)

        result = self._api_call("editMessageText", payload)
        if result is None:
            # Message might have been deleted or edit too frequent - try to resend
            logger.debug("Edit failed, will try to send new message on next update")
            return False
        return True

    def send_dashboard(self, engine: 'LiveTradingEngine') -> Optional[int]:
        """
        Send or EDIT the system dashboard.
        FIRST call: sends new message and stores message_id.
        SUBSEQUENT calls: edits the existing message (NO SPAM).
        """
        account_info = self._get_account_info()
        if not account_info:
            return None

        equity = account_info.get('equity', 0)
        balance = account_info.get('balance', 0)
        profit = equity - balance
        profit_pct = (profit / balance) * 100 if balance > 0 else 0
        margin_level = account_info.get('margin_level', 0)
        free_margin = account_info.get('margin_free', 0)

        win_rate = (engine.winning_trades / max(1, engine.total_trades)) * 100 if engine.total_trades > 0 else 0
        current_dd = (engine.peak_equity - engine.equity) / max(1, engine.peak_equity) * 100 if engine.peak_equity > 0 else 0

        # Position status
        if engine.current_position:
            pos_status = (
                f"  Open: {engine.current_position['direction']} @ {engine.current_position['entry_price']:,.2f}\n"
                f"  PnL: ${engine.position_current_pnl:+,.2f} | Peak: ${engine.position_peak_pnl:+,.2f}\n"
                f"  Smart TP: {engine.position_smart_tp_hits}/4"
            )
        else:
            pos_status = "  No open position"

        msg = (
            f"FOREX QUANTUM BOT - LIVE DASHBOARD\n"
            f"{'=' * 42}\n"
            f"Account\n"
            f"   Balance: ${balance:,.2f}\n"
            f"   Equity: ${equity:,.2f}\n"
            f"   P/L: ${profit:+,.2f} ({profit_pct:+.2f}%)\n"
            f"   Free Margin: ${free_margin:,.2f}\n"
            f"   Level: {margin_level:.1f}%\n"
            f"\n"
            f"Performance\n"
            f"   Trades: {engine.total_trades}\n"
            f"   Wins: {engine.winning_trades} | Losses: {engine.losing_trades}\n"
            f"   Win Rate: {win_rate:.1f}%\n"
            f"   Streak: {engine.consecutive_wins}W / {engine.consecutive_losses}L\n"
            f"   Max DD: {engine.max_drawdown:.2f}%\n"
            f"   Current DD: {current_dd:.2f}%\n"
            f"\n"
            f"System\n"
            f"   Symbol: {engine.symbol}\n"
            f"   Uptime: {engine.get_uptime()}\n"
            f"   Cycles: {engine.cycle_count}\n"
            f"   Signals: {engine.total_signals} | Vetoes: {engine.total_vetoes}\n"
            f"   Session: {engine.current_session}\n"
            f"\n"
            f"Position\n"
            f"{pos_status}\n"
            f"\n"
            f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}"
        )

        keyboard = [
            [
                {"text": "Analysis", "callback_data": "cmd:analysis"},
                {"text": "Positions", "callback_data": "cmd:positions"},
            ],
            [
                {"text": "Signal", "callback_data": "cmd:signal"},
                {"text": "Neural", "callback_data": "cmd:neural"},
            ],
            [
                {"text": "Metrics", "callback_data": "cmd:metrics"},
                {"text": "Close All", "callback_data": "cmd:close_all"},
            ],
        ]

        reply_markup = {"inline_keyboard": keyboard}

        # Try to edit existing message first
        if self.dashboard_message_id is not None:
            success = self.edit_message(self.dashboard_message_id, msg, reply_markup)
            if success:
                return self.dashboard_message_id
            # If edit failed, fall through to send new message

        # Send new message (first time or after failure)
        msg_id = self.send_message(msg, reply_markup=reply_markup)
        if msg_id:
            self.dashboard_message_id = msg_id
        return msg_id

    def send_order_opened(self, ticket: int, direction: str, volume: float,
                          entry: float, sl: float, tp: float, reason: str,
                          confidence: float, votes: Dict = None):
        """Send detailed order opened notification (NEW message for events)."""
        emoji = "BUY" if direction == "BUY" else "SELL"
        vote_info = ""
        if votes:
            vote_info = (
                f"\nVotes\n"
                f"   BUY: {votes.get('buy_votes', 0)} | SELL: {votes.get('sell_votes', 0)} | NEUTRAL: {votes.get('neutral_votes', 0)}\n"
            )

        msg = (
            f"ORDER OPENED\n"
            f"{'=' * 42}\n"
            f"Ticket: {ticket}\n"
            f"Direction: {direction}\n"
            f"Volume: {volume:.2f} lots\n"
            f"Entry: {entry:.2f}\n"
            f"SL: {sl:.2f}\n"
            f"TP: {tp:.2f}\n"
            f"Reason: {reason}\n"
            f"Confidence: {confidence:.2f}\n"
            f"{vote_info}"
            f"{datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}\n"
            f"\n"
            f"Managed by Smart TP + Trailing"
        )

        keyboard = [
            [
                {"text": "Monitor", "callback_data": f"monitor:{ticket}"},
                {"text": "Close", "callback_data": f"close:{ticket}"},
            ],
        ]

        self.send_message(msg, reply_markup={"inline_keyboard": keyboard})

    def send_order_closed(self, ticket: int, direction: str, volume: float,
                          entry: float, exit_price: float, pnl: float,
                          commission: float, reason: str, duration_minutes: int,
                          smart_tp_hits: int = 0):
        """Send detailed order closed notification (NEW message for events)."""
        pnl_sign = "+" if pnl > 0 else ""
        tp_info = f"\nSmart TP Hits: {smart_tp_hits}" if smart_tp_hits > 0 else ""

        msg = (
            f"ORDER CLOSED\n"
            f"{'=' * 42}\n"
            f"Ticket: {ticket}\n"
            f"Direction: {direction}\n"
            f"Volume: {volume:.2f} lots\n"
            f"Entry: {entry:.2f}\n"
            f"Exit: {exit_price:.2f}\n"
            f"P/L: ${pnl_sign}{pnl:,.2f}\n"
            f"Commission: ${commission:,.2f}\n"
            f"Net P/L: ${pnl_sign}{pnl - commission:,.2f}\n"
            f"Reason: {reason}\n"
            f"Duration: {duration_minutes} min\n"
            f"{tp_info}"
            f"{'=' * 42}\n"
            f"{'WIN!' if pnl > 0 else 'LOSS'}"
        )

        self.send_message(msg)

    def handle_callback(self, callback_data: str, engine: 'LiveTradingEngine') -> str:
        """
        Handle button callback queries.
        Returns response text to send back to user.
        """
        # Cooldown to prevent spam
        now = time.time()
        if now - self.last_callback_time < self.callback_cooldown:
            return "Please wait a few seconds before clicking again."
        self.last_callback_time = now

        if callback_data == "cmd:analysis":
            return self._cmd_analysis(engine)
        elif callback_data == "cmd:positions":
            return self._cmd_positions(engine)
        elif callback_data == "cmd:signal":
            return self._cmd_signal(engine)
        elif callback_data == "cmd:neural":
            return self._cmd_neural(engine)
        elif callback_data == "cmd:metrics":
            return self._cmd_metrics(engine)
        elif callback_data == "cmd:close_all":
            return self._cmd_close_all(engine)
        elif callback_data.startswith("monitor:"):
            ticket = int(callback_data.split(":")[1])
            return self._cmd_monitor_ticket(engine, ticket)
        elif callback_data.startswith("close:"):
            ticket = int(callback_data.split(":")[1])
            return self._cmd_close_ticket(engine, ticket)
        else:
            return f"Unknown command: {callback_data}"

    def _cmd_analysis(self, engine: 'LiveTradingEngine') -> str:
        """Market analysis command."""
        df = engine.get_candles(count=200)
        if df is None or len(df) < 50:
            return "Insufficient data for analysis."

        indicators = engine.calculate_indicators(df)
        current_price = df['close'].iloc[-1]
        ema_9 = indicators.get('ema_9', pd.Series([0])).iloc[-1]
        ema_21 = indicators.get('ema_21', pd.Series([0])).iloc[-1]
        rsi_val = indicators.get('rsi_14', pd.Series([50])).iloc[-1]
        atr = indicators.get('atr_14', pd.Series([0])).iloc[-1]

        if pd.isna(rsi_val):
            rsi_val = 50
        if pd.isna(atr):
            atr = 0

        trend = "BULLISH" if ema_9 > ema_21 else "BEARISH"
        rsi_status = "Overbought" if rsi_val > 70 else ("Oversold" if rsi_val < 30 else "Neutral")

        # Last 5 candles
        last_5 = df.tail(5)[['time', 'open', 'high', 'low', 'close']]
        candles_str = ""
        for _, row in last_5.iterrows():
            candles_str += f"  {row['time'].strftime('%H:%M')} O:{row['open']:,.2f} H:{row['high']:,.2f} L:{row['low']:,.2f} C:{row['close']:,.2f}\n"

        msg = (
            f"MARKET ANALYSIS - {engine.symbol}\n"
            f"{'=' * 42}\n"
            f"Price: {current_price:,.2f}\n"
            f"Trend: {trend}\n"
            f"  EMA 9: {ema_9:,.2f}\n"
            f"  EMA 21: {ema_21:,.2f}\n"
            f"  Diff: {abs(ema_9 - ema_21):.2f} pts\n"
            f"\n"
            f"RSI(14): {rsi_val:.1f} - {rsi_status}\n"
            f"ATR(14): {atr:,.2f}\n"
            f"\n"
            f"Last 5 Candles:\n"
            f"{candles_str}"
            f"\n"
            f"Session: {engine.current_session}\n"
            f"{datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}"
        )
        return msg

    def _cmd_positions(self, engine: 'LiveTradingEngine') -> str:
        """Position status command."""
        if engine.current_position:
            pos = engine.current_position
            duration_min = (datetime.now(timezone.utc) - pos['open_time']).total_seconds() / 60
            msg = (
                f"POSITION STATUS\n"
                f"{'=' * 42}\n"
                f"Ticket: {pos['ticket']}\n"
                f"Direction: {pos['direction']}\n"
                f"Entry: {pos['entry_price']:,.2f}\n"
                f"SL: {pos['stop_loss']:,.2f}\n"
                f"TP: {pos['take_profit']:,.2f}\n"
                f"Volume: {pos['volume']:.2f} lots\n"
                f"Duration: {duration_min:.0f} min\n"
                f"Current PnL: ${engine.position_current_pnl:+,.2f}\n"
                f"Peak PnL: ${engine.position_peak_pnl:+,.2f}\n"
                f"Smart TP Hits: {engine.position_smart_tp_hits}/4"
            )
        else:
            msg = "No open positions."
        return msg

    def _cmd_signal(self, engine: 'LiveTradingEngine') -> str:
        """Last signal info."""
        if engine._last_signal:
            sig = engine._last_signal
            votes = sig.get('votes', {})
            msg = (
                f"LAST SIGNAL\n"
                f"{'=' * 42}\n"
                f"Direction: {sig['direction']}\n"
                f"Confidence: {sig['confidence']:.2f}\n"
                f"Entry: {sig['entry_price']:,.2f}\n"
                f"SL: {sig['stop_loss']:,.2f}\n"
                f"TP: {sig['take_profit']:,.2f}\n"
                f"Volume: {sig.get('volume', 0.01):.2f} lots\n"
                f"Votes: BUY={sig.get('buy_votes', 0)} SELL={sig.get('sell_votes', 0)} NEUTRAL={sig.get('neutral_votes', 0)}"
            )
        else:
            msg = "No recent signal."
        return msg

    def _cmd_neural(self, engine: 'LiveTradingEngine') -> str:
        """Neural state info."""
        msg = (
            f"NEURAL MACHINE STATE\n"
            f"{'=' * 42}\n"
            f"Cycle: {engine.cycle_count}\n"
            f"Last Bar: {engine.last_bar_time}\n"
            f"\n"
            f"Signal Generation\n"
            f"   Signals Generated: {engine.total_signals}\n"
            f"   Signals Vetoed: {engine.total_vetoes}\n"
            f"   Approval Rate: {(1 - engine.total_vetoes/max(1,engine.total_signals))*100:.1f}%\n"
            f"\n"
            f"Position State\n"
            f"   Open: {'Yes' if engine.current_position else 'No'}\n"
            f"   Peak PnL: ${engine.position_peak_pnl:+,.2f}\n"
            f"   Current PnL: ${engine.position_current_pnl:+,.2f}\n"
            f"   Smart TP: {engine.position_smart_tp_hits}/4 hits\n"
            f"\n"
            f"Risk State\n"
            f"   Daily P/L: ${engine.daily_pnl:+,.2f}\n"
            f"   Daily Loss Used: {engine.daily_loss_used:.1f}%\n"
            f"   Total Loss Used: {engine.total_loss_used:.1f}%\n"
            f"   FTMO Daily: ${engine.ftmo_daily_remaining:,.0f} left\n"
            f"   FTMO Total: ${engine.ftmo_total_remaining:,.0f} left\n"
            f"\n"
            f"{datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}"
        )
        return msg

    def _cmd_metrics(self, engine: 'LiveTradingEngine') -> str:
        """Performance metrics."""
        win_rate = (engine.winning_trades / max(1, engine.total_trades)) * 100 if engine.total_trades > 0 else 0
        profit_factor = 0.0  # Would need trade history to calculate

        msg = (
            f"PERFORMANCE METRICS\n"
            f"{'=' * 42}\n"
            f"Total Trades: {engine.total_trades}\n"
            f"Wins: {engine.winning_trades}\n"
            f"Losses: {engine.losing_trades}\n"
            f"Win Rate: {win_rate:.1f}%\n"
            f"Streak: {engine.consecutive_wins}W / {engine.consecutive_losses}L\n"
            f"Max DD: {engine.max_drawdown:.2f}%\n"
            f"Signals Generated: {engine.total_signals}\n"
            f"Signals Vetoed: {engine.total_vetoes}\n"
            f"Cycles: {engine.cycle_count}\n"
            f"Uptime: {engine.get_uptime()}\n"
            f"\n"
            f"Cycle Audit\n"
            f"   Session: {engine.cycle_audit.session_id}\n"
            f"   Candles: {engine.cycle_audit.total_candles_processed}\n"
            f"   Orders Sent: {engine.cycle_audit.total_orders_sent}\n"
            f"   Orders Filled: {engine.cycle_audit.total_orders_filled}\n"
            f"   Errors: {engine.cycle_audit.total_errors}\n"
            f"\n"
            f"{datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}"
        )
        return msg

    def _cmd_close_all(self, engine: 'LiveTradingEngine') -> str:
        """Close all positions warning."""
        if engine.current_position:
            return f"WARNING: This would close position {engine.current_position['ticket']}. Use the MT5 terminal to close positions manually for safety."
        else:
            return "No open positions to close."

    def _cmd_monitor_ticket(self, engine: 'LiveTradingEngine', ticket: int) -> str:
        """Monitor specific ticket."""
        if engine.current_position and engine.current_position['ticket'] == ticket:
            return self._cmd_positions(engine)
        else:
            return f"Position {ticket} not found or already closed."

    def _cmd_close_ticket(self, engine: 'LiveTradingEngine', ticket: int) -> str:
        """Close specific ticket warning."""
        return f"To close position {ticket}, please use the MT5 terminal directly for safety."

    def _get_account_info(self) -> Optional[Dict]:
        """Get MT5 account info."""
        try:
            info = mt5.account_info()
            if info:
                return {
                    'balance': info.balance,
                    'equity': info.equity,
                    'margin': info.margin,
                    'margin_free': info.margin_free,
                    'margin_level': info.margin_level,
                }
        except Exception as e:
            logger.warning(f"Failed to get account info: {e}")
        return None


# Need to import pd for the analysis method
import pandas as pd
