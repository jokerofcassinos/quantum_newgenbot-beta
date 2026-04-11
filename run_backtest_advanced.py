"""
Advanced Backtest - With Smart Order Manager integration
CEO: Qwen Code | Created: 2026-04-10

This backtest includes:
- Smart Order Manager (Virtual TP + Dynamic SL)
- Market momentum analysis
- DNA-adjusted profit profiles
- Realistic FTMO costs
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from loguru import logger

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.core.config_manager import ConfigManager
from src.backtesting.backtester import BacktestEngine, BacktestConfig
from src.backtesting.report_generator import ReportGenerator
from src.execution.smart_order_manager import SmartOrderManager


def setup_logging():
    """Configure logging"""
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )


def generate_realistic_btcusd_data(days: int = 180) -> pd.DataFrame:
    """Generate realistic BTCUSD data with realistic patterns"""
    
    logger.info(f"🔬 Generating {days} days of realistic BTCUSD data...")
    
    np.random.seed(42)
    bars_per_day = 288
    total_bars = days * bars_per_day
    start_price = 73000.0
    
    # Random walk with mean reversion and volatility clustering
    prices = [start_price]
    current_vol = 150.0  # Initial volatility
    
    for i in range(1, total_bars):
        # Volatility clustering (GARCH-like)
        current_vol = 0.9 * current_vol + 0.1 * 150 + np.random.normal(0, 10)
        current_vol = max(50, min(300, current_vol))
        
        # Random walk with mean reversion
        deviation = prices[-1] - 73000
        reversion = -deviation * 0.0005
        
        # Add trends (regime changes)
        regime = (i // 10000) % 4  # Change regime every ~35 days
        if regime == 0:
            trend = 5  # Slight bullish
        elif regime == 1:
            trend = -5  # Slight bearish
        elif regime == 2:
            trend = 15  # Strong bullish
        else:
            trend = -15  # Strong bearish
        
        change = trend + reversion + np.random.normal(0, current_vol)
        new_price = max(60000, min(90000, prices[-1] + change))
        prices.append(new_price)
    
    # Build candles
    candles = []
    current_time = datetime.now() - timedelta(days=days)
    current_time = current_time.replace(hour=0, minute=0, second=0)
    
    for i in range(total_bars):
        open_p = prices[i]
        close_p = prices[i+1] if i+1 < len(prices) else prices[i]
        
        # Realistic high/low
        bar_range = abs(np.random.normal(0, current_vol * 0.5))
        high_p = max(open_p, close_p) + bar_range
        low_p = min(open_p, close_p) - bar_range
        
        # Volume pattern
        hour = current_time.hour
        if 13 <= hour < 17:
            vol_base = 1500
        elif 7 <= hour < 13:
            vol_base = 1000
        else:
            vol_base = 500
        
        volume = vol_base * np.random.lognormal(0, 0.3)
        
        candles.append({
            'time': current_time,
            'open': round(open_p, 2),
            'high': round(high_p, 2),
            'low': round(low_p, 2),
            'close': round(close_p, 2),
            'volume': round(volume, 0)
        })
        current_time += timedelta(minutes=5)
    
    df = pd.DataFrame(candles)
    
    logger.info(f"✅ Generated {len(df)} M5 candles")
    logger.info(f"   Period: {df['time'].iloc[0]} to {df['time'].iloc[-1]}")
    logger.info(f"   Price: ${df['close'].iloc[0]:,.0f} → ${df['close'].iloc[-1]:,.0f}")
    logger.info(f"   Range: ${df['low'].min():,.0f} - ${df['high'].max():,.0f}")
    logger.info(f"   Avg volume: {df['volume'].mean():,.0f}")
    
    return df


class AdvancedBacktestEngine:
    """
    Advanced backtest with Smart Order Manager
    """
    
    def __init__(self, candles: pd.DataFrame):
        self.candles = candles
        self.config_manager = ConfigManager()
        self.dna = self.config_manager.load_dna()
        
        # Initialize Smart Order Manager
        self.order_manager = SmartOrderManager(dna_params=self.dna)
        
        # Trade tracking
        self.trades = []
        self.ticket_counter = 1000
        self.current_position = None
        
        # Performance tracking
        self.equity = 100000.0
        self.initial_equity = 100000.0
        self.peak_equity = 100000.0
        self.max_drawdown = 0.0
        
        # Stats
        self.total_signals = 0
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_commissions = 0.0
        self.total_spread_costs = 0.0
        
        # Cooldown
        self.last_trade_time = None
        self.min_cooldown_bars = 12  # Minimum 1 hour (12 x 5min) between trades
        
        logger.info("🚀 Advanced Backtest Engine initialized")
        logger.info(f"   Smart Order Manager: Active")
        logger.info(f"   Virtual TP: Dynamic")
        logger.info(f"   Dynamic SL: Active")
        logger.info(f"   DNA Profiles: Loaded")
    
    def run(self) -> dict:
        """Run advanced backtest"""
        
        logger.info("="*80)
        logger.info("🚀 STARTING ADVANCED BACKTEST")
        logger.info("="*80)
        logger.info(f"   Capital: ${self.initial_equity:,.2f}")
        logger.info(f"   Data: {len(self.candles)} candles")
        logger.info(f"   Period: {self.candles['time'].iloc[0]} to {self.candles['time'].iloc[-1]}")
        logger.info(f"   Smart Order Manager: ENABLED")
        logger.info("="*80)
        
        # Warmup period
        warmup = 50
        
        for i in range(warmup, len(self.candles)):
            current_candle = self.candles.iloc[i]
            current_price = current_candle['close']
            
            # Get recent candles for analysis
            recent_candles = self.candles.iloc[max(0, i-50):i+1]
            
            # If no position open, try to enter
            if self.current_position is None:
                signal = self._generate_signal(recent_candles, current_price)
                
                if signal:
                    self._open_position(signal, current_candle)
            
            # If position open, update Smart Order Manager
            else:
                action = self.order_manager.update_position(
                    ticket=self.current_position['ticket'],
                    current_price=current_price,
                    candles=recent_candles
                )
                
                # Execute action
                if action['action'] == 'close_position':
                    self._close_position(action, current_candle)
                
                # Check if SL hit
                elif self._check_sl_hit(current_candle):
                    self._close_position({
                        'action': 'close_position',
                        'reason': 'Original SL hit',
                        'type': 'stop_loss',
                        'pnl': self._calculate_pnl(current_price),
                    }, current_candle)
                
                # Check if original TP hit
                elif self._check_tp_hit(current_candle):
                    self._close_position({
                        'action': 'close_position',
                        'reason': 'Original TP hit',
                        'type': 'take_profit',
                        'pnl': self._calculate_pnl(current_price),
                    }, current_candle)
            
            # Track equity
            self.peak_equity = max(self.peak_equity, self.equity)
            if self.peak_equity > 0:
                dd = (self.peak_equity - self.equity) / self.peak_equity * 100
                self.max_drawdown = max(self.max_drawdown, dd)
            
            # Progress logging
            if (i - warmup) % 5000 == 0:
                progress = (i - warmup) / (len(self.candles) - warmup) * 100
                logger.info(f"   Progress: {progress:.1f}% | "
                          f"Trades: {self.total_trades} | "
                          f"Equity: ${self.equity:,.2f} | "
                          f"DD: {self.max_drawdown:.2f}%")
        
        # Close any remaining position
        if self.current_position:
            self._close_position({
                'action': 'close_position',
                'reason': 'End of test',
                'type': 'manual',
                'pnl': self._calculate_pnl(self.candles.iloc[-1]['close']),
            }, self.candles.iloc[-1])
        
        return self._calculate_results()
    
    def _generate_signal(self, candles: pd.DataFrame, current_price: float) -> dict:
        """Generate trading signal"""
        if len(candles) < 50:
            return None
        
        # Calculate indicators
        ema_9 = candles['close'].ewm(span=9, adjust=False).mean().iloc[-1]
        ema_21 = candles['close'].ewm(span=21, adjust=False).mean().iloc[-1]
        
        # RSI
        delta = candles['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs)).iloc[-1]
        
        # Determine direction
        ema_diff_pct = abs(ema_9 - ema_21) / current_price * 100
        
        if ema_9 > ema_21 and ema_diff_pct > 0.15:
            direction = "BUY"
            confidence = min(0.65 + ema_diff_pct * 0.5, 0.95)
        elif ema_9 < ema_21 and ema_diff_pct > 0.15:
            direction = "SELL"
            confidence = min(0.65 + ema_diff_pct * 0.5, 0.95)
        elif rsi < 20:
            direction = "BUY"
            confidence = 0.65 + (30 - rsi) * 0.02
        elif rsi > 80:
            direction = "SELL"
            confidence = 0.65 + (rsi - 70) * 0.02
        else:
            return None
        
        if confidence < 0.65:
            return None
        
        # Calculate levels
        atr = self._calculate_atr(candles)
        sl_distance = atr * 1.5
        tp_distance = sl_distance * 2.0
        
        sl_distance = max(sl_distance, 200)  # Min $200 stop
        tp_distance = max(tp_distance, 400)  # Min $400 target
        
        if direction == "BUY":
            sl = current_price - sl_distance
            tp = current_price + tp_distance
        else:
            sl = current_price + sl_distance
            tp = current_price - tp_distance
        
        self.total_signals += 1
        
        # Check cooldown
        if self.last_trade_time is not None:
            bars_since = (candles.iloc[-1]['time'] - self.last_trade_time).total_seconds() / 300
            if bars_since < self.min_cooldown_bars:
                return None
        
        return {
            'direction': direction,
            'entry_price': current_price,
            'stop_loss': sl,
            'take_profit': tp,
            'volume': 0.10,
            'confidence': confidence,
            'atr': atr,
        }
    
    def _calculate_atr(self, candles: pd.DataFrame) -> float:
        """Calculate ATR"""
        high = candles['high']
        low = candles['low']
        prev_close = candles['close'].shift(1)
        
        tr1 = high - low
        tr2 = (high - prev_close).abs()
        tr3 = (low - prev_close).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(14).mean().iloc[-1]
    
    def _open_position(self, signal: dict, candle: pd.Series):
        """Open position and register with Smart Order Manager"""
        
        # Calculate costs
        commission = signal['volume'] * 45.0 * 2  # Round trip
        spread_cost = 100 * signal['volume']  # 100 points
        total_costs = commission + spread_cost
        
        self.total_commissions += commission
        self.total_spread_costs += spread_cost
        
        position = {
            'ticket': self.ticket_counter,
            'symbol': 'BTCUSD',
            'direction': signal['direction'],
            'entry_price': signal['entry_price'],
            'stop_loss': signal['stop_loss'],
            'take_profit': signal['take_profit'],
            'volume': signal['volume'],
            'open_time': candle['time'],
            'costs': total_costs,
        }
        
        # Register with Smart Order Manager
        self.order_manager.open_position(position)
        self.current_position = position
        self.last_trade_time = candle['time']
        
        self.ticket_counter += 1
        
        logger.debug(f"📝 Position opened: {signal['direction']} @ ${signal['entry_price']:,.2f} | "
                    f"SL: ${signal['stop_loss']:,.2f} | TP: ${signal['take_profit']:,.2f}")
    
    def _close_position(self, action: dict, candle: pd.Series):
        """Close position and record result"""
        
        if self.current_position is None:
            return
        
        exit_price = candle['close']
        pnl = self._calculate_pnl(exit_price)
        
        # Net PnL (after costs)
        net_pnl = pnl - self.current_position['costs']
        
        self.equity += net_pnl
        self.total_trades += 1
        
        if net_pnl > 0:
            self.winning_trades += 1
        else:
            self.losing_trades += 1
        
        # Close with Smart Order Manager
        summary = self.order_manager.close_position(
            self.current_position['ticket'],
            reason=action['reason']
        )
        
        self.trades.append({
            'ticket': self.current_position['ticket'],
            'direction': self.current_position['direction'],
            'entry_price': self.current_position['entry_price'],
            'exit_price': exit_price,
            'gross_pnl': pnl,
            'net_pnl': net_pnl,
            'costs': self.current_position['costs'],
            'exit_reason': action['reason'],
            'exit_type': action['type'],
            'open_time': self.current_position['open_time'],
            'close_time': candle['time'],
        })
        
        logger.debug(f"✅ Position closed: {action['reason']} | "
                    f"PnL: ${net_pnl:+,.2f} | Equity: ${self.equity:,.2f}")
        
        self.current_position = None
    
    def _calculate_pnl(self, exit_price: float) -> float:
        """Calculate gross PnL"""
        if self.current_position is None:
            return 0.0
        
        pos = self.current_position
        if pos['direction'] == 'BUY':
            return (exit_price - pos['entry_price']) * pos['volume'] * 100
        else:
            return (pos['entry_price'] - exit_price) * pos['volume'] * 100
    
    def _check_sl_hit(self, candle: pd.Series) -> bool:
        """Check if original SL hit"""
        if self.current_position is None:
            return False
        
        pos = self.current_position
        if pos['direction'] == 'BUY':
            return candle['low'] <= pos['stop_loss']
        else:
            return candle['high'] >= pos['stop_loss']
    
    def _check_tp_hit(self, candle: pd.Series) -> bool:
        """Check if original TP hit"""
        if self.current_position is None:
            return False
        
        pos = self.current_position
        if pos['direction'] == 'BUY':
            return candle['high'] >= pos['take_profit']
        else:
            return candle['low'] <= pos['take_profit']
    
    def _calculate_results(self) -> dict:
        """Calculate final results"""
        
        net_pnl = self.equity - self.initial_equity
        win_rate = self.winning_trades / max(1, self.total_trades)
        
        gross_profit = sum(t['net_pnl'] for t in self.trades if t['net_pnl'] > 0)
        gross_loss = abs(sum(t['net_pnl'] for t in self.trades if t['net_pnl'] <= 0))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        avg_win = gross_profit / max(1, self.winning_trades)
        avg_loss = gross_loss / max(1, self.losing_trades)
        
        return {
            'summary': {
                'initial_capital': self.initial_equity,
                'final_capital': self.equity,
                'net_profit': net_pnl,
                'net_profit_percent': (net_pnl / self.initial_equity) * 100,
                'total_trades': self.total_trades,
                'winning_trades': self.winning_trades,
                'losing_trades': self.losing_trades,
                'win_rate': win_rate,
                'profit_factor': profit_factor,
                'expectancy': net_pnl / max(1, self.total_trades),
                'sharpe_ratio': 0.0,  # Simplified
            },
            'risk': {
                'max_drawdown_percent': self.max_drawdown,
                'max_drawdown_dollars': self.initial_equity * self.max_drawdown / 100,
                'avg_win': avg_win,
                'avg_loss': avg_loss,
                'win_loss_ratio': avg_win / avg_loss if avg_loss > 0 else 0,
                'consecutive_wins_max': 0,
                'consecutive_losses_max': 0,
                'avg_trade_duration_minutes': 0,
            },
            'costs': {
                'total_commissions': self.total_commissions,
                'total_spread_costs': self.total_spread_costs,
                'total_costs': self.total_commissions + self.total_spread_costs,
                'costs_as_percent_of_gross': 0,
            },
            'ftmo': {
                'overall_pass': self.max_drawdown < 10.0,
            },
            'trades': self.trades,
            'equity_curve': [],
        }


def main():
    """Run advanced backtest"""
    setup_logging()
    
    print("\n" + "="*80)
    print("🚀 FOREX QUANTUM BOT - ADVANCED BACKTEST")
    print("   With Smart Order Manager Integration")
    print("="*80 + "\n")
    
    # Generate data
    candles = generate_realistic_btcusd_data(days=180)
    
    print(f"\n💡 Features:")
    print(f"   ✅ Smart Order Manager (Virtual TP + Dynamic SL)")
    print(f"   ✅ Market momentum analysis")
    print(f"   ✅ DNA-adjusted profit profiles")
    print(f"   ✅ Realistic FTMO costs ($45/lot/side)")
    print(f"   ✅ Breakeven protection")
    print(f"   ✅ Trailing stop logic")
    print()
    
    # Run backtest
    engine = AdvancedBacktestEngine(candles)
    results = engine.run()
    
    # Print summary
    summary = results.get('summary', {})
    risk = results.get('risk', {})
    costs = results.get('costs', {})
    ftmo = results.get('ftmo', {})
    
    print("\n" + "="*80)
    print("📊 BACKTEST RESULTS")
    print("="*80)
    
    print(f"\n💰 PERFORMANCE:")
    print(f"   Initial Capital: ${summary.get('initial_capital', 0):,.2f}")
    print(f"   Final Capital: ${summary.get('final_capital', 0):,.2f}")
    print(f"   Net Profit: ${summary.get('net_profit', 0):,.2f} ({summary.get('net_profit_percent', 0):.2f}%)")
    print(f"   Total Trades: {summary.get('total_trades', 0)}")
    print(f"   Win Rate: {summary.get('win_rate', 0)*100:.1f}%")
    print(f"   Profit Factor: {summary.get('profit_factor', 0):.2f}")
    print(f"   Expectancy: ${summary.get('expectancy', 0):.2f}/trade")
    
    print(f"\n⚠️ RISK:")
    print(f"   Max Drawdown: {risk.get('max_drawdown_percent', 0):.2f}%")
    print(f"   Avg Win: ${risk.get('avg_win', 0):.2f}")
    print(f"   Avg Loss: ${risk.get('avg_loss', 0):.2f}")
    
    print(f"\n💸 COSTS:")
    print(f"   Total Commissions: ${costs.get('total_commissions', 0):,.2f}")
    print(f"   Total Spread: ${costs.get('total_spread_costs', 0):,.2f}")
    print(f"   TOTAL COSTS: ${costs.get('total_costs', 0):,.2f}")
    
    print(f"\n🎯 FTMO: {'✅ PASS' if ftmo.get('overall_pass') else '❌ FAIL'}")
    
    # Generate report
    print("\n" + "="*80)
    print("📄 Generating HTML report...")
    report_gen = ReportGenerator()
    path = report_gen.generate_report(results, "backtest_advanced_smart_order.html")
    print(f"✅ Report saved: {path}")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
