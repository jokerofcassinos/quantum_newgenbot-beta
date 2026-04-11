"""
Orchestrator V2 - Complete system integration
CEO: Qwen Code | Created: 2026-04-10

Integrates:
- DNA Engine (adaptive parameters)
- MT5 Execution (connector, market data, orders)
- Risk Management (FTMO compliance)
- Strategy Engine (signal generation)
- Commission Calculator (realistic costs)
- Monitoring (future)
"""

import asyncio
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from loguru import logger

from src.core.config_manager import ConfigManager
from src.dna.dna_engine import DNAEngine
from src.execution.mt5.mt5_connector import MT5Connector
from src.execution.mt5.market_data import MarketDataFetcher
from src.execution.mt5.order_manager import OrderManager
from src.risk.risk_manager import RiskManager
from src.risk.ftmo_commission_calculator import FTMOCommissionCalculator
from src.strategies.btcusd_scalping import BTCUSDScalpingStrategy


class Orchestrator:
    """
    Central orchestrator - Complete integrated system
    
    Manages the full trading lifecycle:
    1. Connect to MT5
    2. Load DNA parameters
    3. Analyze market
    4. Generate signals
    5. Validate risk (including commissions)
    6. Execute trades
    7. Monitor positions
    8. Adapt DNA
    """
    
    def __init__(self, config: ConfigManager, dna: Dict[str, Any]):
        self.config = config
        self.dna = dna
        self.running = False
        
        # Initialize ALL modules
        logger.info("🔧 Initializing all modules...")
        
        # Core
        self.dna_engine = DNAEngine(config=config)
        
        # MT5
        self.mt5_connector = MT5Connector(config=config)
        self.market_data = MarketDataFetcher(config)
        self.order_manager = OrderManager(config)
        
        # Risk
        self.risk_manager = RiskManager(config=config)
        self.commission_calc = FTMOCommissionCalculator()
        
        # Strategy
        self.strategy = BTCUSDScalpingStrategy(dna_params=dna)
        
        # State tracking
        self.is_connected = False
        self.initial_balance = 0.0
        self.current_balance = 0.0
        self.trades_executed = 0
        self.trades_approved = 0
        self.trades_rejected = 0
        
        logger.info("✅ All modules initialized")
    
    async def run(self):
        """Main execution flow"""
        logger.info("="*80)
        logger.info("🚀 FOREX QUANTUM BOT - STARTING COMPLETE SYSTEM")
        logger.info("="*80)
        
        try:
            # Phase 1: Connect to MT5
            await self._phase1_connect()
            
            # Phase 2: Initialize systems
            await self._phase2_initialize()
            
            # Phase 3: Start trading loop
            await self._phase3_trading_loop()
            
        except KeyboardInterrupt:
            logger.warning("⚠️ Manual interruption detected")
            await self.shutdown()
        except Exception as e:
            logger.error(f"💀 Critical error: {e}", exc_info=True)
            await self.emergency_shutdown()
    
    async def _phase1_connect(self):
        """Phase 1: MT5 Connection"""
        logger.info("\n" + "="*80)
        logger.info("📡 PHASE 1: MT5 CONNECTION")
        logger.info("="*80)
        
        # Connect to MT5
        self.is_connected = await self.mt5_connector.connect()
        
        if not self.is_connected:
            logger.error("❌ Failed to connect to MT5 - aborting")
            raise Exception("MT5 connection failed")
        
        # Get account info
        account = self.mt5_connector.account_info
        if account:
            self.initial_balance = account.get("balance", 0)
            self.current_balance = self.initial_balance
            
            logger.info(f"✅ Connected to account: {account.get('login')}")
            logger.info(f"💵 Balance: ${self.initial_balance:,.2f}")
            logger.info(f"📊 Equity: ${account.get('equity', 0):,.2f}")
            logger.info(f"📈 Leverage: 1:{account.get('leverage', 1)}")
    
    async def _phase2_initialize(self):
        """Phase 2: System Initialization"""
        logger.info("\n" + "="*80)
        logger.info("⚙️ PHASE 2: SYSTEM INITIALIZATION")
        logger.info("="*80)
        
        # Load and validate DNA
        self.dna = self.dna_engine.load_dna()
        limits = self.config.load_absolute_limits()
        
        is_valid = self.config.validate_dna_against_limits(self.dna, limits)
        if not is_valid:
            raise Exception("DNA validation failed")
        
        # Initialize risk manager
        await self.risk_manager.initialize(self.current_balance)
        
        # Update strategy with DNA params
        self.strategy = BTCUSDScalpingStrategy(dna_params=self.dna)
        
        # Log configuration
        logger.info("✅ DNA loaded and validated")
        logger.info("✅ Risk manager initialized")
        logger.info("✅ Strategy initialized")
        
        # Print commission info
        logger.info("\n💰 FTMO Commission Structure:")
        logger.info(f"   Commission: $45/lot/side")
        logger.info(f"   Spread: ~100 points ($1.00)")
        logger.info(f"   Total costs per trade (0.10 lots): ~$19")
    
    async def _phase3_trading_loop(self):
        """Phase 3: Main Trading Loop"""
        logger.info("\n" + "="*80)
        logger.info("🔄 PHASE 3: TRADING LOOP")
        logger.info("="*80)
        
        loop_count = 0
        dna_check_interval = 60  # Every 5 minutes (5 sec intervals)
        trade_cooldown = 0
        
        while self.running or loop_count == 0:
            self.running = True
            loop_count += 1
            
            try:
                logger.info(f"\n{'='*60}")
                logger.info(f"📊 LOOP #{loop_count}")
                logger.info(f"{'='*60}")
                
                # Check MT5 health
                if not await self.mt5_connector.check_health():
                    logger.error("❌ MT5 connection lost - attempting reconnect")
                    await self.mt5_connector.connect()
                    continue
                
                # Get current market data
                logger.info("📊 Fetching market data...")
                candles = await self.market_data.get_candles(
                    timeframe="M5",
                    count=100
                )
                
                if candles is None or len(candles) == 0:
                    logger.warning("⚠️ No market data available - skipping loop")
                    await asyncio.sleep(5)
                    continue
                
                # Get current price
                current_price = await self.market_data.get_current_price()
                if current_price:
                    logger.info(f"💰 Current BTCUSD: ${current_price['bid']:.2f} / ${current_price['ask']:.2f}")
                
                # DNA adaptation check
                if loop_count % dna_check_interval == 0:
                    logger.info("🧬 Running DNA adaptation...")
                    await self.dna_engine.adapt()
                
                # Generate signal
                logger.info("📈 Analyzing market...")
                signal = await self.strategy.generate_signal(
                    candles=candles,
                    market_data=current_price or {},
                    dna_params=self.dna
                )
                
                if signal is None:
                    logger.info("ℹ️ No signal generated - continuing")
                    await asyncio.sleep(5)
                    continue
                
                logger.info(f"✅ Signal: {signal.direction} @ ${signal.entry_price:.2f}")
                logger.info(f"   SL: ${signal.stop_loss:.2f} | TP: ${signal.take_profit:.2f}")
                logger.info(f"   R:R: 1:{signal.risk_reward_ratio:.2f} | Confidence: {signal.confidence:.2f}")
                
                # Calculate realistic costs
                costs = self.commission_calc.analyze_trade(
                    volume=0.10,  # Will be calculated properly later
                    entry_price=signal.entry_price,
                    stop_loss_price=signal.stop_loss,
                    take_profit_price=signal.take_profit,
                    spread_points=100
                )
                
                logger.info(f"💰 Trade costs: ${costs['total_costs']:.2f}")
                logger.info(f"📊 Net R:R: 1:{costs['net_rr']:.2f}")
                
                # Validate risk
                logger.info("🛡️ Validating risk...")
                risk_amount = abs(signal.entry_price - signal.stop_loss) * 0.10  # Placeholder
                reward_amount = abs(signal.take_profit - signal.entry_price) * 0.10
                
                validation = await self.risk_manager.validate_trade(
                    risk_amount=risk_amount,
                    reward_amount=reward_amount,
                    capital=self.current_balance
                )
                
                if not validation["approved"]:
                    logger.warning(f"❌ Trade rejected by risk manager:")
                    for reason in validation["reasons"]:
                        logger.warning(f"   - {reason}")
                    self.trades_rejected += 1
                    await asyncio.sleep(5)
                    continue
                
                # Check if should stop trading
                should_stop, stop_reason = await self.risk_manager.should_stop_trading(self.current_balance)
                if should_stop:
                    logger.warning(f"🛑 Trading halted: {stop_reason}")
                    await asyncio.sleep(60)  # Wait 1 minute before checking again
                    continue
                
                # EXECUTE TRADE (commented out for safety - enable when ready)
                # logger.info("📝 Executing trade...")
                # lot_size = await self.risk_manager.calculate_position_size(
                #     capital=self.current_balance,
                #     stop_distance_points=abs(signal.entry_price - signal.stop_loss) / 0.01,
                #     point_value=1.0
                # )
                #
                # result = await self.order_manager.execute_market_order(
                #     order_type=signal.direction,
                #     volume=lot_size,
                #     sl=signal.stop_loss,
                #     tp=signal.take_profit,
                #     comment=f"Signal: {signal.strategy_name}"
                # )
                #
                # if result and result["success"]:
                #     logger.info(f"✅ Trade executed: {result['ticket']}")
                #     self.trades_executed += 1
                # else:
                #     logger.error("❌ Trade execution failed")
                
                logger.info("⚠️ TRADE EXECUTION DISABLED (safety mode)")
                logger.info("   Enable in code when ready for live trading")
                self.trades_approved += 1
                
                # Update P&L tracking
                # (In real trading, this would be updated from MT5)
                
                # DNA engine - save regime if trade was successful
                # (Will be implemented with actual trade history)
                
                # Wait before next loop
                await asyncio.sleep(5)
                
            except asyncio.CancelledError:
                logger.info("⚠️ Trading loop cancelled")
                break
            except Exception as e:
                logger.error(f"❌ Error in trading loop: {e}", exc_info=True)
                await asyncio.sleep(10)  # Wait before retry
    
    async def shutdown(self):
        """Graceful shutdown"""
        logger.info("\n" + "="*80)
        logger.info("🛑 INITIATING GRACEFUL SHUTDOWN")
        logger.info("="*80)
        
        self.running = False
        
        # Close all positions
        if self.is_connected:
            await self.mt5_connector.close_all_positions()
            await self.mt5_connector.disconnect()
        
        # Print summary
        logger.info("\n" + "="*80)
        logger.info("📊 SESSION SUMMARY")
        logger.info("="*80)
        logger.info(f"Initial Balance: ${self.initial_balance:,.2f}")
        logger.info(f"Current Balance: ${self.current_balance:,.2f}")
        logger.info(f"P&L: ${self.current_balance - self.initial_balance:+,.2f}")
        logger.info(f"Signals Generated: {self.strategy.signals_generated}")
        logger.info(f"Signals Approved: {self.strategy.signals_approved}")
        logger.info(f"Signals Rejected: {self.strategy.signals_rejected}")
        logger.info(f"Trades Executed: {self.trades_executed}")
        logger.info("="*80)
        
        logger.info("✅ Graceful shutdown complete")
    
    async def emergency_shutdown(self):
        """Emergency shutdown"""
        logger.critical("\n" + "="*80)
        logger.critical("🚨 EMERGENCY SHUTDOWN INITIATED")
        logger.critical("="*80)
        
        self.running = False
        
        # Close all positions immediately
        if self.is_connected:
            await self.mt5_connector.close_all_positions()
            await self.mt5_connector.disconnect()
        
        logger.critical("💀 Emergency shutdown complete")
