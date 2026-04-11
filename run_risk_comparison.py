"""
Risk Level Comparison Test
Tests multiple risk percentages to find optimal position sizing
"""

import subprocess
import re
import sys

risk_levels = [0.5, 1.0, 1.5, 2.0]

print("\n" + "="*80)
print("📊 RISK LEVEL COMPARISON TEST")
print("="*80 + "\n")

results = []

for risk_pct in risk_levels:
    print(f"\n{'='*60}")
    print(f"🔬 Testing {risk_pct}% risk per trade...")
    print(f"{'='*60}")
    
    # Read backtest file and modify risk_percent
    with open("run_backtest_final.py", "r", encoding='utf-8', errors='replace') as f:
        content = f.read()
    
    # Modify risk_percent
    modified = re.sub(r"risk_percent = [\d.]+", f"risk_percent = {risk_pct}", content)
    
    with open("run_backtest_final.py", "w") as f:
        f.write(modified)
    
    # Run backtest
    result = subprocess.run(["python", "run_backtest_final.py"], 
                          capture_output=True, text=True, encoding='utf-8', errors='replace')
    
    # Parse results
    output = result.stdout
    
    # Extract metrics
    final_match = re.search(r"Final: \$([\d,]+\.?\d*)", output)
    profit_match = re.search(r"Net Profit: \$([\d,]+\.?\d*) \(([\d.]+)%\)", output)
    wr_match = re.search(r"Win Rate: ([\d.]+)%", output)
    pf_match = re.search(r"Profit Factor: ([\d.]+)", output)
    dd_match = re.search(r"Max Drawdown: ([\d.]+)%", output)
    ftmo_match = re.search(r"FTMO: (✅ PASS|❌ FAIL)", output)
    
    if final_match and profit_match:
        result = {
            'risk_pct': risk_pct,
            'final': final_match.group(1),
            'profit': profit_match.group(1),
            'profit_pct': profit_match.group(2),
            'win_rate': wr_match.group(1) if wr_match else "N/A",
            'profit_factor': pf_match.group(1) if pf_match else "N/A",
            'max_dd': dd_match.group(1) if dd_match else "N/A",
            'ftmo': ftmo_match.group(1) if ftmo_match else "N/A",
        }
        results.append(result)
        
        print(f"   Final: ${result['final']}")
        print(f"   Profit: ${result['profit']} ({result['profit_pct']}%)")
        print(f"   Win Rate: {result['win_rate']}%")
        print(f"   Profit Factor: {result['profit_factor']}")
        print(f"   Max DD: {result['max_dd']}%")
        print(f"   FTMO: {result['ftmo']}")

# Restore original risk_percent (0.5)
with open("run_backtest_final.py", "r", encoding='utf-8', errors='replace') as f:
    content = f.read()
modified = re.sub(r"risk_percent = [\d.]+", "risk_percent = 0.5", content)
with open("run_backtest_final.py", "w", encoding='utf-8') as f:
    f.write(modified)

# Print comparison table
print("\n" + "="*80)
print("📊 RISK LEVEL COMPARISON RESULTS")
print("="*80)
print(f"\n{'Risk %':<10} {'Final Equity':<15} {'Profit':<12} {'Win Rate':<10} {'PF':<8} {'Max DD':<10} {'FTMO':<10}")
print("-"*80)

for r in results:
    print(f"{r['risk_pct']:<10} ${r['final']:<15} ${r['profit']:<11} {r['win_rate']:<10} {r['profit_factor']:<8} {r['max_dd']:<10} {r['ftmo']:<10}")

print("\n" + "="*80)

# Find optimal
ftmo_passed = [r for r in results if "PASS" in r['ftmo']]
if ftmo_passed:
    best = max(ftmo_passed, key=lambda x: float(x['profit']))
    print(f"\n✅ OPTIMAL RISK LEVEL: {best['risk_pct']}%")
    print(f"   Profit: ${best['profit']} ({best['profit_pct']}%)")
    print(f"   Max DD: {best['max_dd']}% (FTMO: {best['ftmo']})")
else:
    print(f"\n⚠️ No risk level passes FTMO. Optimal for profit:")
    best = max(results, key=lambda x: float(x['profit']))
    print(f"   Risk: {best['risk_pct']}%")
    print(f"   Profit: ${best['profit']}")
    print(f"   Max DD: {best['max_dd']}% (Would fail FTMO)")

print("\n" + "="*80 + "\n")
