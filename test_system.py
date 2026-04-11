"""
Test Script - Verify MT5 connection and system setup
CEO: Qwen Code | Created: 2026-04-10
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_imports():
    """Test if all required modules can be imported"""
    print("=" * 60)
    print("🧪 TESTING IMPORTS")
    print("=" * 60)
    
    modules = [
        ("MetaTrader5", "mt5"),
        ("pandas", "pd"),
        ("numpy", "np"),
        ("loguru", "logger"),
        ("fastapi", "fastapi"),
        ("json", "json"),
        ("asyncio", "asyncio"),
    ]
    
    success = 0
    failed = 0
    
    for module, alias in modules:
        try:
            __import__(module)
            print(f"✅ {module}")
            success += 1
        except ImportError as e:
            print(f"❌ {module}: {e}")
            failed += 1
    
    # Test local modules
    print("\n📦 Testing local modules...")
    local_modules = [
        "src.core.config_manager",
        "src.core.orchestrator",
        "src.dna.dna_engine",
        "src.execution.mt5.mt5_connector",
        "src.execution.mt5.market_data",
        "src.execution.mt5.order_manager",
        "src.risk.risk_manager",
    ]
    
    for module in local_modules:
        try:
            __import__(module)
            print(f"✅ {module}")
            success += 1
        except Exception as e:
            print(f"❌ {module}: {e}")
            failed += 1
    
    print(f"\n✅ Success: {success} | ❌ Failed: {failed}")
    return failed == 0


def test_mt5_connection():
    """Test MT5 connection"""
    print("\n" + "=" * 60)
    print("🔌 TESTING MT5 CONNECTION")
    print("=" * 60)
    
    try:
        import MetaTrader5 as mt5
        
        # Initialize MT5
        if not mt5.initialize():
            print(f"❌ MT5 initialization failed: {mt5.last_error()}")
            return False
        
        print("✅ MT5 initialized")
        
        # Get account info
        account = mt5.account_info()
        if account:
            print(f"✅ Account: {account.login}")
            print(f"💵 Balance: ${account.balance:.2f}")
            print(f"📊 Equity: ${account.equity:.2f}")
            print(f"📈 Leverage: 1:{account.leverage}")
            print(f"💱 Currency: {account.currency}")
            print(f"🖥️ Server: {account.server}")
        else:
            print("❌ No account info - not logged in")
        
        # Test BTCUSD symbol
        print("\n📊 Testing BTCUSD symbol...")
        if mt5.symbol_select("BTCUSD", True):
            symbol_info = mt5.symbol_info("BTCUSD")
            if symbol_info:
                print(f"✅ BTCUSD available")
                print(f"   Spread: {symbol_info.spread} points")
                print(f"   Min lot: {symbol_info.volume_min}")
                print(f"   Max lot: {symbol_info.volume_max}")
                print(f"   Point: {symbol_info.point}")
                
                # Get current price
                tick = mt5.symbol_info_tick("BTCUSD")
                if tick:
                    print(f"\n💰 Current Price:")
                    print(f"   Bid: ${tick.bid:.2f}")
                    print(f"   Ask: ${tick.ask:.2f}")
                    print(f"   Spread: ${tick.ask - tick.bid:.2f}")
            else:
                print("❌ BTCUSD symbol info failed")
        else:
            print("❌ BTCUSD symbol not available")
        
        # Shutdown
        mt5.shutdown()
        print("\n✅ MT5 connection test complete")
        return True
        
    except Exception as e:
        print(f"❌ MT5 test error: {e}")
        return False


def test_config():
    """Test configuration loading"""
    print("\n" + "=" * 60)
    print("⚙️ TESTING CONFIGURATION")
    print("=" * 60)
    
    try:
        from src.core.config_manager import ConfigManager
        
        config = ConfigManager()
        print("✅ ConfigManager initialized")
        
        # Load DNA
        dna = config.load_dna()
        print(f"✅ DNA loaded: {len(dna)} top-level keys")
        
        # Load absolute limits
        limits = config.load_absolute_limits()
        print(f"✅ Absolute limits loaded")
        
        # Test validation
        is_valid = config.validate_dna_against_limits(dna, limits)
        print(f"✅ DNA validation: {'PASSED' if is_valid else 'FAILED'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Config test error: {e}")
        return False


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("🚀 FOREX QUANTUM BOT - SYSTEM TESTS")
    print("=" * 60 + "\n")
    
    results = {
        "imports": test_imports(),
        "mt5": test_mt5_connection(),
        "config": test_config(),
    }
    
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    for test, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test.upper()}: {status}")
    
    all_passed = all(results.values())
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 ALL TESTS PASSED - System ready!")
    else:
        print("⚠️ SOME TESTS FAILED - Please check errors above")
    print("=" * 60 + "\n")
    
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
