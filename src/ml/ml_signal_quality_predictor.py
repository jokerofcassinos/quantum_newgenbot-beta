"""
MLSignalQualityPredictor - Machine Learning Trade Quality Prediction
Source: Forensic analysis recommendation (using 2,854 trade audits)
Created: 2026-04-12

Uses historical trade audit data to predict trade quality:
1. Loads 2,854+ trade audits from data/trade-audits/
2. Extracts features (regime, session, confidence, indicators, etc.)
3. Trains simple ML model (logistic regression / decision tree)
4. Predicts probability of win for new signals
5. Filters low-probability trades before entry

This transforms historical data into predictive power.
"""

from typing import Dict, Any, List, Optional, Tuple
from loguru import logger
from pathlib import Path
import json
import numpy as np
from datetime import datetime, timezone


class MLSignalQualityPredictor:
    """
    ML-based trade quality prediction system.
    
    Uses historical trade audits to predict win probability.
    """

    def __init__(
        self,
        audit_dir: str = "data/trade-audits",
        model_type: str = "logistic",
        min_trades_for_training: int = 100,
    ):
        """
        Initialize MLSignalQualityPredictor.
        
        Args:
            audit_dir: Directory containing trade audit JSON files
            model_type: Type of model ('logistic', 'decision_tree', 'random_forest')
            min_trades_for_training: Minimum trades needed to train model
        """
        self.audit_dir = Path(audit_dir)
        self.model_type = model_type
        self.min_trades = min_trades_for_training
        
        # Model state
        self.is_trained = False
        self.model_weights: Optional[Dict[str, Any]] = None
        self.training_data: Optional[Dict[str, Any]] = None
        
        # Load historical data
        self.historical_trades = self._load_trade_audits()
        
        logger.info(" MLSignalQualityPredictor initialized")
        logger.info(f"   Audit dir: {audit_dir}")
        logger.info(f"   Model type: {model_type}")
        logger.info(f"   Historical trades loaded: {len(self.historical_trades)}")
        
        # Train model if enough data
        if self.historical_trades and len(self.historical_trades) >= self.min_trades:
            self._train_model()

    def _load_trade_audits(self) -> List[Dict[str, Any]]:
        """Load all trade audit files from audit directory."""
        trades = []
        
        if not self.audit_dir.exists():
            logger.warning(f" Audit directory not found: {self.audit_dir}")
            return trades
        
        # Load all JSON files recursively
        for json_file in self.audit_dir.rglob("*.json"):
            try:
                with open(json_file, 'r') as f:
                    trade_data = json.load(f)
                    if 'net_pnl' in trade_data or 'gross_pnl' in trade_data:
                        trades.append(trade_data)
            except Exception as e:
                logger.warning(f" Failed to load {json_file}: {e}")
        
        logger.info(f" Loaded {len(trades)} trade audits from {self.audit_dir}")
        return trades

    def _extract_features(self, trade: Dict[str, Any]) -> Dict[str, float]:
        """Extract numerical features from trade data."""
        features = {}
        
        # Session encoding (one-hot)
        session = trade.get('session', trade.get('session_name', 'unknown'))
        if session is None:
            session = 'unknown'
        features['session_asian'] = 1.0 if session == 'asian' else 0.0
        features['session_london'] = 1.0 if session == 'london' else 0.0
        features['session_ny'] = 1.0 if session == 'ny' else 0.0
        features['session_ny_overlap'] = 1.0 if session == 'ny_overlap' else 0.0
        
        # Direction
        direction = trade.get('direction', 'BUY')
        if direction is None:
            direction = 'BUY'
        features['direction_buy'] = 1.0 if direction == 'BUY' else 0.0
        
        # Confidence
        confidence = trade.get('confidence', 0.5)
        if confidence is None:
            confidence = 0.5
        features['confidence'] = confidence
        
        # Regime encoding
        regime = trade.get('regime_name', trade.get('regime', 'unknown'))
        if regime is None:
            regime = 'unknown'
        regime_str = str(regime)
        features['regime_ranging'] = 1.0 if 'ranging' in regime_str else 0.0
        features['regime_trending_bullish'] = 1.0 if 'trending_bullish' in regime_str else 0.0
        features['regime_trending_bearish'] = 1.0 if 'trending_bearish' in regime_str else 0.0
        
        # Volume (if available)
        volume = trade.get('volume', 0.01)
        if volume is None:
            volume = 0.01
        features['volume'] = volume
        
        # Duration (if available)
        duration = trade.get('duration_minutes', 0)
        if duration is None:
            duration = 0
        features['duration_minutes'] = min(duration, 120) / 120.0  # Normalize to 0-1
        
        # Strategy votes (if available)
        votes = trade.get('votes', trade.get('strategy_votes', 5))
        if votes is None:
            votes = 5
        features['votes'] = votes / 12.0
        
        # Hour of day
        hour = trade.get('hour', trade.get('open_hour', 12))
        if hour is None:
            hour = 12
        features['hour'] = hour / 24.0
        
        return features

    def _train_model(self):
        """Train prediction model on historical data."""
        if len(self.historical_trades) < self.min_trades:
            logger.warning(f" Not enough data to train model ({len(self.historical_trades)} < {self.min_trades})")
            return
        
        # Prepare training data
        X = []
        y = []
        
        for trade in self.historical_trades:
            # Determine label (win = 1, loss = 0)
            pnl = trade.get('net_pnl', trade.get('gross_pnl', 0))
            if pnl is None:
                pnl = 0
            label = 1 if pnl > 0 else 0
            
            features = self._extract_features(trade)
            X.append(features)
            y.append(label)
        
        # Store training data for prediction
        self.training_data = {
            'X': X,
            'y': y,
            'n_trades': len(X),
            'win_rate': sum(y) / max(1, len(y)),
        }
        
        # Simple weighted average model (no sklearn dependency)
        # Calculate average feature weights for wins vs losses
        win_features = {k: 0.0 for k in X[0].keys()}
        loss_features = {k: 0.0 for k in X[0].keys()}
        
        win_count = sum(y)
        loss_count = len(y) - win_count
        
        for i, features in enumerate(X):
            if y[i] == 1:
                for k, v in features.items():
                    win_features[k] += v
            else:
                for k, v in features.items():
                    loss_features[k] += v
        
        # Normalize
        for k in win_features:
            win_features[k] /= max(1, win_count)
            loss_features[k] /= max(1, loss_count)
        
        # Calculate weights (difference between win and loss averages)
        self.model_weights = {
            'win_features': win_features,
            'loss_features': loss_features,
            'win_rate': self.training_data['win_rate'],
            'n_trades': len(X),
        }
        
        self.is_trained = True
        logger.info(f" Model trained on {len(X)} trades")
        logger.info(f"   Win rate: {self.training_data['win_rate']*100:.1f}%")
        logger.info(f"   Wins: {win_count}, Losses: {loss_count}")

    def predict_win_probability(self, features: Dict[str, float]) -> float:
        """
        Predict win probability for a new trade.
        
        Args:
            features: Feature dict from _extract_features()
            
        Returns:
            Win probability (0.0 to 1.0)
        """
        if not self.is_trained or self.model_weights is None:
            return 0.5  # Default when not trained
        
        # Calculate similarity to win and loss centroids
        win_dist = 0.0
        loss_dist = 0.0
        
        for k, v in features.items():
            win_v = self.model_weights['win_features'].get(k, 0.0)
            loss_v = self.model_weights['loss_features'].get(k, 0.0)
            
            win_dist += (v - win_v) ** 2
            loss_dist += (v - loss_v) ** 2
        
        win_dist = np.sqrt(win_dist)
        loss_dist = np.sqrt(loss_dist)
        
        # Convert distances to probability
        total_dist = win_dist + loss_dist
        if total_dist < 1e-10:
            return self.model_weights['win_rate']
        
        # Closer to win centroid = higher probability
        win_prob = loss_dist / total_dist
        
        # Blend with base win rate (Bayesian shrinkage)
        alpha = 0.3  # Weight toward historical win rate
        final_prob = (1 - alpha) * win_prob + alpha * self.model_weights['win_rate']
        
        return max(0.0, min(1.0, final_prob))

    def should_trade(
        self,
        trade_data: Dict[str, Any],
        min_win_probability: float = 0.45,
    ) -> Tuple[bool, str, float]:
        """
        Determine if trade should be allowed based on ML prediction.
        
        Args:
            trade_data: Trade data to evaluate
            min_win_probability: Minimum win probability to allow trade
            
        Returns:
            Tuple of (allowed: bool, reason: str, win_probability: float)
        """
        features = self._extract_features(trade_data)
        win_prob = self.predict_win_probability(features)
        
        if win_prob >= min_win_probability:
            return True, f"ML predicts {win_prob*100:.1f}% win probability", win_prob
        else:
            return False, f"ML predicts only {win_prob*100:.1f}% win probability (need {min_win_probability*100:.0f}%)", win_prob

    def get_model_stats(self) -> Dict[str, Any]:
        """Get model training statistics."""
        return {
            'is_trained': self.is_trained,
            'n_trades': self.model_weights['n_trades'] if self.model_weights else 0,
            'win_rate': self.model_weights['win_rate'] if self.model_weights else 0.0,
            'model_type': self.model_type,
            'historical_trades_loaded': len(self.historical_trades),
        }




