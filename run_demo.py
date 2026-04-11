"""
Demo - Complete System Test (NO LIVE TRADING)
CEO: Qwen Code | Created: 2026-04-10

This script demonstrates the complete system WITHOUT executing real trades.
Perfect for testing the integration safely.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import asyncio
from loguru import logger
from src.core.config_manager import ConfigManager
from src.core.orchestrator_v2 import Orchestrator


async def demo():
    """Run complete system demo"""
    
    # Setup logging
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )
    
    print("\n" + "="*80)
    print("🚀 FOREX QUANTUM BOT - COMPLETE SYSTEM DEMO")
    print("   ⚠️ SAFETY MODE: No live trades will be executed")
    print("="*80 + "\n")
    
    # Initialize
    config = ConfigManager()
    dna = config.load_dna()
    
    # Create orchestrator
    orchestrator = Orchestrator(config=config, dna=dna)
    
    # Run system
    try:
        await orchestrator.run()
    except KeyboardInterrupt:
        logger.info("\n⚠️ Demo interrupted by user")
        await orchestrator.shutdown()
    except Exception as e:
        logger.error(f"\n❌ Demo error: {e}")
        await orchestrator.emergency_shutdown()


def main():
    """Entry point"""
    print("\n" + "="*80)
    print("💡 ABOUT THIS DEMO")
    print("="*80)
    print("""
This demo will:
✅ Connect to your FTMO MT5 account
✅ Load current BTCUSD market data
✅ Analyze market conditions (M5 timeframe)
✅ Generate trading signals
✅ Calculate realistic costs (commissions + spread)
✅ Validate against risk management rules
✅ Show what trades WOULD be executed

This demo will NOT:
❌ Execute real trades (safety lock enabled)
❌ Send real orders to MT5
❌ Risk any capital

To enable live trading, you must:
1. Review all code thoroughly
2. Test extensively in demo mode
3. Uncomment trade execution in orchestrator_v2.py
4. Accept the risks
""")
    
    response = input("\n❓ Ready to run demo? (yes/no): ").strip().lower()
    
    if response in ["yes", "y"]:
        print("\n🚀 Starting demo...\n")
        asyncio.run(demo())
    else:
        print("\n👋 Demo cancelled")
    
    print("\n" + "="*80)
    print("✅ DEMO COMPLETE")
    print("="*80)
    print("\nNext steps:")
    print("1. Review the signals generated")
    print("2. Check if risk validation is working")
    print("3. Verify cost calculations")
    print("4. When ready, enable live trading in orchestrator_v2.py")
    print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    main()
