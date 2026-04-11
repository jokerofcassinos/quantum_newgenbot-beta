#ifndef DIMENSION_MANAGER_HPP
#define DIMENSION_MANAGER_HPP

/**
 * Parallel Quantum Dimensions Manager
 * 
 * Implements a multi-dimensional quantum system where each dimension
 * represents a parallel market state. Uses quantum computing principles:
 * 
 * 1. Superposition: Market exists in ALL possible states simultaneously
 * 2. Entanglement: Correlations between market variables are non-local
 * 3. Interference: Price patterns interfere constructively/destructively
 * 4. Tunneling: Market can "tunnel" through support/resistance levels
 * 5. Measurement Collapse: Observation collapses to classical state
 * 6. Decoherence: Quantum states decay to classical over time
 * 
 * Each quantum dimension tracks:
 * - Wave function evolution
 * - Probability amplitudes
 * - Phase relationships
 * - Entanglement entropy
 * - Decoherence rates
 * 
 * Applications:
 * - Ultra-precise price prediction
 * - Regime detection before classical signals
 * - Anomaly detection (market manipulation)
 * - Optimal entry/exit timing
 * - Risk assessment with quantum uncertainty
 */

#include <vector>
#include <complex>
#include <memory>
#include <string>
#include <functional>
#include <unordered_map>
#include <tuple>
#include <cmath>
#include <algorithm>
#include <omp.h>

namespace quantum_trading {
namespace quantum {

// ============================================================
// QUANTUM STATE DEFINITIONS
// ============================================================

struct QuantumState {
    std::vector<std::complex<double>> amplitudes;
    double normalization;
    double entropy;           // Von Neumann entropy
    double coherence;         // Measure of quantum coherence
    double decoherence_rate;  // Rate of quantum-to-classical decay
    std::string dimension_id;
    int dimension_index;
};

struct QuantumDimension {
    int id;
    std::string name;
    std::string description;
    
    // Dimension parameters
    double energy_level;       // "Energy" of this dimension
    double frequency;          // Oscillation frequency
    double damping;            // Damping coefficient
    double coupling_strength;  // Coupling to other dimensions
    
    // Market interpretation
    std::string market_regime; // What regime this dimension represents
    double probability_weight; // Weight in superposition
    double phase_shift;        // Phase relative to base dimension
    
    // State vectors
    QuantumState current_state;
    QuantumState initial_state;
    
    // Entanglement
    std::vector<std::pair<int, double>> entangled_dimensions;
    double entanglement_entropy;
    
    // Evolution
    std::function<void(QuantumState&, double)> evolution_operator;
    
    // Metrics
    double prediction_accuracy;
    double regime_detection_rate;
    double anomaly_score;
};

struct QuantumMeasurement {
    int collapsed_dimension;
    double collapsed_price;
    double probability;
    double confidence;
    std::vector<double> all_probabilities;
    double entropy_before;
    double entropy_after;
    std::string market_interpretation;
};

struct QuantumPrediction {
    double predicted_price;
    double uncertainty;
    double confidence_interval_95_lower;
    double confidence_interval_95_upper;
    double regime_change_probability;
    double anomaly_probability;
    std::vector<std::pair<double, double>> price_distribution;  // (price, probability)
    std::vector<std::string> possible_regimes;
    std::vector<double> regime_probabilities;
    double quantum_advantage;  // Improvement over classical prediction
};

// ============================================================
// PARALLEL QUANTUM DIMENSIONS MANAGER
// ============================================================

class DimensionManager {
public:
    DimensionManager(int num_dimensions = 12);
    ~DimensionManager();
    
    // Dimension management
    void initialize_dimensions();
    void add_dimension(const std::string& name, const std::string& regime, double energy);
    void remove_dimension(int dimension_id);
    
    // Quantum operations
    void create_superposition();
    void entangle_dimensions(int dim1, int dim2, double strength);
    void apply_evolution(double time_step);
    void induce_decoherence(double rate);
    
    // Market analysis
    QuantumMeasurement measure_market_state();
    QuantumPrediction predict_price_evolution(double time_horizon = 252);
    QuantumPrediction detect_regime_change();
    QuantumPrediction detect_anomalies();
    
    // Interference patterns
    std::vector<double> calculate_interference_pattern();
    std::vector<double> detect_constructive_interference();
    std::vector<double> detect_destructive_interference();
    
    // Tunneling analysis
    double calculate_tunneling_probability(double barrier_height, double barrier_width);
    std::vector<double> find_tunneling_opportunities(double support_level, double resistance_level);
    
    // State visualization
    std::vector<std::pair<double, double>> get_probability_distribution();
    std::vector<std::pair<double, double>> get_phase_distribution();
    
    // Advanced quantum metrics
    double calculate_von_neumann_entropy();
    double calculate_concurrence();  // Entanglement measure
    double calculate_fidelity(const QuantumState& state1, const QuantumState& state2);
    
    // Integration with market data
    void update_with_market_data(double current_price, double volatility,
                                const std::vector<double>& recent_prices);
    void calibrate_to_historical(const std::vector<double>& prices,
                               const std::vector<double>& volatilities);
    
    // Parallel dimension evolution
    void evolve_dimensions_parallel(double dt, int num_threads = -1);
    
    // Get quantum state
    const std::vector<QuantumDimension>& get_dimensions() const { return dimensions_; }
    const QuantumState& get_superposition_state() const { return superposition_state_; }

private:
    // Core quantum operations
    void normalize_state(QuantumState& state);
    double calculate_entropy(const QuantumState& state);
    std::complex<double> apply_hamiltonian(const QuantumState& state, int index);
    
    // Evolution operators for different dimensions
    void evolve_bull_market(QuantumState& state, double dt);
    void evolve_bear_market(QuantumState& state, double dt);
    void evolve_choppy_market(QuantumState& state, double dt);
    void evolve_crash_market(QuantumState& state, double dt);
    
    // Interference calculations
    std::complex<double> calculate_wave_interference(int dim1, int dim2);
    double calculate_phase_difference(int dim1, int dim2);
    
    // Measurement collapse
    int collapse_to_dimension(const std::vector<double>& probabilities);
    double sample_from_distribution(const std::vector<double>& probs);
    
    // Member variables
    std::vector<QuantumDimension> dimensions_;
    QuantumState superposition_state_;
    
    int num_dimensions_;
    int num_basis_states_;
    double total_energy_;
    double planck_constant_;  // Effective "h-bar" for market quantum system
    
    // Market parameters
    double current_price_;
    double current_volatility_;
    double risk_free_rate_;
    
    // Decoherence parameters
    double decoherence_rate_;
    double thermal_bath_coupling_;
    
    // Calibration
    bool is_calibrated_;
    std::vector<double> historical_means_;
    std::vector<double> historical_vols_;
    
    // Parallel processing
    int num_threads_;
};

} // namespace quantum
} // namespace quantum_trading

#endif // DIMENSION_MANAGER_HPP
