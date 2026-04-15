"""
Neural Trade Audit System - Ultra-comprehensive trade logging
CEO: Qwen Code | Created: 2026-04-10

Captures COMPLETE neural state at moment of each trade:
- Market regime analysis
- Session context
- Multi-timeframe analysis
- All indicators values
- Momentum metrics
- Volatility state
- Volume profile
- Order flow dynamics
- DNA state
- Risk parameters
- Smart Order Manager state

Structure:
data/
 trade-audits/
     2026-04-10/
         trade_1000.json
         trade_1001.json
         trade_1002.json
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from dataclasses import dataclass, asdict, field
import numpy as np
import pandas as pd
from loguru import logger


@dataclass
class MarketRegimeAudit:
    """Complete market regime analysis"""
    regime_type: str  # trending_bullish, trending_bearish, ranging, crashing, pumping
    regime_confidence: float
    trend_strength: float  # 0-1
    trend_direction: str  # up, down, neutral
    volatility_regime: str  # low, medium, high, extreme
    volatility_value: float
    volume_regime: str  # low, normal, high
    volume_ratio: float
    market_phase: str  # accumulation, markup, distribution, decline
    session: str  # asian, london, ny, overlap, weekend
    session_volume_profile: float


@dataclass
class MultiTimeframeAudit:
    """Analysis across all timeframes"""
    M1_trend: str
    M5_trend: str
    M15_trend: str
    H1_trend: str
    H4_trend: str
    D1_trend: str
    alignment_score: float  # How aligned are all timeframes (-1 to 1)
    dominant_timeframe: str
    conflict_detected: bool


@dataclass
class IndicatorsAudit:
    """All indicators at moment of trade"""
    # Moving Averages
    ema_9: float
    ema_21: float
    ema_50: float
    ema_200: float
    sma_20: float
    sma_50: float
    
    # MA Relationships
    ema_9_21_cross: str  # bullish, bearish, neutral
    ema_21_50_cross: str
    price_vs_ema_200: str  # above, below
    
    # Momentum
    rsi_14: float
    rsi_regime: str  # oversold, neutral, overbought
    macd_line: float
    macd_signal: float
    macd_histogram: float
    macd_cross: str  # bullish, bearish, neutral
    stochastic_k: float
    stochastic_d: float
    
    # Volatility
    atr_14: float
    atr_percentile: float  # Current ATR vs historical
    bollinger_upper: float
    bollinger_middle: float
    bollinger_lower: float
    bollinger_width: float
    price_vs_bollinger: str  # above_upper, inside, below_lower
    
    # Volume
    volume_current: float
    volume_avg_20: float
    volume_ratio: float
    volume_trend: str  # increasing, decreasing, stable
    obv_trend: str  # up, down, neutral


@dataclass
class PriceActionAudit:
    """Price action analysis"""
    current_price: float
    price_change_1h: float  # % change last hour
    price_change_4h: float  # % change last 4 hours
    price_change_24h: float  # % change last 24 hours
    
    # Support/Resistance
    nearest_support: float
    nearest_resistance: float
    distance_to_support_pct: float
    distance_to_resistance_pct: float
    
    # Candlestick patterns
    current_candle_type: str  # bullish, bearish, doji, hammer, shooting_star
    candle_body_size: float
    candle_wick_ratio: float
    engulfing_detected: bool
    inside_bar_detected: bool
    
    # Price structure
    higher_highs: bool
    higher_lows: bool
    lower_highs: bool
    lower_lows: bool
    structure: str  # uptrend, downtrend, ranging, breaking


@dataclass
class MomentumAudit:
    """Real-time momentum analysis"""
    velocity: float  # points/sec
    acceleration: float
    gravity: float  # mean reversion force
    oscillation: float
    volume_pressure: float
    microstructure_score: float
    momentum_divergence: bool  # Price vs momentum divergence
    exhaustion_signals: List[str]  # Signs of momentum ending


@dataclass
class RiskContextAudit:
    """Risk context at moment of trade"""
    capital: float
    equity: float
    daily_pnl: float
    daily_pnl_percent: float
    total_pnl: float
    total_pnl_percent: float
    current_drawdown: float
    max_drawdown: float
    consecutive_wins: int
    consecutive_losses: int
    daily_loss_used_percent: float
    total_loss_used_percent: float
    ftmo_daily_remaining: float
    ftmo_total_remaining: float


@dataclass
class DNAStateAudit:
    """DNA Engine state at moment of trade"""
    current_regime: str
    regime_confidence: float
    active_strategy: str
    strategy_weights: Dict[str, float]
    risk_percent: float
    min_rr_ratio: float
    confidence_threshold: float
    last_mutation_time: str
    mutation_count: int
    dna_memory_regimes: int


@dataclass
class SmartOrderManagerAudit:
    """Smart Order Manager state"""
    virtual_tp_original: float
    virtual_tp_current: float
    virtual_tp_adjustment_factor: float
    virtual_tp_difficulty: str
    dynamic_sl_original: float
    dynamic_sl_current: float
    breakeven_activated: bool
    profit_targets_reached: List[float]
    momentum_at_entry: Dict[str, float]


@dataclass
class StrategyVoteAudit:
    """Individual strategy vote tracking"""
    strategy_name: str
    vote: str  # BUY, SELL, NEUTRAL
    confidence: float


@dataclass
class StrategyVotingAudit:
    """Complete 12-strategy voting breakdown"""
    strategy_votes: List[StrategyVoteAudit]  # List of individual votes
    buy_votes: int
    sell_votes: int
    neutral_votes: int
    total_strategies: int
    consensus_direction: str
    consensus_confidence: float


@dataclass
class SessionVetoAudit:
    """Session-specific veto tracking"""
    session_name: str  # asian, london, ny, ny_overlap, weekend
    trading_allowed: bool
    min_confidence_threshold: float
    max_position_size: float
    risk_multiplier: float
    min_strategy_votes: int
    min_coherence: float
    veto_applied: bool
    veto_reason: Optional[str] = None


@dataclass
class AdvancedVetoV2Audit:
    """Advanced Veto v2 system tracking"""
    rsi_extremes_veto: bool
    rsi_current: float
    top_bottom_veto: bool
    rsi_divergence_veto: bool
    low_liquidity_veto: bool
    bollinger_extremes_veto: bool
    session_compatibility_veto: bool
    all_vetoes_passed: bool
    vetoed_by: Optional[str] = None
    veto_severity: Optional[str] = None


@dataclass
class TradeAuditLog:
    """Complete neural state audit for a single trade"""
    # Basic info
    ticket: int
    timestamp: str
    symbol: str
    direction: str
    entry_price: float
    stop_loss: float
    take_profit: float
    volume: float
    strategy_name: str
    signal_confidence: float
    
    # Complete neural state
    market_regime: MarketRegimeAudit
    multi_timeframe: MultiTimeframeAudit
    indicators: IndicatorsAudit
    price_action: PriceActionAudit
    momentum: MomentumAudit
    risk_context: RiskContextAudit
    dna_state: DNAStateAudit
    smart_order_manager: SmartOrderManagerAudit

    # NEW: Strategy voting breakdown
    strategy_voting: Optional[StrategyVotingAudit] = None

    # NEW: Session and Advanced Veto tracking
    session_veto: Optional[SessionVetoAudit] = None
    advanced_veto_v2: Optional[AdvancedVetoV2Audit] = None
    
    # Outcome (filled when trade closes)
    exit_price: Optional[float] = None
    exit_timestamp: Optional[str] = None
    exit_reason: Optional[str] = None
    gross_pnl: Optional[float] = None
    net_pnl: Optional[float] = None
    duration_minutes: Optional[int] = None
    max_profit_reached: Optional[float] = None
    max_drawdown_reached: Optional[float] = None
    
    # Analysis
    was_error: bool = False
    error_type: Optional[str] = None  # "overtrading", "wrong_regime", "crash", etc.
    severity: Optional[str] = None  # "minor", "major", "lethal"
    lessons_learned: List[str] = field(default_factory=list)


class NeuralTradeAuditor:
    """
    Captures and stores complete neural state for each trade
    
    Usage:
    1. Call capture_entry_state() when opening trade
    2. Call capture_exit_state() when closing trade
    3. Files saved to data/trade-audits/YYYY-MM-DD/trade_TICKET.json
    """
    
    def __init__(self, base_path: str = "data/trade-audits"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        # Active audits (pending exit)
        self.active_audits: Dict[int, TradeAuditLog] = {}
        
        logger.info(f" Neural Trade Auditor initialized at {self.base_path}")
    
    def capture_entry_state(
        self,
        ticket: int,
        direction: str,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        volume: float,
        strategy_name: str,
        signal_confidence: float,
        market_regime: Dict[str, Any],
        multi_timeframe: Dict[str, Any],
        indicators: Dict[str, Any],
        price_action: Dict[str, Any],
        momentum: Dict[str, Any],
        risk_context: Dict[str, Any],
        dna_state: Dict[str, Any],
        smart_order_manager: Dict[str, Any],
        strategy_voting: Dict[str, Any] = None,  # NEW: Optional voting data
        session_veto: Dict[str, Any] = None,  # NEW: Optional session veto data
        advanced_veto_v2: Dict[str, Any] = None,  # NEW: Optional advanced veto v2 data
    ) -> TradeAuditLog:
        """
        Capture COMPLETE neural state at trade entry
        
        This captures EVERYTHING about the market and system state
        """
        timestamp = datetime.now(timezone.utc).isoformat()

        # Create dataclasses from dicts
        regime_audit = MarketRegimeAudit(**market_regime)
        mtf_audit = MultiTimeframeAudit(**multi_timeframe)
        indicators_audit = IndicatorsAudit(**indicators)
        price_action_audit = PriceActionAudit(**price_action)
        momentum_audit = MomentumAudit(**momentum)
        risk_audit = RiskContextAudit(**risk_context)
        dna_audit = DNAStateAudit(**dna_state)
        som_audit = SmartOrderManagerAudit(**smart_order_manager)

        # NEW: Process strategy voting data if provided
        voting_audit = None
        if strategy_voting:
            # Convert individual strategy votes to StrategyVoteAudit objects
            individual_votes = []
            for strat_name, vote_data in strategy_voting.get('strategy_votes', {}).items():
                individual_votes.append(StrategyVoteAudit(
                    strategy_name=strat_name,
                    vote=vote_data.get('vote', 'NEUTRAL'),
                    confidence=vote_data.get('confidence', 0.5),
                ))
            
            voting_audit = StrategyVotingAudit(
                strategy_votes=individual_votes,
                buy_votes=strategy_voting.get('buy_votes', 0),
                sell_votes=strategy_voting.get('sell_votes', 0),
                neutral_votes=strategy_voting.get('neutral_votes', 0),
                total_strategies=strategy_voting.get('total_strategies', 12),
                consensus_direction=direction,
                consensus_confidence=signal_confidence,
            )

        # NEW: Process session veto data if provided
        session_veto_audit = None
        if session_veto:
            session_veto_audit = SessionVetoAudit(
                session_name=session_veto.get('session_name', 'unknown'),
                trading_allowed=session_veto.get('trading_allowed', True),
                min_confidence_threshold=session_veto.get('min_confidence_threshold', 0.60),
                max_position_size=session_veto.get('max_position_size', 0.10),
                risk_multiplier=session_veto.get('risk_multiplier', 1.0),
                min_strategy_votes=session_veto.get('min_strategy_votes', 3),
                min_coherence=session_veto.get('min_coherence', 0.55),
                veto_applied=not session_veto.get('approved', True),
                veto_reason=session_veto.get('reason'),
            )

        # NEW: Process advanced veto v2 data if provided
        advanced_veto_audit = None
        if advanced_veto_v2:
            advanced_veto_audit = AdvancedVetoV2Audit(
                rsi_extremes_veto=advanced_veto_v2.get('rsi_extremes_veto', False),
                rsi_current=advanced_veto_v2.get('rsi_current', 50.0),
                top_bottom_veto=advanced_veto_v2.get('top_bottom_veto', False),
                rsi_divergence_veto=advanced_veto_v2.get('rsi_divergence_veto', False),
                low_liquidity_veto=advanced_veto_v2.get('low_liquidity_veto', False),
                bollinger_extremes_veto=advanced_veto_v2.get('bollinger_extremes_veto', False),
                session_compatibility_veto=advanced_veto_v2.get('session_compatibility_veto', False),
                all_vetoes_passed=advanced_veto_v2.get('all_vetoes_passed', True),
                vetoed_by=advanced_veto_v2.get('vetoed_by'),
                veto_severity=advanced_veto_v2.get('veto_severity'),
            )

        audit = TradeAuditLog(
            ticket=ticket,
            timestamp=timestamp,
            symbol="BTCUSD",
            direction=direction,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            volume=volume,
            strategy_name=strategy_name,
            signal_confidence=signal_confidence,
            market_regime=regime_audit,
            multi_timeframe=mtf_audit,
            indicators=indicators_audit,
            price_action=price_action_audit,
            momentum=momentum_audit,
            risk_context=risk_audit,
            dna_state=dna_audit,
            smart_order_manager=som_audit,
            strategy_voting=voting_audit,  # NEW: Add voting audit
            session_veto=session_veto_audit,  # NEW: Add session veto audit
            advanced_veto_v2=advanced_veto_audit,  # NEW: Add advanced veto v2 audit
        )
        
        # Store in active audits
        self.active_audits[ticket] = audit
        
        # Save to file
        self._save_audit(audit)
        
        logger.info(f" Entry audit captured for trade #{ticket}")
        logger.info(f"   Regime: {regime_audit.regime_type} ({regime_audit.regime_confidence:.2f})")
        logger.info(f"   Session: {regime_audit.session}")
        logger.info(f"   Momentum: velocity={momentum_audit.velocity:.4f}")
        logger.info(f"   Saved to: {self._get_audit_path(audit)}")
        
        return audit
    
    def capture_exit_state(
        self,
        ticket: int,
        exit_price: float,
        exit_reason: str,
        gross_pnl: float,
        net_pnl: float,
        duration_minutes: int,
        max_profit_reached: float,
        max_drawdown_reached: float,
    ) -> Optional[TradeAuditLog]:
        """
        Capture trade exit and analyze outcome
        """
        if ticket not in self.active_audits:
            logger.warning(f" No active audit for trade #{ticket}")
            return None
        
        audit = self.active_audits[ticket]
        
        # Update exit info
        audit.exit_price = exit_price
        audit.exit_timestamp = datetime.now(timezone.utc).isoformat()
        audit.exit_reason = exit_reason
        audit.gross_pnl = gross_pnl
        audit.net_pnl = net_pnl
        audit.duration_minutes = duration_minutes
        audit.max_profit_reached = max_profit_reached
        audit.max_drawdown_reached = max_drawdown_reached
        
        # Analyze if this was an error trade
        self._analyze_trade_error(audit)
        
        # Save updated audit
        self._save_audit(audit)
        
        # Remove from active
        del self.active_audits[ticket]
        
        logger.info(f" Exit audit captured for trade #{ticket}")
        logger.info(f"   PnL: ${net_pnl:+,.2f}")
        logger.info(f"   Reason: {exit_reason}")
        logger.info(f"   Error: {'YES - ' + audit.error_type if audit.was_error else 'NO'}")
        
        return audit
    
    def _analyze_trade_error(self, audit: TradeAuditLog):
        """
        Analyze if this trade was an error and why
        
        This is the BRAIN that learns from mistakes
        """
        errors = []
        severity = "minor"
        
        # Check 1: Wrong regime
        if audit.market_regime.regime_type in ["crashing", "extreme_volatility"]:
            errors.append("traded_in_extreme_regime")
            severity = "lethal"
        
        # Check 2: Overtrading (consecutive trades in short time)
        if audit.risk_context.consecutive_losses >= 3:
            errors.append("overtrading_after_losses")
            severity = "major"
        
        # Check 3: Low confidence trade
        if audit.signal_confidence < 0.65:
            errors.append("low_confidence_entry")
            severity = "major"
        
        # Check 4: Wrong session
        if audit.market_regime.session in ["asian", "weekend"]:
            if audit.net_pnl is not None and audit.net_pnl < 0:
                errors.append("traded_in_low_liquidity_session")
                severity = "major"
        
        # Check 5: Against strong trend
        if abs(audit.multi_timeframe.alignment_score) > 0.7:
            if (audit.multi_timeframe.M5_trend == "up" and audit.direction == "SELL") or \
               (audit.multi_timeframe.M5_trend == "down" and audit.direction == "BUY"):
                errors.append("traded_against_strong_trend")
                severity = "lethal"
        
        # Check 6: High volatility without adjustment
        if audit.indicators.atr_percentile > 80:
            if audit.net_pnl is not None and audit.net_pnl < 0:
                errors.append("high_volatility_no_adjustment")
                severity = "major"
        
        # Check 7: Near support/resistance
        if audit.price_action.distance_to_support_pct < 0.5 and audit.direction == "SELL":
            errors.append("sold_near_support")
            severity = "major"
        
        if audit.price_action.distance_to_resistance_pct < 0.5 and audit.direction == "BUY":
            errors.append("bought_near_resistance")
            severity = "major"
        
        # Check 8: RSI extreme
        if audit.indicators.rsi_regime == "oversold" and audit.direction == "SELL":
            errors.append("sold_in_oversold")
            severity = "minor"
        
        if audit.indicators.rsi_regime == "overbought" and audit.direction == "BUY":
            errors.append("bought_in_overbought")
            severity = "minor"
        
        # Set error status
        if errors:
            audit.was_error = True
            audit.error_type = ";".join(errors)
            audit.severity = severity
            audit.lessons_learned = self._generate_lessons(errors, audit)
    
    def _generate_lessons(self, errors: List[str], audit: TradeAuditLog) -> List[str]:
        """Generate lessons learned from errors"""
        lessons = []
        
        error_lessons = {
            "traded_in_extreme_regime": "NEVER trade in crashing/extreme volatility regimes",
            "overtrading_after_losses": "STOP after 3 consecutive losses - cool down required",
            "low_confidence_entry": "REJECT signals with confidence < 0.65",
            "traded_in_low_liquidity_session": "AVOID trading in Asian session/weekends",
            "traded_against_strong_trend": "NEVER trade against aligned multi-timeframe trend",
            "high_volatility_no_adjustment": "REDUCE size or WIDEN stops in high volatility",
            "sold_near_support": "DON'T sell when price is near support level",
            "bought_near_resistance": "DON'T buy when price is near resistance level",
            "sold_in_oversold": "DON'T sell when RSI < 30 (oversold)",
            "bought_in_overbought": "DON'T buy when RSI > 70 (overbought)",
        }
        
        for error in errors:
            if error in error_lessons:
                lessons.append(error_lessons[error])
        
        return lessons
    
    def _save_audit(self, audit: TradeAuditLog):
        """Save audit to JSON file AND memory buffer in backtest mode"""
        if getattr(self, '_backtest_mode', False):
            if not hasattr(self, 'audits'):
                self.audits = []
            
            existing = [i for i, a in enumerate(self.audits) if a.ticket == audit.ticket]
            if existing:
                self.audits[existing[0]] = audit
            else:
                self.audits.append(audit)
            # Removed the `return` here so we ALSO write to physical disk during backtest!
        
        filepath = self._get_audit_path(audit)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert to dict
        audit_dict = asdict(audit)
        
        # Save
        with open(filepath, 'w') as f:
            json.dump(audit_dict, f, indent=2, default=str)
    
    def _get_audit_path(self, audit: TradeAuditLog) -> Path:
        """Get file path for audit"""
        date_str = audit.timestamp[:10]  # YYYY-MM-DD
        return self.base_path / date_str / f"trade_{audit.ticket}.json"
    
    def get_all_audits(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[TradeAuditLog]:
        """Load all audits (from memory if in backtest mode, else disk)"""
        if getattr(self, '_backtest_mode', False) and hasattr(self, 'audits') and self.audits:
            return self.audits

        audits = []
        
        base = self.base_path
        if not base.exists():
            return []
        
        # Iterate through date folders
        for date_dir in sorted(base.iterdir()):
            if not date_dir.is_dir():
                continue
            
            date_str = date_dir.name
            
            # Filter by date range
            if start_date and date_str < start_date:
                continue
            if end_date and date_str > end_date:
                continue
            
            # Load all trade files
            for trade_file in sorted(date_dir.glob("trade_*.json")):
                try:
                    with open(trade_file, 'r') as f:
                        data = json.load(f)
                    audit = TradeAuditLog(**data)
                    audits.append(audit)
                except Exception as e:
                    logger.error(f"Error loading {trade_file}: {e}")
        
        return audits




