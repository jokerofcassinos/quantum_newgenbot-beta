"""
Risk Manager - FTMO compliance and risk control
CEO: Qwen Code | Created: 2026-04-10

Handles:
- Position sizing calculations
- Risk validation per trade
- Drawdown monitoring
- FTMO rules compliance
- Exposure management
- Circuit breaker functionality
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timezone, timedelta
from loguru import logger

from src.core.config_manager import ConfigManager


class RiskManager:
    """
    Central risk management system
    
    Enforces:
    - FTMO rules (5% daily, 10% total)
    - Per-trade risk limits
    - Drawdown protection
    - Exposure limits
    - Consecutive loss protection
    """
    
    def __init__(self, config: ConfigManager):
        self.config = config
        self.current_dna = config.load_dna()
        self.absolute_limits = config.load_absolute_limits()
        
        # Tracking
        self.daily_pnl = 0.0
        self.total_pnl = 0.0
        self.daily_start_balance = 0.0
        self.consecutive_losses = 0
        self.consecutive_wins = 0
        self.trades_today = 0
        
        logger.info(" Risk Manager initialized")
    
    async def initialize(self, current_balance: float):
        """
        Initialize risk manager with current balance
        
        Args:
            current_balance: Current account balance
        """
        self.daily_start_balance = current_balance
        self.total_pnl = 0.0
        self.daily_pnl = 0.0
        
        logger.info(f" Risk Manager initialized with ${current_balance:.2f}")
        logger.info(f"   Daily loss limit: ${current_balance * 0.05:.2f} (5%)")
        logger.info(f"   Total loss limit: ${current_balance * 0.10:.2f} (10%)")
    
    async def validate_trade(self, 
                            risk_amount: float,
                            reward_amount: float,
                            capital: float) -> Dict[str, Any]:
        """
        Validate if a trade meets risk criteria
        
        Args:
            risk_amount: Potential loss in USD
            reward_amount: Potential profit in USD
            capital: Current account capital
        
        Returns:
            dict: Validation result with details
        """
        try:
            validation = {
                "approved": False,
                "reasons": [],
                "warnings": [],
                "details": {}
            }
            
            # 1. Calculate risk percentage
            risk_percent = (risk_amount / capital) * 100
            validation["details"]["risk_percent"] = risk_percent
            
            # 2. Check against DNA risk params
            max_risk_percent = self.config.get_param(self.current_dna, "risk_params.base_risk_percent")
            if risk_percent > max_risk_percent:
                validation["reasons"].append(
                    f"Risk {risk_percent:.2f}% exceeds max {max_risk_percent}%"
                )
            
            # 3. Check R:R ratio
            if reward_amount > 0:
                rr_ratio = reward_amount / risk_amount
                validation["details"]["rr_ratio"] = rr_ratio
                
                min_rr = self.config.get_param(self.current_dna, "risk_params.min_risk_reward_ratio")
                if rr_ratio < min_rr:
                    validation["reasons"].append(
                        f"R:R {rr_ratio:.2f} below minimum {min_rr}"
                    )
            
            # 4. Check daily loss limit
            daily_loss_limit = capital * 0.05  # 5% FTMO rule
            current_daily_loss = abs(min(0, self.daily_pnl))
            
            if current_daily_loss + risk_amount > daily_loss_limit:
                validation["reasons"].append(
                    f"Potential daily loss ${current_daily_loss + risk_amount:.2f} "
                    f"exceeds limit ${daily_loss_limit:.2f}"
                )
            
            # 5. Check total drawdown limit
            total_loss_limit = capital * 0.10  # 10% FTMO rule
            current_total_loss = abs(min(0, self.total_pnl))
            
            if current_total_loss + risk_amount > total_loss_limit:
                validation["reasons"].append(
                    f"Potential total loss ${current_total_loss + risk_amount:.2f} "
                    f"exceeds limit ${total_loss_limit:.2f}"
                )
            
            # 6. Check consecutive losses
            if self.consecutive_losses >= 3:
                validation["warnings"].append(
                    f" {self.consecutive_losses} consecutive losses - consider reducing risk"
                )
            
            # 7. Check exposure
            # (Would need current open positions - implement later)
            
            # Final decision
            validation["approved"] = len(validation["reasons"]) == 0
            
            if validation["approved"]:
                logger.info(f" Trade validated: Risk ${risk_amount:.2f} ({risk_percent:.2f}%), "
                          f"Reward ${reward_amount:.2f}, R:R {validation['details'].get('rr_ratio', 0):.2f}")
            else:
                logger.warning(f" Trade rejected: {'; '.join(validation['reasons'])}")
            
            return validation
            
        except Exception as e:
            logger.error(f" Error validating trade: {e}")
            return {
                "approved": False,
                "reasons": [f"Validation error: {str(e)}"],
                "warnings": [],
                "details": {}
            }
    
    async def calculate_position_size(self,
                                     capital: float,
                                     stop_distance_points: float,
                                     point_value: float) -> float:
        """
        Calculate position size based on risk parameters
        
        Args:
            capital: Account capital
            stop_distance_points: Stop loss distance in points
            point_value: Value per point
        
        Returns:
            float: Lot size
        """
        try:
            # Get risk % from DNA
            risk_percent = self.config.get_param(self.current_dna, "risk_params.base_risk_percent")
            
            # Adjust for consecutive losses
            if self.consecutive_losses > 0:
                reduction_factor = 0.75 ** self.consecutive_losses
                risk_percent *= reduction_factor
                logger.info(f" Risk reduced by {reduction_factor:.2f}x due to "
                          f"{self.consecutive_losses} consecutive losses")
            
            # Calculate risk amount
            risk_amount = capital * (risk_percent / 100)
            
            # Calculate lot size
            lot_size = risk_amount / (stop_distance_points * point_value)
            
            # Round to reasonable precision
            lot_size = round(lot_size, 2)
            
            logger.info(f" Position size calculated:")
            logger.info(f"   Capital: ${capital:.2f}")
            logger.info(f"   Risk %: {risk_percent:.2f}%")
            logger.info(f"   Risk amount: ${risk_amount:.2f}")
            logger.info(f"   Stop distance: {stop_distance_points} points")
            logger.info(f"   Point value: ${point_value:.4f}")
            logger.info(f"   Lot size: {lot_size:.2f}")
            
            return lot_size
            
        except Exception as e:
            logger.error(f" Error calculating position size: {e}")
            return 0.0
    
    async def update_daily_pnl(self, pnl: float):
        """
        Update daily P&L
        
        Args:
            pnl: Profit/loss from trade
        """
        self.daily_pnl += pnl
        self.total_pnl += pnl
        self.trades_today += 1
        
        if pnl > 0:
            self.consecutive_wins += 1
            self.consecutive_losses = 0
        else:
            self.consecutive_losses += 1
            self.consecutive_wins = 0
        
        # Log status
        logger.info(f" Daily P&L: ${self.daily_pnl:+.2f} | "
                   f"Total P&L: ${self.total_pnl:+.2f} | "
                   f"Trades: {self.trades_today}")
    
    async def check_ftmo_compliance(self, capital: float) -> Dict[str, Any]:
        """
        Check FTMO rules compliance
        
        Args:
            capital: Current account capital
        
        Returns:
            dict: Compliance status
        """
        compliance = {
            "daily_loss_ok": True,
            "total_loss_ok": True,
            "consistency_ok": True,
            "critical_alerts": [],
            "warnings": []
        }
        
        # 1. Daily loss check (5%)
        daily_loss = abs(min(0, self.daily_pnl))
        daily_limit = self.daily_start_balance * 0.05
        daily_used_percent = (daily_loss / daily_limit) * 100
        
        compliance["daily_loss_used"] = daily_loss
        compliance["daily_loss_limit"] = daily_limit
        compliance["daily_loss_percent"] = daily_used_percent
        
        if daily_loss >= daily_limit:
            compliance["daily_loss_ok"] = False
            compliance["critical_alerts"].append(
                f" DAILY LOSS LIMIT REACHED: ${daily_loss:.2f} / ${daily_limit:.2f} "
                f"({daily_used_percent:.1f}%)"
            )
        elif daily_used_percent > 80:
            compliance["warnings"].append(
                f" Daily loss at {daily_used_percent:.1f}% of limit"
            )
        
        # 2. Total loss check (10%)
        total_loss = abs(min(0, self.total_pnl))
        total_limit = capital * 0.10
        total_used_percent = (total_loss / total_limit) * 100
        
        compliance["total_loss_used"] = total_loss
        compliance["total_loss_limit"] = total_limit
        compliance["total_loss_percent"] = total_used_percent
        
        if total_loss >= total_limit:
            compliance["total_loss_ok"] = False
            compliance["critical_alerts"].append(
                f" TOTAL LOSS LIMIT REACHED: ${total_loss:.2f} / ${total_limit:.2f} "
                f"({total_used_percent:.1f}%)"
            )
        elif total_used_percent > 80:
            compliance["warnings"].append(
                f" Total loss at {total_used_percent:.1f}% of limit"
            )
        
        # 3. Consistency rule (no single day > 30% of total profit)
        if self.total_pnl > 0 and self.daily_pnl > 0:
            consistency_percent = (self.daily_pnl / self.total_pnl) * 100
            if consistency_percent > 30:
                compliance["consistency_ok"] = False
                compliance["warnings"].append(
                    f" Today's profit is {consistency_percent:.1f}% of total "
                    f"(max 30% for FTMO consistency)"
                )
        
        return compliance
    
    async def check_drawdown_levels(self, capital: float) -> Dict[str, Any]:
        """
        Check drawdown levels and recommend actions
        
        Args:
            capital: Current account capital
        
        Returns:
            dict: Drawdown status
        """
        drawdown_percent = (abs(min(0, self.total_pnl)) / capital) * 100
        
        levels = {
            "current_drawdown": drawdown_percent,
            "status": "normal",
            "action_required": None,
            "alerts": []
        }
        
        if drawdown_percent >= 9:
            levels["status"] = "critical"
            levels["action_required"] = "STOP_ALL_TRADING"
            levels["alerts"].append(" DANGER: 9% drawdown - $100 from FTMO failure")
        
        elif drawdown_percent >= 7:
            levels["status"] = "emergency"
            levels["action_required"] = "STOP_24H"
            levels["alerts"].append(" EMERGENCY: 7% drawdown - Stop for 24h")
        
        elif drawdown_percent >= 5:
            levels["status"] = "critical_warning"
            levels["action_required"] = "STOP_2H"
            levels["alerts"].append(" CRITICAL: 5% drawdown - Stop for 2 hours")
        
        elif drawdown_percent >= 3:
            levels["status"] = "warning"
            levels["action_required"] = "REDUCE_RISK"
            levels["alerts"].append(" WARNING: 3% drawdown - Reduce risk to 0.5%")
        
        return levels
    
    async def should_stop_trading(self, capital: float) -> tuple[bool, str]:
        """
        Determine if trading should be stopped
        
        Args:
            capital: Current capital
        
        Returns:
            tuple: (should_stop, reason)
        """
        # Check daily loss
        daily_loss = abs(min(0, self.daily_pnl))
        daily_limit = self.daily_start_balance * 0.05
        if daily_loss >= daily_limit:
            return True, f"Daily loss limit reached: ${daily_loss:.2f} / ${daily_limit:.2f}"
        
        # Check total loss
        total_loss = abs(min(0, self.total_pnl))
        total_limit = capital * 0.10
        if total_loss >= total_limit:
            return True, f"Total loss limit reached: ${total_loss:.2f} / ${total_limit:.2f}"
        
        # Check consecutive losses
        if self.consecutive_losses >= 7:
            return True, f"7 consecutive losses - mandatory review"
        
        # Check drawdown
        drawdown = await self.check_drawdown_levels(capital)
        if drawdown["status"] in ["critical", "emergency"]:
            return True, f"Critical drawdown: {drawdown['current_drawdown']:.2f}%"
        
        return False, "Trading allowed"
    
    def get_risk_summary(self, capital: float) -> Dict[str, Any]:
        """
        Get comprehensive risk summary
        
        Args:
            capital: Current capital
        
        Returns:
            dict: Risk summary
        """
        return {
            "capital": capital,
            "daily_pnl": self.daily_pnl,
            "total_pnl": self.total_pnl,
            "daily_loss_used_percent": (abs(min(0, self.daily_pnl)) / (self.daily_start_balance * 0.05)) * 100,
            "total_loss_used_percent": (abs(min(0, self.total_pnl)) / (capital * 0.10)) * 100,
            "consecutive_losses": self.consecutive_losses,
            "consecutive_wins": self.consecutive_wins,
            "trades_today": self.trades_today,
            "base_risk_percent": self.config.get_param(self.current_dna, "risk_params.base_risk_percent")
        }
    
    async def reset_daily_tracking(self, new_balance: float):
        """Reset daily tracking (call at start of new day)"""
        self.daily_start_balance = new_balance
        self.daily_pnl = 0.0
        self.trades_today = 0
        logger.info(f" Daily tracking reset - New balance: ${new_balance:.2f}")




