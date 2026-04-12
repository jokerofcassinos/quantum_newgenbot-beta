"""
Session-Specific Risk Profiles
CEO: Qwen Code | Created: 2026-04-12

Creates specialized profiles for:
1. Asian Session (low liquidity) - Higher thresholds, smaller positions
2. Weekend (Sat/Sun) - Very high thresholds or NO trading
3. London/NY Sessions - Normal thresholds (baseline)
"""

import pandas as pd
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from dataclasses import dataclass
from loguru import logger


@dataclass
class SessionProfile:
    """Session-specific trading parameters"""
    session_name: str
    min_confidence_threshold: float  # Minimum signal confidence to trade
    max_position_size: float  # Maximum lot size
    risk_multiplier: float  # Risk % multiplier (1.0 = normal)
    min_strategy_votes: int  # Minimum strategies that must agree
    min_coherence: float  # Minimum coherence score
    trading_allowed: bool  # Whether to allow trading at all
    description: str


SESSION_PROFILES = {
    # Asian Session (00:00 - 07:00 UTC) - LOW LIQUIDITY
    "asian": SessionProfile(
        session_name="Asian",
        min_confidence_threshold=0.40,  # Fixed: was 0.75 (aligned with 5/12 = 41.7%)
        max_position_size=2.0,  # Increased from 0.03 (Ghost Audit: DD is 0.02%)
        risk_multiplier=0.3,
        min_strategy_votes=5,  # Need 5/12 strategies
        min_coherence=0.40,  # Fixed: was 0.60 (aligned with signal generation)
        trading_allowed=True,
        description="Low liquidity - require strong consensus"
    ),

    # London Session (07:00 - 13:00 UTC) - HIGH LIQUIDITY
    "london": SessionProfile(
        session_name="London",
        min_confidence_threshold=0.40,  # Fixed: was 0.60 (aligned with 5/12 = 41.7%)
        max_position_size=5.0,  # Increased from 0.10 (Ghost Audit: DD is 0.02%)
        risk_multiplier=1.0,
        min_strategy_votes=5,  # Fixed: was 4 (aligned with signal gen minimum)
        min_coherence=0.40,  # Fixed: was 0.55
        trading_allowed=True,
        description="High liquidity - normal trading"
    ),

    # NY Session (13:00 - 17:00 UTC) - HIGH LIQUIDITY
    "ny": SessionProfile(
        session_name="New York",
        min_confidence_threshold=0.40,  # Fixed: was 0.60 (aligned with 5/12 = 41.7%)
        max_position_size=5.0,  # Increased from 0.10 (Ghost Audit: DD is 0.02%)
        risk_multiplier=1.0,
        min_strategy_votes=5,  # Fixed: was 4 (aligned with signal gen minimum)
        min_coherence=0.40,  # Fixed: was 0.55
        trading_allowed=True,
        description="High liquidity - normal trading"
    ),

    # NY/London Overlap (13:00 - 16:00 UTC) - HIGHEST LIQUIDITY
    "ny_overlap": SessionProfile(
        session_name="NY/London Overlap",
        min_confidence_threshold=0.40,  # Fixed: was 0.55 (aligned with 5/12 = 41.7%)
        max_position_size=5.0,  # Increased from 0.12 (Ghost Audit: DD is 0.02%)
        risk_multiplier=1.2,
        min_strategy_votes=5,  # Fixed: was 3 (aligned with signal gen minimum)
        min_coherence=0.40,  # Fixed: was 0.50
        trading_allowed=True,
        description="Highest liquidity - optimal conditions"
    ),

    # Weekend (Saturday/Sunday) - GHOST AUDIT SELECTIVE HOURS
    # Ghost audit found: Weekend 08-09h and 17-20h UTC are PROFITABLE (+$117K)
    # But other weekend hours lose money
    "weekend_profitable": SessionProfile(
        session_name="Weekend Profitable Hours",
        min_confidence_threshold=0.45,  # Slightly higher than normal
        max_position_size=3.0,  # Increased from 0.08 (Ghost Audit: DD is 0.02%)
        risk_multiplier=0.8,  # 80% of normal risk
        min_strategy_votes=5,
        min_coherence=0.45,
        trading_allowed=True,  # ALLOWED during profitable hours
        description="Weekend 08-09h and 17-20h UTC - profitable hours only"
    ),

    # Weekend (Saturday/Sunday) - EXTREME LOW LIQUIDITY (other hours)
    "weekend": SessionProfile(
        session_name="Weekend",
        min_confidence_threshold=0.85,  # Extremely high threshold
        max_position_size=0.01,  # Minimum position
        risk_multiplier=0.1,  # 10% of normal risk
        min_strategy_votes=5,  # ALL strategies must agree
        min_coherence=0.85,  # Near-perfect coherence
        trading_allowed=False,  # DISABLED for non-profitable hours
        description="Weekend non-profitable hours - trading DISABLED"
    ),
}


def detect_session(dt: datetime = None) -> str:
    """
    Detect current market session based on UTC time

    GHOST AUDIT FIX: Weekend selective hours
    Ghost audit found: Weekend 08-09h and 17-20h UTC are PROFITABLE (+$117K)

    Sessions (UTC):
    - Asian: 00:00 - 07:00
    - London: 07:00 - 13:00
    - NY: 13:00 - 21:00
    - NY Overlap: 13:00 - 16:00 (within NY)
    - Weekend Profitable: Sat/Sun 08-09h and 17-20h UTC
    - Weekend: Sat/Sun other hours (DISABLED)
    """
    if dt is None:
        dt = datetime.now(timezone.utc)

    # Check weekend first
    if dt.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
        hour = dt.hour
        # GHOST AUDIT FIX: Allow weekend only during profitable hours
        if hour == 8 or hour == 9 or (17 <= hour <= 20):
            return "weekend_profitable"  # Profitable weekend hours
        else:
            return "weekend"  # Non-profitable weekend hours (DISABLED)

    hour = dt.hour

    if 0 <= hour < 7:
        return "asian"
    elif 7 <= hour < 13:
        return "london"
    elif 13 <= hour < 16:
        return "ny_overlap"
    elif 16 <= hour < 21:
        return "ny"
    else:  # 21:00 - 24:00
        return "asian"


def get_session_profile(session: str = None) -> SessionProfile:
    """
    Get session-specific trading profile
    
    Args:
        session: Session name (auto-detect if None)
    
    Returns:
        SessionProfile with trading parameters
    """
    if session is None:
        session = detect_session()
    
    profile = SESSION_PROFILES.get(session, SESSION_PROFILES["asian"])
    
    return profile


def apply_session_veto(session_profile: SessionProfile, signal: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply session-specific veto rules
    
    Returns:
        dict with veto result and adjustments
    """
    result = {
        'approved': True,
        'reason': '',
        'adjusted_volume': signal.get('volume', 0.01),
        'adjusted_threshold': session_profile.min_confidence_threshold,
    }
    
    # Check if trading is allowed
    if not session_profile.trading_allowed:
        result['approved'] = False
        result['reason'] = f"Trading disabled for {session_profile.session_name} session"
        return result
    
    # Check confidence threshold
    confidence = signal.get('confidence', 0)
    if confidence < session_profile.min_confidence_threshold:
        result['approved'] = False
        result['reason'] = f"Confidence {confidence:.2f} < {session_profile.min_confidence_threshold:.2f} ({session_profile.session_name} threshold)"
        return result
    
    # Check strategy votes - handle both old int format and new dict format
    strategy_votes_raw = signal.get('strategy_votes', 0)
    
    if isinstance(strategy_votes_raw, dict):
        # New format: dict with vote breakdown
        direction = signal.get('direction', '')
        if direction == 'BUY':
            strategy_votes = strategy_votes_raw.get('buy_votes', 0)
        elif direction == 'SELL':
            strategy_votes = strategy_votes_raw.get('sell_votes', 0)
        else:
            strategy_votes = 0
    else:
        # Old format: plain int
        strategy_votes = strategy_votes_raw
    
    if strategy_votes < session_profile.min_strategy_votes:
        result['approved'] = False
        result['reason'] = f"Only {strategy_votes}/12 strategies agree (need {session_profile.min_strategy_votes} for {session_profile.session_name})"
        return result
    
    # Check coherence
    coherence = signal.get('coherence', 0)
    if coherence < session_profile.min_coherence:
        result['approved'] = False
        result['reason'] = f"Coherence {coherence:.2f} < {session_profile.min_coherence:.2f} ({session_profile.session_name} minimum)"
        return result
    
    # Adjust position size for session
    base_volume = signal.get('volume', 0.01)
    adjusted_volume = min(base_volume * session_profile.risk_multiplier, session_profile.max_position_size)
    adjusted_volume = max(0.01, adjusted_volume)  # Minimum 0.01
    
    result['approved'] = True
    result['reason'] = f"Session {session_profile.session_name} - approved with adjusted volume"
    result['adjusted_volume'] = adjusted_volume
    
    return result
