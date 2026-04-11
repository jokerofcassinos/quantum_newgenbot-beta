"""
Performance Tracker - Real-time trading performance monitoring
CEO: Qwen Code | Created: 2026-04-10

Tracks:
- P&L (realized and unrealized)
- Win rate over time
- Drawdown analysis
- Trade frequency
- Risk metrics
- Consistency tracking
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from loguru import logger


@dataclass
class TradeRecord:
    """Record of a single trade"""
    ticket: int
    timestamp: datetime
    symbol: str
    direction: str
    volume: float
    entry_price: float
    exit_price: Optional[float]
    sl: float
    tp: float
    pnl: float
    pnl_points: float
    duration_minutes: int
    exit_reason: str
    commission: float
    spread_cost: float
    net_pnl: float


class PerformanceTracker:
    """
    Real-time performance tracking system
    
    Provides:
    - P&L tracking (daily, weekly, monthly)
    - Win rate analysis
    - Drawdown monitoring
    - Trade statistics
    - Consistency metrics
    """
    
    def __init__(self, initial_capital: float = 100000.0):
        self.initial_capital = initial_capital
        self.current_equity = initial_capital
        self.peak_equity = initial_capital
        self.current_drawdown = 0.0
        self.max_drawdown = 0.0
        
        # Trade history
        self.trades: List[TradeRecord] = []
        
        # Time-based P&L
        self.daily_pnl: Dict[str, float] = {}
        self.weekly_pnl: Dict[str, float] = {}
        self.monthly_pnl: Dict[str, float] = {}
        
        # Rolling metrics
        self.rolling_win_rates = []
        self.rolling_profit_factors = []
        
        logger.info(f"📈 Performance Tracker initialized (${initial_capital:,.2f})")
    
    def record_trade(self, trade: TradeRecord):
        """Record a completed trade"""
        self.trades.append(trade)
        
        # Update equity
        self.current_equity += trade.net_pnl
        self.current_equity = max(0, self.current_equity)  # Don't go negative
        
        # Update peak and drawdown
        self.peak_equity = max(self.peak_equity, self.current_equity)
        
        if self.peak_equity > 0:
            self.current_drawdown = (self.peak_equity - self.current_equity) / self.peak_equity * 100
            self.max_drawdown = max(self.max_drawdown, self.current_drawdown)
        
        # Update daily P&L
        day_key = trade.timestamp.strftime('%Y-%m-%d')
        self.daily_pnl[day_key] = self.daily_pnl.get(day_key, 0) + trade.net_pnl
        
        # Update weekly P&L
        week_key = trade.timestamp.strftime('%Y-W%W')
        self.weekly_pnl[week_key] = self.weekly_pnl.get(week_key, 0) + trade.net_pnl
        
        # Update monthly P&L
        month_key = trade.timestamp.strftime('%Y-%m')
        self.monthly_pnl[month_key] = self.monthly_pnl.get(month_key, 0) + trade.net_pnl
        
        # Update rolling metrics (last 50 trades)
        if len(self.trades) >= 10:
            recent = self.trades[-50:]
            wins = sum(1 for t in recent if t.net_pnl > 0)
            win_rate = wins / len(recent)
            self.rolling_win_rates.append(win_rate)
        
        logger.info(f"📊 Trade recorded: {trade.direction} #{trade.ticket} | "
                   f"PnL: ${trade.net_pnl:+,.2f} | "
                   f"Equity: ${self.current_equity:,.2f}")
    
    def get_current_stats(self) -> Dict[str, Any]:
        """Get current performance statistics"""
        if not self.trades:
            return {
                'total_trades': 0,
                'current_equity': self.initial_capital,
                'net_pnl': 0,
                'win_rate': 0,
            }
        
        # Basic stats
        total_trades = len(self.trades)
        winning_trades = [t for t in self.trades if t.net_pnl > 0]
        losing_trades = [t for t in self.trades if t.net_pnl <= 0]
        
        win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0
        
        gross_profit = sum(t.net_pnl for t in winning_trades)
        gross_loss = abs(sum(t.net_pnl for t in losing_trades))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        # Averages
        avg_win = gross_profit / len(winning_trades) if winning_trades else 0
        avg_loss = gross_loss / len(losing_trades) if losing_trades else 0
        win_loss_ratio = avg_win / avg_loss if avg_loss > 0 else 0
        
        # Duration
        durations = [t.duration_minutes for t in self.trades if t.duration_minutes > 0]
        avg_duration = np.mean(durations) if durations else 0
        
        # Consecutive
        consec_wins, consec_losses = self._max_consecutive()
        
        return {
            'total_trades': total_trades,
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': win_rate,
            'current_equity': self.current_equity,
            'peak_equity': self.peak_equity,
            'net_pnl': self.current_equity - self.initial_capital,
            'net_pnl_percent': (self.current_equity / self.initial_capital - 1) * 100,
            'gross_profit': gross_profit,
            'gross_loss': gross_loss,
            'profit_factor': profit_factor,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'win_loss_ratio': win_loss_ratio,
            'avg_duration_minutes': avg_duration,
            'max_consecutive_wins': consec_wins,
            'max_consecutive_losses': consec_losses,
            'current_drawdown': self.current_drawdown,
            'max_drawdown': self.max_drawdown,
            'total_commissions': sum(t.commission for t in self.trades),
            'total_spread_costs': sum(t.spread_cost for t in self.trades),
        }
    
    def get_daily_summary(self, days: int = 7) -> Dict[str, Any]:
        """Get daily P&L summary"""
        recent_days = dict(list(self.daily_pnl.items())[-days:])
        
        profitable_days = sum(1 for pnl in recent_days.values() if pnl > 0)
        losing_days = sum(1 for pnl in recent_days.values() if pnl < 0)
        break_even_days = sum(1 for pnl in recent_days.values() if pnl == 0)
        
        return {
            'days': recent_days,
            'total_days': len(recent_days),
            'profitable_days': profitable_days,
            'losing_days': losing_days,
            'break_even_days': break_even_days,
            'profitable_percent': profitable_days / max(1, len(recent_days)) * 100,
            'avg_daily_pnl': np.mean(list(recent_days.values())) if recent_days else 0,
            'best_day': max(recent_days.values()) if recent_days else 0,
            'worst_day': min(recent_days.values()) if recent_days else 0,
        }
    
    def get_weekly_summary(self, weeks: int = 4) -> Dict[str, Any]:
        """Get weekly P&L summary"""
        recent_weeks = dict(list(self.weekly_pnl.items())[-weeks:])
        
        return {
            'weeks': recent_weeks,
            'total_weeks': len(recent_weeks),
            'net_pnl': sum(recent_weeks.values()),
            'avg_weekly_pnl': np.mean(list(recent_weeks.values())) if recent_weeks else 0,
            'best_week': max(recent_weeks.values()) if recent_weeks else 0,
            'worst_week': min(recent_weeks.values()) if recent_weeks else 0,
        }
    
    def get_equity_curve(self) -> List[Dict[str, Any]]:
        """Get equity curve data"""
        if not self.trades:
            return []
        
        equity = self.initial_capital
        curve = []
        
        for trade in self.trades:
            equity += trade.net_pnl
            curve.append({
                'timestamp': trade.timestamp.isoformat(),
                'equity': equity,
                'trade_number': len(curve) + 1,
                'pnl': trade.net_pnl,
            })
        
        return curve
    
    def _max_consecutive(self) -> tuple[int, int]:
        """Calculate max consecutive wins and losses"""
        if not self.trades:
            return 0, 0
        
        max_wins = 0
        max_losses = 0
        current_wins = 0
        current_losses = 0
        
        for trade in self.trades:
            if trade.net_pnl > 0:
                current_wins += 1
                current_losses = 0
                max_wins = max(max_wins, current_wins)
            else:
                current_losses += 1
                current_wins = 0
                max_losses = max(max_losses, current_losses)
        
        return max_wins, max_losses
