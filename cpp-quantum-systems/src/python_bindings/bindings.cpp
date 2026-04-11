/**
 * Python bindings for Quantum Trading Systems
 * Uses pybind11 to expose C++ classes to Python
 * 
 * Usage:
 *   import quantum_trading
 *   sim = quantum_trading.AdvancedSimulator(100000, 252)
 *   result = sim.run_simulation()
 *   print(f"Mean: ${result.mean_price:.2f}")
 */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/numpy.h>
#include "monte_carlo/advanced_simulator.hpp"
#include "quantum/dimension_manager.hpp"

namespace py = pybind11;
using namespace quantum_trading;

PYBIND11_MODULE(quantum_trading, m) {
    m.doc() = "Quantum Trading Systems - Monte Carlo & Parallel Quantum Dimensions";
    
    // ============================================================
    // MONTE CARLO BINDINGS
    // ============================================================
    
    py::class_<monte_carlo::MarketState>(m, "MarketState")
        .def(py::init<>())
        .def_readwrite("spot_price", &monte_carlo::MarketState::spot_price)
        .def_readwrite("volatility", &monte_carlo::MarketState::volatility)
        .def_readwrite("interest_rate", &monte_carlo::MarketState::interest_rate)
        .def_readwrite("dividend_yield", &monte_carlo::MarketState::dividend_yield)
        .def_readwrite("jump_intensity", &monte_carlo::MarketState::jump_intensity)
        .def_readwrite("jump_mean", &monte_carlo::MarketState::jump_mean)
        .def_readwrite("jump_vol", &monte_carlo::MarketState::jump_vol);
    
    py::class_<monte_carlo::SimulationResult>(m, "SimulationResult")
        .def(py::init<>())
        .def_readonly("mean_price", &monte_carlo::SimulationResult::mean_price)
        .def_readonly("median_price", &monte_carlo::SimulationResult::median_price)
        .def_readonly("std_dev", &monte_carlo::SimulationResult::std_dev)
        .def_readonly("skewness", &monte_carlo::SimulationResult::skewness)
        .def_readonly("excess_kurtosis", &monte_carlo::SimulationResult::excess_kurtosis)
        .def_readonly("var_95", &monte_carlo::SimulationResult::var_95)
        .def_readonly("var_99", &monte_carlo::SimulationResult::var_99)
        .def_readonly("cvar_95", &monte_carlo::SimulationResult::cvar_95)
        .def_readonly("cvar_99", &monte_carlo::SimulationResult::cvar_99)
        .def_readonly("max_price", &monte_carlo::SimulationResult::max_price)
        .def_readonly("min_price", &monte_carlo::SimulationResult::min_price)
        .def_readonly("probability_profit", &monte_carlo::SimulationResult::probability_profit)
        .def_readonly("probability_loss_greater_than_5pct", 
                     &monte_carlo::SimulationResult::probability_loss_greater_than_5pct)
        .def_readonly("final_prices", &monte_carlo::SimulationResult::final_prices);
    
    py::class_<monte_carlo::AdvancedSimulator>(m, "AdvancedSimulator")
        .def(py::init<int, int, double>(),
             py::arg("num_paths") = 1000000,
             py::arg("num_steps") = 252,
             py::arg("dt") = 1.0/252.0)
        .def("set_market_state", &monte_carlo::AdvancedSimulator::set_market_state)
        .def("run_simulation", &monte_carlo::AdvancedSimulator::run_simulation,
             py::arg("num_threads") = -1)
        .def("calculate_density", &monte_carlo::AdvancedSimulator::estimate_density,
             py::arg("grid_points") = 1000)
        .def("calculate_probability", &monte_carlo::AdvancedSimulator::calculate_probability)
        .def("get_regime_probabilities", &monte_carlo::AdvancedSimulator::get_regime_probabilities);
    
    // ============================================================
    // QUANTUM DIMENSIONS BINDINGS
    // ============================================================
    
    py::class_<quantum::QuantumMeasurement>(m, "QuantumMeasurement")
        .def(py::init<>())
        .def_readonly("collapsed_price", &quantum::QuantumMeasurement::collapsed_price)
        .def_readonly("probability", &quantum::QuantumMeasurement::probability)
        .def_readonly("confidence", &quantum::QuantumMeasurement::confidence)
        .def_readonly("market_interpretation", &quantum::QuantumMeasurement::market_interpretation)
        .def_readonly("entropy_before", &quantum::QuantumMeasurement::entropy_before)
        .def_readonly("entropy_after", &quantum::QuantumMeasurement::entropy_after);
    
    py::class_<quantum::QuantumPrediction>(m, "QuantumPrediction")
        .def(py::init<>())
        .def_readonly("predicted_price", &quantum::QuantumPrediction::predicted_price)
        .def_readonly("uncertainty", &quantum::QuantumPrediction::uncertainty)
        .def_readonly("confidence_interval_95_lower", 
                     &quantum::QuantumPrediction::confidence_interval_95_lower)
        .def_readonly("confidence_interval_95_upper",
                     &quantum::QuantumPrediction::confidence_interval_95_upper)
        .def_readonly("regime_change_probability",
                     &quantum::QuantumPrediction::regime_change_probability)
        .def_readonly("anomaly_probability",
                     &quantum::QuantumPrediction::anomaly_probability)
        .def_readonly("quantum_advantage",
                     &quantum::QuantumPrediction::quantum_advantage)
        .def_readonly("possible_regimes",
                     &quantum::QuantumPrediction::possible_regimes)
        .def_readonly("regime_probabilities",
                     &quantum::QuantumPrediction::regime_probabilities);
    
    py::class_<quantum::DimensionManager>(m, "DimensionManager")
        .def(py::init<int>(),
             py::arg("num_dimensions") = 12)
        .def("initialize_dimensions", &quantum::DimensionManager::initialize_dimensions)
        .def("apply_evolution", &quantum::DimensionManager::apply_evolution)
        .def("measure_market_state", &quantum::DimensionManager::measure_market_state)
        .def("predict_price_evolution", &quantum::DimensionManager::predict_price_evolution,
             py::arg("time_horizon") = 252)
        .def("detect_regime_change", &quantum::DimensionManager::detect_regime_change)
        .def("detect_anomalies", &quantum::DimensionManager::detect_anomalies)
        .def("calculate_tunneling_probability", 
             &quantum::DimensionManager::calculate_tunneling_probability)
        .def("find_tunneling_opportunities",
             &quantum::DimensionManager::find_tunneling_opportunities)
        .def("get_probability_distribution",
             &quantum::DimensionManager::get_probability_distribution)
        .def("calculate_von_neumann_entropy",
             &quantum::DimensionManager::calculate_von_neumann_entropy)
        .def("update_with_market_data",
             &quantum::DimensionManager::update_with_market_data)
        .def("calibrate_to_historical",
             &quantum::DimensionManager::calibrate_to_historical);
}
