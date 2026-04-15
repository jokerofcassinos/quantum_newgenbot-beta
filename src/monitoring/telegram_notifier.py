"""
Telegram Notifier - Send notifications via Telegram
CEO: Qwen Code | Created: 2026-04-10

Features:
- Trade notifications
- Risk alerts
- Daily reports
- Emergency alerts
- Health status updates
"""

import requests
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from loguru import logger


class TelegramNotifier:
    """
    Telegram notification system
    
    Provides:
    - Trade execution alerts
    - Risk warnings
    - Daily/weekly reports
    - Emergency notifications
    - System health updates
    """
    
    def __init__(self, bot_token: Optional[str] = None, chat_id: Optional[str] = None):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.enabled = bool(bot_token and chat_id)
        
        self.base_url = f"https://api.telegram.org/bot{bot_token}" if bot_token else ""
        
        # Message queue (for batching)
        self.message_queue: List[str] = []
        self.last_send_time = None
        self.min_interval_seconds = 5  # Minimum 5 seconds between messages
        
        if self.enabled:
            logger.info(f" Telegram Notifier initialized")
        else:
            logger.warning(" Telegram not configured - notifications disabled")
    
    def send_message(self, message: str, parse_mode: str = "HTML") -> bool:
        """
        Send a message via Telegram
        
        Args:
            message: Message text (supports HTML)
            parse_mode: "HTML" or "Markdown"
        
        Returns:
            bool: True if sent successfully
        """
        if not self.enabled:
            logger.debug(" Telegram disabled - message skipped")
            return False
        
        # Check rate limit
        now = datetime.now(timezone.utc)
        if self.last_send_time:
            seconds_since_last = (now - self.last_send_time).total_seconds()
            if seconds_since_last < self.min_interval_seconds:
                # Queue message for later
                self.message_queue.append(message)
                logger.debug(f" Message queued (rate limit)")
                return False
        
        try:
            url = f"{self.base_url}/sendMessage"
            payload = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': parse_mode,
                'disable_web_page_preview': True,
            }
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                logger.info(f" Telegram message sent")
                self.last_send_time = now
                
                # Send queued messages
                self._flush_queue()
                
                return True
            else:
                logger.error(f" Telegram error: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f" Telegram send error: {e}")
            return False
    
    def _flush_queue(self):
        """Send queued messages"""
        while self.message_queue:
            message = self.message_queue.pop(0)
            self.send_message(message)
    
    def notify_trade_opened(self, trade: Dict[str, Any]):
        """Send trade opened notification"""
        message = f"""
 <b>TRADE ABERTO</b>

 <b>{trade.get('symbol', 'BTCUSD')}</b>
 Direo: <b>{trade.get('direction', 'BUY')}</b>
 Entry: <b>${trade.get('entry_price', 0):,.2f}</b>
 Stop: <b>${trade.get('sl', 0):,.2f}</b>
 Target: <b>${trade.get('tp', 0):,.2f}</b>

 Risk/Reward: <b>1:{trade.get('rr_ratio', 0):.2f}</b>
 Volume: <b>{trade.get('volume', 0):.2f} lots</b>
 Risco: <b>${trade.get('risk_amount', 0):,.2f}</b>

 Strategy: {trade.get('strategy', 'Unknown')}
 Time: {datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}
"""
        self.send_message(message.strip())
    
    def notify_trade_closed(self, trade: Dict[str, Any]):
        """Send trade closed notification"""
        pnl = trade.get('net_pnl', 0)
        emoji = "" if pnl > 0 else ""
        
        message = f"""
{emoji} <b>TRADE FECHADO</b>

 <b>{trade.get('symbol', 'BTCUSD')}</b>
 Direo: <b>{trade.get('direction', 'BUY')}</b>

 Entry: ${trade.get('entry_price', 0):,.2f}
 Exit: ${trade.get('exit_price', 0):,.2f}


 <b>P&L Lquido: ${pnl:+,.2f}</b>
 Pontos: {trade.get('pnl_points', 0):+,.0f}
 Durao: {trade.get('duration_minutes', 0)} min
 Exit: {trade.get('exit_reason', 'Unknown')}

 Comisso: ${trade.get('commission', 0):,.2f}
"""
        self.send_message(message.strip())
    
    def notify_risk_alert(self, alert: Dict[str, Any]):
        """Send risk alert notification"""
        severity = alert.get('severity', 'WARNING')
        
        if severity == 'CRITICAL':
            emoji = ""
        elif severity == 'WARNING':
            emoji = ""
        else:
            emoji = ""
        
        message = f"""
{emoji} <b>ALERTA DE RISCO</b>

 Severidade: <b>{severity}</b>

 {alert.get('message', 'Unknown issue')}

 Equity Atual: ${alert.get('equity', 0):,.2f}
 Drawdown: {alert.get('drawdown', 0):.2f}%
 Daily Loss: ${alert.get('daily_loss', 0):,.2f}

 {datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}
"""
        self.send_message(message.strip())
    
    def notify_daily_report(self, report: Dict[str, Any]):
        """Send daily performance report"""
        net_pnl = report.get('net_pnl', 0)
        emoji = "" if net_pnl > 0 else ""
        
        message = f"""
{emoji} <b>RELATRIO DIRIO</b>

 {datetime.now(timezone.utc).strftime('%Y-%m-%d')}

 <b>P&L do Dia: ${net_pnl:+,.2f}</b>
 Trades: {report.get('trades_today', 0)}
 Win Rate: {report.get('win_rate', 0)*100:.1f}%


 Equity: ${report.get('equity', 0):,.2f}
 Peak: ${report.get('peak_equity', 0):,.2f}
 Drawdown: {report.get('drawdown', 0):.2f}%

 Profit Factor: {report.get('profit_factor', 0):.2f}
 Comisses: ${report.get('total_commissions', 0):,.2f}


{report.get('message', '')}
"""
        self.send_message(message.strip())
    
    def notify_system_status(self, status: str, message: str):
        """Send system status update"""
        if status == 'healthy':
            emoji = ""
        elif status == 'warning':
            emoji = ""
        else:
            emoji = ""
        
        msg = f"""
{emoji} <b>SYSTEM STATUS</b>

Status: <b>{status.upper()}</b>

{message}

 {datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}
"""
        self.send_message(msg.strip())
    
    def notify_emergency(self, message: str):
        """Send emergency notification (bypasses rate limits)"""
        emergency_msg = f"""
 <b>EMERGENCY ALERT</b>


{message}

 {datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}
 <b>ATENO IMEDIATA REQUERIDA</b>
"""
        # Send immediately, bypass rate limit
        if self.enabled:
            try:
                url = f"{self.base_url}/sendMessage"
                payload = {
                    'chat_id': self.chat_id,
                    'text': emergency_msg.strip(),
                    'parse_mode': 'HTML',
                }
                requests.post(url, json=payload, timeout=10)
                logger.critical(f" Emergency notification sent")
            except Exception as e:
                logger.error(f" Emergency notification failed: {e}")




