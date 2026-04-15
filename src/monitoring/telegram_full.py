"""
Telegram Notification System - Complete integration
CEO: Qwen Code | Created: 2026-04-11

Features:
- Trade execution alerts
- Risk warnings
- Daily performance reports
- System health alerts
- Neural analysis summaries
"""

import requests
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from loguru import logger


class TelegramFullNotifier:
    """
    Complete Telegram notification system
    
    Setup:
    1. Create bot via @BotFather on Telegram
    2. Get bot token
    3. Get chat ID
    4. Save to config/telegram-config.json
    
    Config format:
    {
        "bot_token": "123456789:ABC...",
        "chat_id": "987654321"
    }
    """
    
    def __init__(self, config_path: str = "config/telegram-config.json"):
        self.config_path = config_path
        self.enabled = False
        self.bot_token = None
        self.chat_id = None
        
        # Load config
        try:
            import json
            from pathlib import Path
            if Path(config_path).exists():
                with open(config_path, 'r') as f:
                    config = json.load(f)
                
                self.bot_token = config.get('bot_token')
                self.chat_id = config.get('chat_id')
                
                if self.bot_token and self.chat_id:
                    self.enabled = True
                    logger.info(f" Telegram enabled")
                else:
                    logger.warning(" Telegram not configured (missing token or chat_id)")
            else:
                logger.warning(f" Telegram config not found at {config_path}")
        except Exception as e:
            logger.error(f" Failed to load Telegram config: {e}")
    
    def send_message(self, message: str, parse_mode: str = "HTML") -> bool:
        """Send a message to Telegram"""
        if not self.enabled:
            logger.debug(" Telegram disabled - message skipped")
            return False
        
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            payload = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': parse_mode,
                'disable_web_page_preview': True,
            }
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                logger.info(f" Telegram message sent")
                return True
            else:
                logger.error(f" Telegram error: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f" Telegram send error: {e}")
            return False
    
    def send_trade_alert(self, trade: Dict[str, Any]):
        """Send trade execution alert"""
        emoji = "" if trade.get('direction') == 'BUY' else ""
        
        message = f"""
{emoji} <b>TRADE EXECUTED</b>

 <b>BTCUSD {trade.get('direction', 'UNKNOWN')}</b>
 Entry: <b>${trade.get('entry_price', 0):,.2f}</b>
 SL: ${trade.get('stop_loss', 0):,.2f}
 TP: ${trade.get('take_profit', 0):,.2f}

 Size: {trade.get('volume', 0):.2f} lots
 Risk: ${trade.get('risk_amount', 0):,.2f}
 R:R: 1:{trade.get('rr_ratio', 0):.1f}

 Profile: {trade.get('profile', 'Unknown')}
 Coherence: {trade.get('coherence', 0):.2f}
 Consensus: {trade.get('consensus', 0):+.2f}

 {datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}
"""
        self.send_message(message.strip())
    
    def send_trade_close(self, trade: Dict[str, Any]):
        """Send trade closure alert"""
        pnl = trade.get('net_pnl', 0)
        emoji = "" if pnl > 0 else ""
        
        message = f"""
{emoji} <b>TRADE CLOSED</b>

 <b>BTCUSD {trade.get('direction', 'UNKNOWN')}</b>
 Entry: ${trade.get('entry_price', 0):,.2f}
 Exit: ${trade.get('exit_price', 0):,.2f}

 <b>P&L: ${pnl:+,.2f}</b>
 Points: {trade.get('pnl_points', 0):+,.0f}
 Duration: {trade.get('duration_minutes', 0)} min

 Reason: {trade.get('exit_reason', 'Unknown')}

 {datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}
"""
        self.send_message(message.strip())
    
    def send_risk_alert(self, alert: Dict[str, Any]):
        """Send risk warning"""
        severity = alert.get('severity', 'WARNING')
        
        if severity == 'CRITICAL':
            emoji = ""
        elif severity == 'WARNING':
            emoji = ""
        else:
            emoji = ""
        
        message = f"""
{emoji} <b>RISK ALERT</b>

 Severity: <b>{severity}</b>

 {alert.get('message', 'Unknown issue')}

 Equity: ${alert.get('equity', 0):,.2f}
 Drawdown: {alert.get('drawdown', 0):.2f}%
 Daily Loss: ${alert.get('daily_loss', 0):,.2f}

 {datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}
"""
        self.send_message(message.strip())
    
    def send_daily_report(self, report: Dict[str, Any]):
        """Send daily performance report"""
        net_pnl = report.get('net_pnl', 0)
        emoji = "" if net_pnl > 0 else ""
        
        message = f"""
{emoji} <b>DAILY REPORT</b>

 {datetime.now(timezone.utc).strftime('%Y-%m-%d')}

 <b>P&L: ${net_pnl:+,.2f}</b>
 Trades: {report.get('trades_today', 0)}
 Win Rate: {report.get('win_rate', 0)*100:.1f}%
 Profit Factor: {report.get('profit_factor', 0):.2f}


 Equity: ${report.get('equity', 0):,.2f}
 Peak: ${report.get('peak_equity', 0):,.2f}
 Drawdown: {report.get('drawdown', 0):.2f}%

 DNA Mutations: {report.get('dna_mutations', 0)}
 Avg Coherence: {report.get('avg_coherence', 0):.2f}


{report.get('message', '')}
"""
        self.send_message(message.strip())
    
    def send_system_health(self, status: str, message: str):
        """Send system health alert"""
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




