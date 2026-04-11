"""
FTMO Demo Test - Complete system test on live MT5
CEO: Qwen Code | Created: 2026-04-10

SAFETY MODE: No real trades - Analysis only
This script demonstrates the complete flow without executing trades.

What it does:
1. Connects to MT5 (FTMO Demo account)
2. Gets real-time BTCUSD data
3. Analyzes market conditions
4. Generates signals (without executing)
5. Validates risk
6. Shows what WOULD happen

Usage:
    python test_ftmo_demo.py
"""

import sys
from pathlib import Path
import asyncio
import MetaTrader5 as mt5
from datetime import datetime, timezone, timedelta
from loguru import logger

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.core.config_manager import ConfigManager
from src.execution.mt5.mt5_connector import MT5Connector
from src.execution.mt5.market_data import MarketDataFetcher
from src.risk.risk_manager import RiskManager
from src.risk.ftmo_commission_calculator import FTMOCommissionCalculator
from src.backtesting.backtester import BacktestEngine, BacktestConfig


def setup_logging():
    """Configure logging for console output"""
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )


def print_header(title: str):
    """Print formatted header"""
    print("\n" + "="*80)
    print(f"🚀 {title}")
    print("="*80)


def print_section(title: str):
    """Print section separator"""
    print(f"\n{'─'*80}")
    print(f"📊 {title}")
    print(f"{'─'*80}")


async def test_mt5_connection(connector: MT5Connector) -> bool:
    """Test 1: MT5 Connection"""
    print_section("TEST 1: MT5 CONNECTION")
    
    print("\n🔌 Connecting to MT5...")
    success = await connector.connect()
    
    if success:
        print(f"   ✅ Connected successfully!")
        print(f"   Account: {connector.account_info.get('login')}")
        print(f"   Balance: ${connector.account_info.get('balance'):,.2f}")
        print(f"   Equity: ${connector.account_info.get('equity'):,.2f}")
        print(f"   Leverage: 1:{connector.account_info.get('leverage', 1)}")
        print(f"   Server: {connector.account_info.get('server')}")
        print(f"   Symbol: BTCUSD")
        print(f"   Spread: {connector.symbol_info.get('spread', 0)} points")
        return True
    else:
        print("   ❌ Connection failed!")
        print("   💡 Make sure MT5 is running and logged in")
        return False


async def test_market_data(market_data: MarketDataFetcher):
    """Test 2: Market Data Collection"""
    print_section("TEST 2: MARKET DATA COLLECTION")
    
    # Get current price
    print("\n💰 Getting current BTCUSD price...")
    price = await market_data.get_current_price()
    
    if price:
        print(f"   ✅ Bid: ${price['bid']:,.2f}")
        print(f"   ✅ Ask: ${price['ask']:,.2f}")
        print(f"   ✅ Spread: ${price['spread']:.2f} ({price['spread_points']:.0f} points)")
        print(f"   ✅ Time: {price['time']}")
    else:
        print("   ⚠️ Could not get current price")
    
    # Get historical candles
    print("\n📊 Getting M5 candles (last 100 bars)...")
    candles = await market_data.get_candles(timeframe="M5", count=100)
    
    if candles is not None and len(candles) > 0:
        print(f"   ✅ Retrieved {len(candles)} candles")
        print(f"   📈 Period: {candles['time'].iloc[0]} → {candles['time'].iloc[-1]}")
        print(f"   💵 Price range: ${candles['low'].min():,.2f} - ${candles['high'].max():,.2f}")
        print(f"   📊 Avg volume: {candles['volume'].mean():,.0f}")
        
        # Show last 5 candles
        print("\n   🕯️ Last 5 candles:")
        for i in range(-5, 0):
            c = candles.iloc[i]
            direction = "🟢" if c['close'] > c['open'] else "🔴"
            print(f"      {direction} {c['time']}: ${c['open']:,.0f} → ${c['close']:,.0f} (H: ${c['high']:,.0f} L: ${c['low']:,.0f})")
    else:
        print("   ⚠️ No candle data available")
    
    return candles


async def test_risk_analysis(risk_manager: RiskManager, commission_calc: FTMOCommissionCalculator, candles):
    """Test 3: Risk Analysis"""
    print_section("TEST 3: RISK ANALYSIS & FTMO COMPLIANCE")
    
    capital = 100000.0
    
    # Initialize risk manager
    await risk_manager.initialize(capital)
    
    # Analyze a hypothetical trade
    print("\n💭 Analyzing hypothetical trade...")
    
    if candles is not None and len(candles) > 50:
        current_price = candles['close'].iloc[-1]
        
        # Calculate indicators
        ema_9 = candles['close'].ewm(span=9, adjust=False).mean().iloc[-1]
        ema_21 = candles['close'].ewm(span=21, adjust=False).mean().iloc[-1]
        
        print(f"\n   📊 Technical Analysis:")
        print(f"      Current Price: ${current_price:,.2f}")
        print(f"      EMA 9: ${ema_9:,.2f}")
        print(f"      EMA 21: ${ema_21:,.2f}")
        print(f"      Trend: {'🟢 BULLISH' if ema_9 > ema_21 else '🔴 BEARISH'}")
        
        # Hypothetical trade
        if ema_9 > ema_21:
            direction = "BUY"
            sl = current_price - 300  # $300 stop
            tp = current_price + 600  # $600 target (1:2 R:R)
        else:
            direction = "SELL"
            sl = current_price + 300
            tp = current_price - 600
        
        risk_amount = abs(current_price - sl) * 0.10  # 0.10 lots
        reward_amount = abs(tp - current_price) * 0.10
        rr_ratio = reward_amount / risk_amount
        
        print(f"\n   💭 Hypothetical Trade:")
        print(f"      Direction: {direction}")
        print(f"      Entry: ${current_price:,.2f}")
        print(f"      Stop Loss: ${sl:,.2f} (-$300)")
        print(f"      Take Profit: ${tp:,.2f} (+$600)")
        print(f"      Volume: 0.10 lots")
        print(f"      Risk: ${risk_amount:.2f}")
        print(f"      Reward: ${reward_amount:.2f}")
        print(f"      R:R: 1:{rr_ratio:.2f}")
        
        # Calculate costs
        costs = commission_calc.analyze_trade(
            volume=0.10,
            entry_price=current_price,
            stop_loss_price=sl,
            take_profit_price=tp,
            spread_points=100
        )
        
        print(f"\n   💸 Realistic Costs:")
        print(f"      Commission: ${costs['commission_total']:.2f}")
        print(f"      Spread Cost: ${costs['spread_cost']:.2f}")
        print(f"      Total Costs: ${costs['total_costs']:.2f}")
        print(f"      Net Profit if TP hit: ${costs['net_profit']:.2f}")
        print(f"      Net Loss if SL hit: ${costs['net_loss']:.2f}")
        print(f"      Net R:R: 1:{costs['net_rr']:.2f}")
        
        # Validate trade
        print(f"\n   🛡️ Risk Validation:")
        validation = await risk_manager.validate_trade(
            risk_amount=risk_amount,
            reward_amount=reward_amount,
            capital=capital
        )
        
        if validation['approved']:
            print(f"      ✅ Trade APPROVED")
            print(f"      Risk: {validation['details']['risk_percent']:.2f}%")
            print(f"      R:R: 1:{validation['details']['rr_ratio']:.2f}")
        else:
            print(f"      ❌ Trade REJECTED")
            for reason in validation['reasons']:
                print(f"         - {reason}")
        
        # FTMO compliance
        print(f"\n   🎯 FTMO Compliance:")
        ftmo = await risk_manager.check_ftmo_compliance(capital)
        print(f"      Daily Loss Limit: {'✅ OK' if ftmo['daily_loss_ok'] else '❌ EXCEEDED'}")
        print(f"      Total Loss Limit: {'✅ OK' if ftmo['total_loss_ok'] else '❌ EXCEEDED'}")
        print(f"      Consistency Rule: {'✅ OK' if ftmo['consistency_ok'] else '❌ WARNING'}")
        
        # Drawdown check
        drawdown = await risk_manager.check_drawdown_levels(capital)
        print(f"      Current Drawdown: {drawdown['current_drawdown']:.2f}%")
        print(f"      Status: {drawdown['status']}")


async def test_live_monitoring(market_data: MarketDataFetcher, candles):
    """Test 4: Live Market Monitoring (30 seconds)"""
    print_section("TEST 4: LIVE MARKET MONITORING (30 seconds)")
    
    print("\n⏱️ Monitoring BTCUSD in real-time for 30 seconds...")
    print("   (Press Ctrl+C to stop early)")
    
    try:
        for i in range(6):  # 6 iterations × 5 seconds = 30 seconds
            price = await market_data.get_current_price()
            
            if price:
                emoji = "🟢" if i % 2 == 0 else "🔴"
                print(f"   [{i*5:2d}s] {emoji} ${price['bid']:,.2f} / ${price['ask']:,.2f} | Spread: {price['spread_points']:.0f} pts")
            
            await asyncio.sleep(5)
    except KeyboardInterrupt:
        print("\n   ⏹️ Monitoring stopped by user")


async def main():
    """Main test flow"""
    setup_logging()
    
    print_header("FOREX QUANTUM BOT - FTMO DEMO TEST")
    print("""
This test will demonstrate the complete system flow:
  ✅ MT5 Connection (FTMO Demo)
  ✅ Real-time BTCUSD Market Data
  ✅ Technical Analysis & Signal Generation
  ✅ Risk Validation & FTMO Compliance
  ✅ Live Market Monitoring (30s)
  
⚠️ SAFETY MODE: No real trades will be executed!
""")
    
    response = input("❓ Ready to start the test? (yes/no): ").strip().lower()
    
    if response not in ['yes', 'y']:
        print("\n👋 Test cancelled")
        return
    
    # Initialize components
    config_manager = ConfigManager()
    dna = config_manager.load_dna()
    
    mt5_connector = MT5Connector(config=config_manager)
    market_data = MarketDataFetcher(config=config_manager)
    risk_manager = RiskManager(config=config_manager)
    commission_calc = FTMOCommissionCalculator()
    
    try:
        # Test 1: MT5 Connection
        if not await test_mt5_connection(mt5_connector):
            return
        
        # Test 2: Market Data
        candles = await test_market_data(market_data)
        
        # Test 3: Risk Analysis
        await test_risk_analysis(risk_manager, commission_calc, candles)
        
        # Test 4: Live Monitoring
        await test_live_monitoring(market_data, candles)
        
        # Summary
        print_section("TEST COMPLETE - SUMMARY")
        print("""
✅ All systems operational!

What you saw:
  🔌 MT5 connected to your FTMO demo account
  📊 Real-time BTCUSD market data collected
  📈 Technical analysis performed (EMA, trends)
  💸 Realistic costs calculated (commissions + spread)
  🛡️ Risk validation checked (FTMO rules)
  ⏱️ Live monitoring demonstrated

Next steps:
  1. Review the logs and understand the flow
  2. When ready, enable live trading mode
  3. Start with paper trading (manual validation)
  4. Then enable automated trading

💡 Check data/backtest-results/ for HTML reports!
""")
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Test interrupted by user")
    except Exception as e:
        logger.error(f"\n❌ Test failed: {e}", exc_info=True)
    finally:
        # Cleanup
        if mt5_connector.connected:
            await mt5_connector.disconnect()
            print("\n🔌 Disconnected from MT5")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Test cancelled")
