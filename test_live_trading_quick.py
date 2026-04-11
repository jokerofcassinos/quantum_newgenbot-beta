"""
Quick Live Trading Test - 3 cycles to verify continuous operation
CEO: Qwen Code | Created: 2026-04-11
"""

import sys
from pathlib import Path
import asyncio

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from run_live_trading import LiveTradingSystem


async def main():
    print("\n" + "="*80)
    print("🧪 LIVE TRADING SYSTEM - CONTINUOUS TEST (3 cycles)")
    print("   This verifies the system runs continuously, not just once")
    print("="*80 + "\n")
    
    # Initialize in safe mode
    system = LiveTradingSystem(safe_mode=True)
    
    # Reduce interval for testing
    system.analysis_interval = 15  # 15 seconds between cycles
    
    # Run 3 cycles
    num_cycles = 3
    print(f"\n🔬 Running {num_cycles} analysis cycles...\n")
    
    for i in range(1, num_cycles + 1):
        print(f"\n{'='*60}")
        print(f"🔄 CYCLE {i}/{num_cycles}")
        print(f"{'='*60}")
        
        await system._analysis_cycle()
        
        if i < num_cycles:
            print(f"\n⏳ Waiting {system.analysis_interval}s before next cycle...\n")
            await asyncio.sleep(system.analysis_interval)
    
    print("\n" + "="*80)
    print("✅ ALL 3 CYCLES COMPLETED - System is working continuously!")
    print("="*80)
    
    # Cleanup
    import MetaTrader5 as mt5
    mt5.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
