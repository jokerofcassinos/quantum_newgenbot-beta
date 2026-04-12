"""
Forex Quantum Bot - Telegram Dashboard v2.0
ULTRA-DETAILED interactive dashboard with buttons
CEO: Forex Quantum Bot | Created: 2026-04-12

Features:
- Interactive dashboards with inline buttons
- Real-time market analysis on button click
- Position monitoring with close buttons
- Order lifecycle notifications
- System status and metrics
- Neural state visualization
"""

import requests
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from loguru import logger
import json


class TelegramDashboardV2:
    """
    Professional Telegram dashboard with interactive buttons.
    """

    def __init__(self, config_path: str = "config/telegram-config.json"):
        self.config_path = config_path
        self.enabled = False
        self.bot_token = None
        self.chat_id = None
        self.last_message_id = None  # For editing messages

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
                    logger.info(f"✅ Telegram Dashboard V2 enabled")
        except Exception as e:
            logger.warning(f"⚠️ Telegram not configured: {e}")

    def _api_url(self, method: str) -> str:
        """Build Telegram API URL."""
        return f"https://api.telegram.org/bot{self.bot_token}/{method}"

    def send_message(self, text: str, parse_mode: str = "HTML", reply_markup: Dict = None) -> Optional[int]:
        """Send message and return message_id."""
        if not self.enabled:
            return None

        try:
            url = self._api_url("sendMessage")
            payload = {
                'chat_id': self.chat_id,
                'text': text,
                'parse_mode': parse_mode,
                'disable_web_page_preview': True,
            }
            if reply_markup:
                payload['reply_markup'] = json.dumps(reply_markup)

            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                msg_id = response.json().get('result', {}).get('message_id')
                self.last_message_id = msg_id
                return msg_id
        except Exception as e:
            logger.error(f"❌ Telegram send error: {e}")
        return None

    def edit_message(self, message_id: int, text: str, reply_markup: Dict = None):
        """Edit existing message."""
        if not self.enabled or not message_id:
            return

        try:
            url = self._api_url("editMessageText")
            payload = {
                'chat_id': self.chat_id,
                'message_id': message_id,
                'text': text,
                'parse_mode': 'HTML',
            }
            if reply_markup:
                payload['reply_markup'] = json.dumps(reply_markup)

            requests.post(url, json=payload, timeout=10)
        except Exception as e:
            logger.error(f"❌ Telegram edit error: {e}")

    def send_dashboard(self, engine: 'LiveTradingEngine') -> Optional[int]:
        """Send comprehensive system dashboard with buttons."""
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

        msg = (
            f"🚀 <b>FOREX QUANTUM BOT - LIVE</b>\n"
            f"{'─' * 42}\n"
            f"💰 <b>Account</b>\n"
            f"   Balance: ${balance:,.2f}\n"
            f"   Equity: ${equity:,.2f}\n"
            f"   P/L: <b>${profit:+,.2f}</b> ({profit_pct:+.2f}%)\n"
            f"   Free Margin: ${free_margin:,.2f}\n"
            f"   Level: {margin_level:.1f}%\n"
            f"\n"
            f"📈 <b>Performance</b>\n"
            f"   Trades: {engine.total_trades}\n"
            f"   Wins: {engine.winning_trades} ✅ | Losses: {engine.losing_trades} ❌\n"
            f"   Win Rate: <b>{win_rate:.1f}%</b>\n"
            f"   Streak: {engine.consecutive_wins}W / {engine.consecutive_losses}L\n"
            f"   Max DD: {engine.max_drawdown:.2f}%\n"
            f"   Current DD: {current_dd:.2f}%\n"
            f"\n"
            f"🤖 <b>System</b>\n"
            f"   Symbol: {engine.symbol}\n"
            f"   Uptime: {engine.get_uptime()}\n"
            f"   Vetoes: {engine.total_vetoes}\n"
            f"   Session: {engine.current_session}\n"
            f"\n"
            f"⏰ {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}"
        )

        keyboard = [
            [
                {"text": "📊 Analysis", "callback_data": "cmd:analysis"},
                {"text": "📋 Positions", "callback_data": "cmd:positions"},
            ],
            [
                {"text": "🎯 Signal", "callback_data": "cmd:signal"},
                {"text": "🧠 Neural", "callback_data": "cmd:neural"},
            ],
            [
                {"text": "📈 Metrics", "callback_data": "cmd:metrics"},
                {"text": "🛑 Close All", "callback_data": "cmd:close_all"},
            ],
        ]

        return self.send_message(msg, reply_markup={"inline_keyboard": keyboard})

    def send_order_opened(self, ticket: int, direction: str, volume: float,
                          entry: float, sl: float, tp: float, reason: str,
                          confidence: float, votes: Dict = None):
        """Send detailed order opened notification."""
        emoji = "🟢" if direction == "BUY" else "🔴"
        vote_info = ""
        if votes:
            vote_info = (
                f"\n🗳️ <b>Votes</b>\n"
                f"   BUY: {votes.get('buy_votes', 0)} | SELL: {votes.get('sell_votes', 0)} | NEUTRAL: {votes.get('neutral_votes', 0)}\n"
            )

        msg = (
            f"{emoji} <b>ORDER OPENED</b>\n"
            f"{'─' * 42}\n"
            f"🎫 Ticket: <code>{ticket}</code>\n"
            f"📊 Direction: <b>{direction}</b>\n"
            f"📦 Volume: <b>{volume:.2f} lots</b>\n"
            f"💰 Entry: <code>{entry:.2f}</code>\n"
            f"🛑 SL: <code>{sl:.2f}</code>\n"
            f"🎯 TP: <code>{tp:.2f}</code>\n"
            f"📝 Reason: {reason}\n"
            f"🎯 Confidence: {confidence:.2f}\n"
            f"{vote_info}"
            f"⏰ {datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}\n"
            f"\n"
            f"🤖 Managed by Smart TP + Trailing"
        )

        keyboard = [
            [
                {"text": "📊 Monitor", "callback_data": f"monitor:{ticket}"},
                {"text": "🛑 Close", "callback_data": f"close:{ticket}"},
            ],
        ]

        self.send_message(msg, reply_markup={"inline_keyboard": keyboard})

    def send_order_closed(self, ticket: int, direction: str, volume: float,
                          entry: float, exit_price: float, pnl: float,
                          commission: float, reason: str, duration_minutes: int,
                          smart_tp_hits: int = 0):
        """Send detailed order closed notification."""
        emoji = "✅" if pnl > 0 else "❌"
        pnl_emoji = "💰" if pnl > 0 else "💸"
        tp_info = f"\n🎯 Smart TP Hits: {smart_tp_hits}" if smart_tp_hits > 0 else ""

        msg = (
            f"{emoji} <b>ORDER CLOSED</b>\n"
            f"{'─' * 42}\n"
            f"🎫 Ticket: <code>{ticket}</code>\n"
            f"📊 Direction: <b>{direction}</b>\n"
            f"📦 Volume: <b>{volume:.2f} lots</b>\n"
            f"💰 Entry: <code>{entry:.2f}</code>\n"
            f"🚪 Exit: <code>{exit_price:.2f}</code>\n"
            f"{pnl_emoji} <b>P/L: ${pnl:+,.2f}</b>\n"
            f"💳 Commission: ${commission:,.2f}\n"
            f"📝 Reason: {reason}\n"
            f"⏱️ Duration: {duration_minutes} min\n"
            f"{tp_info}"
            f"{'─' * 42}\n"
            f"{'✅ WIN!' if pnl > 0 else '❌ LOSS'}"
        )

        self.send_message(msg)

    def send_market_analysis(self, df, indicators: Dict, votes: Dict, regime: str, session: str):
        """Send comprehensive market analysis."""
        current_price = df['close'].iloc[-1]
        ema_9 = indicators.get('ema_9', pd.Series([0])).iloc[-1]
        ema_21 = indicators.get('ema_21', pd.Series([0])).iloc[-1]
        rsi = indicators.get('rsi_14', pd.Series([50])).iloc[-1]
        atr = indicators.get('atr_14', pd.Series([0])).iloc[-1]

        trend = "📈 BULLISH" if ema_9 > ema_21 else "📉 BEARISH"
        rsi_status = "🔴 Overbought" if rsi > 70 else ("🟢 Oversold" if rsi < 30 else "⚪ Neutral")

        msg = (
            f"🧠 <b>MARKET ANALYSIS</b>\n"
            f"{'─' * 42}\n"
            f"💰 BTCUSD: <code>{current_price:,.2f}</code>\n"
            f"📊 Trend: {trend}\n"
            f"   EMA 9: <code>{ema_9:.2f}</code>\n"
            f"   EMA 21: <code>{ema_21:.2f}</code>\n"
            f"   Diff: {abs(ema_9 - ema_21):.2f} pts\n"
            f"\n"
            f"📈 RSI(14): <code>{rsi:.1f}</code> {rsi_status}\n"
            f"📊 ATR(14): <code>{atr:.2f}</code>\n"
            f"\n"
            f"🗳️ <b>Strategy Votes</b>\n"
            f"   🟢 BUY: {votes.get('buy_votes', 0)}\n"
            f"   🔴 SELL: {votes.get('sell_votes', 0)}\n"
            f"   ⚪ NEUTRAL: {votes.get('neutral_votes', 0)}\n"
            f"\n"
            f"🎯 Regime: <b>{regime}</b>\n"
            f"🕐 Session: <b>{session}</b>\n"
            f"\n"
            f"⏰ {datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}"
        )

        self.send_message(msg)

    def send_neural_state(self, engine: 'LiveTradingEngine'):
        """Send detailed neural machine state."""
        msg = (
            f"🧠 <b>NEURAL MACHINE STATE</b>\n"
            f"{'─' * 42}\n"
            f"🔄 Cycle: {engine.cycle_count}\n"
            f"🕐 Last Bar: {engine.last_bar_time}\n"
            f"\n"
            f"📊 <b>Signal Generation</b>\n"
            f"   Signals Generated: {engine.total_signals}\n"
            f"   Signals Vetoed: {engine.total_vetoes}\n"
            f"   Approval Rate: {(1 - engine.total_vetoes/max(1,engine.total_signals))*100:.1f}%\n"
            f"\n"
            f"🎯 <b>Position State</b>\n"
            f"   Open: {'Yes' if engine.current_position else 'No'}\n"
            f"   Peak PnL: ${engine.position_peak_pnl:+,.2f}\n"
            f"   Current PnL: ${engine.position_current_pnl:+,.2f}\n"
            f"   Smart TP: {engine.position_smart_tp_hits}/4 hits\n"
            f"\n"
            f"🛡️ <b>Risk State</b>\n"
            f"   Daily P/L: ${engine.daily_pnl:+,.2f}\n"
            f"   Daily Loss Used: {engine.daily_loss_used:.1f}%\n"
            f"   Total Loss Used: {engine.total_loss_used:.1f}%\n"
            f"   FTMO Daily: ${engine.ftmo_daily_remaining:,.0f} left\n"
            f"   FTMO Total: ${engine.ftmo_total_remaining:,.0f} left\n"
            f"\n"
            f"⏰ {datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}"
        )

        self.send_message(msg)

    def _get_account_info(self) -> Optional[Dict]:
        """Get MT5 account info."""
        try:
            import MetaTrader5 as mt5
            info = mt5.account_info()
            if info:
                return {
                    'balance': info.balance,
                    'equity': info.equity,
                    'margin': info.margin,
                    'margin_free': info.margin_free,
                    'margin_level': info.margin_level,
                }
        except:
            pass
        return None


# Need to import pd for the analysis method
import pandas as pd
