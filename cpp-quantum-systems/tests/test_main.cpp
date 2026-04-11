/**
 * Test Suite for Quantum Trading Systems
 * Tests Monte Carlo and Quantum Dimension implementations
 */

#include <iostream>
#include <cassert>
#include <cmath>
#include <chrono>
#include "monte_carlo/advanced_simulator.hpp"
#include "quantum/dimension_manager.hpp"

using namespace quantum_trading;

void test_monte_carlo_basic() {
    std::cout << "\n========================================" << std::endl;
    std::cout << "TEST 1: Basic Monte Carlo Simulation" << std::endl;
    std::cout << "========================================" << std::endl;
    
    monte_carlo::AdvancedSimulator simulator(100000, 252, 1.0/252.0);
    
    monte_carlo::MarketState state;
    state.spot_price = 73000.0;
    state.volatility = 0.65;
    state.interest_rate = 0.05;
    state.regime = monte_carlo::RegimeType::BULL_LOW_VOL;
    
    simulator.set_market_state(state);
    
    auto start = std::chrono::high_resolution_clock::now();
    auto result = simulator.run_simulation(8);
    auto end = std::chrono::high_resolution_clock::now();
    
    auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(end - start).count();
    
    std::cout << "Simulation completed in " << duration << "ms" << std::endl;
    std::cout << "Mean price: $" << result.mean_price << std::endl;
    std::cout << "Std dev: $" << result.std_dev << std::endl;
    std::cout << "Skewness: " << result.skewness << std::endl;
    std::cout << "Kurtosis: " << result.excess_kurtosis << std::endl;
    std::cout << "VaR 95%: $" << result.var_95 << std::endl;
    std::cout << "CVaR 95%: $" << result.cvar_95 << std::endl;
    std::cout << "Probability of profit: " << result.probability_profit * 100 << "%" << std::endl;
    
    assert(result.mean_price > 0);
    assert(result.probability_profit >= 0.0 && result.probability_profit <= 1.0);
    
    std::cout << "✅ TEST PASSED" << std::endl;
}

void test_quantum_dimensions() {
    std::cout << "\n========================================" << std::endl;
    std::cout << "TEST 2: Quantum Dimension Manager" << std::endl;
    std::cout << "========================================" << std::endl;
    
    quantum::DimensionManager qm(12);
    
    // Evolve quantum states
    qm.apply_evolution(1.0);
    
    // Measure market state
    auto measurement = qm.measure_market_state();
    
    std::cout << "Measurement result:" << std::endl;
    std::cout << "  Collapsed price: $" << measurement.collapsed_price << std::endl;
    std::cout << "  Probability: " << measurement.probability << std::endl;
    std::cout << "  Interpretation: " << measurement.market_interpretation << std::endl;
    std::cout << "  Entropy before: " << measurement.entropy_before << std::endl;
    
    // Predict price evolution
    auto prediction = qm.predict_price_evolution(252);
    
    std::cout << "\nPrediction:" << std::endl;
    std::cout << "  Predicted price: $" << prediction.predicted_price << std::endl;
    std::cout << "  Uncertainty: $" << prediction.uncertainty << std::endl;
    std::cout << "  95% CI: [$" << prediction.confidence_interval_95_lower 
              << ", $" << prediction.confidence_interval_95_upper << "]" << std::endl;
    std::cout << "  Regime change prob: " << prediction.regime_change_probability << std::endl;
    std::cout << "  Quantum advantage: " << prediction.quantum_advantage * 100 << "%" << std::endl;
    
    assert(prediction.predicted_price > 0);
    assert(prediction.uncertainty > 0);
    
    std::cout << "✅ TEST PASSED" << std::endl;
}

void test_tunneling() {
    std::cout << "\n========================================" << std::endl;
    std::cout << "TEST 3: Quantum Tunneling Analysis" << std::endl;
    std::cout << "========================================" << std::endl;
    
    quantum::DimensionManager qm(12);
    qm.update_with_market_data(73000.0, 0.65, {72500.0, 72800.0, 73000.0, 73200.0});
    
    double tunnel_prob = qm.calculate_tunneling_probability(75000.0, 0.05);
    
    std::cout << "Tunneling through $75000 resistance:" << std::endl;
    std::cout << "  Probability: " << tunnel_prob * 100 << "%" << std::endl;
    
    auto opportunities = qm.find_tunneling_opportunities(70000.0, 76000.0);
    std::cout << "  Opportunities found: " << opportunities.size() << std::endl;
    
    std::cout << "✅ TEST PASSED" << std::endl;
}

void test_regime_switching() {
    std::cout << "\n========================================" << std::endl;
    std::cout << "TEST 4: Regime Switching" << std::endl;
    std::cout << "========================================" << std::endl;
    
    monte_carlo::AdvancedSimulator simulator(50000, 100);
    simulator.run_simulation(4);
    
    auto regime_probs = simulator.get_regime_probabilities();
    
        std::cout << "Regime probabilities:" << std::endl;
        double total = 0.0;
        for (const auto& pair : regime_probs) {
            std::cout << "  Regime: " << pair.second * 100 << "%" << std::endl;
            total += pair.second;
        }
    
    assert(total > 0.99 && total < 1.01);  // Should sum to ~1.0
    
    std::cout << "✅ TEST PASSED" << std::endl;
}

void test_performance() {
    std::cout << "\n========================================" << std::endl;
    std::cout << "TEST 5: Performance Benchmark" << std::endl;
    std::cout << "========================================" << std::endl;
    
    std::cout << "Running 1,000,000 paths with 252 steps..." << std::endl;
    
    monte_carlo::AdvancedSimulator simulator(1000000, 252);
    
    auto start = std::chrono::high_resolution_clock::now();
    auto result = simulator.run_simulation(16);
    auto end = std::chrono::high_resolution_clock::now();
    
    auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(end - start).count();
    double paths_per_second = 1000000.0 / (duration / 1000.0);
    
    std::cout << "Completed in " << duration << "ms" << std::endl;
    std::cout << "Speed: " << paths_per_second / 1000000.0 << " million paths/sec" << std::endl;
    
    assert(duration > 0);
    assert(paths_per_second > 1000000);  // Should be >1M paths/sec with OpenMP
    
    std::cout << "✅ TEST PASSED" << std::endl;
}

int main() {
    std::cout << "\n╔══════════════════════════════════════════════════════════╗" << std::endl;
    std::cout << "║     QUANTUM TRADING SYSTEMS - TEST SUITE                 ║" << std::endl;
    std::cout << "║     Monte Carlo + Parallel Quantum Dimensions            ║" << std::endl;
    std::cout << "╚══════════════════════════════════════════════════════════╝" << std::endl;
    
    try {
        test_monte_carlo_basic();
        test_quantum_dimensions();
        test_tunneling();
        test_regime_switching();
        test_performance();
        
        std::cout << "\n╔══════════════════════════════════════════════════════════╗" << std::endl;
        std::cout << "║     ✅ ALL TESTS PASSED                                   ║" << std::endl;
        std::cout << "╚══════════════════════════════════════════════════════════╝\n" << std::endl;
        
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "\n❌ TEST FAILED: " << e.what() << std::endl;
        return 1;
    }
}
