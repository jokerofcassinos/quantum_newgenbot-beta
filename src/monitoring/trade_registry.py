"""
TradeRegistry - Comprehensive Trade Audit System
Source: DubaiMatrixASI (salvaged and improved)
Created: 2026-04-11

Records all trades with complete audit trail:
- Entry state (indicators, regime, session)
- Exit state (PnL, duration, reason)
- Performance analytics
"""

import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from loguru import logger


class TradeRegistry:
    """
    Trade audit registry.
    
    Inspired by DubaiMatrixASI's implementation.
    """

    def __init__(self, audit_dir: str = "data/trade-registries"):
        """
        Initialize TradeRegistry.
        
        Args:
            audit_dir: Directory for audit files
        """
        self.audit_dir = Path(audit_dir)
        self.audit_dir.mkdir(parents=True, exist_ok=True)
        
        # Current session tracking
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_dir = self.audit_dir / self.session_id
        self.session_dir.mkdir(exist_ok=True)
        
        # Cleanup old sessions (keep last 3)
        self._cleanup_old_sessions()
        
        # Trade tracking
        self.trades: List[Dict[str, Any]] = []
        self.trade_counter = 0
        
        logger.info("📋 TradeRegistry initialized")
        logger.info(f"   Session: {self.session_id}")
        logger.info(f"   Audit dir: {self.session_dir}")

    def _cleanup_old_sessions(self):
        """Remove old session directories, keeping only the last 3."""
        if not self.audit_dir.exists():
            return
        
        sessions = sorted([d for d in self.audit_dir.iterdir() if d.is_dir()])
        for old_session in sessions[:-3]:  # Keep last 3
            import shutil
            shutil.rmtree(old_session, ignore_errors=True)
            logger.info(f"🗑️ Cleaned old session: {old_session.name}")

    def record_entry(self, trade_data: Dict[str, Any]) -> int:
        """
        Record trade entry.
        
        Args:
            trade_data: Complete trade state at entry
            
        Returns:
            Trade ID
        """
        self.trade_counter += 1
        trade_id = self.trade_counter
        
        entry_record = {
            'trade_id': trade_id,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'type': 'entry',
            **trade_data,
        }
        
        # Save to file
        audit_file = self.session_dir / f"trade_{trade_id:04d}_entry.json"
        with open(audit_file, 'w') as f:
            json.dump(entry_record, f, indent=2)
        
        self.trades.append(entry_record)
        
        return trade_id

    def record_exit(self, trade_id: int, exit_data: Dict[str, Any]):
        """
        Record trade exit.
        
        Args:
            trade_id: Trade ID from record_entry
            exit_data: Complete trade state at exit
        """
        exit_record = {
            'trade_id': trade_id,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'type': 'exit',
            **exit_data,
        }
        
        # Save to file
        audit_file = self.session_dir / f"trade_{trade_id:04d}_exit.json"
        with open(audit_file, 'w') as f:
            json.dump(exit_record, f, indent=2)
        
        # Update in-memory trade
        for i, trade in enumerate(self.trades):
            if trade.get('trade_id') == trade_id:
                self.trades[i].update(exit_record)
                break

    def get_session_summary(self) -> Dict[str, Any]:
        """Get summary of current session."""
        if not self.trades:
            return {'total_trades': 0}
        
        wins = [t for t in self.trades if t.get('net_pnl', 0) > 0]
        losses = [t for t in self.trades if t.get('net_pnl', 0) <= 0]
        
        total_pnl = sum(t.get('net_pnl', 0) for t in self.trades)
        
        return {
            'session_id': self.session_id,
            'total_trades': len(self.trades),
            'wins': len(wins),
            'losses': len(losses),
            'win_rate': len(wins) / max(1, len(self.trades)),
            'total_pnl': total_pnl,
            'avg_win': sum(t.get('net_pnl', 0) for t in wins) / max(1, len(wins)),
            'avg_loss': sum(t.get('net_pnl', 0) for t in losses) / max(1, len(losses)),
        }
