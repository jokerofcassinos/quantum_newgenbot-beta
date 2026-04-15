"""
GhostAuditEngine - Shadow Trading for Veto Analysis
CEO: User Suggestion | Created: 2026-04-12

Runs ALL signals (approved + vetoed) as "ghost" trades:
1. Ghost trades follow same TP/SL rules as real trades
2. Generate audit JSON files just like normal trades
3. After backtest, analyze:
   - Vetoed trades that hit TP (false positives = bad vetos)
   - Approved trades that hit SL (true positives = good vetos)
4. Use data to OPTIMIZE veto thresholds instead of guessing

This transforms subjective filtering into data-driven optimization.
"""

from typing import Dict, Any, List, Optional
from loguru import logger
from pathlib import Path
from datetime import datetime, timezone
import json
import numpy as np


class GhostPosition:
    """A ghost trade that runs in parallel to track veto performance."""

    def __init__(
        self,
        ticket: int,
        direction: str,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        volume: float,
        veto_reason: str,
        open_bar_index: int,
        open_time: Any,
        session: str,
        confidence: float,
        regime: str,
    ):
        self.ticket = ticket
        self.direction = direction
        self.entry_price = entry_price
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.volume = volume
        self.veto_reason = veto_reason  # Why was this vetoed?
        self.open_bar_index = open_bar_index
        self.open_time = open_time
        self.session = session
        self.confidence = confidence
        self.regime = regime
        self.is_closed = False
        self.exit_price = None
        self.exit_reason = None
        self.exit_bar_index = None
        self.pnl = 0.0
        self.is_win = False


class GhostAuditEngine:
    """
    Runs ghost trades for ALL signals (including vetoed ones) to analyze veto performance.
    """

    def __init__(
        self,
        audit_dir: str = "data/ghost-audits",
    ):
        """
        Initialize GhostAuditEngine.
        
        Args:
            audit_dir: Directory for ghost audit files
        """
        self.audit_dir = Path(audit_dir)
        self.audit_dir.mkdir(parents=True, exist_ok=True)
        
        # Current session
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_dir = self.audit_dir / self.session_id
        self.session_dir.mkdir(exist_ok=True)
        
        # Ghost positions
        self.ghost_positions: List[GhostPosition] = []
        self.ticket_counter = 0
        
        # Statistics
        self.total_ghost_trades = 0
        self.ghost_wins = 0
        self.ghost_losses = 0
        self.ghost_total_pnl = 0.0
        
        logger.info(" GhostAuditEngine initialized")
        logger.info(f"   Audit dir: {self.session_dir}")

    def create_ghost(
        self,
        signal: Dict[str, Any],
        veto_reason: str,
        bar_index: int,
        cur_time: Any,
        session: str,
    ) -> Optional[GhostPosition]:
        """
        Create a ghost trade for a vetoed signal.
        
        Args:
            signal: The trading signal that was vetoed
            veto_reason: Why this signal was vetoed
            bar_index: Current bar index
            cur_time: Current timestamp
            session: Current session name
            
        Returns:
            GhostPosition object or None
        """
        if 'entry_price' not in signal or 'stop_loss' not in signal or 'take_profit' not in signal:
            return None
        
        self.ticket_counter += 1
        self.total_ghost_trades += 1
        
        ghost = GhostPosition(
            ticket=self.ticket_counter,
            direction=signal['direction'],
            entry_price=signal['entry_price'],
            stop_loss=signal['stop_loss'],
            take_profit=signal['take_profit'],
            volume=signal.get('volume', 0.01),
            veto_reason=veto_reason,
            open_bar_index=bar_index,
            open_time=cur_time,
            session=session,
            confidence=signal.get('confidence', 0.5),
            regime=signal.get('regime') if isinstance(signal.get('regime'), dict) else {'regime_name': str(signal.get('regime', 'unknown'))},
        )
        
        # Correo ps-processamento para garantir que o regime seja o nome
        ghost.regime = ghost.regime.get('regime_name', 'unknown') if isinstance(ghost.regime, dict) else ghost.regime

        
        self.ghost_positions.append(ghost)
        
        # Create entry audit
        self._save_entry_audit(ghost)
        
        return ghost

    def update_ghosts(
        self,
        cur_high: float,
        cur_low: float,
        cur_close: float,
        bar_index: int,
        atr: float,
    ) -> List[GhostPosition]:
        """
        Update all open ghost positions and close any that hit TP/SL.
        
        Args:
            cur_high: Current bar high
            cur_low: Current bar low
            cur_close: Current bar close
            bar_index: Current bar index
            atr: Current ATR value
            
        Returns:
            List of ghost positions that were closed this bar
        """
        closed_ghosts = []
        
        for ghost in self.ghost_positions:
            if ghost.is_closed:
                continue
            
            # Check SL hit
            sl_hit = False
            if ghost.direction == 'BUY' and cur_low <= ghost.stop_loss:
                sl_hit = True
            elif ghost.direction == 'SELL' and cur_high >= ghost.stop_loss:
                sl_hit = True
            
            # Check TP hit
            tp_hit = False
            if ghost.direction == 'BUY' and cur_high >= ghost.take_profit:
                tp_hit = True
            elif ghost.direction == 'SELL' and cur_low <= ghost.take_profit:
                tp_hit = True
            
            # Close position
            if sl_hit:
                ghost.is_closed = True
                ghost.exit_price = ghost.stop_loss
                ghost.exit_reason = 'SL_hit'
                ghost.exit_bar_index = bar_index
                
                if ghost.direction == 'BUY':
                    ghost.pnl = (ghost.exit_price - ghost.entry_price) * ghost.volume
                else:
                    ghost.pnl = (ghost.entry_price - ghost.exit_price) * ghost.volume
                
                ghost.is_win = ghost.pnl > 0
                closed_ghosts.append(ghost)
                
            elif tp_hit:
                ghost.is_closed = True
                ghost.exit_price = ghost.take_profit
                ghost.exit_reason = 'TP_hit'
                ghost.exit_bar_index = bar_index
                
                if ghost.direction == 'BUY':
                    ghost.pnl = (ghost.exit_price - ghost.entry_price) * ghost.volume
                else:
                    ghost.pnl = (ghost.entry_price - ghost.exit_price) * ghost.volume
                
                ghost.is_win = ghost.pnl > 0
                closed_ghosts.append(ghost)
        
        return closed_ghosts

    def _save_entry_audit(self, ghost: GhostPosition):
        """Save entry audit for ghost trade."""
        # Convert non-serializable types
        open_time_str = str(ghost.open_time) if ghost.open_time else 'unknown'
        
        audit_data = {
            'trade_id': ghost.ticket,
            'type': 'ghost_entry',
            'direction': str(ghost.direction),
            'entry_price': float(ghost.entry_price),
            'stop_loss': float(ghost.stop_loss),
            'take_profit': float(ghost.take_profit),
            'volume': float(ghost.volume),
            'veto_reason': str(ghost.veto_reason) if ghost.veto_reason else 'unknown',
            'session': str(ghost.session) if ghost.session else 'unknown',
            'confidence': float(ghost.confidence) if ghost.confidence else 0.0,
            'regime': str(ghost.regime) if ghost.regime else 'unknown',
            'open_time': open_time_str,
            'timestamp': datetime.now(timezone.utc).isoformat(),
        }
        
        audit_file = self.session_dir / f"ghost_{ghost.ticket:04d}_entry.json"
        with open(audit_file, 'w') as f:
            json.dump(audit_data, f, indent=2)

    def _save_exit_audit(self, ghost: GhostPosition):
        """Save exit audit for ghost trade."""
        # Convert non-serializable types
        open_time_str = str(ghost.open_time) if ghost.open_time else 'unknown'
        
        audit_data = {
            'trade_id': ghost.ticket,
            'type': 'ghost_exit',
            'direction': ghost.direction,
            'entry_price': float(ghost.entry_price),
            'exit_price': float(ghost.exit_price) if ghost.exit_price else None,
            'pnl': float(ghost.pnl),
            'is_win': bool(ghost.is_win),
            'exit_reason': str(ghost.exit_reason) if ghost.exit_reason else 'unknown',
            'veto_reason': str(ghost.veto_reason) if ghost.veto_reason else 'unknown',
            'session': str(ghost.session) if ghost.session else 'unknown',
            'confidence': float(ghost.confidence) if ghost.confidence else 0.0,
            'regime': str(ghost.regime) if ghost.regime else 'unknown',
            'duration_bars': int(ghost.exit_bar_index - ghost.open_bar_index) if ghost.exit_bar_index else 0,
            'open_time': open_time_str,
            'timestamp': datetime.now(timezone.utc).isoformat(),
        }
        
        audit_file = self.session_dir / f"ghost_{ghost.ticket:04d}_exit.json"
        with open(audit_file, 'w') as f:
            json.dump(audit_data, f, indent=2)

    def record_exit(self, ghost: GhostPosition):
        """Record a ghost trade exit."""
        if ghost.is_win:
            self.ghost_wins += 1
        else:
            self.ghost_losses += 1
        
        self.ghost_total_pnl += ghost.pnl
        self._save_exit_audit(ghost)

    def generate_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive ghost audit report.
        
        Returns:
            Dict with analysis of veto performance
        """
        if not self.ghost_positions:
            return {'total_ghost_trades': 0}
        
        closed = [g for g in self.ghost_positions if g.is_closed]
        open_positions = [g for g in self.ghost_positions if not g.is_closed]
        
        wins = [g for g in closed if g.is_win]
        losses = [g for g in closed if not g.is_win]
        
        # Analyze veto reasons
        veto_reason_stats = {}
        for ghost in closed:
            reason = ghost.veto_reason or 'unknown'
            if reason not in veto_reason_stats:
                veto_reason_stats[reason] = {
                    'total': 0,
                    'wins': 0,
                    'losses': 0,
                    'total_pnl': 0.0,
                }
            veto_reason_stats[reason]['total'] += 1
            if ghost.is_win:
                veto_reason_stats[reason]['wins'] += 1
            else:
                veto_reason_stats[reason]['losses'] += 1
            veto_reason_stats[reason]['total_pnl'] += ghost.pnl
        
        # Calculate WR for each veto reason
        for reason, stats in veto_reason_stats.items():
            stats['win_rate'] = stats['wins'] / max(1, stats['total'])
        
        # Identify bad vetos (vetoed trades that would have won)
        bad_vetos = [g for g in closed if g.is_win]
        good_vetos = [g for g in closed if not g.is_win]
        
        report = {
            'total_ghost_trades': self.total_ghost_trades,
            'closed_ghosts': len(closed),
            'open_ghosts': len(open_positions),
            'ghost_wins': self.ghost_wins,
            'ghost_losses': self.ghost_losses,
            'ghost_win_rate': self.ghost_wins / max(1, len(closed)),
            'ghost_total_pnl': self.ghost_total_pnl,
            'bad_vetos': len(bad_vetos),  # Trades we vetoed but would have won
            'good_vetos': len(good_vetos),  # Trades we vetoed that would have lost
            'veto_reason_stats': veto_reason_stats,
            'avg_win_size': sum(g.pnl for g in wins) / max(1, len(wins)),
            'avg_loss_size': sum(abs(g.pnl) for g in losses) / max(1, len(losses)),
        }
        
        return report

    def print_analysis(self):
        """Print ghost audit analysis to console."""
        report = self.generate_report()
        
        logger.info("=" * 80)
        logger.info(" GHOST AUDIT ANALYSIS")
        logger.info("=" * 80)
        logger.info(f"   Total Ghost Trades: {report['total_ghost_trades']}")
        logger.info(f"   Closed: {report['closed_ghosts']}")
        logger.info(f"   Still Open: {report['open_ghosts']}")
        logger.info(f"   Ghost Win Rate: {report['ghost_win_rate']*100:.1f}%")
        logger.info(f"   Ghost Total PnL: ${report['ghost_total_pnl']:.2f}")
        logger.info(f"   Bad Vetos (would have won): {report['bad_vetos']}")
        logger.info(f"   Good Vetos (would have lost): {report['good_vetos']}")
        logger.info("")
        
        logger.info(" VETO REASON BREAKDOWN:")
        for reason, stats in report.get('veto_reason_stats', {}).items():
            wr = stats['win_rate'] * 100
            logger.info(f"   {reason}:")
            logger.info(f"      Total: {stats['total']} | WR: {wr:.1f}% | PnL: ${stats['total_pnl']:.2f}")
            if wr > 50:
                logger.warning(f"       BAD VETO: {wr:.0f}% of these would have WON! Consider relaxing this filter.")
            else:
                logger.info(f"       GOOD VETO: Only {wr:.0f}% would have won.")
        
        logger.info("=" * 80)




