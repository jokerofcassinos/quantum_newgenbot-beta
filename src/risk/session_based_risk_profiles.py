"""
SessionBasedRiskProfiles - Dynamic Risk Adjustment by Trading Session
Source: Atl4s (salvaged and improved)
Created: 2026-04-12

Adjusts risk parameters based on trading session characteristics:
- Asian: Lower risk, wider stops (choppy)
- London: Higher risk, tighter stops (trending)
- NY: Medium risk, medium stops (mixed)
- NY Overlap: Highest risk, tightest stops (most liquid)
"""

from typing import Dict, Any
from loguru import logger
from datetime import datetime, timezone


class SessionBasedRiskProfiles:
    """
    Session-based risk profile system.
    
    Inspired by Atl4s implementation but simplified.
    """

    def __init__(self):
        """Initialize SessionBasedRiskProfiles."""
        self.session_profiles = {
            'asian': {
                'risk_multiplier': 0.5,
                'max_trades_per_session': 3,
                'stop_multiplier': 1.5,
                'tp_multiplier': 2.5,
                'min_confidence': 0.45,
                'description': 'Low risk, wide stops (choppy market)',
            },
            'london': {
                'risk_multiplier': 1.0,
                'max_trades_per_session': 8,
                'stop_multiplier': 1.0,
                'tp_multiplier': 3.0,
                'min_confidence': 0.40,
                'description': 'Normal risk, trending market',
            },
            'ny': {
                'risk_multiplier': 0.8,
                'max_trades_per_session': 6,
                'stop_multiplier': 1.2,
                'tp_multiplier': 2.8,
                'min_confidence': 0.42,
                'description': 'Medium risk, mixed conditions',
            },
            'ny_overlap': {
                'risk_multiplier': 1.2,
                'max_trades_per_session': 10,
                'stop_multiplier': 0.8,
                'tp_multiplier': 3.5,
                'min_confidence': 0.38,
                'description': 'High risk, tight stops (most liquid)',
            },
        }
        
        logger.info("🕐 SessionBasedRiskProfiles initialized")
        for session, profile in self.session_profiles.items():
            logger.info(f"   {session}: risk={profile['risk_multiplier']}x, max_trades={profile['max_trades_per_session']}")

    def get_session_profile(self, session: str) -> Dict[str, Any]:
        """Get risk profile for a session."""
        return self.session_profiles.get(session, self.session_profiles['london'])

    def adjust_for_session(
        self,
        base_risk_percent: float,
        base_stop_distance: float,
        base_tp_distance: float,
        session: str,
    ) -> Dict[str, float]:
        """
        Adjust risk parameters for current session.
        
        Args:
            base_risk_percent: Base risk per trade (%)
            base_stop_distance: Base stop loss distance
            base_tp_distance: Base take profit distance
            session: Current session name
            
        Returns:
            Dict with adjusted parameters
        """
        profile = self.get_session_profile(session)
        mult = profile['risk_multiplier']
        stop_mult = profile['stop_multiplier']
        tp_mult = profile['tp_multiplier']
        
        return {
            'adjusted_risk_percent': base_risk_percent * mult,
            'adjusted_stop_distance': base_stop_distance * stop_mult,
            'adjusted_tp_distance': base_tp_distance * tp_mult,
            'max_trades': profile['max_trades_per_session'],
            'min_confidence': profile['min_confidence'],
            'session': session,
        }
