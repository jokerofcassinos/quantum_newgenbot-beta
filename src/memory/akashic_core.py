"""
AkashicCore - Hyperdimensional Computing Pattern Memory
Source: Laplace-Demon-AGI v3.0 (salvaged and improved)
Created: 2026-04-11

Uses Hyperdimensional Computing (HDC) for pattern memory:
- Encode market states as high-dimensional vectors
- Store patterns with outcomes in associative memory
- Retrieve similar historical patterns via cosine similarity
- Use historical outcomes to inform current decisions

This enables "experience-based" trading decisions.
"""

from typing import Dict, Any, List, Tuple, Optional
from loguru import logger
import numpy as np


class AkashicCore:
    """
    Hyperdimensional Computing pattern memory system.
    
    Inspired by Laplace-Demon-AGI v3.0 implementation.
    """

    def __init__(
        self,
        vector_dim: int = 1000,
        memory_capacity: int = 1000,
        similarity_threshold: float = 0.6,
    ):
        """
        Initialize AkashicCore.
        
        Args:
            vector_dim: Dimensionality of HDC vectors
            memory_capacity: Maximum number of patterns to store
            similarity_threshold: Minimum similarity for pattern match
        """
        self.vector_dim = vector_dim
        self.memory_capacity = memory_capacity
        self.similarity_threshold = similarity_threshold
        
        # Pattern memory: list of (vector, outcome) tuples
        self.memory: List[Tuple[np.ndarray, float]] = []
        
        # Generate random basis vectors for encoding
        np.random.seed(42)  # Reproducible
        self.basis_vectors = {
            'trend': self._random_vector(vector_dim),
            'volatility': self._random_vector(vector_dim),
            'volume': self._random_vector(vector_dim),
            'momentum': self._random_vector(vector_dim),
            'regime': self._random_vector(vector_dim),
        }
        
        logger.info("📚 AkashicCore initialized")
        logger.info(f"   Vector dim: {vector_dim}")
        logger.info(f"   Memory capacity: {memory_capacity}")
        logger.info(f"   Similarity threshold: {similarity_threshold}")

    def _random_vector(self, dim: int) -> np.ndarray:
        """Generate random bipolar HDC vector."""
        return np.random.choice([-1, 1], size=dim).astype(np.float64)

    def encode_state(
        self,
        trend: float,
        volatility: float,
        volume: float,
        momentum: float,
        regime: str,
    ) -> np.ndarray:
        """
        Encode market state as HDC vector.
        
        Args:
            trend: Trend value (-1 to 1)
            volatility: Volatility value (0 to 1)
            volume: Volume ratio (0 to 1)
            momentum: Momentum value (-1 to 1)
            regime: Regime type ('trending', 'ranging', etc.)
            
        Returns:
            HDC vector representing this state
        """
        # Bind features to basis vectors
        trend_vec = self.basis_vectors['trend'] * trend
        vol_vec = self.basis_vectors['volatility'] * volatility
        vol_volume = self.basis_vectors['volume'] * volume
        momentum_vec = self.basis_vectors['momentum'] * momentum
        
        # Regime encoding (simple hash)
        regime_hash = hash(regime) % self.vector_dim
        regime_vec = np.zeros(self.vector_dim)
        regime_vec[regime_hash] = 1.0
        
        # Bundle all features
        state_vector = trend_vec + vol_vec + vol_volume + momentum_vec + regime_vec
        
        # Normalize to bipolar
        state_vector = np.sign(state_vector)
        
        return state_vector

    def store_pattern(
        self,
        state_vector: np.ndarray,
        outcome: float,
    ):
        """
        Store pattern with outcome in memory.
        
        Args:
            state_vector: HDC vector of market state
            outcome: Trade outcome (PnL or win/loss)
        """
        self.memory.append((state_vector.copy(), outcome))
        
        # Trim memory if exceeds capacity
        if len(self.memory) > self.memory_capacity:
            self.memory = self.memory[-self.memory_capacity:]

    def recall_similar_patterns(
        self,
        state_vector: np.ndarray,
        k: int = 10,
    ) -> List[Tuple[float, float]]:
        """
        Recall similar historical patterns.
        
        Args:
            state_vector: Current market state vector
            k: Number of most similar patterns to return
            
        Returns:
            List of (similarity, outcome) tuples
        """
        if not self.memory:
            return []
        
        # Calculate cosine similarity with all stored patterns
        similarities = []
        for stored_vec, outcome in self.memory:
            sim = self._cosine_similarity(state_vector, stored_vec)
            similarities.append((sim, outcome))
        
        # Sort by similarity descending
        similarities.sort(key=lambda x: x[0], reverse=True)
        
        return similarities[:k]

    def _cosine_similarity(self, v1: np.ndarray, v2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors."""
        dot = np.dot(v1, v2)
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot / (norm1 * norm2)

    def predict_outcome(
        self,
        state_vector: np.ndarray,
    ) -> Dict[str, Any]:
        """
        Predict outcome based on similar historical patterns.
        
        Args:
            state_vector: Current market state vector
            
        Returns:
            Dict with prediction results
        """
        similar = self.recall_similar_patterns(state_vector, k=20)
        
        if not similar:
            return {
                'predicted_outcome': 0.0,
                'confidence': 0.0,
                'num_matches': 0,
                'recommendation': 'NEUTRAL',
            }
        
        # Filter by similarity threshold
        good_matches = [(sim, outcome) for sim, outcome in similar if sim > self.similarity_threshold]
        
        if not good_matches:
            return {
                'predicted_outcome': 0.0,
                'confidence': 0.0,
                'num_matches': 0,
                'recommendation': 'NEUTRAL',
            }
        
        # Weight outcomes by similarity
        total_sim = sum(sim for sim, _ in good_matches)
        weighted_outcome = sum(sim * outcome for sim, outcome in good_matches) / total_sim
        
        avg_similarity = np.mean([sim for sim, _ in good_matches])
        
        # Generate recommendation
        if weighted_outcome > 0.1:
            recommendation = 'BUY'
        elif weighted_outcome < -0.1:
            recommendation = 'SELL'
        else:
            recommendation = 'NEUTRAL'
        
        return {
            'predicted_outcome': weighted_outcome,
            'confidence': avg_similarity,
            'num_matches': len(good_matches),
            'recommendation': recommendation,
        }

    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        return {
            'total_patterns': len(self.memory),
            'capacity': self.memory_capacity,
            'utilization': len(self.memory) / self.memory_capacity,
        }
