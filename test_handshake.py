"""
Quick handshake test - Python writes, EA reads
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from run_signal_generator import SignalGenerator

# Initialize just enough to test handshake
gen = SignalGenerator()

print("\n✅ Handshake files created:")
print(f"   Local: {gen.handshake_file}")
print(f"   MT5 Common: {Path.home() / 'AppData' / 'Roaming' / 'MetaQuotes' / 'Terminal' / 'Common' / 'Files' / 'quantum_signals' / 'connection.txt'}")

# Verify files exist
if Path(gen.handshake_file).exists():
    print(f"\n✅ Local handshake file exists!")
    with open(gen.handshake_file, 'r') as f:
        print(f.read())

mt5_common = Path.home() / "AppData" / "Roaming" / "MetaQuotes" / "Terminal" / "Common" / "Files" / "quantum_signals" / "connection.txt"
if mt5_common.exists():
    print(f"\n✅ MT5 Common handshake file exists!")
    with open(str(mt5_common), 'r') as f:
        print(f.read())
