"""
Veto Orchestrator - Pre-trade validation system
CEO: Qwen Code | Created: 2026-04-10

Before ANY trade executes, it must pass through the Veto Chain:
1. Load veto rules from pattern analysis
2. Check trade against ALL rules
3. If ANY lethal rule triggers  REJECT
4. If ANY major rule triggers  REJECT
5. If multiple minor rules trigger  REJECT
6. If passes all  APPROVE

This is the FINAL gatekeeper before trade execution.
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass
from loguru import logger


@dataclass
class VetoResult:
    """Result of veto check"""
    approved: bool
    vetoed_by: Optional[str] = None
    severity: Optional[str] = None
    confidence: Optional[float] = None
    reason: Optional[str] = None
    triggered_rules: List[Dict[str, Any]] = None


class VetoOrchestrator:
    """
    Pre-trade veto system
    
    Before any trade executes, it MUST pass through this orchestrator.
    The orchestrator checks against ALL learned veto rules.
    """
    
    def __init__(self, veto_rules_path: str = "config/veto_rules.json"):
        self.veto_rules_path = Path(veto_rules_path)
        self.veto_rules = {"rules": []}
        self.total_checks = 0
        self.total_vetoes = 0
        self.veto_history: List[Dict[str, Any]] = []
        
        # Load rules
        self._load_rules()
        
        logger.info(f" Veto Orchestrator initialized")
        logger.info(f"   Rules loaded: {len(self.veto_rules.get('rules', []))}")
        logger.info(f"   Lethal rules: {sum(1 for r in self.veto_rules.get('rules', []) if r.get('severity') == 'lethal')}")
        logger.info(f"   Major rules: {sum(1 for r in self.veto_rules.get('rules', []) if r.get('severity') == 'major')}")
    
    def _load_rules(self):
        """Load veto rules from file"""
        if self.veto_rules_path.exists():
            with open(self.veto_rules_path, 'r') as f:
                self.veto_rules = json.load(f)
            logger.info(f" Loaded {len(self.veto_rules.get('rules', []))} veto rules")
        else:
            logger.warning(f" No veto rules found at {self.veto_rules_path}")
            logger.warning(f"   Run pattern analysis first to generate rules")
    
    def reload_rules(self):
        """Reload rules (call after pattern analysis updates)"""
        self._load_rules()
    
    def check_trade(self, trade_context: Dict[str, Any]) -> VetoResult:
        """
        Check if a trade should be vetoed
        
        Args:
            trade_context: Complete trade context (same structure as audit)
        
        Returns:
            VetoResult: approved=True if trade can proceed
        """
        self.total_checks += 1
        
        rules = self.veto_rules.get("rules", [])
        
        if not rules:
            # No rules = approve by default
            return VetoResult(
                approved=True,
                reason="No veto rules configured"
            )
        
        triggered = []
        
        # Check each rule
        for rule in rules:
            if self._rule_triggers(rule, trade_context):
                triggered.append(rule)
        
        # Determine result
        if not triggered:
            return VetoResult(
                approved=True,
                reason="Passed all veto checks"
            )
        
        # Find most severe trigger
        lethal_rules = [r for r in triggered if r.get("severity") == "lethal"]
        major_rules = [r for r in triggered if r.get("severity") == "major"]
        minor_rules = [r for r in triggered if r.get("severity") == "minor"]
        
        if lethal_rules:
            veto_rule = lethal_rules[0]
            veto_reason = f"LETHAL: {veto_rule.get('name', 'Unknown rule')}"
            self.total_vetoes += 1
            
        elif major_rules:
            veto_rule = major_rules[0]
            veto_reason = f"MAJOR: {veto_rule.get('name', 'Unknown rule')}"
            self.total_vetoes += 1
            
        elif len(minor_rules) >= 2:  # 2+ minor rules = veto
            veto_rule = minor_rules[0]
            veto_reason = f"MULTIPLE MINOR: {len(minor_rules)} minor rules triggered"
            self.total_vetoes += 1
        else:
            # Only 1 minor rule = approve with warning
            return VetoResult(
                approved=True,
                reason="Passed with 1 minor warning"
            )
        
        # Log veto
        self.veto_history.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "vetoed_by": veto_rule.get("name"),
            "severity": veto_rule.get("severity"),
            "confidence": veto_rule.get("confidence"),
            "reason": veto_reason,
        })
        
        logger.warning(f" TRADE VETOED: {veto_reason}")
        logger.warning(f"   Rule: {veto_rule.get('name')}")
        logger.warning(f"   Confidence: {veto_rule.get('confidence'):.2f}")
        logger.warning(f"   Total vetoes: {self.total_vetoes}/{self.total_checks}")
        
        return VetoResult(
            approved=False,
            vetoed_by=veto_rule.get("name"),
            severity=veto_rule.get("severity"),
            confidence=veto_rule.get("confidence"),
            reason=veto_reason,
            triggered_rules=triggered,
        )
    
    def _rule_triggers(self, rule: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """
        Check if a specific rule triggers for this trade
        
        Each rule has conditions that must all be true
        """
        conditions = rule.get("conditions", {})
        
        # Check regime condition
        if "regime_type" in conditions:
            if context.get("market_regime", {}).get("regime_type") != conditions["regime_type"]:
                return False
        
        # Check MTF conflict
        if "mtf_conflict" in conditions:
            if context.get("multi_timeframe", {}).get("conflict_detected") != conditions["mtf_conflict"]:
                return False
        
        # Check consecutive losses
        if "consecutive_losses" in conditions:
            threshold = conditions["consecutive_losses"]
            if context.get("risk_context", {}).get("consecutive_losses", 0) < threshold:
                return False
        
        # Check session
        if "session" in conditions:
            if context.get("market_regime", {}).get("session") != conditions["session"]:
                return False
        
        # Check RSI
        if "rsi_extreme" in conditions:
            rsi = context.get("indicators", {}).get("rsi_14", 50)
            direction = context.get("direction", "")
            if conditions["rsi_extreme"] == "oversold_sell" and not (rsi < 30 and direction == "SELL"):
                return False
            if conditions["rsi_extreme"] == "overbought_buy" and not (rsi > 70 and direction == "BUY"):
                return False
        
        # All conditions met
        return True
    
    def get_stats(self) -> Dict[str, Any]:
        """Get veto statistics"""
        return {
            "total_checks": self.total_checks,
            "total_vetoes": self.total_vetoes,
            "veto_rate": self.total_vetoes / max(1, self.total_checks) * 100,
            "rules_loaded": len(self.veto_rules.get("rules", [])),
            "lethal_rules": sum(1 for r in self.veto_rules.get("rules", []) if r.get("severity") == "lethal"),
            "major_rules": sum(1 for r in self.veto_rules.get("rules", []) if r.get("severity") == "major"),
            "minor_rules": sum(1 for r in self.veto_rules.get("rules", []) if r.get("severity") == "minor"),
        }




