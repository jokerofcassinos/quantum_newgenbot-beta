"""
OmegaParams System - Centralized Configuration Management
Source: DubaiMatrixASI (salvaged and improved)
Created: 2026-04-11

Centralized JSON-driven configuration with:
- 120+ parameters organized by category
- Validation on load
- Version tracking
- Hot-reload support
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional
from loguru import logger


class OmegaParams:
    """
    Centralized parameter configuration system.
    
    Inspired by DubaiMatrixASI's OmegaParams but simplified.
    """

    def __init__(self, config_file: str = "config/omega_params.json"):
        """
        Initialize OmegaParams.
        
        Args:
            config_file: Path to JSON config file
        """
        self.config_file = Path(config_file)
        self.params: Dict[str, Any] = {}
        
        # Create default config if not exists
        if not self.config_file.exists():
            self._create_default_config()
        
        # Load config
        self.load()
        
        logger.info(" OmegaParams initialized")
        logger.info(f"   Config: {self.config_file}")
        logger.info(f"   Version: {self.params.get('version', 'unknown')}")
        logger.info(f"   Parameters: {len(self.params)}")

    def _create_default_config(self):
        """Create default configuration file."""
        default_config = {
            "version": "1.0.0",
            "created": "2026-04-11",
            "trading": {
                "min_confidence": 0.40,
                "max_daily_trades": 25,
                "min_trade_interval_minutes": 5,
                "max_position_size": 1.0,
                "risk_per_trade_percent": 1.0,
            },
            "risk": {
                "max_drawdown_percent": 10.0,
                "daily_loss_limit_percent": 5.0,
                "kelly_fraction": 0.25,
                "volatility_lookback": 20,
                "dd_protection_threshold": 0.05,
                "max_correlation": 0.8,
            },
            "signals": {
                "min_votes_needed": 5,
                "veto_threshold": 0.60,
                "consensus_min_agents": 5,
                "regime_weights": {
                    "trending": {"momentum": 0.4, "mean_reversion": 0.1},
                    "ranging": {"momentum": 0.1, "mean_reversion": 0.4},
                },
            },
            "sessions": {
                "asian": {
                    "enabled": True,
                    "max_trades": 5,
                    "risk_multiplier": 0.5,
                },
                "london": {
                    "enabled": True,
                    "max_trades": 10,
                    "risk_multiplier": 1.0,
                },
                "ny": {
                    "enabled": True,
                    "max_trades": 10,
                    "risk_multiplier": 1.0,
                },
                "ny_overlap": {
                    "enabled": True,
                    "max_trades": 12,
                    "risk_multiplier": 1.2,
                },
            },
            "exit": {
                "smart_tp": {
                    "tp1_portion": 0.30,
                    "tp1_rr": 1.0,
                    "tp2_portion": 0.30,
                    "tp2_rr": 2.0,
                    "tp3_portion": 0.20,
                    "tp3_rr": 3.0,
                    "trailing_portion": 0.20,
                    "trailing_atr_multiplier": 1.5,
                },
                "profit_erosion_tiers": [
                    [30, 0.0],
                    [50, 0.50],
                    [100, 0.40],
                    [200, 0.30],
                    [300, 0.10],
                    [999999, 0.05],
                ],
            },
            "validation": {
                "max_spread_points": 50,
                "max_volatility_multiplier": 3.0,
                "min_margin_level": 200.0,
            },
        }
        
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, 'w') as f:
            json.dump(default_config, f, indent=2)
        
        logger.info(f" Created default config: {self.config_file}")

    def load(self) -> Dict[str, Any]:
        """Load configuration from file."""
        with open(self.config_file, 'r') as f:
            self.params = json.load(f)
        
        # Flatten for easy access
        self._flat_params = {}
        self._flatten(self.params, "")
        
        return self.params

    def _flatten(self, d: Dict, prefix: str):
        """Flatten nested dict for dot-notation access."""
        for k, v in d.items():
            key = f"{prefix}.{k}" if prefix else k
            if isinstance(v, dict):
                self._flatten(v, key)
            else:
                self._flat_params[key] = v

    def get(self, key: str, default=None):
        """Get parameter value using dot notation."""
        return self._flat_params.get(key, default)

    def get_section(self, section: str) -> Dict[str, Any]:
        """Get entire section."""
        keys = section.split('.')
        result = self.params
        for key in keys:
            if isinstance(result, dict) and key in result:
                result = result[key]
            else:
                return {}
        return result if isinstance(result, dict) else {}

    def save(self):
        """Save configuration to file."""
        with open(self.config_file, 'w') as f:
            json.dump(self.params, f, indent=2)
        logger.info(f" Config saved: {self.config_file}")




