"""
Complete Neural Audit System Demo
CEO: Qwen Code | Created: 2026-04-10

Demonstrates:
1. Neural Trade Auditor capturing complete state
2. Pattern Analyzer finding error patterns
3. Veto Orchestrator blocking bad trades
4. Complete feedback loop

Usage:
    python run_neural_audit_demo.py
"""

import sys
from pathlib import Path
import json
import numpy as np
from datetime import datetime, timezone

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.monitoring.neural_trade_auditor import NeuralTradeAuditor
from src.monitoring.trade_pattern_analyzer import TradePatternAnalyzer
from src.monitoring.veto_orchestrator import VetoOrchestrator


def create_sample_audit(
    ticket: int,
    regime: str,
    session: str,
    direction: str,
    rsi: float,
    pnl: float,
    consecutive_losses: int = 0,
    mtf_conflict: bool = False,
    velocity: float = 0.5,
) -> dict:
    """Create a sample neural audit for testing"""
    
    return {
        # Basic
        "ticket": ticket,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "symbol": "BTCUSD",
        "direction": direction,
        "entry_price": 73000.0,
        "stop_loss": 72700.0,
        "take_profit": 73600.0,
        "volume": 0.10,
        "strategy_name": "momentum_scalping",
        "signal_confidence": 0.75,
        
        # Market Regime
        "market_regime": {
            "regime_type": regime,
            "regime_confidence": 0.80,
            "trend_strength": 0.60,
            "trend_direction": "up" if direction == "BUY" else "down",
            "volatility_regime": "medium",
            "volatility_value": 200.0,
            "volume_regime": "normal",
            "volume_ratio": 1.0,
            "market_phase": "markup",
            "session": session,
            "session_volume_profile": 0.8,
        },
        
        # Multi-Timeframe
        "multi_timeframe": {
            "M1_trend": "up",
            "M5_trend": "up",
            "M15_trend": "up",
            "H1_trend": "up",
            "H4_trend": "neutral",
            "D1_trend": "neutral",
            "alignment_score": 0.5,
            "dominant_timeframe": "M5",
            "conflict_detected": mtf_conflict,
        },
        
        # Indicators
        "indicators": {
            "ema_9": 73050.0,
            "ema_21": 73000.0,
            "ema_50": 72900.0,
            "ema_200": 72000.0,
            "sma_20": 73020.0,
            "sma_50": 72950.0,
            "ema_9_21_cross": "bullish",
            "ema_21_50_cross": "bullish",
            "price_vs_ema_200": "above",
            "rsi_14": rsi,
            "rsi_regime": "oversold" if rsi < 30 else "overbought" if rsi > 70 else "neutral",
            "macd_line": 50.0,
            "macd_signal": 40.0,
            "macd_histogram": 10.0,
            "macd_cross": "bullish",
            "stochastic_k": 50.0,
            "stochastic_d": 45.0,
            "atr_14": 250.0,
            "atr_percentile": 50.0,
            "bollinger_upper": 73500.0,
            "bollinger_middle": 73000.0,
            "bollinger_lower": 72500.0,
            "bollinger_width": 1000.0,
            "price_vs_bollinger": "inside",
            "volume_current": 1000.0,
            "volume_avg_20": 1000.0,
            "volume_ratio": 1.0,
            "volume_trend": "stable",
            "obv_trend": "neutral",
        },
        
        # Price Action
        "price_action": {
            "current_price": 73000.0,
            "price_change_1h": 0.5,
            "price_change_4h": 1.0,
            "price_change_24h": 2.0,
            "nearest_support": 72500.0,
            "nearest_resistance": 73500.0,
            "distance_to_support_pct": 0.68,
            "distance_to_resistance_pct": 0.68,
            "current_candle_type": "bullish",
            "candle_body_size": 100.0,
            "candle_wick_ratio": 0.3,
            "engulfing_detected": False,
            "inside_bar_detected": False,
            "higher_highs": True,
            "higher_lows": True,
            "lower_highs": False,
            "lower_lows": False,
            "structure": "uptrend",
        },
        
        # Momentum
        "momentum": {
            "velocity": velocity,
            "acceleration": 0.1,
            "gravity": 0.3,
            "oscillation": 50.0,
            "volume_pressure": 0.5,
            "microstructure_score": 0.6,
            "momentum_divergence": False,
            "exhaustion_signals": [],
        },
        
        # Risk Context
        "risk_context": {
            "capital": 100000.0,
            "equity": 100000.0,
            "daily_pnl": 0.0,
            "daily_pnl_percent": 0.0,
            "total_pnl": 0.0,
            "total_pnl_percent": 0.0,
            "current_drawdown": 0.0,
            "max_drawdown": 0.0,
            "consecutive_wins": 0,
            "consecutive_losses": consecutive_losses,
            "daily_loss_used_percent": 0.0,
            "total_loss_used_percent": 0.0,
            "ftmo_daily_remaining": 5000.0,
            "ftmo_total_remaining": 10000.0,
        },
        
        # DNA State
        "dna_state": {
            "current_regime": "trending_bullish",
            "regime_confidence": 0.80,
            "active_strategy": "momentum_scalping",
            "strategy_weights": {"momentum": 0.6, "mean_reversion": 0.2, "breakout": 0.2},
            "risk_percent": 0.5,
            "min_rr_ratio": 1.5,
            "confidence_threshold": 0.65,
            "last_mutation_time": datetime.now(timezone.utc).isoformat(),
            "mutation_count": 10,
            "dna_memory_regimes": 5,
        },
        
        # Smart Order Manager
        "smart_order_manager": {
            "virtual_tp_original": 73600.0,
            "virtual_tp_current": 73500.0,
            "virtual_tp_adjustment_factor": 0.85,
            "virtual_tp_difficulty": "moderate",
            "dynamic_sl_original": 72700.0,
            "dynamic_sl_current": 72800.0,
            "breakeven_activated": False,
            "profit_targets_reached": [],
            "momentum_at_entry": {"velocity": 0.5},
        },
        
        # Outcome
        "exit_price": 73200.0 if pnl > 0 else 72800.0,
        "exit_timestamp": datetime.now(timezone.utc).isoformat(),
        "exit_reason": "take_profit" if pnl > 0 else "stop_loss",
        "gross_pnl": pnl + 19.0,
        "net_pnl": pnl,
        "duration_minutes": 15,
        "max_profit_reached": pnl + 50.0,
        "max_drawdown_reached": -20.0,
    }


def demo_neural_audit_system():
    """Complete demonstration of the neural audit system"""
    
    print("\n" + "="*80)
    print("🧠 FOREX QUANTUM BOT - NEURAL AUDIT SYSTEM DEMO")
    print("="*80)
    
    # Step 1: Create sample trades
    print("\n📊 Step 1: Creating sample trade audits...")
    
    auditor = NeuralTradeAuditor()
    
    # Create various trades with different conditions
    sample_trades = [
        # Good trades
        {"ticket": 1000, "regime": "trending_bullish", "session": "ny_overlap", "direction": "BUY", "rsi": 55, "pnl": 150, "consecutive_losses": 0},
        {"ticket": 1001, "regime": "trending_bullish", "session": "london", "direction": "BUY", "rsi": 50, "pnl": 200, "consecutive_losses": 0},
        {"ticket": 1002, "regime": "ranging", "session": "ny_overlap", "direction": "SELL", "rsi": 65, "pnl": 100, "consecutive_losses": 0},
        
        # Bad trades - wrong regime
        {"ticket": 1003, "regime": "crashing", "session": "ny", "direction": "BUY", "rsi": 25, "pnl": -500, "consecutive_losses": 0},
        {"ticket": 1004, "regime": "crashing", "session": "ny", "direction": "BUY", "rsi": 20, "pnl": -600, "consecutive_losses": 1},
        {"ticket": 1005, "regime": "extreme_volatility", "session": "ny", "direction": "SELL", "rsi": 80, "pnl": -700, "consecutive_losses": 2},
        
        # Bad trades - overtrading
        {"ticket": 1006, "regime": "trending_bearish", "session": "asian", "direction": "SELL", "rsi": 30, "pnl": -200, "consecutive_losses": 3},
        {"ticket": 1007, "regime": "trending_bearish", "session": "asian", "direction": "SELL", "rsi": 28, "pnl": -300, "consecutive_losses": 4},
        
        # Bad trades - MTF conflict
        {"ticket": 1008, "regime": "ranging", "session": "ny_overlap", "direction": "BUY", "rsi": 60, "pnl": -150, "consecutive_losses": 0, "mtf_conflict": True},
        {"ticket": 1009, "regime": "ranging", "session": "ny_overlap", "direction": "BUY", "rsi": 62, "pnl": -180, "consecutive_losses": 1, "mtf_conflict": True},
        
        # Mixed
        {"ticket": 1010, "regime": "trending_bullish", "session": "ny_overlap", "direction": "BUY", "rsi": 55, "pnl": 180, "consecutive_losses": 0},
        {"ticket": 1011, "regime": "ranging", "session": "london", "direction": "SELL", "rsi": 70, "pnl": -100, "consecutive_losses": 0},
        {"ticket": 1012, "regime": "trending_bullish", "session": "ny_overlap", "direction": "BUY", "rsi": 50, "pnl": 250, "consecutive_losses": 0},
    ]
    
    print(f"   Creating {len(sample_trades)} sample trades...")
    
    for trade_data in sample_trades:
        audit_data = create_sample_audit(**trade_data)
        
        # Capture entry
        auditor.capture_entry_state(
            ticket=trade_data["ticket"],
            direction=trade_data["direction"],
            entry_price=73000.0,
            stop_loss=72700.0,
            take_profit=73600.0,
            volume=0.10,
            strategy_name="momentum_scalping",
            signal_confidence=0.75,
            market_regime=audit_data["market_regime"],
            multi_timeframe=audit_data["multi_timeframe"],
            indicators=audit_data["indicators"],
            price_action=audit_data["price_action"],
            momentum=audit_data["momentum"],
            risk_context=audit_data["risk_context"],
            dna_state=audit_data["dna_state"],
            smart_order_manager=audit_data["smart_order_manager"],
        )
        
        # Capture exit
        auditor.capture_exit_state(
            ticket=trade_data["ticket"],
            exit_price=audit_data["exit_price"],
            exit_reason=audit_data["exit_reason"],
            gross_pnl=audit_data["gross_pnl"],
            net_pnl=audit_data["net_pnl"],
            duration_minutes=audit_data["duration_minutes"],
            max_profit_reached=audit_data["max_profit_reached"],
            max_drawdown_reached=audit_data["max_drawdown_reached"],
        )
    
    print(f"   ✅ {len(sample_trades)} trade audits captured and saved")
    
    # Step 2: Analyze patterns
    print("\n🔬 Step 2: Analyzing trade patterns...")
    
    analyzer = TradePatternAnalyzer(auditor)
    analysis_results = analyzer.analyze_all()
    
    # Save veto rules
    analyzer.save_veto_rules()
    
    # Step 3: Test veto system
    print("\n🛡️ Step 3: Testing Veto Orchestrator...")
    
    veto_orchestrator = VetoOrchestrator()
    
    # Test various trades
    test_trades = [
        {"name": "Good trade in bullish regime", "regime": "trending_bullish", "session": "ny_overlap", "direction": "BUY", "consecutive_losses": 0, "mtf_conflict": False},
        {"name": "Trade in crashing regime", "regime": "crashing", "session": "ny", "direction": "BUY", "consecutive_losses": 0, "mtf_conflict": False},
        {"name": "Trade after 3+ losses", "regime": "trending_bullish", "session": "ny_overlap", "direction": "SELL", "consecutive_losses": 3, "mtf_conflict": False},
        {"name": "Trade with MTF conflict", "regime": "ranging", "session": "ny_overlap", "direction": "BUY", "consecutive_losses": 0, "mtf_conflict": True},
    ]
    
    print()
    for test_trade in test_trades:
        context = create_sample_audit(
            ticket=9999,
            regime=test_trade["regime"],
            session=test_trade["session"],
            direction=test_trade["direction"],
            rsi=55,
            pnl=0,
            consecutive_losses=test_trade["consecutive_losses"],
            mtf_conflict=test_trade["mtf_conflict"],
        )
        
        result = veto_orchestrator.check_trade(context)
        
        status = "✅ APPROVED" if result.approved else f"🚫 VETOED ({result.severity})"
        print(f"   {test_trade['name']}:")
        print(f"      {status}")
        if result.reason:
            print(f"      Reason: {result.reason}")
        print()
    
    # Summary
    stats = veto_orchestrator.get_stats()
    
    print("\n" + "="*80)
    print("📊 NEURAL AUDIT SYSTEM SUMMARY")
    print("="*80)
    print(f"\n✅ Trade Audits Created: {len(sample_trades)}")
    print(f"🔬 Error Patterns Found: {len(analyzer.error_patterns)}")
    print(f"🛡️ Veto Rules Generated: {len(veto_orchestrator.veto_rules.get('rules', []))}")
    print(f"📋 Veto Checks: {stats['total_checks']}")
    print(f"🚫 Trades Vetoed: {stats['total_vetoes']}")
    print(f"📊 Veto Rate: {stats['veto_rate']:.1f}%")
    
    print(f"\n🎯 Top Veto Rules:")
    for rule in veto_orchestrator.veto_rules.get("rules", [])[:5]:
        print(f"   [{rule['severity'].upper()}] {rule['name']} (confidence: {rule['confidence']:.2f})")
    
    print("\n" + "="*80)
    print("✅ NEURAL AUDIT SYSTEM DEMO COMPLETE")
    print("="*80)
    print(f"""
📁 Audit files saved to: data/trade-audits/
📋 Veto rules saved to: config/veto_rules.json

Next steps:
1. Run live trading with neural auditing enabled
2. After 100+ trades, run pattern analysis
3. Update veto rules
4. Bot becomes smarter with every trade!
""")
    print("="*80 + "\n")


if __name__ == "__main__":
    try:
        demo_neural_audit_system()
    except KeyboardInterrupt:
        print("\n\n⚠️ Demo interrupted")
    except Exception as e:
        print(f"\n\n❌ Demo error: {e}")
        import traceback
        traceback.print_exc()
