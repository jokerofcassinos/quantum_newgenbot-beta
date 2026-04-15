"""
PositionManager Smart TP - Multi-Target Take-Profit System
Source: DubaiMatrixASI (salvaged and improved)
Created: 2026-04-11

Splits positions into multiple chunks with different TP levels:
- 30%  TP1 at 1:1 R:R (quick profit)
- 30%  TP2 at 1:2 R:R (medium target)
- 20%  TP3 at 1:3 R:R (runner)
- 20%  Trailing stop (let it run)

As each TP hits:
- Lock in profit for that portion
- Move remaining SL to breakeven
- Continue managing remainder
"""

from typing import Dict, Any, List, Optional, Tuple
from loguru import logger


class PositionManagerSmartTP:
    """
    Manages positions with multi-target take-profit system.
    
    Inspired by DubaiMatrixASI's Smart TP implementation but simplified and improved.
    """

    def __init__(
        self,
        tp1_portion: float = 0.30,
        tp1_rr: float = 1.0,
        tp2_portion: float = 0.30,
        tp2_rr: float = 2.0,
        tp3_portion: float = 0.20,
        tp3_rr: float = 3.0,
        trailing_portion: float = 0.20,
        trailing_atr_multiplier: float = 1.5,
    ):
        """
        Initialize Smart TP Position Manager.
        
        Args:
            tp1_portion: Portion for first TP (default 30%)
            tp1_rr: R:R ratio for first TP (default 1:1)
            tp2_portion: Portion for second TP (default 30%)
            tp2_rr: R:R ratio for second TP (default 1:2)
            tp3_portion: Portion for third TP (default 20%)
            tp3_rr: R:R ratio for third TP (default 1:3)
            trailing_portion: Portion for trailing stop (default 20%)
            trailing_atr_multiplier: ATR multiplier for trailing distance
        """
        # Validate portions sum to 1.0
        total = tp1_portion + tp2_portion + tp3_portion + trailing_portion
        if abs(total - 1.0) > 0.01:
            logger.warning(f" Smart TP portions sum to {total:.2f}, normalizing to 1.0")
            scale = 1.0 / total
            tp1_portion *= scale
            tp2_portion *= scale
            tp3_portion *= scale
            trailing_portion *= scale
        
        self.tp1_portion = tp1_portion
        self.tp1_rr = tp1_rr
        self.tp2_portion = tp2_portion
        self.tp2_rr = tp2_rr
        self.tp3_portion = tp3_portion
        self.tp3_rr = tp3_rr
        self.trailing_portion = trailing_portion
        self.trailing_atr_multiplier = trailing_atr_multiplier
        
        logger.info(" PositionManager Smart TP initialized")
        logger.info(f"   TP1: {tp1_portion*100:.0f}% @ {tp1_rr}:1 R:R")
        logger.info(f"   TP2: {tp2_portion*100:.0f}% @ {tp2_rr}:1 R:R")
        logger.info(f"   TP3: {tp3_portion*100:.0f}% @ {tp3_rr}:1 R:R")
        logger.info(f"   Trail: {trailing_portion*100:.0f}% @ {trailing_atr_multiplier}x ATR")

    def create_position_targets(
        self,
        entry_price: float,
        stop_loss: float,
        direction: str,
        atr: float,
    ) -> Dict[str, Any]:
        """
        Create TP targets for a new position.
        
        Args:
            entry_price: Entry price
            stop_loss: Stop loss price
            direction: 'BUY' or 'SELL'
            atr: Current ATR value
            
        Returns:
            Dict with position targets and tracking state
        """
        # Calculate initial risk
        risk_distance = abs(entry_price - stop_loss)
        
        # Calculate TP levels based on R:R
        if direction == 'BUY':
            tp1_price = entry_price + (risk_distance * self.tp1_rr)
            tp2_price = entry_price + (risk_distance * self.tp2_rr)
            tp3_price = entry_price + (risk_distance * self.tp3_rr)
        else:  # SELL
            tp1_price = entry_price - (risk_distance * self.tp1_rr)
            tp2_price = entry_price - (risk_distance * self.tp2_rr)
            tp3_price = entry_price - (risk_distance * self.tp3_rr)
        
        return {
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'original_stop': stop_loss,
            'direction': direction,
            'risk_distance': risk_distance,
            'targets': [
                {
                    'name': 'TP1',
                    'portion': self.tp1_portion,
                    'rr': self.tp1_rr,
                    'price': tp1_price,
                    'closed': False,
                    'closed_price': None,
                    'pnl': 0.0,
                },
                {
                    'name': 'TP2',
                    'portion': self.tp2_portion,
                    'rr': self.tp2_rr,
                    'price': tp2_price,
                    'closed': False,
                    'closed_price': None,
                    'pnl': 0.0,
                },
                {
                    'name': 'TP3',
                    'portion': self.tp3_portion,
                    'rr': self.tp3_rr,
                    'price': tp3_price,
                    'closed': False,
                    'closed_price': None,
                    'pnl': 0.0,
                },
                {
                    'name': 'TRAILING',
                    'portion': self.trailing_portion,
                    'rr': None,  # Dynamic
                    'price': None,  # Dynamic
                    'closed': False,
                    'closed_price': None,
                    'pnl': 0.0,
                    'trailing_stop': stop_loss,
                    'peak_price': entry_price,
                },
            ],
            'breakeven_active': False,
            'total_realized_pnl': 0.0,
            'remaining_portion': 1.0,
        }

    def check_targets(
        self,
        position_targets: Dict[str, Any],
        current_price: float,
        current_volume: float,
        atr: float = 0.0,
    ) -> Tuple[bool, float, List[Dict[str, Any]]]:
        """
        Check if any TP targets have been hit.
        
        Args:
            position_targets: Position targets dict from create_position_targets()
            current_price: Current market price
            current_volume: Current remaining volume
            atr: Current ATR (for trailing stop)
            
        Returns:
            Tuple of (position_closed, realized_pnl, closed_targets)
        """
        direction = position_targets['direction']
        entry_price = position_targets['entry_price']
        closed_targets = []
        total_realized_pnl = 0.0
        position_closed = False
        
        # Update trailing stop peak and stop
        trailing_target = position_targets['targets'][3]  # TRAILING target
        if not trailing_target['closed']:
            # Update peak price
            if direction == 'BUY':
                if current_price > trailing_target['peak_price']:
                    trailing_target['peak_price'] = current_price
            else:
                if current_price < trailing_target['peak_price']:
                    trailing_target['peak_price'] = current_price
            
            # Update trailing stop if ATR provided
            if atr > 0:
                trail_distance = atr * self.trailing_atr_multiplier
                if direction == 'BUY':
                    new_trailing_stop = current_price - trail_distance
                    if new_trailing_stop > trailing_target['trailing_stop']:
                        trailing_target['trailing_stop'] = new_trailing_stop
                else:
                    new_trailing_stop = current_price + trail_distance
                    if new_trailing_stop < trailing_target['trailing_stop']:
                        trailing_target['trailing_stop'] = new_trailing_stop
        
        # Check each target
        for target in position_targets['targets']:
            if target['closed']:
                continue
            
            # Check if TP hit (for fixed targets)
            if target['name'] != 'TRAILING':
                tp_hit = False
                if direction == 'BUY' and current_price >= target['price']:
                    tp_hit = True
                elif direction == 'SELL' and current_price <= target['price']:
                    tp_hit = True
                
                if tp_hit:
                    target['closed'] = True
                    target['closed_price'] = current_price
                    
                    # Calculate PnL for this portion
                    target_volume = current_volume * target['portion'] / position_targets['remaining_portion']
                    if direction == 'BUY':
                        target_pnl = (current_price - entry_price) * target_volume
                    else:
                        target_pnl = (entry_price - current_price) * target_volume
                    
                    target['pnl'] = target_pnl
                    total_realized_pnl += target_pnl
                    closed_targets.append(target)
                    
                    logger.info(f" {target['name']} hit: +${target_pnl:.2f} ({target['portion']*100:.0f}% position)")
            
            # Check trailing stop hit
            elif target['name'] == 'TRAILING':
                trailing_stop = target['trailing_stop']
                stop_hit = False
                
                if direction == 'BUY' and current_price <= trailing_stop:
                    stop_hit = True
                elif direction == 'SELL' and current_price >= trailing_stop:
                    stop_hit = True
                
                if stop_hit:
                    target['closed'] = True
                    target['closed_price'] = trailing_stop
                    
                    # Calculate PnL for trailing portion
                    target_volume = current_volume * target['portion'] / position_targets['remaining_portion']
                    if direction == 'BUY':
                        target_pnl = (trailing_stop - entry_price) * target_volume
                    else:
                        target_pnl = (entry_price - trailing_stop) * target_volume
                    
                    target['pnl'] = target_pnl
                    total_realized_pnl += target_pnl
                    closed_targets.append(target)
                    
                    logger.info(f" Trailing stop hit: ${target_pnl:+.2f} ({target['portion']*100:.0f}% position)")
        
        # Update remaining portion
        closed_portion = sum(t['portion'] for t in position_targets['targets'] if t['closed'])
        position_targets['remaining_portion'] = 1.0 - closed_portion
        position_targets['total_realized_pnl'] += total_realized_pnl
        
        # Check if position is fully closed
        position_closed = all(t['closed'] for t in position_targets['targets'])
        
        # Move SL to breakeven if TP1 hit (if not already done)
        if not position_targets['breakeven_active'] and position_targets['targets'][0]['closed']:
            position_targets['breakeven_active'] = True
            # Update trailing stop to breakeven
            trailing_target['trailing_stop'] = entry_price
            logger.info(f" SL moved to breakeven")
        
        return position_closed, total_realized_pnl, closed_targets

    def get_position_status(self, position_targets: Dict[str, Any]) -> Dict[str, Any]:
        """Get current position status for monitoring."""
        closed_targets = [t for t in position_targets['targets'] if t['closed']]
        open_targets = [t for t in position_targets['targets'] if not t['closed']]
        
        return {
            'entry_price': position_targets['entry_price'],
            'direction': position_targets['direction'],
            'remaining_portion': position_targets['remaining_portion'],
            'total_realized_pnl': position_targets['total_realized_pnl'],
            'breakeven_active': position_targets['breakeven_active'],
            'closed_targets': len(closed_targets),
            'open_targets': len(open_targets),
            'open_target_details': [
                {
                    'name': t['name'],
                    'portion': t['portion'],
                    'price': t.get('price') or t.get('trailing_stop'),
                }
                for t in open_targets
            ],
        }




