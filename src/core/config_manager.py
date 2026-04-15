"""
Configuration Manager - Dynamic configuration loading and management
CEO: Qwen Code | Created: 2026-04-10
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from loguru import logger


class ConfigManager:
    """Manages all configuration loading, validation, and access"""
    
    def __init__(self, base_path: Optional[str] = None):
        self.base_path = Path(base_path) if base_path else Path(__file__).parent.parent.parent
        self.config_path = self.base_path / "config"
        self.dna_path = self.config_path / "dna"
        
        # File paths
        self.dna_file_path = self.dna_path / "current_dna.json"
        self.absolute_limits_path = self.dna_path / "absolute_limits.json"
        self.dna_memory_path = self.dna_path / "dna_memory.json"
        
        logger.debug(f" ConfigManager initialized at: {self.config_path}")
    
    def load_json(self, file_path: Path) -> Dict[str, Any]:
        """Load JSON configuration file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            logger.info(f" Config loaded: {file_path.name}")
            return data
        except FileNotFoundError:
            logger.error(f" Config file not found: {file_path}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f" Invalid JSON in {file_path}: {e}")
            raise
    
    def save_json(self, file_path: Path, data: Dict[str, Any]) -> None:
        """Save JSON configuration file"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info(f" Config saved: {file_path.name}")
        except Exception as e:
            logger.error(f" Failed to save {file_path}: {e}")
            raise
    
    def load_dna(self) -> Dict[str, Any]:
        """Load current DNA configuration"""
        return self.load_json(self.dna_file_path)
    
    def save_dna(self, dna: Dict[str, Any]) -> None:
        """Save updated DNA configuration"""
        self.save_json(self.dna_file_path, dna)
        logger.info(" DNA saved successfully")
    
    def load_absolute_limits(self) -> Dict[str, Any]:
        """Load absolute safety limits (non-modifiable by DNA engine)"""
        return self.load_json(self.absolute_limits_path)
    
    def load_dna_memory(self) -> Dict[str, Any]:
        """Load DNA memory (regime history)"""
        if self.dna_memory_path.exists():
            return self.load_json(self.dna_memory_path)
        else:
            logger.info(" DNA memory file not found  initializing empty memory")
            return {"regimes": {}, "version": "1.0"}
    
    def save_dna_memory(self, memory: Dict[str, Any]) -> None:
        """Save updated DNA memory"""
        self.save_json(self.dna_memory_path, memory)
    
    def get_param(self, dna: Dict[str, Any], param_path: str) -> Any:
        """
        Get nested parameter using dot notation
        Example: get_param(dna, "risk_params.base_risk_percent")
        """
        keys = param_path.split(".")
        value = dna
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                logger.warning(f" Parameter not found: {param_path}")
                return None
        
        return value
    
    def set_param(self, dna: Dict[str, Any], param_path: str, value: Any) -> Dict[str, Any]:
        """
        Set nested parameter using dot notation
        Example: set_param(dna, "risk_params.base_risk_percent", 1.5)
        """
        keys = param_path.split(".")
        current = dna
        
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        current[keys[-1]] = value
        return dna
    
    def validate_dna_against_limits(self, dna: Dict[str, Any], limits: Dict[str, Any]) -> bool:
        """
        Validate DNA configuration against absolute safety limits
        Returns True if valid, False if violations found
        """
        violations = []
        
        # Check risk per trade
        dna_risk = self.get_param(dna, "risk_params.base_risk_percent")
        max_risk = limits["absolute_limits"]["max_risk_per_trade_percent"]
        if dna_risk and dna_risk > max_risk:
            violations.append(f"Risk per trade {dna_risk}% exceeds max {max_risk}%")
        
        # Check daily loss
        dna_daily = self.get_param(dna, "risk_params.max_daily_loss_percent")
        max_daily = limits["absolute_limits"]["max_daily_loss_percent"]
        if dna_daily and dna_daily > max_daily:
            violations.append(f"Daily loss {dna_daily}% exceeds max {max_daily}%")
        
        # Check total drawdown
        dna_drawdown = self.get_param(dna, "risk_params.max_total_drawdown_percent")
        max_drawdown = limits["absolute_limits"]["max_total_drawdown_percent"]
        if dna_drawdown and dna_drawdown > max_drawdown:
            violations.append(f"Total drawdown {dna_drawdown}% exceeds max {max_drawdown}%")
        
        # Check min R:R
        dna_rr = self.get_param(dna, "risk_params.min_risk_reward_ratio")
        min_rr = limits["absolute_limits"]["min_risk_reward_ratio"]
        if dna_rr and dna_rr < min_rr:
            violations.append(f"Min R:R {dna_rr} below minimum {min_rr}")
        
        if violations:
            logger.error(" DNA VALIDATION FAILED:")
            for violation in violations:
                logger.error(f"    {violation}")
            return False
        
        logger.info(" DNA validation passed - All within safety limits")
        return True
    
    def get_telegram_config(self) -> Dict[str, str]:
        """Load Telegram configuration"""
        telegram_path = self.config_path / "telegram-config.json"
        if telegram_path.exists():
            return self.load_json(telegram_path)
        else:
            logger.warning(" Telegram config not found - notifications disabled")
            return {}
    
    def get_trading_params(self) -> Dict[str, Any]:
        """Load trading parameters (legacy support)"""
        trading_path = self.config_path / "trading-params.json"
        if trading_path.exists():
            return self.load_json(trading_path)
        return {}




