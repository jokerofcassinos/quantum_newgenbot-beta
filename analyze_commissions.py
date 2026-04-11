"""
FTMO Commission Analysis - Real cost breakdown
CEO: Qwen Code | Created: 2026-04-10

This script shows the REAL impact of FTMO commissions on trading profitability.
"""

from src.risk.ftmo_commission_calculator import FTMOCommissionCalculator

def main():
    print("\n" + "="*80)
    print("💰 FOREX QUANTUM BOT - FTMO COMMISSION ANALYSIS")
    print("="*80 + "\n")
    
    calculator = FTMOCommissionCalculator()
    
    # Print detailed examples
    calculator.print_cost_examples()
    
    # Specific analysis for our setup
    print("="*80)
    print("📊 SPECIFIC ANALYSIS FOR $100K FTMO ACCOUNT")
    print("="*80)
    
    capital = 100000
    risk_percent = 0.5
    stop_loss_points = 300  # $300 stop loss
    spread_points = 100     # $1.00 spread
    
    recommendations = calculator.get_lot_size_recommendations(
        capital=capital,
        risk_percent=risk_percent,
        stop_loss_points=stop_loss_points,
        spread_points=spread_points
    )
    
    print(f"\n💵 Capital: ${capital:,.2f}")
    print(f"⚠️ Risk per trade: {risk_percent}% = ${recommendations['risk_amount']:.2f}")
    print(f"🎯 Stop loss: {stop_loss_points} points (${stop_loss_points * 0.01:.2f})")
    print(f"📊 Spread: {spread_points} points (${spread_points * 0.01:.2f})")
    
    print("\n📋 LOT SIZE RECOMMENDATIONS:")
    print("-" * 80)
    print(f"{'Lot Size':<12} {'Position Risk':<15} {'Total Costs':<15} {'Cost % of Risk':<18} {'Net Profit':<15} {'R:R':<10} {'Viable':<10}")
    print("-" * 80)
    
    for lot_name, data in recommendations['recommendations'].items():
        viable = "✅" if data['viable'] else "❌"
        print(f"{data['lot_size']:<12.2f} "
              f"${data['position_risk']:<14.2f} "
              f"${data['total_costs']:<14.2f} "
              f"{data['costs_as_risk_percent']:<17.1f}% "
              f"${data['net_profit']:<14.2f} "
              f"{data['realistic_rr']:<10.2f} "
              f"{viable:<10}")
    
    print("-" * 80)
    
    # Reality check
    print("\n" + "="*80)
    print("⚠️ REALITY CHECK")
    print("="*80)
    
    # Calculate how much you need to win to break even after commissions
    print("\n📊 BREAK-EVEN ANALYSIS:")
    print("   To make $1 profit AFTER commissions:")
    print("   - You need to win $1 + commission costs")
    print("   - With 0.01 lots: Commission = $0.90 round trip")
    print("   - So you need $1.90 gross profit to keep $1 net")
    print("   - That's 47.5% of your profit eaten by commissions!")
    
    print("\n📊 SCALPING REALITY:")
    print("   Average scalp target: 200-400 points ($2-$4)")
    print("   Commission on 0.01 lots: $0.90")
    print("   Spread cost: ~$1.00")
    print("   Total costs: ~$1.90")
    print("   ")
    print("   If target is $2.00 profit:")
    print("   - Net profit after costs: $0.10 (5% of target!)")
    print("   - Cost eats 95% of profit!")
    print("   ")
    print("   If target is $4.00 profit:")
    print("   - Net profit after costs: $2.10 (52.5% of target)")
    print("   - Cost eats 47.5% of profit")
    
    print("\n" + "="*80)
    print("💡 CONCLUSION")
    print("="*80)
    print("""
With FTMO's $45/lot commission structure:

1. MINIMUM viable scalp target: 400+ points ($4+)
   - Below this, commissions eat too much profit
   
2. OPTIMAL lot size for scalping: 0.01-0.05 lots
   - Keeps position risk manageable
   - Costs as % of risk: 10-30%
   
3. REQUIRED win rate increases dramatically:
   - Without costs: 55% win rate profitable
   - With costs: Need 60-65% win rate minimum
   
4. R:R must be REALISTIC:
   - Apparent R:R: 1:2 might look good
   - After costs: Actually 1:1.3 or worse
   - Always calculate NET R:R, not gross!

5. Strategy implication:
   - Target LARGER moves (400-800 points)
   - Avoid tiny scalps (100-200 points)
   - Wait for HIGH-probability setups only
""")
    
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
