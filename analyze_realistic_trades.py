"""
Realistic Trade Analysis with FTMO Commissions
CEO: Qwen Code | Created: 2026-04-10
"""

from src.risk.ftmo_commission_calculator import FTMOCommissionCalculator

def main():
    print("\n" + "="*80)
    print("📊 FOREX QUANTUM BOT - REALISTIC TRADE ANALYSIS")
    print("   BTCUSD Scalping with FTMO Commissions")
    print("="*80)
    
    calc = FTMOCommissionCalculator()
    
    # Scenario 1: Tight scalp (BAD idea with commissions)
    print("\n\n" + "="*80)
    print("❌ SCENARIO 1: Tight Scalp (100 point target)")
    print("="*80)
    
    analysis1 = calc.analyze_trade(
        volume=0.10,
        entry_price=73000.00,
        stop_loss_price=72950.00,    # 50 points stop
        take_profit_price=73100.00,  # 100 points target
        spread_points=100
    )
    calc.print_analysis(analysis1)
    
    # Scenario 2: Normal scalp (MARGINAL)
    print("\n\n" + "="*80)
    print("⚠️ SCENARIO 2: Normal Scalp (300 point target)")
    print("="*80)
    
    analysis2 = calc.analyze_trade(
        volume=0.10,
        entry_price=73000.00,
        stop_loss_price=72850.00,    # 150 points stop
        take_profit_price=73300.00,  # 300 points target
        spread_points=100
    )
    calc.print_analysis(analysis2)
    
    # Scenario 3: Good scalp (VIABLE)
    print("\n\n" + "="*80)
    print("✅ SCENARIO 3: Good Scalp (600 point target)")
    print("="*80)
    
    analysis3 = calc.analyze_trade(
        volume=0.10,
        entry_price=73000.00,
        stop_loss_price=72700.00,    # 300 points stop
        take_profit_price=73600.00,  # 600 points target
        spread_points=100
    )
    calc.print_analysis(analysis3)
    
    # Scenario 4: Swing trade (OPTIMAL)
    print("\n\n" + "="*80)
    print("🎯 SCENARIO 4: Swing Trade (1500 point target)")
    print("="*80)
    
    analysis4 = calc.analyze_trade(
        volume=0.10,
        entry_price=73000.00,
        stop_loss_price=72500.00,    # 500 points stop
        take_profit_price=74500.00,  # 1500 points target
        spread_points=100
    )
    calc.print_analysis(analysis4)
    
    # Comparison table
    print("\n\n" + "="*80)
    print("📋 COMPARISON TABLE")
    print("="*80)
    
    print(f"\n{'Scenario':<20} {'Gross R:R':<12} {'Net R:R':<12} {'Costs':<12} {'Cost %':<12} {'Viable':<10}")
    print("-" * 80)
    
    scenarios = [
        ("Tight Scalp", analysis1),
        ("Normal Scalp", analysis2),
        ("Good Scalp", analysis3),
        ("Swing Trade", analysis4),
    ]
    
    for name, analysis in scenarios:
        viable = "✅" if analysis['net_rr'] >= 1.5 else "❌"
        print(f"{name:<20} "
              f"1:{analysis['gross_rr']:<10.2f} "
              f"1:{analysis['net_rr']:<10.2f} "
              f"${analysis['total_costs']:<11.2f} "
              f"{analysis['costs_eat_profit_percent']:<11.1f}% "
              f"{viable:<10}")
    
    print("\n" + "="*80)
    print("💡 KEY INSIGHTS")
    print("="*80)
    print("""
1. Commissions are FIXED ($45/lot/side) - can't avoid them
2. Spread is ~100 points ($1.00) on BTCUSD
3. Total costs per trade: ~$10 for 0.10 lots

4. IMPACT ON R:R:
   - Tight scalp (1:2 gross) → 0.33 net (LOSING strategy!)
   - Normal scalp (1:2 gross) → 1.09 net (BARELY viable)
   - Good scalp (1:2 gross) → 1.38 net (ACCEPTABLE)
   - Swing trade (1:3 gross) → 2.26 net (EXCELLENT)

5. CONCLUSION FOR STRATEGY:
   - AVOID: Tight scalps (<200 points)
   - MINIMIZE: Normal scalps (200-400 points)  
   - FOCUS ON: Good scalps (400-800 points)
   - IDEAL: Swing trades (1000+ points)

6. With $100K account and 0.5% risk ($500):
   - Need minimum 400+ point targets
   - Optimal: 800-1500 point targets
   - This means HOLDING trades longer (5-30 min vs 1-5 min)
""")
    
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
