"""
MT5 Connector - MetaTrader 5 connection and session management
CEO: Qwen Code | Created: 2026-04-10

Handles:
- MT5 platform connection
- Authentication
- Symbol validation
- Connection health monitoring
- Graceful shutdown
"""

import MetaTrader5 as mt5
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from loguru import logger

from src.core.config_manager import ConfigManager


class MT5Connector:
    """
    Manages connection to MetaTrader 5 platform
    
    Responsible for:
    - Initializing MT5 connection
    - Authenticating with broker
    - Validating symbols (BTCUSD)
    - Monitoring connection health
    - Providing market data access
    """
    
    def __init__(self, config: ConfigManager):
        self.config = config
        self.connected = False
        self.account_info: Optional[Dict[str, Any]] = None
        self.symbol_info: Optional[Dict[str, Any]] = None
        self.last_health_check = None
        
        # Connection parameters
        self.login = None  # Will be loaded from .env
        self.password = None
        self.server = None
        
        logger.info("🔌 MT5 Connector initialized")
    
    async def connect(self, login: Optional[str] = None, 
                     password: Optional[str] = None, 
                     server: Optional[str] = None) -> bool:
        """
        Establish connection to MT5 platform
        
        Args:
            login: MT5 account login
            password: MT5 account password
            server: Broker server name
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info("🔌 Connecting to MT5...")
            
            # Initialize MT5
            if not mt5.initialize():
                error = mt5.last_error()
                logger.error(f"❌ MT5 initialization failed: {error}")
                return False
            
            # If credentials provided, login
            if login and password and server:
                self.login = login
                self.password = password
                self.server = server
                
                if mt5.login(login, password, server):
                    logger.info(f"✅ Logged in to MT5: Account {login}")
                else:
                    error = mt5.last_error()
                    logger.error(f"❌ MT5 login failed: {error}")
                    return False
            else:
                # Use current MT5 terminal login
                logger.info("ℹ️ Using current MT5 terminal credentials")
            
            # Get account info
            self.account_info = await self.get_account_info()
            if not self.account_info:
                logger.error("❌ Failed to retrieve account info")
                return False
            
            logger.info(f"💰 Account: {self.account_info.get('login')}")
            logger.info(f"💵 Balance: ${self.account_info.get('balance', 0):.2f}")
            logger.info(f"📊 Equity: ${self.account_info.get('equity', 0):.2f}")
            logger.info(f"📈 Leverage: 1:{self.account_info.get('leverage', 1)}")
            
            # Validate BTCUSD symbol
            if not await self.validate_symbol("BTCUSD"):
                logger.error("❌ BTCUSD symbol not available on this account")
                return False
            
            # Get symbol info
            self.symbol_info = await self.get_symbol_info("BTCUSD")
            logger.info(f"📊 BTCUSD Info:")
            logger.info(f"   Spread: {self.symbol_info.get('spread', 0)} points")
            logger.info(f"   Point value: ${self.symbol_info.get('point_value', 0):.4f}")
            logger.info(f"   Min lot: {self.symbol_info.get('volume_min', 0)}")
            logger.info(f"   Max lot: {self.symbol_info.get('volume_max', 0)}")
            logger.info(f"   Lot step: {self.symbol_info.get('volume_step', 0)}")
            
            self.connected = True
            self.last_health_check = datetime.now(timezone.utc)
            
            logger.info("✅ MT5 Connection established successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ MT5 connection error: {e}", exc_info=True)
            self.connected = False
            return False
    
    async def disconnect(self):
        """Gracefully disconnect from MT5"""
        if self.connected:
            logger.info("🔌 Disconnecting from MT5...")
            
            # Close all positions if any
            positions = await self.get_positions()
            if positions:
                logger.warning(f"⚠️ Closing {len(positions)} open position(s)")
                await self.close_all_positions()
            
            mt5.shutdown()
            self.connected = False
            logger.info("✅ Disconnected from MT5")
    
    async def validate_symbol(self, symbol: str) -> bool:
        """
        Validate if symbol is available and tradable
        
        Args:
            symbol: Trading symbol (e.g., BTCUSD)
        
        Returns:
            bool: True if valid, False otherwise
        """
        try:
            # Enable symbol if needed
            if not mt5.symbol_select(symbol, True):
                logger.error(f"❌ Failed to select symbol {symbol}")
                return False
            
            # Get symbol info
            symbol_info = mt5.symbol_info(symbol)
            if symbol_info is None:
                logger.error(f"❌ Symbol {symbol} not found")
                return False
            
            # Check if symbol is visible
            if not symbol_info.visible:
                logger.warning(f"⚠️ Symbol {symbol} not visible, enabling...")
                if not mt5.symbol_select(symbol, True):
                    return False
            
            # Check if trading is allowed
            if symbol_info.trade_mode == mt5.SYMBOL_TRADE_MODE_DISABLED:
                logger.error(f"❌ Trading disabled for {symbol}")
                return False
            
            logger.info(f"✅ Symbol {symbol} validated")
            return True
            
        except Exception as e:
            logger.error(f"❌ Symbol validation error: {e}")
            return False
    
    async def get_account_info(self) -> Optional[Dict[str, Any]]:
        """
        Get current account information
        
        Returns:
            dict: Account information
        """
        try:
            account = mt5.account_info()
            if account is None:
                return None
            
            return {
                "login": account.login,
                "balance": account.balance,
                "equity": account.equity,
                "margin": account.margin,
                "margin_free": account.margin_free,
                "margin_level": account.margin_level,
                "leverage": account.leverage,
                "currency": account.currency,
                "name": account.name,
                "server": account.server,
                "trade_mode": account.trade_mode
            }
        except Exception as e:
            logger.error(f"❌ Error getting account info: {e}")
            return None
    
    async def get_symbol_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed symbol information
        
        Args:
            symbol: Trading symbol
        
        Returns:
            dict: Symbol information
        """
        try:
            info = mt5.symbol_info(symbol)
            if info is None:
                return None
            
            # Calculate point value
            point_value = info.point * info.trade_tick_value
            
            return {
                "name": info.name,
                "description": info.description,
                "spread": info.spread,
                "point": info.point,
                "point_value": point_value,
                "digits": info.digits,
                "volume_min": info.volume_min,
                "volume_max": info.volume_max,
                "volume_step": info.volume_step,
                "volume_limit": info.volume_limit,
                "trade_tick_size": info.trade_tick_size,
                "trade_tick_value": info.trade_tick_value,
                "trade_contract_size": info.trade_contract_size,
                "margin_initial": info.margin_initial,
                "margin_maintenance": info.margin_maintenance,
                "session_high": getattr(info, 'sessionhigh', info.bid),
                "session_low": getattr(info, 'sessionlow', info.ask),
                "bid": info.bid,
                "ask": info.ask,
                "last": info.last
            }
        except Exception as e:
            logger.error(f"❌ Error getting symbol info: {e}")
            return None
    
    async def get_positions(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all open positions
        
        Args:
            symbol: Filter by symbol (optional)
        
        Returns:
            list: List of open positions
        """
        try:
            if symbol:
                positions = mt5.positions_get(symbol=symbol)
            else:
                positions = mt5.positions_get()
            
            if positions is None:
                return []
            
            result = []
            for pos in positions:
                result.append({
                    "ticket": pos.ticket,
                    "symbol": pos.symbol,
                    "type": "BUY" if pos.type == mt5.ORDER_TYPE_BUY else "SELL",
                    "volume": pos.volume,
                    "price_open": pos.price_open,
                    "sl": pos.sl,
                    "tp": pos.tp,
                    "price_current": pos.price_current,
                    "profit": pos.profit,
                    "swap": pos.swap,
                    "commission": pos.commission,
                    "magic": pos.magic,
                    "comment": pos.comment,
                    "time": datetime.fromtimestamp(pos.time)
                })
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error getting positions: {e}")
            return []
    
    async def check_health(self) -> bool:
        """
        Check MT5 connection health
        
        Returns:
            bool: True if healthy, False otherwise
        """
        try:
            if not self.connected:
                return False
            
            # Try to get server time
            server_time = mt5.symbol_info_tick("BTCUSD")
            if server_time is None:
                logger.warning("⚠️ MT5 health check failed")
                return False
            
            self.last_health_check = datetime.now(timezone.utc)
            return True
            
        except Exception as e:
            logger.error(f"❌ Health check error: {e}")
            return False
    
    async def close_all_positions(self, symbol: Optional[str] = "BTCUSD") -> bool:
        """
        Close all open positions
        
        Args:
            symbol: Close only positions for this symbol
        
        Returns:
            bool: True if all closed successfully
        """
        try:
            positions = await self.get_positions(symbol)
            
            if not positions:
                logger.info("ℹ️ No positions to close")
                return True
            
            success_count = 0
            for pos in positions:
                # Create close request
                close_request = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": pos["symbol"],
                    "volume": pos["volume"],
                    "type": mt5.ORDER_TYPE_SELL if pos["type"] == "BUY" else mt5.ORDER_TYPE_BUY,
                    "position": pos["ticket"],
                    "price": pos["price_current"],
                    "deviation": 20,
                    "magic": pos["magic"],
                    "comment": "Close all - Emergency shutdown",
                    "type_time": mt5.ORDER_TIME_GTC,
                    "type_filling": mt5.ORDER_FILLING_IOC,
                }
                
                # Send close order
                result = mt5.order_send(close_request)
                
                if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                    logger.info(f"✅ Closed position {pos['ticket']}")
                    success_count += 1
                else:
                    logger.error(f"❌ Failed to close position {pos['ticket']}: {result}")
            
            logger.info(f"✅ Closed {success_count}/{len(positions)} positions")
            return success_count == len(positions)
            
        except Exception as e:
            logger.error(f"❌ Error closing positions: {e}")
            return False
    
    def get_connection_status(self) -> Dict[str, Any]:
        """
        Get connection status summary
        
        Returns:
            dict: Connection status
        """
        return {
            "connected": self.connected,
            "account": self.account_info.get("login") if self.account_info else None,
            "balance": self.account_info.get("balance") if self.account_info else 0,
            "symbol": "BTCUSD",
            "last_health_check": self.last_health_check,
            "positions_open": len(self.account_info) if self.account_info else 0
        }
