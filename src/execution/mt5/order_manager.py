"""
Order Manager - Trade execution and position management
CEO: Qwen Code | Created: 2026-04-10

Handles:
- Order execution (market, limit, stop)
- Position modification (SL, TP)
- Order status tracking
- Trade history retrieval
- Position closure (partial, full)
"""

import MetaTrader5 as mt5
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone, timedelta
from loguru import logger

from src.core.config_manager import ConfigManager


class OrderManager:
    """
    Manages all order execution and position lifecycle
    
    Provides:
    - Market order execution
    - Pending order placement
    - Position modification
    - Partial/complete closure
    - Trade history
    """
    
    def __init__(self, config: ConfigManager):
        self.config = config
        self.symbol = "BTCUSD"
        self.default_deviation = 20  # points
        self.default_magic = 20260410
        
        logger.info("📝 Order Manager initialized")
    
    async def execute_market_order(self,
                                   order_type: str,
                                   volume: float,
                                   sl: Optional[float] = None,
                                   tp: Optional[float] = None,
                                   comment: str = "",
                                   magic: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Execute market order (BUY or SELL)
        
        Args:
            order_type: "BUY" or "SELL"
            volume: Lot size
            sl: Stop loss price (optional)
            tp: Take profit price (optional)
            comment: Order comment
            magic: Magic number
        
        Returns:
            dict: Order result
        """
        try:
            # Get current price
            tick = mt5.symbol_info_tick(self.symbol)
            if tick is None:
                logger.error("❌ Failed to get current price")
                return None
            
            # Determine price and order type
            if order_type.upper() == "BUY":
                price = tick.ask
                mt5_order_type = mt5.ORDER_TYPE_BUY
            elif order_type.upper() == "SELL":
                price = tick.bid
                mt5_order_type = mt5.ORDER_TYPE_SELL
            else:
                logger.error(f"❌ Invalid order type: {order_type}")
                return None
            
            # Get symbol info for point calculation
            symbol_info = mt5.symbol_info(self.symbol)
            if symbol_info is None:
                logger.error("❌ Failed to get symbol info")
                return None
            
            point = symbol_info.point
            
            # Build request
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": self.symbol,
                "volume": volume,
                "type": mt5_order_type,
                "price": price,
                "deviation": self.default_deviation,
                "type_filling": mt5.ORDER_FILLING_IOC,
                "type_time": mt5.ORDER_TIME_GTC,
            }
            
            # Add optional parameters
            if sl:
                request["sl"] = sl
            if tp:
                request["tp"] = tp
            if magic:
                request["magic"] = magic
            if comment:
                request["comment"] = comment
            
            logger.info(f"📝 Executing {order_type}: {volume} lots @ ${price:.2f}")
            if sl:
                logger.info(f"   SL: ${sl:.2f}")
            if tp:
                logger.info(f"   TP: ${tp:.2f}")
            
            # Send order
            result = mt5.order_send(request)
            
            if result is None:
                logger.error("❌ Order send returned None")
                return None
            
            # Check result
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                logger.info(f"✅ Order executed successfully")
                logger.info(f"   Ticket: {result.order}")
                logger.info(f"   Deal: {result.deal}")
                logger.info(f"   Price: ${result.price:.2f}")
                
                return {
                    "success": True,
                    "ticket": result.order,
                    "deal": result.deal,
                    "price": result.price,
                    "volume": volume,
                    "type": order_type,
                    "sl": sl,
                    "tp": tp,
                    "comment": comment,
                    "retcode": result.retcode,
                    "time": datetime.now(timezone.utc)
                }
            else:
                logger.error(f"❌ Order failed: {result.retcode} - {result.comment}")
                return {
                    "success": False,
                    "retcode": result.retcode,
                    "comment": result.comment,
                    "error": f"Error {result.retcode}: {result.comment}"
                }
                
        except Exception as e:
            logger.error(f"❌ Error executing market order: {e}", exc_info=True)
            return None
    
    async def place_pending_order(self,
                                 order_type: str,
                                 volume: float,
                                 entry_price: float,
                                 sl: Optional[float] = None,
                                 tp: Optional[float] = None,
                                 expiration: Optional[datetime] = None,
                                 comment: str = "",
                                 magic: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Place pending order (limit or stop)
        
        Args:
            order_type: "BUY_LIMIT", "SELL_LIMIT", "BUY_STOP", "SELL_STOP"
            volume: Lot size
            entry_price: Entry price
            sl: Stop loss
            tp: Take profit
            expiration: Order expiration time
            comment: Comment
            magic: Magic number
        
        Returns:
            dict: Order result
        """
        try:
            # Map order type
            type_map = {
                "BUY_LIMIT": mt5.ORDER_TYPE_BUY_LIMIT,
                "SELL_LIMIT": mt5.ORDER_TYPE_SELL_LIMIT,
                "BUY_STOP": mt5.ORDER_TYPE_BUY_STOP,
                "SELL_STOP": mt5.ORDER_TYPE_SELL_STOP
            }
            
            if order_type not in type_map:
                logger.error(f"❌ Invalid pending order type: {order_type}")
                return None
            
            mt5_order_type = type_map[order_type]
            
            # Build request
            request = {
                "action": mt5.TRADE_ACTION_PENDING,
                "symbol": self.symbol,
                "volume": volume,
                "type": mt5_order_type,
                "price": entry_price,
                "type_time": mt5.ORDER_TIME_GTC,
            }
            
            # Add optional parameters
            if sl:
                request["sl"] = sl
            if tp:
                request["tp"] = tp
            if expiration:
                request["expiration"] = int(expiration.timestamp())
            if magic:
                request["magic"] = magic
            if comment:
                request["comment"] = comment
            
            logger.info(f"📝 Placing {order_type}: {volume} lots @ ${entry_price:.2f}")
            
            # Send order
            result = mt5.order_send(request)
            
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                logger.info(f"✅ Pending order placed: Ticket {result.order}")
                return {
                    "success": True,
                    "ticket": result.order,
                    "price": entry_price,
                    "type": order_type,
                    "volume": volume
                }
            else:
                logger.error(f"❌ Pending order failed: {result.comment if result else 'Unknown'}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error placing pending order: {e}")
            return None
    
    async def modify_position(self,
                             ticket: int,
                             sl: Optional[float] = None,
                             tp: Optional[float] = None) -> bool:
        """
        Modify existing position (SL/TP)
        
        Args:
            ticket: Position ticket
            sl: New stop loss (None to keep current)
            tp: New take profit (None to keep current)
        
        Returns:
            bool: True if successful
        """
        try:
            # Get position
            positions = mt5.positions_get(ticket=ticket)
            if positions is None or len(positions) == 0:
                logger.error(f"❌ Position {ticket} not found")
                return False
            
            position = positions[0]
            
            # Use existing SL/TP if not provided
            new_sl = sl if sl is not None else position.sl
            new_tp = tp if tp is not None else position.tp
            
            # Build request
            request = {
                "action": mt5.TRADE_ACTION_SLTP,
                "symbol": position.symbol,
                "sl": new_sl,
                "tp": new_tp,
                "position": ticket,
            }
            
            logger.info(f"📝 Modifying position {ticket}")
            if sl:
                logger.info(f"   New SL: ${sl:.2f}")
            if tp:
                logger.info(f"   New TP: ${tp:.2f}")
            
            # Send request
            result = mt5.order_send(request)
            
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                logger.info(f"✅ Position {ticket} modified successfully")
                return True
            else:
                logger.error(f"❌ Failed to modify position: {result.comment if result else 'Unknown'}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error modifying position: {e}")
            return False
    
    async def close_position(self,
                            ticket: int,
                            volume: Optional[float] = None,
                            comment: str = "") -> bool:
        """
        Close position (full or partial)
        
        Args:
            ticket: Position ticket
            volume: Volume to close (None for full)
            comment: Comment
        
        Returns:
            bool: True if successful
        """
        try:
            # Get position
            positions = mt5.positions_get(ticket=ticket)
            if positions is None or len(positions) == 0:
                logger.error(f"❌ Position {ticket} not found")
                return False
            
            position = positions[0]
            close_volume = volume if volume else position.volume
            
            # Get current price
            tick = mt5.symbol_info_tick(self.symbol)
            if tick is None:
                logger.error("❌ Failed to get current price")
                return False
            
            # Determine close order type and price
            if position.type == mt5.POSITION_TYPE_BUY:
                close_type = mt5.ORDER_TYPE_SELL
                close_price = tick.bid
            else:
                close_type = mt5.ORDER_TYPE_BUY
                close_price = tick.ask
            
            # Build request
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": position.symbol,
                "volume": close_volume,
                "type": close_type,
                "position": ticket,
                "price": close_price,
                "deviation": self.default_deviation,
                "type_filling": mt5.ORDER_FILLING_IOC,
                "type_time": mt5.ORDER_TIME_GTC,
                "comment": comment if comment else "Manual close",
            }
            
            logger.info(f"📝 Closing position {ticket}: {close_volume} lots @ ${close_price:.2f}")
            
            # Send request
            result = mt5.order_send(request)
            
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                logger.info(f"✅ Position {ticket} closed successfully")
                logger.info(f"   P&L: ${position.profit:.2f}")
                return True
            else:
                logger.error(f"❌ Failed to close position: {result.comment if result else 'Unknown'}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error closing position: {e}", exc_info=True)
            return False
    
    async def close_partial_position(self,
                                    ticket: int,
                                    close_percent: float,
                                    comment: str = "") -> bool:
        """
        Close partial position (percentage)
        
        Args:
            ticket: Position ticket
            close_percent: Percentage to close (0.0 to 1.0)
            comment: Comment
        
        Returns:
            bool: True if successful
        """
        try:
            positions = mt5.positions_get(ticket=ticket)
            if positions is None or len(positions) == 0:
                return False
            
            position = positions[0]
            close_volume = position.volume * close_percent
            
            # Validate volume
            symbol_info = mt5.symbol_info(self.symbol)
            if close_volume < symbol_info.volume_min:
                logger.warning(f"⚠️ Close volume too small: {close_volume}")
                return False
            
            return await self.close_position(ticket, close_volume, comment)
            
        except Exception as e:
            logger.error(f"❌ Error in partial close: {e}")
            return False
    
    async def get_trade_history(self, 
                               from_date: Optional[datetime] = None,
                               to_date: Optional[datetime] = None,
                               symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get trade history
        
        Args:
            from_date: Start date
            to_date: End date
            symbol: Filter by symbol
        
        Returns:
            list: Trade history
        """
        try:
            # Set default dates (last 7 days)
            if not from_date:
                from_date = datetime.now(timezone.utc) - timedelta(days=7)
            if not to_date:
                to_date = datetime.now(timezone.utc)
            
            # Get history
            history = mt5.history_orders_get(from_date, to_date, symbol or self.symbol)
            
            if history is None:
                return []
            
            result = []
            for order in history:
                result.append({
                    "ticket": order.ticket,
                    "symbol": order.symbol,
                    "type": "BUY" if order.type == mt5.ORDER_TYPE_BUY else "SELL",
                    "volume": order.volume,
                    "price_open": order.price_open,
                    "price_close": order.price_close,
                    "profit": order.profit,
                    "swap": order.swap,
                    "commission": order.commission,
                    "magic": order.magic,
                    "comment": order.comment,
                    "time_open": datetime.fromtimestamp(order.time_setup),
                    "time_close": datetime.fromtimestamp(order.time_done)
                })
            
            logger.info(f"📊 Retrieved {len(result)} historical orders")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error getting trade history: {e}")
            return []
    
    async def calculate_position_size(self,
                                     risk_amount: float,
                                     stop_distance: float,
                                     dna_params: Optional[Dict[str, Any]] = None) -> float:
        """
        Calculate position size based on risk parameters
        
        Args:
            risk_amount: Risk amount in USD
            stop_distance: Stop loss distance in points
            dna_params: DNA parameters for validation
        
        Returns:
            float: Lot size
        """
        try:
            # Get symbol info
            symbol_info = mt5.symbol_info(self.symbol)
            if symbol_info is None:
                logger.error("❌ Failed to get symbol info")
                return 0.0
            
            # Calculate lot size
            # Formula: Lot Size = Risk Amount / (Stop Distance * Tick Value)
            tick_value = symbol_info.trade_tick_value
            tick_size = symbol_info.trade_tick_size
            
            if tick_value == 0 or tick_size == 0:
                logger.error("❌ Invalid tick value or size")
                return 0.0
            
            # Raw calculation
            raw_lot = risk_amount / (stop_distance * (tick_value / tick_size))
            
            # Round to step size
            step = symbol_info.volume_step
            adjusted_lot = round(raw_lot / step) * step
            
            # Ensure within limits
            adjusted_lot = max(adjusted_lot, symbol_info.volume_min)
            adjusted_lot = min(adjusted_lot, symbol_info.volume_max)
            
            logger.info(f"📊 Position size calculation:")
            logger.info(f"   Risk: ${risk_amount:.2f}")
            logger.info(f"   Stop distance: {stop_distance} points")
            logger.info(f"   Raw lot: {raw_lot:.4f}")
            logger.info(f"   Adjusted lot: {adjusted_lot:.4f}")
            
            return adjusted_lot
            
        except Exception as e:
            logger.error(f"❌ Error calculating position size: {e}")
            return 0.0
