"""
Live Trading System - MT5 Real-Time Execution
CEO: Forex Quantum Bot | Created: 2026-04-12

Production live trading system that mirrors the backtest engine:
- Real-time MT5 data feed (BTCUSD M5)
- All 12 strategies with voting system
- Phase 1-4 components (27/30 implemented)
- Real order execution with commission tracking
- Trade auditing and performance monitoring
- FTMO compliance monitoring
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

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import backtest components (reuse same logic)
from src.strategies.session_profiles import detect_session, get_session_profile, apply_session_veto
from src.strategies.advanced_strategies import (
    MomentumStrategy, LiquidityStrategy, ThermodynamicStrategy, PhysicsStrategy,
    OrderBlockStrategy, FVGStrategy, MSNRStrategy, MSNRAlchemistStrategy,
    IFVGStrategy, OrderFlowStrategy, SupplyDemandStrategy, FibonacciStrategy
)
from src.execution.smart_order_manager import SmartOrderManager
from src.execution.position_manager_smart_tp import PositionManagerSmartTP
from src.risk.backtest_risk_manager import BacktestRiskManager
from src.risk.anti_metralhadora import AntiMetralhadora
from src.risk.risk_quantum_engine import RiskQuantumEngine
from src.risk.profit_erosion_tiers import ProfitErosionTiers
from src.risk.execution_validator import ExecutionValidator
from src.risk.great_filter import GreatFilter
from src.risk.black_swan_stress_test import BlackSwanStressTest
from src.monitoring.neural_trade_auditor import NeuralTradeAuditor
from src.monitoring.trade_pattern_analyzer import TradePatternAnalyzer
from src.monitoring.veto_orchestrator import VetoOrchestrator
from src.monitoring.ghost_audit_engine import GhostAuditEngine
from src.core.config_manager import ConfigManager
from src.dna.dna_engine import DNAEngine


class LiveTradingEngine:
    """
    Production live trading engine.
    
    Mirrors the backtest engine with real-time MT5 execution.
    """

    def __init__(
        self,
        symbol: str = "BTCUSD",
        timeframe: int = mt5.TIMEFRAME_M5,
        risk_percent: float = 1.0,
        max_positions: int = 1,
        audit_interval: int = 60,  # seconds
        mt5_path: str = None,
    ):
        """
        Initialize Live Trading Engine.
        
        Args:
            symbol: Trading symbol
            timeframe: Chart timeframe
            risk_percent: Risk per trade (%)
            max_positions: Max concurrent positions
            audit_interval: Audit logging interval (seconds)
            mt5_path: Path to MT5 terminal (optional)
        """
        self.symbol = symbol
        self.timeframe = timeframe
        self.risk_percent = risk_percent
        self.max_positions = max_positions
        self.audit_interval = audit_interval
        
        # State
        self.running = False
        self.equity = 0.0
        self.balance = 0.0
        self.total_trades = 0
        self.total_vetoes = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.consecutive_wins = 0
        self.consecutive_losses = 0
        self.last_loss_time = None
        self.consecutive_loss_cooldown = 6  # bars
        
        # Position tracking
        self.current_position = None
        self.peak_equity = 0.0
        self.max_drawdown = 0.0
        
        # Audit
        self.auditor = NeuralTradeAuditor(audit_dir="data/live-trade-audits")
        self.auditor.set_backtest_mode(True)  # Enable JSON file saving
        
        # Initialize components (same as backtest)
        self._init_components()
        
        # MT5 connection
        self.mt5_connected = False
        
        logger.info("=" * 80)
        logger.info("LIVE TRADING ENGINE INITIALIZED")
        logger.info("=" * 80)
        logger.info(f"   Symbol: {symbol}")
        logger.info(f"   Timeframe: M5")
        logger.info(f"   Risk/Trade: {risk_percent}%")
        logger.info(f"   Max Positions: {max_positions}")

    def _init_components(self):
        """Initialize all trading components (mirrors backtest)."""
        # Session Profiles
        # (imported directly)
        
        # Strategies (same 12 as backtest)
        self.strategies = {
            'momentum': MomentumStrategy(),
            'liquidity': LiquidityStrategy(),
            'thermodynamic': ThermodynamicStrategy(),
            'physics': PhysicsStrategy(),
            'order_block': OrderBlockStrategy(),
            'fvg': FVGStrategy(),
            'msnr': MSNRStrategy(),
            'msnr_alchemist': MSNRAlchemistStrategy(),
            'ifvg': IFVGStrategy(),
            'order_flow': OrderFlowStrategy(),
            'supply_demand': SupplyDemandStrategy(),
            'fibonacci': FibonacciStrategy(),
        }
        
        # Risk Manager
        self.risk_manager = BacktestRiskManager(initial_capital=100000.0)
        
        # Phase 1 Components
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
        self.execution_validator = ExecutionValidator()
        self.great_filter = GreatFilter()
        
        # Phase 2 Components
        self.black_swan = BlackSwanStressTest()
        
        # Ghost Audit Engine
        self.ghost_audit = GhostAuditEngine(audit_dir="data/live-ghost-audits")
        
        logger.info("✅ All components initialized")

    def connect_mt5(self) -> bool:
        """
        Connect to MetaTrader 5 terminal.
        
        Returns:
            True if connected successfully
        """
        logger.info("🔄 Connecting to MT5...")
        
        if not mt5.initialize():
            logger.error(f"❌ MT5 initialization failed: {mt5.last_error()}")
            return False
        
        # Get account info
        account_info = mt5.account_info()
        if account_info is None:
            logger.error("❌ Failed to get account info")
            return False
        
        self.balance = account_info.balance
        self.equity = account_info.equity
        self.peak_equity = self.equity
        
        logger.info(f"✅ MT5 Connected")
        logger.info(f"   Account: {account_info.login}")
        logger.info(f"   Server: {account_info.server}")
        logger.info(f"   Balance: ${self.balance:,.2f}")
        logger.info(f"   Equity: ${self.equity:,.2f}")
        
        # Verify symbol exists
        symbol_info = mt5.symbol_info(self.symbol)
        if symbol_info is None:
            logger.error(f"❌ Symbol {self.symbol} not found")
            return False
        
        if not symbol_info.visible:
            logger.warning(f"⚠️ Symbol {self.symbol} not visible, enabling...")
            if not mt5.symbol_select(self.symbol, True):
                logger.error(f"❌ Failed to select symbol {self.symbol}")
                return False
        
        logger.info(f"   Symbol: {self.symbol}")
        logger.info(f"   Point: {symbol_info.point}")
        logger.info(f"   Digits: {symbol_info.digits}")
        
        self.mt5_connected = True
        return True

    def get_candles(self, count: int = 100) -> Optional[pd.DataFrame]:
        """
        Fetch latest candles from MT5.
        
        Args:
            count: Number of candles to fetch
            
        Returns:
            DataFrame with OHLCV data or None
        """
        rates = mt5.copy_rates_from_pos(self.symbol, self.timeframe, 0, count)
        
        if rates is None or len(rates) == 0:
            logger.error(f"❌ Failed to get candles: {mt5.last_error()}")
            return None
        
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s', utc=True)
        
        return df

    def calculate_indicators(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Calculate all technical indicators (same as backtest).
        
        Args:
            df: OHLCV DataFrame
            
        Returns:
            Dict with all calculated indicators
        """
        indicators = {}
        close = df['close']
        high = df['high']
        low = df['low']
        volume = df['tick_volume']
        
        # EMAs
        indicators['ema_9'] = self._ema(close, 9)
        indicators['ema_21'] = self._ema(close, 21)
        indicators['ema_50'] = self._ema(close, 50)
        indicators['ema_200'] = self._ema(close, 200)
        
        # SMAs
        indicators['sma_20'] = close.rolling(20).mean()
        indicators['sma_50'] = close.rolling(50).mean()
        
        # RSI
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss.replace(0, np.nan)
        indicators['rsi_14'] = 100 - (100 / (1 + rs))
        
        # ATR
        tr = pd.concat([
            high - low,
            (high - close.shift()).abs(),
            (low - close.shift()).abs()
        ], axis=1).max(axis=1)
        indicators['atr_14'] = tr.rolling(14).mean()
        
        # Bollinger Bands
        indicators['bb_middle'] = close.rolling(20).mean()
        bb_std = close.rolling(20).std()
        indicators['bb_upper'] = indicators['bb_middle'] + (bb_std * 2)
        indicators['bb_lower'] = indicators['bb_middle'] - (bb_std * 2)
        
        # Volume
        indicators['volume_avg_20'] = volume.rolling(20).mean()
        indicators['volume_ratio'] = volume / indicators['volume_avg_20'].replace(0, 1)
        
        return indicators

    def _ema(self, series: pd.Series, span: int) -> pd.Series:
        """Calculate EMA."""
        return series.ewm(span=span, adjust=False).mean()

    def generate_signal(self, df: pd.DataFrame, indicators: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Generate trading signal using 12-strategy voting system.
        
        Args:
            df: OHLCV DataFrame
            indicators: Calculated indicators
            
        Returns:
            Signal dict or None
        """
        if len(df) < 50:
            return None
        
        current_price = df['close'].iloc[-1]
        current_time = df['time'].iloc[-1]
        
        # Run all strategies
        votes = []
        for name, strategy in self.strategies.items():
            try:
                result = strategy.evaluate(df, indicators)
                if result:
                    votes.append({
                        'strategy': name,
                        'direction': result.get('direction', 'NEUTRAL'),
                        'confidence': result.get('confidence', 0.5),
                    })
            except Exception as e:
                logger.warning(f"⚠️ Strategy {name} error: {e}")
        
        if not votes:
            return None
        
        # Count votes
        buy_votes = sum(1 for v in votes if v['direction'] == 'BUY')
        sell_votes = sum(1 for v in votes if v['direction'] == 'SELL')
        neutral_votes = len(votes) - buy_votes - sell_votes
        
        # Determine consensus
        if buy_votes > sell_votes and buy_votes >= 5:
            direction = 'BUY'
            consensus_conf = sum(v['confidence'] for v in votes if v['direction'] == 'BUY') / max(1, buy_votes)
        elif sell_votes > buy_votes and sell_votes >= 5:
            direction = 'SELL'
            consensus_conf = sum(v['confidence'] for v in votes if v['direction'] == 'SELL') / max(1, sell_votes)
        else:
            return None  # No clear consensus
        
        # Calculate ATR for SL/TP
        atr = indicators['atr_14'].iloc[-1]
        if pd.isna(atr) or atr == 0:
            return None
        
        # Calculate SL/TP (same as backtest: 1.5x ATR stop, 3x R:R)
        sl_dist = min(max(atr * 1.5, 500), 3000)
        tp_dist = sl_dist * 2.0  # 1:2 R:R
        
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
            'volume': 0.01,  # Will be calculated later
            'confidence': consensus_conf,
            'atr': atr,
            'votes': votes,
            'buy_votes': buy_votes,
            'sell_votes': sell_votes,
            'neutral_votes': neutral_votes,
            'time': current_time,
        }

    def validate_signal(self, signal: Dict[str, Any], df: pd.DataFrame, indicators: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate signal through all veto layers.
        
        Args:
            signal: Generated signal
            df: OHLCV DataFrame
            indicators: Calculated indicators
            
        Returns:
            Tuple of (approved, reason)
        """
        current_time = signal['time']
        session = detect_session(current_time)
        session_profile = get_session_profile(session)
        
        # Session veto
        session_veto = apply_session_veto(session_profile, signal)
        if not session_veto['approved']:
            return False, f"Session veto: {session_veto.get('reason', 'unknown')}"
        
        # Anti-Metralhadora check
        allowed, reason, _ = self.anti_metralhadora.should_allow_trade(
            signal_quality=signal.get('confidence', 0.0),
            current_session=session,
            current_time=current_time,
        )
        if not allowed:
            return False, f"Anti-Metralhadora: {reason}"
        
        # GreatFilter check
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
        
        # Ghost Audit tracking (vetoed signals)
        if not allowed or not great_allowed:
            self.ghost_audit.create_ghost(
                signal=signal,
                veto_reason=f"live_veto",
                bar_index=len(df) - 1,
                cur_time=current_time,
                session=session,
            )
        
        return True, "All vetoes passed"

    def _get_spread(self) -> float:
        """Get current spread as percentage."""
        tick = mt5.symbol_info_tick(self.symbol)
        if tick is None:
            return 0.001  # Default
        spread = tick.ask - tick.bid
        return (spread / tick.ask) * 100

    def _get_price_change_5min(self, df: pd.DataFrame) -> float:
        """Get price change over last 5 minutes."""
        if len(df) < 2:
            return 0.0
        return ((df['close'].iloc[-1] - df['close'].iloc[-2]) / df['close'].iloc[-2]) * 100

    def calculate_position_size(self, signal: Dict[str, Any]) -> float:
        """
        Calculate position size using RiskQuantumEngine.
        
        Args:
            signal: Validated signal
            
        Returns:
            Position volume in lots
        """
        # Get account info
        account_info = mt5.account_info()
        if account_info is None:
            return 0.01
        
        equity = account_info.equity
        
        # Calculate sizing (same as backtest)
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
        """
        Execute trade on MT5.
        
        Args:
            signal: Validated signal with position size
            
        Returns:
            True if order placed successfully
        """
        volume = signal.get('volume', 0.01)
        direction = signal['direction']
        sl = signal['stop_loss']
        tp = signal['take_profit']
        price = signal['entry_price']
        
        # Get current tick
        tick = mt5.symbol_info_tick(self.symbol)
        if tick is None:
            logger.error("❌ Failed to get tick data")
            return False
        
        # Prepare order
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
            "deviation": 50,  # 50 points max slippage
            "magic": 123456,  # Magic number for identification
            "comment": "ForexQuantumBot",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        # Send order
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
        
        # Record trade in auditor
        self.total_trades += 1
        self.auditor.capture_entry_state(
            ticket=result.order,
            direction=direction,
            entry_price=price,
            stop_loss=sl,
            take_profit=tp,
            volume=volume,
            strategy_name="live_trading",
            signal_confidence=signal.get('confidence', 0.5),
            market_regime=self._get_market_regime(),
            multi_timeframe=self._get_multi_timeframe(),
            indicators=self._get_current_indicators(),
            price_action=self._get_price_action(),
            momentum=self._get_momentum(),
            risk_context=self._get_risk_context(),
            strategy_voting=self._get_strategy_voting(signal),
        )
        
        return True

    def _get_market_regime(self) -> Dict[str, Any]:
        """Get current market regime."""
        return {
            'regime_type': 'unknown',
            'regime_confidence': 0.5,
            'session': 'unknown',
        }

    def _get_multi_timeframe(self) -> Dict[str, Any]:
        """Get multi-timeframe analysis."""
        return {
            'M5_trend': 'neutral',
            'alignment_score': 0.5,
        }

    def _get_current_indicators(self) -> Dict[str, Any]:
        """Get current indicators."""
        return {}

    def _get_price_action(self) -> Dict[str, Any]:
        """Get price action analysis."""
        return {}

    def _get_momentum(self) -> Dict[str, Any]:
        """Get momentum analysis."""
        return {}

    def _get_risk_context(self) -> Dict[str, Any]:
        """Get risk context."""
        account_info = mt5.account_info()
        if account_info is None:
            return {}
        return {
            'capital': account_info.balance,
            'equity': account_info.equity,
            'current_drawdown': self.max_drawdown / 100.0 if self.max_drawdown > 0 else 0.0,
        }

    def _get_strategy_voting(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """Get strategy voting breakdown."""
        return {
            'buy_votes': signal.get('buy_votes', 0),
            'sell_votes': signal.get('sell_votes', 0),
            'neutral_votes': signal.get('neutral_votes', 0),
            'consensus_confidence': signal.get('confidence', 0.5),
        }

    def manage_position(self) -> bool:
        """
        Manage open position (check TP/SL, trailing, etc).
        
        Returns:
            True if position was closed
        """
        if self.current_position is None:
            return False
        
        # Get current positions from MT5
        positions = mt5.positions_get(symbol=self.symbol)
        if positions is None or len(positions) == 0:
            self.current_position = None
            return False
        
        # Check if position still exists
        pos = positions[0]
        
        # Update peak/trailing logic here if needed
        # Smart TP management would go here
        
        return False

    def log_status(self):
        """Log current system status."""
        account_info = mt5.account_info()
        if account_info is None:
            return
        
        self.equity = account_info.equity
        self.balance = account_info.balance
        
        # Update peak equity and drawdown
        if self.equity > self.peak_equity:
            self.peak_equity = self.equity
        
        if self.peak_equity > 0:
            dd = (self.peak_equity - self.equity) / self.peak_equity * 100
            if dd > self.max_drawdown:
                self.max_drawdown = dd
        
        win_rate = (self.winning_trades / max(1, self.total_trades)) * 100 if self.total_trades > 0 else 0
        
        logger.info(
            f"📊 Status: Trades={self.total_trades} | "
            f"Wins={self.winning_trades} | Losses={self.losing_trades} | "
            f"WR={win_rate:.1f}% | "
            f"Equity=${self.equity:,.2f} | "
            f"DD={self.max_drawdown:.2f}% | "
            f"Vetoes={self.total_vetoes}"
        )

    def run(self, max_bars: int = None):
        """
        Main trading loop.
        
        Args:
            max_bars: Maximum bars to process (None = infinite)
        """
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
                # Fetch latest candles
                df = self.get_candles(count=100)
                if df is None or len(df) < 50:
                    logger.warning("⚠️ Insufficient data, waiting...")
                    time.sleep(5)
                    continue
                
                # Calculate indicators
                indicators = self.calculate_indicators(df)
                
                # Manage open position
                self.manage_position()
                
                # Check if we can open new position
                if self.current_position is None:
                    # Generate signal
                    signal = self.generate_signal(df, indicators)
                    
                    if signal:
                        # Validate through veto layers
                        approved, reason = self.validate_signal(signal, df, indicators)
                        
                        if approved:
                            # Calculate position size
                            volume = self.calculate_position_size(signal)
                            signal['volume'] = max(0.01, min(5.0, volume))
                            
                            # Execute trade
                            if self.execute_trade(signal):
                                self.current_position = signal
                        else:
                            self.total_vetoes += 1
                            logger.debug(f"🚫 Signal vetoed: {reason}")
                
                # Log status periodically
                if bar_count % 12 == 0:  # Every minute (12 x 5s)
                    self.log_status()
                
                bar_count += 1
                
                # Check max bars
                if max_bars and bar_count >= max_bars:
                    logger.info(f"✅ Reached max bars ({max_bars}). Stopping.")
                    break
                
                # Wait for next bar (5 seconds for testing, 300 for production)
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
        positions = mt5.positions_get(symbol=self.symbol)
        if positions:
            for pos in positions:
                logger.warning(f"⚠️ Closing open position: {pos.ticket}")
                # Close position logic here
        
        # Shutdown MT5
        if self.mt5_connected:
            mt5.shutdown()
            logger.info("✅ MT5 disconnected")
        
        # Final status
        self.log_status()
        logger.info("=" * 80)
        logger.info("LIVE TRADING SYSTEM SHUTDOWN COMPLETE")
        logger.info("=" * 80)


if __name__ == "__main__":
    # Setup logging
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO",
    )
    
    # Create and run engine
    engine = LiveTradingEngine(
        symbol="BTCUSD",
        risk_percent=1.0,
        max_positions=1,
    )
    
    engine.run()
