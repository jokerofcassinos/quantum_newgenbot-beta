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
        min_confidence_threshold=0.75,  # Very high threshold
        max_position_size=0.03,  # Small positions only
        risk_multiplier=0.3,  # 30% of normal risk
        min_strategy_votes=4,  # Need 4/5 strategies to agree
        min_coherence=0.70,  # High coherence required
        trading_allowed=True,  # Allow but restricted
        description="Low liquidity - require strong consensus"
    ),
    
    # London Session (07:00 - 13:00 UTC) - HIGH LIQUIDITY
    "london": SessionProfile(
        session_name="London",
        min_confidence_threshold=0.60,  # Normal threshold
        max_position_size=0.10,  # Normal positions
        risk_multiplier=1.0,  # 100% risk
        min_strategy_votes=3,  # Need 3/5 strategies
        min_coherence=0.55,  # Normal coherence
        trading_allowed=True,
        description="High liquidity - normal trading"
    ),
    
    # NY Session (13:00 - 17:00 UTC) - HIGH LIQUIDITY
    "ny": SessionProfile(
        session_name="New York",
        min_confidence_threshold=0.60,  # Normal threshold
        max_position_size=0.10,  # Normal positions
        risk_multiplier=1.0,  # 100% risk
        min_strategy_votes=3,  # Need 3/5 strategies
        min_coherence=0.55,  # Normal coherence
        trading_allowed=True,
        description="High liquidity - normal trading"
    ),
    
    # NY/London Overlap (13:00 - 16:00 UTC) - HIGHEST LIQUIDITY
    "ny_overlap": SessionProfile(
        session_name="NY/London Overlap",
        min_confidence_threshold=0.55,  # Slightly lower threshold
        max_position_size=0.12,  # Can take slightly larger positions
        risk_multiplier=1.2,  # 120% risk (best conditions)
        min_strategy_votes=3,  # Need 3/5 strategies
        min_coherence=0.50,  # Lower coherence needed
        trading_allowed=True,
        description="Highest liquidity - optimal conditions"
    ),
    
    # Weekend (Saturday/Sunday) - EXTREME LOW LIQUIDITY
    "weekend": SessionProfile(
        session_name="Weekend",
        min_confidence_threshold=0.85,  # Extremely high threshold
        max_position_size=0.01,  # Minimum position
        risk_multiplier=0.1,  # 10% of normal risk
        min_strategy_votes=5,  # ALL strategies must agree
        min_coherence=0.85,  # Near-perfect coherence
        trading_allowed=False,  # DISABLED by default
        description="Extreme low liquidity - trading DISABLED"
    ),
}


def detect_session(dt: datetime = None) -> str:
    """
    Detect current market session based on UTC time
    
    Sessions (UTC):
    - Asian: 00:00 - 07:00
    - London: 07:00 - 13:00
    - NY: 13:00 - 21:00
    - NY Overlap: 13:00 - 16:00 (within NY)
    - Weekend: Saturday/Sunday
    """
    if dt is None:
        dt = datetime.now(timezone.utc)
    
    # Check weekend first
    if dt.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
        return "weekend"
    
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
    
    logger.info(f"🕐 Session: {profile.session_name}")
    logger.info(f"   Confidence Threshold: {profile.min_confidence_threshold:.2f}")
    logger.info(f"   Max Position Size: {profile.max_position_size}")
    logger.info(f"   Risk Multiplier: {profile.risk_multiplier:.1f}x")
    logger.info(f"   Min Strategy Votes: {profile.min_strategy_votes}/5")
    logger.info(f"   Min Coherence: {profile.min_coherence:.2f}")
    logger.info(f"   Trading Allowed: {'✅ YES' if profile.trading_allowed else '❌ NO'}")
    logger.info(f"   {profile.description}")
    
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
    
    # Check strategy votes
    strategy_votes = signal.get('strategy_votes', 0)
    if strategy_votes < session_profile.min_strategy_votes:
        result['approved'] = False
        result['reason'] = f"Only {strategy_votes}/5 strategies agree (need {session_profile.min_strategy_votes} for {session_profile.session_name})"
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
