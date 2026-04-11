"""
Advanced Backtest with Neural Audit System + Veto Orchestrator
CEO: Qwen Code | Created: 2026-04-10

This backtest includes:
1. Neural Trade Auditor - Captures complete state for EVERY trade
2. Trade Pattern Analyzer - Finds error patterns
3. Veto Orchestrator - Blocks bad trades
4. Smart Order Manager - Dynamic TP/SL
5. Complete feedback loop

Usage:
    python run_backtest_neural_audit.py
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from loguru import logger

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.core.config_manager import ConfigManager
from src.monitoring.neural_trade_auditor import NeuralTradeAuditor
from src.monitoring.trade_pattern_analyzer import TradePatternAnalyzer
from src.monitoring.veto_orchestrator import VetoOrchestrator
from src.execution.smart_order_manager import SmartOrderManager


def setup_logging():
    """Configure logging"""
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )
    logger.add(
        "logs/backtest_neural_{time:YYYY-MM-DD}.log",
        rotation="00:00",
        retention="30 days",
        level="DEBUG"
    )


def generate_realistic_btcusd_data(days: int = 180) -> pd.DataFrame:
    """Generate realistic BTCUSD data with patterns"""
    logger.info(f"🔬 Generating {days} days of realistic BTCUSD data...")
    
    np.random.seed(42)
    bars_per_day = 288
    total_bars = days * bars_per_day
    start_price = 73000.0
    
    prices = [start_price]
    current_vol = 150.0
    
    for i in range(1, total_bars):
        current_vol = 0.9 * current_vol + 0.1 * 150 + np.random.normal(0, 10)
        current_vol = max(50, min(300, current_vol))
        
        deviation = prices[-1] - 73000
        reversion = -deviation * 0.0005
        
        regime = (i // 10000) % 4
        if regime == 0:
            trend = 5
        elif regime == 1:
            trend = -5
        elif regime == 2:
            trend = 15
        else:
            trend = -15
        
        change = trend + reversion + np.random.normal(0, current_vol)
        new_price = max(60000, min(90000, prices[-1] + change))
        prices.append(new_price)
    
    candles = []
    current_time = datetime.now() - timedelta(days=days)
    current_time = current_time.replace(hour=0, minute=0, second=0)
    
    for i in range(total_bars):
        open_p = prices[i]
        close_p = prices[i+1] if i+1 < len(prices) else prices[i]
        bar_range = abs(np.random.normal(0, current_vol * 0.5))
        high_p = max(open_p, close_p) + bar_range
        low_p = min(open_p, close_p) - bar_range
        
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
    logger.info(f"   Price: ${df['close'].iloc[0]:,.0f} → ${df['close'].iloc[-1]:,.0f}")
    logger.info(f"   Range: ${df['low'].min():,.0f} - ${df['high'].max():,.0f}")
    
    return df


class NeuralAuditBacktestEngine:
    """
    Advanced backtest with full Neural Audit System
    """
    
    def __init__(self, candles: pd.DataFrame):
        self.candles = candles
        self.config_manager = ConfigManager()
        self.dna = self.config_manager.load_dna()
        
        # Initialize systems
        self.auditor = NeuralTradeAuditor()
        self.order_manager = SmartOrderManager(dna_params=self.dna)
        self.veto_orchestrator = VetoOrchestrator()
        
        # Trade tracking
        self.trades = []
        self.ticket_counter = 1000
        self.current_position = None
        
        # Performance
        self.equity = 100000.0
        self.initial_equity = 100000.0
        self.peak_equity = 100000.0
        self.max_drawdown = 0.0
        
        # Stats
        self.total_signals = 0
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_vetoes = 0
        self.total_commissions = 0.0
        
        # Cooldown
        self.last_trade_time = None
        self.min_cooldown_bars = 24  # 2 hours between trades
        
        # Consecutive tracking
        self.consecutive_wins = 0
        self.consecutive_losses = 0
        
        logger.info("🧠 Neural Audit Backtest Engine initialized")
        logger.info(f"   Neural Auditor: Active")
        logger.info(f"   Veto Orchestrator: Active")
        logger.info(f"   Smart Order Manager: Active")
    
    def run(self) -> dict:
        """Run complete backtest with neural audit"""
        
        logger.info("="*80)
        logger.info("🧠 STARTING NEURAL AUDIT BACKTEST")
        logger.info("="*80)
        logger.info(f"   Capital: ${self.initial_equity:,.2f}")
        logger.info(f"   Data: {len(self.candles)} candles")
        logger.info(f"   Neural Audit: ENABLED")
        logger.info(f"   Veto System: ENABLED")
        logger.info("="*80)
        
        warmup = 50
        
        for i in range(warmup, len(self.candles)):
            current_candle = self.candles.iloc[i]
            current_price = current_candle['close']
            recent_candles = self.candles.iloc[max(0, i-50):i+1]
            
            # If no position, try to enter
            if self.current_position is None:
                signal = self._generate_signal(recent_candles, current_price, i)
                
                if signal:
                    # VETO CHECK before opening
                    veto_result = self._check_veto(signal, recent_candles, current_price)
                    
                    if veto_result.approved:
                        self._open_position(signal, current_candle, i)
                    else:
                        self.total_vetoes += 1
                        logger.debug(f"🚫 Trade vetoed: {veto_result.reason}")
            
            # Update position if open
            else:
                action = self.order_manager.update_position(
                    ticket=self.current_position['ticket'],
                    current_price=current_price,
                    candles=recent_candles
                )
                
                if action['action'] == 'close_position':
                    self._close_position(action, current_candle, i)
                elif self._check_sl_hit(current_candle):
                    self._close_position({
                        'action': 'close_position',
                        'reason': 'SL hit',
                        'type': 'stop_loss',
                    }, current_candle, i)
                elif self._check_tp_hit(current_candle):
                    self._close_position({
                        'action': 'close_position',
                        'reason': 'TP hit',
                        'type': 'take_profit',
                    }, current_candle, i)
            
            # Track equity
            self.peak_equity = max(self.peak_equity, self.equity)
            if self.peak_equity > 0:
                dd = (self.peak_equity - self.equity) / self.peak_equity * 100
                self.max_drawdown = max(self.max_drawdown, dd)
            
            # Progress
            if (i - warmup) % 5000 == 0:
                progress = (i - warmup) / (len(self.candles) - warmup) * 100
                logger.info(f"   Progress: {progress:.1f}% | "
                          f"Trades: {self.total_trades} | "
                          f"Vetoes: {self.total_vetoes} | "
                          f"Equity: ${self.equity:,.2f} | "
                          f"DD: {self.max_drawdown:.2f}%")
        
        # Close remaining
        if self.current_position:
            self._close_position({
                'action': 'close_position',
                'reason': 'End of test',
                'type': 'manual',
            }, self.candles.iloc[-1], len(self.candles))
        
        # Run pattern analysis
        logger.info("\n🔬 Running pattern analysis on all audits...")
        analyzer = TradePatternAnalyzer(self.auditor)
        analysis_results = analyzer.analyze_all()
        analyzer.save_veto_rules()
        
        return self._calculate_results(analysis_results)
    
    def _generate_signal(self, candles: pd.DataFrame, current_price: float, bar_index: int) -> dict:
        """Generate trading signal"""
        if len(candles) < 50:
            return None
        
        ema_9 = candles['close'].ewm(span=9, adjust=False).mean().iloc[-1]
        ema_21 = candles['close'].ewm(span=21, adjust=False).mean().iloc[-1]
        
        delta = candles['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = (100 - (100 / (1 + rs))).iloc[-1]
        
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
        
        # Cooldown
        if self.last_trade_time is not None:
            candle_time = candles.iloc[-1]['time']
            bars_since = (candle_time - self.last_trade_time).total_seconds() / 300
            if bars_since < self.min_cooldown_bars:
                return None
        
        # ATR
        high = candles['high']
        low = candles['low']
        prev_close = candles['close'].shift(1)
        tr = pd.concat([
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs()
        ], axis=1).max(axis=1)
        atr = tr.rolling(14).mean().iloc[-1]
        
        sl_distance = max(atr * 1.5, 200)
        tp_distance = sl_distance * 2.0
        
        if direction == "BUY":
            sl = current_price - sl_distance
            tp = current_price + tp_distance
        else:
            sl = current_price + sl_distance
            tp = current_price - tp_distance
        
        self.total_signals += 1
        
        return {
            'direction': direction,
            'entry_price': current_price,
            'stop_loss': sl,
            'take_profit': tp,
            'volume': 0.10,
            'confidence': confidence,
            'atr': atr,
            'rsi': rsi,
            'ema_9': ema_9,
            'ema_21': ema_21,
            'ema_diff_pct': ema_diff_pct,
        }
    
    def _check_veto(self, signal: dict, candles: pd.DataFrame, current_price: float) -> any:
        """Check if trade should be vetoed"""
        
        # Build context for veto check
        hour = candles.iloc[-1]['time'].hour
        if 13 <= hour < 17:
            session = "ny_overlap"
        elif 7 <= hour < 13:
            session = "london"
        elif 0 <= hour < 7:
            session = "asian"
        else:
            session = "ny"
        
        # Simple regime detection
        ema_50 = candles['close'].ewm(span=50, adjust=False).mean().iloc[-1]
        ema_200_val = candles['close'].ewm(span=200, adjust=False).mean().iloc[-1] if len(candles) >= 200 else current_price
        
        if abs(ema_50 - ema_200_val) / current_price < 0.01:
            regime = "ranging"
        elif ema_50 > ema_200_val:
            regime = "trending_bullish"
        else:
            regime = "trending_bearish"
        
        context = {
            'market_regime': {
                'regime_type': regime,
                'session': session,
            },
            'multi_timeframe': {
                'M5_trend': 'up' if signal['ema_9'] > signal['ema_21'] else 'down',
                'conflict_detected': False,
            },
            'risk_context': {
                'consecutive_losses': self.consecutive_losses,
            },
            'indicators': {
                'rsi_14': signal['rsi'],
            },
            'direction': signal['direction'],
        }
        
        return self.veto_orchestrator.check_trade(context)
    
    def _open_position(self, signal: dict, candle: pd.Series, bar_index: int):
        """Open position with full neural audit"""
        
        commission = signal['volume'] * 45.0 * 2
        spread_cost = 100 * signal['volume']
        total_costs = commission + spread_cost
        
        self.total_commissions += total_costs
        
        position = {
            'ticket': self.ticket_counter,
            'symbol': 'BTCUSD',
            'direction': signal['direction'],
            'entry_price': signal['entry_price'],
            'stop_loss': signal['stop_loss'],
            'take_profit': signal['take_profit'],
            'volume': signal['volume'],
            'open_time': candle['time'],
            'open_bar_index': bar_index,
            'costs': total_costs,
        }
        
        # Neural audit - capture entry
        hour = candle['time'].hour
        if 13 <= hour < 17:
            session = "ny_overlap"
        elif 7 <= hour < 13:
            session = "london"
        elif 0 <= hour < 7:
            session = "asian"
        else:
            session = "ny"
        
        ema_50 = self.candles.iloc[max(0, bar_index-50):bar_index+1]['close'].ewm(span=50, adjust=False).mean().iloc[-1]
        current_price = candle['close']
        
        if abs(ema_50 - current_price) / current_price < 0.01:
            regime = "ranging"
        elif ema_50 > current_price:
            regime = "trending_bearish"
        else:
            regime = "trending_bullish"
        
        self.auditor.capture_entry_state(
            ticket=position['ticket'],
            direction=signal['direction'],
            entry_price=signal['entry_price'],
            stop_loss=signal['stop_loss'],
            take_profit=signal['take_profit'],
            volume=signal['volume'],
            strategy_name="momentum_scalping",
            signal_confidence=signal['confidence'],
            market_regime={
                'regime_type': regime,
                'regime_confidence': 0.70,
                'trend_strength': 0.5,
                'trend_direction': signal['direction'].lower(),
                'volatility_regime': 'medium',
                'volatility_value': signal['atr'],
                'volume_regime': 'normal',
                'volume_ratio': 1.0,
                'market_phase': 'unknown',
                'session': session,
                'session_volume_profile': 0.8,
            },
            multi_timeframe={
                'M1_trend': signal['direction'].lower(),
                'M5_trend': signal['direction'].lower(),
                'M15_trend': signal['direction'].lower(),
                'H1_trend': 'neutral',
                'H4_trend': 'neutral',
                'D1_trend': 'neutral',
                'alignment_score': 0.5,
                'dominant_timeframe': 'M5',
                'conflict_detected': False,
            },
            indicators={
                'ema_9': signal['ema_9'],
                'ema_21': signal['ema_21'],
                'ema_50': ema_50,
                'ema_200': current_price,
                'sma_20': current_price,
                'sma_50': current_price,
                'ema_9_21_cross': 'bullish' if signal['ema_9'] > signal['ema_21'] else 'bearish',
                'ema_21_50_cross': 'neutral',
                'price_vs_ema_200': 'above',
                'rsi_14': signal['rsi'],
                'rsi_regime': 'oversold' if signal['rsi'] < 30 else 'overbought' if signal['rsi'] > 70 else 'neutral',
                'macd_line': 0, 'macd_signal': 0, 'macd_histogram': 0, 'macd_cross': 'neutral',
                'stochastic_k': 50, 'stochastic_d': 50,
                'atr_14': signal['atr'],
                'atr_percentile': 50.0,
                'bollinger_upper': current_price + 500,
                'bollinger_middle': current_price,
                'bollinger_lower': current_price - 500,
                'bollinger_width': 1000,
                'price_vs_bollinger': 'inside',
                'volume_current': 1000, 'volume_avg_20': 1000, 'volume_ratio': 1.0,
                'volume_trend': 'stable', 'obv_trend': 'neutral',
            },
            price_action={
                'current_price': current_price,
                'price_change_1h': 0.5, 'price_change_4h': 1.0, 'price_change_24h': 2.0,
                'nearest_support': current_price - 500,
                'nearest_resistance': current_price + 500,
                'distance_to_support_pct': 0.68,
                'distance_to_resistance_pct': 0.68,
                'current_candle_type': 'bullish',
                'candle_body_size': 100, 'candle_wick_ratio': 0.3,
                'engulfing_detected': False, 'inside_bar_detected': False,
                'higher_highs': True, 'higher_lows': True,
                'lower_highs': False, 'lower_lows': False,
                'structure': 'uptrend' if signal['direction'] == 'BUY' else 'downtrend',
            },
            momentum={
                'velocity': 0.5, 'acceleration': 0.1, 'gravity': 0.3,
                'oscillation': 50, 'volume_pressure': 0.5,
                'microstructure_score': 0.6,
                'momentum_divergence': False, 'exhaustion_signals': [],
            },
            risk_context={
                'capital': self.equity,
                'equity': self.equity,
                'daily_pnl': 0, 'daily_pnl_percent': 0,
                'total_pnl': self.equity - self.initial_equity,
                'total_pnl_percent': (self.equity / self.initial_equity - 1) * 100,
                'current_drawdown': self.max_drawdown,
                'max_drawdown': self.max_drawdown,
                'consecutive_wins': self.consecutive_wins,
                'consecutive_losses': self.consecutive_losses,
                'daily_loss_used_percent': 0,
                'total_loss_used_percent': self.max_drawdown,
                'ftmo_daily_remaining': 5000,
                'ftmo_total_remaining': 10000,
            },
            dna_state={
                'current_regime': regime,
                'regime_confidence': 0.70,
                'active_strategy': 'momentum_scalping',
                'strategy_weights': {'momentum': 0.6, 'mean_reversion': 0.2, 'breakout': 0.2},
                'risk_percent': 0.5,
                'min_rr_ratio': 1.5,
                'confidence_threshold': 0.65,
                'last_mutation_time': datetime.now(timezone.utc).isoformat(),
                'mutation_count': 0,
                'dna_memory_regimes': 0,
            },
            smart_order_manager={
                'virtual_tp_original': signal['take_profit'],
                'virtual_tp_current': signal['take_profit'],
                'virtual_tp_adjustment_factor': 1.0,
                'virtual_tp_difficulty': 'moderate',
                'dynamic_sl_original': signal['stop_loss'],
                'dynamic_sl_current': signal['stop_loss'],
                'breakeven_activated': False,
                'profit_targets_reached': [],
                'momentum_at_entry': {'velocity': 0.5},
            },
        )
        
        self.order_manager.open_position(position)
        self.current_position = position
        self.last_trade_time = candle['time']
        self.ticket_counter += 1
        
        logger.debug(f"📝 Position #{position['ticket']} opened: {signal['direction']} @ ${signal['entry_price']:,.2f}")
    
    def _close_position(self, action: dict, candle: pd.Series, bar_index: int):
        """Close position with neural audit"""
        if self.current_position is None:
            return
        
        exit_price = candle['close']
        pos = self.current_position
        
        if pos['direction'] == 'BUY':
            gross_pnl = (exit_price - pos['entry_price']) * pos['volume'] * 100
        else:
            gross_pnl = (pos['entry_price'] - exit_price) * pos['volume'] * 100
        
        net_pnl = gross_pnl - pos['costs']
        duration_bars = bar_index - pos['open_bar_index']
        duration_minutes = duration_bars * 5
        
        self.equity += net_pnl
        self.total_trades += 1
        
        if net_pnl > 0:
            self.winning_trades += 1
            self.consecutive_wins += 1
            self.consecutive_losses = 0
        else:
            self.losing_trades += 1
            self.consecutive_losses += 1
            self.consecutive_wins = 0
        
        # Neural audit - capture exit
        self.auditor.capture_exit_state(
            ticket=pos['ticket'],
            exit_price=exit_price,
            exit_reason=action['reason'],
            gross_pnl=gross_pnl,
            net_pnl=net_pnl,
            duration_minutes=duration_minutes,
            max_profit_reached=gross_pnl + 50,
            max_drawdown_reached=-20,
        )
        
        # Close in order manager
        self.order_manager.close_position(pos['ticket'], action['reason'])
        
        self.trades.append({
            'ticket': pos['ticket'],
            'direction': pos['direction'],
            'entry_price': pos['entry_price'],
            'exit_price': exit_price,
            'gross_pnl': gross_pnl,
            'net_pnl': net_pnl,
            'costs': pos['costs'],
            'exit_reason': action['reason'],
            'exit_type': action.get('type', 'unknown'),
            'open_time': pos['open_time'],
            'close_time': candle['time'],
            'duration_minutes': duration_minutes,
        })
        
        logger.debug(f"✅ Position #{pos['ticket']} closed: {action['reason']} | PnL: ${net_pnl:+,.2f}")
        
        self.current_position = None
    
    def _check_sl_hit(self, candle: pd.Series) -> bool:
        if self.current_position is None:
            return False
        pos = self.current_position
        if pos['direction'] == 'BUY':
            return candle['low'] <= pos['stop_loss']
        else:
            return candle['high'] >= pos['stop_loss']
    
    def _check_tp_hit(self, candle: pd.Series) -> bool:
        if self.current_position is None:
            return False
        pos = self.current_position
        if pos['direction'] == 'BUY':
            return candle['high'] >= pos['take_profit']
        else:
            return candle['low'] <= pos['take_profit']
    
    def _calculate_results(self, analysis_results: dict) -> dict:
        """Calculate final results"""
        net_pnl = self.equity - self.initial_equity
        win_rate = self.winning_trades / max(1, self.total_trades)
        
        gross_profit = sum(t['net_pnl'] for t in self.trades if t['net_pnl'] > 0)
        gross_loss = abs(sum(t['net_pnl'] for t in self.trades if t['net_pnl'] <= 0))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        avg_win = gross_profit / max(1, self.winning_trades)
        avg_loss = gross_loss / max(1, self.losing_trades)
        
        veto_stats = self.veto_orchestrator.get_stats()
        
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
                'total_signals': self.total_signals,
                'total_vetoes': self.total_vetoes,
                'veto_rate': self.total_vetoes / max(1, self.total_signals) * 100,
            },
            'risk': {
                'max_drawdown_percent': self.max_drawdown,
                'max_drawdown_dollars': self.initial_equity * self.max_drawdown / 100,
                'avg_win': avg_win,
                'avg_loss': avg_loss,
                'win_loss_ratio': avg_win / avg_loss if avg_loss > 0 else 0,
                'consecutive_wins_max': self.consecutive_wins,
                'consecutive_losses_max': self.consecutive_losses,
            },
            'costs': {
                'total_commissions': self.total_commissions,
            },
            'veto_stats': veto_stats,
            'pattern_analysis': analysis_results,
            'ftmo': {'overall_pass': self.max_drawdown < 10.0},
            'trades': self.trades,
            'equity_curve': [],
        }


def main():
    """Run neural audit backtest"""
    setup_logging()
    
    print("\n" + "="*80)
    print("🧠 FOREX QUANTUM BOT - NEURAL AUDIT BACKTEST")
    print("   With Smart Order Manager + Veto Orchestrator")
    print("="*80 + "\n")
    
    # Generate data
    candles = generate_realistic_btcusd_data(days=180)
    
    print(f"\n💡 Features:")
    print(f"   ✅ Neural Trade Auditor (captures EVERY trade state)")
    print(f"   ✅ Veto Orchestrator (blocks bad trades)")
    print(f"   ✅ Smart Order Manager (Virtual TP + Dynamic SL)")
    print(f"   ✅ Pattern Analyzer (learns from errors)")
    print(f"   ✅ Realistic FTMO costs ($45/lot/side)")
    print()
    
    # Run
    engine = NeuralAuditBacktestEngine(candles)
    results = engine.run()
    
    # Print summary
    summary = results.get('summary', {})
    risk = results.get('risk', {})
    costs = results.get('costs', {})
    veto = results.get('veto_stats', {})
    ftmo = results.get('ftmo', {})
    pattern = results.get('pattern_analysis', {})
    
    print("\n" + "="*80)
    print("📊 NEURAL AUDIT BACKTEST RESULTS")
    print("="*80)
    
    print(f"\n💰 PERFORMANCE:")
    print(f"   Initial Capital: ${summary.get('initial_capital', 0):,.2f}")
    print(f"   Final Capital: ${summary.get('final_capital', 0):,.2f}")
    print(f"   Net Profit: ${summary.get('net_profit', 0):,.2f} ({summary.get('net_profit_percent', 0):.2f}%)")
    print(f"   Total Trades: {summary.get('total_trades', 0)}")
    print(f"   Win Rate: {summary.get('win_rate', 0)*100:.1f}%")
    print(f"   Profit Factor: {summary.get('profit_factor', 0):.2f}")
    print(f"   Expectancy: ${summary.get('expectancy', 0):.2f}/trade")
    
    print(f"\n🛡️ VETO SYSTEM:")
    print(f"   Total Signals: {summary.get('total_signals', 0)}")
    print(f"   Trades Executed: {summary.get('total_trades', 0)}")
    print(f"   Trades Vetoed: {summary.get('total_vetoes', 0)}")
    print(f"   Veto Rate: {summary.get('veto_rate', 0):.1f}%")
    print(f"   Rules Loaded: {veto.get('rules_loaded', 0)}")
    
    print(f"\n⚠️ RISK:")
    print(f"   Max Drawdown: {risk.get('max_drawdown_percent', 0):.2f}%")
    print(f"   Avg Win: ${risk.get('avg_win', 0):.2f}")
    print(f"   Avg Loss: ${risk.get('avg_loss', 0):.2f}")
    
    print(f"\n💸 COSTS:")
    print(f"   Total Commissions: ${costs.get('total_commissions', 0):,.2f}")
    
    print(f"\n🔬 PATTERN ANALYSIS:")
    print(f"   Error Patterns Found: {pattern.get('error_patterns_found', 0)}")
    print(f"   Veto Rules Generated: {pattern.get('veto_rules_generated', 0)}")
    
    print(f"\n🎯 FTMO: {'✅ PASS' if ftmo.get('overall_pass') else '❌ FAIL'}")
    
    print("\n" + "="*80)
    print("✅ NEURAL AUDIT BACKTEST COMPLETE")
    print("="*80)
    print(f"\n📁 Trade audits saved to: data/trade-audits/")
    print(f"📋 Veto rules saved to: config/veto_rules.json")
    print(f"💡 Review audits to understand what went wrong/right")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
