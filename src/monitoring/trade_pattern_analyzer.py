"""
Trade Pattern Analyzer - Finds patterns in losing trades
CEO: Qwen Code | Created: 2026-04-10

Analyzes ALL trade audits to find:
- Common error patterns
- Lethal conditions
- Regime-specific failures
- Session-based weaknesses
- Indicator confluences that predict failure
- DNA states that correlate with losses

Output: veto_rules.json - Rules that should veto future trades
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime, timezone
from collections import Counter, defaultdict
from dataclasses import dataclass
import numpy as np
from loguru import logger

from src.monitoring.neural_trade_auditor import NeuralTradeAuditor, TradeAuditLog


@dataclass
class ErrorPattern:
    """Discovered error pattern"""
    pattern_id: str
    pattern_name: str
    severity: str  # lethal, major, minor
    frequency: int  # How often this pattern appears
    loss_rate: float  # % of trades with this pattern that lose
    avg_loss_when_present: float
    conditions: Dict[str, Any]  # Conditions that define this pattern
    veto_recommendation: bool  # Should we veto trades with this pattern?
    confidence: float  # How confident we are this is a real pattern


class TradePatternAnalyzer:
    """
    Analyzes trade audits to find patterns in losses
    
    Uses statistical analysis to find conditions that correlate with losses
    """
    
    def __init__(self, auditor: NeuralTradeAuditor):
        self.auditor = auditor
        self.error_patterns: List[ErrorPattern] = []
        self.veto_rules: Dict[str, Any] = {}
        
        logger.info(" Trade Pattern Analyzer initialized")
    
    def analyze_all(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict[str, Any]:
        """
        Complete analysis of all trades
        
        Returns:
            dict: Analysis results and veto rules
        """
        logger.info("="*80)
        logger.info(" STARTING TRADE PATTERN ANALYSIS")
        logger.info("="*80)
        
        # Load all audits
        audits = self.auditor.get_all_audits(start_date, end_date)
        
        if not audits:
            logger.warning(" No trade audits found")
            return {}
        
        logger.info(f" Loaded {len(audits)} trade audits")
        
        # Separate winners and losers
        winners = [a for a in audits if a.net_pnl and a.net_pnl > 0]
        losers = [a for a in audits if a.net_pnl and a.net_pnl <= 0]
        errors = [a for a in audits if a.was_error]
        
        logger.info(f"   Winners: {len(winners)} ({len(winners)/len(audits)*100:.1f}%)")
        logger.info(f"   Losers: {len(losers)} ({len(losers)/len(audits)*100:.1f}%)")
        logger.info(f"   Flagged Errors: {len(errors)}")
        
        # Analysis 1: Error type frequency
        self._analyze_error_types(audits)
        
        # Analysis 2: Regime-based patterns
        self._analyze_regime_patterns(audits, winners, losers)
        
        # Analysis 3: Session-based patterns
        self._analyze_session_patterns(audits, winners, losers)
        
        # Analysis 4: Multi-timeframe conflict patterns
        self._analyze_mtf_patterns(audits, winners, losers)
        
        # Analysis 5: Indicator confluence patterns
        self._analyze_indicator_patterns(audits, winners, losers)
        
        # Analysis 6: Risk context patterns
        self._analyze_risk_patterns(audits, winners, losers)
        
        # Analysis 7: Momentum at entry patterns
        self._analyze_momentum_patterns(audits, winners, losers)
        
        # Analysis 8: Time-based patterns
        self._analyze_time_patterns(audits, winners, losers)
        
        # Generate veto rules
        self._generate_veto_rules()
        
        # Summary
        results = self._generate_summary()
        
        logger.info(f"\n{'='*80}")
        logger.info(f" ANALYSIS COMPLETE")
        logger.info(f"{'='*80}")
        logger.info(f"   Total Trades Analyzed: {len(audits)}")
        logger.info(f"   Error Patterns Found: {len(self.error_patterns)}")
        logger.info(f"   Veto Rules Generated: {len(self.veto_rules.get('rules', []))}")
        logger.info(f"   Estimated Loss Prevention: {results.get('estimated_improvement', 0):.1f}%")
        logger.info(f"{'='*80}")
        
        return results
    
    def _analyze_error_types(self, audits: List[TradeAuditLog]):
        """Analyze frequency of each error type"""
        logger.info(f"\n Analysis 1: Error Types")
        
        error_counter = Counter()
        severity_counter = Counter()
        
        for audit in audits:
            if audit.was_error and audit.error_type:
                for error in audit.error_type.split(";"):
                    error_counter[error] += 1
                    if audit.severity:
                        severity_counter[audit.severity] += 1
        
        logger.info(f"   Error frequencies:")
        for error, count in error_counter.most_common(10):
            logger.info(f"      {error}: {count} occurrences")
        
        logger.info(f"   Severity distribution:")
        for sev, count in severity_counter.most_common():
            logger.info(f"      {sev}: {count}")
    
    def _get_regime(self, audit):
        """Helper to get regime from audit (handles both dict and dataclass)"""
        if isinstance(audit, dict):
            return audit.get('market_regime', {}).get('regime_type', 'unknown')
        return getattr(audit.market_regime, 'regime_type', 'unknown')
    
    def _get_pnl(self, audit):
        """Helper to get PnL from audit"""
        if isinstance(audit, dict):
            return audit.get('net_pnl', 0)
        return getattr(audit, 'net_pnl', 0)
    
    def _get_session(self, audit):
        """Helper to get session"""
        if isinstance(audit, dict):
            return audit.get('market_regime', {}).get('session', 'unknown')
        return getattr(audit.market_regime, 'session', 'unknown')
    
    def _get_mtf_conflict(self, audit):
        """Helper to get MTF conflict status"""
        if isinstance(audit, dict):
            return audit.get('multi_timeframe', {}).get('conflict_detected', False)
        return getattr(audit.multi_timeframe, 'conflict_detected', False)
    
    def _get_rsi_regime(self, audit):
        """Helper to get RSI regime"""
        if isinstance(audit, dict):
            return audit.get('indicators', {}).get('rsi_regime', 'neutral')
        return getattr(audit.indicators, 'rsi_regime', 'neutral')
    
    def _get_direction(self, audit):
        """Helper to get trade direction"""
        if isinstance(audit, dict):
            return audit.get('direction', 'unknown')
        return getattr(audit, 'direction', 'unknown')
    
    def _get_consecutive_losses(self, audit):
        """Helper to get consecutive losses"""
        if isinstance(audit, dict):
            return audit.get('risk_context', {}).get('consecutive_losses', 0)
        return getattr(audit.risk_context, 'consecutive_losses', 0)
    
    def _get_atr_percentile(self, audit):
        """Helper to get ATR percentile"""
        if isinstance(audit, dict):
            return audit.get('indicators', {}).get('atr_percentile', 50)
        return getattr(audit.indicators, 'atr_percentile', 50)
    
    def _get_distance_to_support(self, audit):
        """Helper to get distance to support"""
        if isinstance(audit, dict):
            return audit.get('price_action', {}).get('distance_to_support_pct', 1.0)
        return getattr(audit.price_action, 'distance_to_support_pct', 1.0)
    
    def _get_distance_to_resistance(self, audit):
        """Helper to get distance to resistance"""
        if isinstance(audit, dict):
            return audit.get('price_action', {}).get('distance_to_resistance_pct', 1.0)
        return getattr(audit.price_action, 'distance_to_resistance_pct', 1.0)
    
    def _get_velocity(self, audit):
        """Helper to get momentum velocity"""
        if isinstance(audit, dict):
            return audit.get('momentum', {}).get('velocity', 0.5)
        return getattr(audit.momentum, 'velocity', 0.5)
    
    def _analyze_regime_patterns(self, audits, winners, losers):
        """Find regimes that correlate with losses"""
        logger.info(f"\n Analysis 2: Regime Patterns")
        
        winner_regimes = Counter(self._get_regime(a) for a in winners)
        loser_regimes = Counter(self._get_regime(a) for a in losers)
        all_regimes = Counter(self._get_regime(a) for a in audits)
        
        logger.info(f"   Regime distribution:")
        for regime in all_regimes.most_common():
            wins = winner_regimes.get(regime[0], 0)
            loss = loser_regimes.get(regime[0], 0)
            total = wins + loss
            loss_rate = loss / total * 100 if total > 0 else 0
            win_rate = wins / total * 100 if total > 0 else 0

            logger.info(f"      {regime[0]}: {regime[1]} trades | WR: {win_rate:.1f}% | LR: {loss_rate:.1f}%")
            
            # If loss rate > 70%, create veto pattern
            if loss_rate > 70 and total >= 5:
                pattern = ErrorPattern(
                    pattern_id=f"regime_{regime[0]}",
                    pattern_name=f"Trade in {regime[0]} regime",
                    severity="lethal" if loss_rate > 80 else "major",
                    frequency=total,
                    loss_rate=loss_rate / 100,
                    avg_loss_when_present=np.mean([a.net_pnl for a in losers if a.market_regime.regime_type == regime[0]]),
                    conditions={"regime_type": regime[0]},
                    veto_recommendation=True,
                    confidence=min(loss_rate / 100, 1.0),
                )
                self.error_patterns.append(pattern)
    
    def _analyze_session_patterns(self, audits, winners, losers):
        """Find sessions that correlate with losses"""
        logger.info(f"\n Analysis 3: Session Patterns")
        
        winner_sessions = Counter(self._get_session(a) for a in winners)
        loser_sessions = Counter(self._get_session(a) for a in losers)
        all_sessions = Counter(self._get_session(a) for a in audits)
        
        logger.info(f"   Session performance:")
        for session in all_sessions.most_common():
            wins = winner_sessions.get(session[0], 0)
            loss = loser_sessions.get(session[0], 0)
            total = wins + loss
            loss_rate = loss / total * 100 if total > 0 else 0
            win_rate = wins / total * 100 if total > 0 else 0

            logger.info(f"      {session[0]}: {session[1]} trades | WR: {win_rate:.1f}% | LR: {loss_rate:.1f}%")
    
    def _analyze_mtf_patterns(self, audits, winners, losers):
        """Find multi-timeframe conflict patterns"""
        logger.info(f"\n Analysis 4: Multi-Timeframe Patterns")
        
        aligned_wins = sum(1 for a in winners if abs(a.get('multi_timeframe', {}).get('alignment_score', 0) if isinstance(a, dict) else abs(getattr(a.multi_timeframe, 'alignment_score', 0))) > 0.5)
        aligned_losses = sum(1 for a in losers if abs(a.get('multi_timeframe', {}).get('alignment_score', 0) if isinstance(a, dict) else abs(getattr(a.multi_timeframe, 'alignment_score', 0))) > 0.5)
        aligned_total = aligned_wins + aligned_losses
        
        if aligned_total > 0:
            aligned_wr = aligned_wins / aligned_total * 100
            logger.info(f"   High alignment (|score| > 0.5): {aligned_total} trades | WR: {aligned_wr:.1f}%")
        
        conflict_wins = sum(1 for a in winners if self._get_mtf_conflict(a))
        conflict_losses = sum(1 for a in losers if self._get_mtf_conflict(a))
        conflict_total = conflict_wins + conflict_losses
        
        if conflict_total > 0:
            conflict_wr = conflict_wins / conflict_total * 100
            logger.info(f"   MTF conflicts: {conflict_total} trades | WR: {conflict_wr:.1f}%")
            
            if conflict_wr < 40 and conflict_total >= 5:
                pattern = ErrorPattern(
                    pattern_id="mtf_conflict",
                    pattern_name="Trade during MTF conflict",
                    severity="major",
                    frequency=conflict_total,
                    loss_rate=1 - conflict_wr/100,
                    avg_loss_when_present=np.mean([a.net_pnl for a in losers if a.multi_timeframe.conflict_detected]),
                    conditions={"mtf_conflict": True},
                    veto_recommendation=True,
                    confidence=1 - conflict_wr/100,
                )
                self.error_patterns.append(pattern)
    
    def _analyze_indicator_patterns(self, audits, winners, losers):
        """Find indicator patterns that correlate with losses"""
        logger.info(f"\n Analysis 5: Indicator Patterns")
        
        rsi_oversold_losses = sum(1 for a in losers if self._get_rsi_regime(a) == 'oversold' and self._get_direction(a) == 'SELL')
        rsi_overbought_losses = sum(1 for a in losers if self._get_rsi_regime(a) == 'overbought' and self._get_direction(a) == 'BUY')
        
        logger.info(f"   RSI extremes causing losses:")
        logger.info(f"      Sold in oversold: {rsi_oversold_losses}")
        logger.info(f"      Bought in overbought: {rsi_overbought_losses}")
        
        high_atr_losses = [a for a in losers if self._get_atr_percentile(a) > 80]
        if len(high_atr_losses) >= 5:
            logger.info(f"   High ATR losses: {len(high_atr_losses)}")
    
    def _analyze_risk_patterns(self, audits, winners, losers):
        """Find risk context patterns"""
        logger.info(f"\n Analysis 6: Risk Context Patterns")
        
        consec_3_plus = [a for a in audits if self._get_consecutive_losses(a) >= 3]
        consec_losses_in_series = sum(1 for a in consec_3_plus if self._get_pnl(a) and self._get_pnl(a) < 0)
        
        if consec_3_plus:
            loss_rate = consec_losses_in_series / len(consec_3_plus) * 100
            logger.info(f"   Trades after 3+ consecutive losses: {len(consec_3_plus)} | LR: {loss_rate:.1f}%")
            
            if loss_rate > 60:
                pattern = ErrorPattern(
                    pattern_id="consecutive_losses",
                    pattern_name="Trade after 3+ consecutive losses",
                    severity="lethal",
                    frequency=len(consec_3_plus),
                    loss_rate=loss_rate / 100,
                    avg_loss_when_present=np.mean([a.net_pnl for a in consec_3_plus if a.net_pnl and a.net_pnl < 0]),
                    conditions={"consecutive_losses": 3},
                    veto_recommendation=True,
                    confidence=loss_rate / 100,
                )
                self.error_patterns.append(pattern)
        
        # Daily loss approaching limit
        def check_daily_loss(a):
            val = a.get('risk_context', {}).get('daily_loss_used_percent', 0) if isinstance(a, dict) else getattr(a.risk_context, 'daily_loss_used_percent', 0)
            return val > 60
        
        high_daily_loss = [a for a in audits if check_daily_loss(a)]
        if high_daily_loss:
            daily_losses = sum(1 for a in high_daily_loss if self._get_pnl(a) and self._get_pnl(a) < 0)
            logger.info(f"   Trades when daily loss > 60%: {len(high_daily_loss)} | Losses: {daily_losses}")
    
    def _analyze_momentum_patterns(self, audits, winners, losers):
        """Find momentum patterns at entry"""
        logger.info(f"\n Analysis 7: Momentum Patterns")
        
        high_vel = [a for a in audits if self._get_velocity(a) > 2.0]
        if high_vel:
            high_vel_losses = sum(1 for a in high_vel if self._get_pnl(a) and self._get_pnl(a) < 0)
            loss_rate = high_vel_losses / len(high_vel) * 100
            logger.info(f"   High velocity entries: {len(high_vel)} | LR: {loss_rate:.1f}%")
    
    def _analyze_time_patterns(self, audits, winners, losers):
        """Find time-based patterns"""
        logger.info(f"\n Analysis 8: Time Patterns")
        
        hourly = defaultdict(lambda: {"wins": 0, "losses": 0})
        
        for audit in audits:
            try:
                ts = audit.get('timestamp', '') if isinstance(audit, dict) else getattr(audit, 'timestamp', '')
                if ts:
                    hour = datetime.fromisoformat(ts).hour
                    pnl = self._get_pnl(audit)
                    if pnl and pnl > 0:
                        hourly[hour]["wins"] += 1
                    else:
                        hourly[hour]["losses"] += 1
            except:
                pass
        
        logger.info(f"   Hourly performance:")
        for hour in sorted(hourly.keys()):
            data = hourly[hour]
            total = data["wins"] + data["losses"]
            if total >= 3:
                wr = data["wins"] / total * 100
                logger.info(f"      {hour:02d}:00 | {total} trades | WR: {wr:.1f}%")
    
    def _generate_veto_rules(self):
        """Generate veto rules from discovered patterns"""
        logger.info(f"\n Generating veto rules...")
        
        rules = []
        
        for pattern in self.error_patterns:
            if pattern.veto_recommendation and pattern.confidence > 0.6:
                rule = {
                    "rule_id": pattern.pattern_id,
                    "name": pattern.pattern_name,
                    "severity": pattern.severity,
                    "conditions": pattern.conditions,
                    "confidence": pattern.confidence,
                    "expected_loss_prevention": pattern.loss_rate,
                    "frequency": pattern.frequency,
                }
                rules.append(rule)
        
        # Sort by severity and confidence
        severity_order = {"lethal": 0, "major": 1, "minor": 2}
        rules.sort(key=lambda r: (severity_order.get(r["severity"], 3), -r["confidence"]))
        
        self.veto_rules = {
            "version": "1.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_patterns_analyzed": len(self.error_patterns),
            "rules": rules,
            "implementation": {
                "check_order": "lethal > major > minor",
                "min_confidence_threshold": 0.6,
                "action_on_veto": "REJECT trade immediately",
                "override_possible": False,
            }
        }
        
        logger.info(f"   Generated {len(rules)} veto rules:")
        for rule in rules:
            logger.info(f"      [{rule['severity'].upper()}] {rule['name']} (confidence: {rule['confidence']:.2f})")
    
    def _generate_summary(self) -> Dict[str, Any]:
        """Generate analysis summary"""
        total_trades = sum(p.frequency for p in self.error_patterns)
        lethal_patterns = [p for p in self.error_patterns if p.severity == "lethal"]
        major_patterns = [p for p in self.error_patterns if p.severity == "major"]
        
        # Estimate improvement
        potential_saves = sum(p.frequency * p.loss_rate for p in self.error_patterns if p.veto_recommendation)
        
        return {
            "total_trades_analyzed": total_trades,
            "error_patterns_found": len(self.error_patterns),
            "lethal_patterns": len(lethal_patterns),
            "major_patterns": len(major_patterns),
            "veto_rules_generated": len(self.veto_rules.get("rules", [])),
            "estimated_improvement": potential_saves,
            "top_errors": [
                {"pattern": p.pattern_name, "frequency": p.frequency, "loss_rate": p.loss_rate}
                for p in sorted(self.error_patterns, key=lambda x: -x.frequency)[:5]
            ],
            "veto_rules": self.veto_rules,
        }
    
    def save_veto_rules(self, filepath: str = "config/veto_rules.json"):
        """Save veto rules to file"""
        if not self.veto_rules.get("rules"):
            logger.info("   No new rules generated. Preserving existing veto_rules.json.")
            return
            
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w') as f:
            json.dump(self.veto_rules, f, indent=2, default=str)
        
        logger.info(f" Veto rules saved to {path}")




