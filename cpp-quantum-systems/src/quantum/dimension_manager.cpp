#include "quantum/dimension_manager.hpp"
#include <cmath>
#include <numeric>
#include <algorithm>
#include <iostream>
#include <thread>
#include <random>
#include <stdexcept>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

namespace quantum_trading {
namespace quantum {

// ============================================================
// CONSTRUCTOR AND INITIALIZATION
// ============================================================

DimensionManager::DimensionManager(int num_dimensions)
    : num_dimensions_(num_dimensions), num_basis_states_(256),
      total_energy_(0.0), planck_constant_(1.054571817e-34),
      current_price_(73000.0), current_volatility_(0.65),
      risk_free_rate_(0.05), decoherence_rate_(0.01),
      thermal_bath_coupling_(0.001), is_calibrated_(false),
      num_threads_(omp_get_max_threads()) {
    
    initialize_dimensions();
}

DimensionManager::~DimensionManager() {}

void DimensionManager::initialize_dimensions() {
    dimensions_.clear();
    
    // Create 12 parallel quantum dimensions representing different market regimes
    std::vector<std::tuple<std::string, std::string, double>> dimension_defs = {
        {"Bull-LowVol", "BULL_LOW_VOL", 1.0},
        {"Bull-HighVol", "BULL_HIGH_VOL", 1.2},
        {"Bear-LowVol", "BEAR_LOW_VOL", 0.9},
        {"Bear-HighVol", "BEAR_HIGH_VOL", 1.5},
        {"Choppy-Narrow", "CHOPPY_NARROW", 0.8},
        {"Choppy-Wide", "CHOPPY_WIDE", 1.1},
        {"Trend-Up", "TREND_UP", 1.0},
        {"Trend-Down", "TREND_DOWN", 1.0},
        {"MeanReversion", "MEAN_REVERSION", 0.95},
        {"Momentum", "MOMENTUM", 1.15},
        {"Crash", "CRASH", 2.0},
        {"BlackSwan", "BLACK_SWAN", 2.5}
    };
    
    for (int i = 0; i < num_dimensions_ && i < (int)dimension_defs.size(); ++i) {
        auto [name, regime, energy] = dimension_defs[i];
        
        QuantumDimension dim;
        dim.id = i;
        dim.name = name;
        dim.description = "Quantum dimension: " + name;
        dim.energy_level = energy;
        dim.frequency = energy * 2.0 * M_PI;
        dim.damping = 0.01 * energy;
        dim.coupling_strength = 0.1;
        dim.market_regime = regime;
        dim.probability_weight = 1.0 / num_dimensions_;
        dim.phase_shift = i * 2.0 * M_PI / num_dimensions_;
        
        // Initialize quantum state
        dim.current_state.amplitudes.resize(num_basis_states_);
        dim.current_state.normalization = 0.0;
        dim.current_state.entropy = 0.0;
        dim.current_state.coherence = 1.0;
        dim.current_state.decoherence_rate = decoherence_rate_;
        dim.current_state.dimension_id = name;
        dim.current_state.dimension_index = i;
        
        // Gaussian wave packet initialization
        double center = num_basis_states_ / 2.0;
        double sigma = num_basis_states_ / 8.0;
        
        for (int j = 0; j < num_basis_states_; ++j) {
            double x = j - center;
            double amplitude = std::exp(-x * x / (4 * sigma * sigma));
            double phase = dim.phase_shift + dim.frequency * j / num_basis_states_;
            dim.current_state.amplitudes[j] = std::complex<double>(
                amplitude * std::cos(phase),
                amplitude * std::sin(phase)
            );
        }
        
        normalize_state(dim.current_state);
        dim.initial_state = dim.current_state;
        dim.entanglement_entropy = 0.0;
        dim.prediction_accuracy = 0.0;
        dim.regime_detection_rate = 0.0;
        dim.anomaly_score = 0.0;
        
        dimensions_.push_back(dim);
        total_energy_ += energy;
    }
    
    // Initialize superposition state
    superposition_state_.amplitudes.resize(num_basis_states_);
    create_superposition();
}

// ============================================================
// QUANTUM OPERATIONS
// ============================================================

void DimensionManager::create_superposition() {
    // Create equal superposition of all dimensions
    for (int i = 0; i < num_basis_states_; ++i) {
        std::complex<double> amp(0.0, 0.0);
        
        for (const auto& dim : dimensions_) {
            amp += std::sqrt(dim.probability_weight) * dim.current_state.amplitudes[i];
        }
        
        superposition_state_.amplitudes[i] = amp;
    }
    
    normalize_state(superposition_state_);
    superposition_state_.entropy = calculate_entropy(superposition_state_);
    superposition_state_.coherence = 1.0;
}

void DimensionManager::entangle_dimensions(int dim1, int dim2, double strength) {
    if (dim1 < 0 || dim1 >= num_dimensions_ || dim2 < 0 || dim2 >= num_dimensions_) {
        return;
    }
    
    dimensions_[dim1].entangled_dimensions.push_back({dim2, strength});
    dimensions_[dim2].entangled_dimensions.push_back({dim1, strength});
    
    // Calculate entanglement entropy
    double entropy = -strength * std::log(strength);
    dimensions_[dim1].entanglement_entropy = entropy;
    dimensions_[dim2].entanglement_entropy = entropy;
    
    // Apply entanglement operation to states
    for (int i = 0; i < num_basis_states_; ++i) {
        std::complex<double> psi1 = dimensions_[dim1].current_state.amplitudes[i];
        std::complex<double> psi2 = dimensions_[dim2].current_state.amplitudes[i];
        
        // Bell state-like operation
        dimensions_[dim1].current_state.amplitudes[i] = (psi1 + psi2) / std::sqrt(2.0);
        dimensions_[dim2].current_state.amplitudes[i] = (psi1 - psi2) / std::sqrt(2.0);
    }
    
    normalize_state(dimensions_[dim1].current_state);
    normalize_state(dimensions_[dim2].current_state);
}

void DimensionManager::apply_evolution(double time_step) {
    evolve_dimensions_parallel(time_step);
    
    // Update superposition
    create_superposition();
    
    // Calculate decoherence
    induce_decoherence(decoherence_rate_ * time_step);
}

void DimensionManager::induce_decoherence(double rate) {
    for (auto& dim : dimensions_) {
        dim.current_state.coherence *= std::exp(-rate);
        dim.current_state.decoherence_rate = rate;
        
        // Mix with maximally mixed state
        for (int i = 0; i < num_basis_states_; ++i) {
            double mixed = 1.0 / num_basis_states_;
            double quantum = std::norm(dim.current_state.amplitudes[i]);
            double new_prob = (1.0 - dim.current_state.coherence) * mixed + 
                            dim.current_state.coherence * quantum;
            dim.current_state.amplitudes[i] = std::complex<double>(std::sqrt(new_prob), 0.0);
        }
        
        normalize_state(dim.current_state);
    }
}

// ============================================================
// MARKET ANALYSIS AND MEASUREMENT
// ============================================================

QuantumMeasurement DimensionManager::measure_market_state() {
    QuantumMeasurement measurement;
    
    // Calculate probabilities from superposition
    std::vector<double> probs(num_basis_states_);
    for (int i = 0; i < num_basis_states_; ++i) {
        probs[i] = std::norm(superposition_state_.amplitudes[i]);
    }
    
    // Normalize probabilities
    double sum = std::accumulate(probs.begin(), probs.end(), 0.0);
    for (auto& p : probs) p /= sum;
    
    // Sample collapsed state
    int collapsed_idx = sample_from_distribution(probs);
    
    measurement.collapsed_dimension = collapsed_idx;
    measurement.collapsed_price = current_price_ * (1.0 + (collapsed_idx - num_basis_states_/2.0) / num_basis_states_);
    measurement.probability = probs[collapsed_idx];
    measurement.confidence = superposition_state_.coherence;
    measurement.all_probabilities = probs;
    measurement.entropy_before = superposition_state_.entropy;
    
    // Calculate entropy after measurement (should be 0 for pure state)
    measurement.entropy_after = 0.0;
    
    // Market interpretation
    if (collapsed_idx < num_basis_states_ * 0.3) {
        measurement.market_interpretation = "Strong bearish signal";
    } else if (collapsed_idx < num_basis_states_ * 0.45) {
        measurement.market_interpretation = "Moderate bearish signal";
    } else if (collapsed_idx < num_basis_states_ * 0.55) {
        measurement.market_interpretation = "Neutral/Ranging";
    } else if (collapsed_idx < num_basis_states_ * 0.7) {
        measurement.market_interpretation = "Moderate bullish signal";
    } else {
        measurement.market_interpretation = "Strong bullish signal";
    }
    
    return measurement;
}

QuantumPrediction DimensionManager::predict_price_evolution(double time_horizon) {
    QuantumPrediction prediction;
    
    // Calculate probability distribution
    auto prob_dist = get_probability_distribution();
    prediction.price_distribution = prob_dist;
    
    // Weighted average prediction
    double weighted_sum = 0.0;
    double weight_sum = 0.0;
    for (const auto& [price, prob] : prob_dist) {
        weighted_sum += price * prob;
        weight_sum += prob;
    }
    
    prediction.predicted_price = weighted_sum / weight_sum;
    
    // Uncertainty (standard deviation)
    double var_sum = 0.0;
    for (const auto& [price, prob] : prob_dist) {
        double diff = price - prediction.predicted_price;
        var_sum += diff * diff * prob;
    }
    prediction.uncertainty = std::sqrt(var_sum / weight_sum);
    
    // Confidence intervals
    std::vector<double> sorted_prices;
    for (const auto& [price, prob] : prob_dist) {
        int samples = static_cast<int>(prob * 1000);
        sorted_prices.insert(sorted_prices.end(), samples, price);
    }
    std::sort(sorted_prices.begin(), sorted_prices.end());
    
    int idx_2_5 = static_cast<int>(sorted_prices.size() * 0.025);
    int idx_97_5 = static_cast<int>(sorted_prices.size() * 0.975);
    
    prediction.confidence_interval_95_lower = sorted_prices[idx_2_5];
    prediction.confidence_interval_95_upper = sorted_prices[idx_97_5];
    
    // Regime change probability
    double regime_change_prob = 0.0;
    for (const auto& dim : dimensions_) {
        if (dim.market_regime.find("Crash") != std::string::npos ||
            dim.market_regime.find("BlackSwan") != std::string::npos) {
            regime_change_prob += dim.probability_weight;
        }
    }
    prediction.regime_change_probability = regime_change_prob;
    
    // Anomaly detection
    prediction.anomaly_probability = calculate_von_neumann_entropy() / std::log(num_basis_states_);
    
    // Regime probabilities
    for (const auto& dim : dimensions_) {
        prediction.possible_regimes.push_back(dim.market_regime);
        prediction.regime_probabilities.push_back(dim.probability_weight);
    }
    
    // Quantum advantage (vs classical prediction)
    prediction.quantum_advantage = superposition_state_.coherence * 0.2;  // Up to 20% improvement
    
    return prediction;
}

// ============================================================
// TUNNELING ANALYSIS
// ============================================================

double DimensionManager::calculate_tunneling_probability(double barrier_height, double barrier_width) {
    // Quantum tunneling through support/resistance
    double mass = current_volatility_ * current_volatility_;
    double energy = current_price_;
    double hbar = 1.0;  // Normalized
    
    if (energy >= barrier_height) {
        return 1.0;  // Classical case - no barrier
    }
    
    double kappa = std::sqrt(2 * mass * (barrier_height - energy)) / hbar;
    double T = std::exp(-2 * kappa * barrier_width);
    
    return std::min(T, 1.0);
}

std::vector<double> DimensionManager::find_tunneling_opportunities(double support, double resistance) {
    std::vector<double> opportunities;
    
    // Check for price levels with high tunneling probability
    double price_step = (resistance - support) / 100;
    
    for (double price = support; price <= resistance; price += price_step) {
        double barrier_height = std::max(price, current_price_) * 1.01;
        double barrier_width = std::abs(price - current_price_) / current_price_;
        
        double tunnel_prob = calculate_tunneling_probability(barrier_height, barrier_width);
        opportunities.push_back(tunnel_prob);
    }
    
    return opportunities;
}

// ============================================================
// PARALLEL EVOLUTION
// ============================================================

void DimensionManager::evolve_dimensions_parallel(double dt, int num_threads) {
    if (num_threads < 0) {
        num_threads = num_threads_;
    }
    
    omp_set_num_threads(num_threads);
    
    #pragma omp parallel for
    for (int i = 0; i < num_dimensions_; ++i) {
        auto& dim = dimensions_[i];
        
        // Select evolution operator based on regime
        if (dim.market_regime.find("BULL") != std::string::npos) {
            evolve_bull_market(dim.current_state, dt);
        } else if (dim.market_regime.find("BEAR") != std::string::npos) {
            evolve_bear_market(dim.current_state, dt);
        } else if (dim.market_regime.find("CRASH") != std::string::npos ||
                   dim.market_regime.find("BLACK_SWAN") != std::string::npos) {
            evolve_crash_market(dim.current_state, dt);
        } else {
            evolve_choppy_market(dim.current_state, dt);
        }
        
        // Apply damping
        for (int j = 0; j < num_basis_states_; ++j) {
            dim.current_state.amplitudes[j] *= std::exp(-dim.damping * dt);
        }
        
        normalize_state(dim.current_state);
    }
}

void DimensionManager::evolve_bull_market(QuantumState& state, double dt) {
    // Bull market: wave packet drifts upward with spreading
    double drift_velocity = 0.02;
    double spreading_rate = 0.01;
    
    std::vector<std::complex<double>> new_amplitudes(num_basis_states_);
    
    for (int i = 0; i < num_basis_states_; ++i) {
        // Drift upward
        int drift_idx = std::min(i + static_cast<int>(drift_velocity * num_basis_states_ * dt),
                                num_basis_states_ - 1);
        
        // Quantum phase evolution
        double phase = std::arg(state.amplitudes[i]) + state.dimension_index * dt;
        double amp = std::abs(state.amplitudes[i]) * (1.0 + spreading_rate * dt);
        
        new_amplitudes[drift_idx] += std::complex<double>(
            amp * std::cos(phase),
            amp * std::sin(phase)
        );
    }
    
    state.amplitudes = std::move(new_amplitudes);
}

void DimensionManager::evolve_bear_market(QuantumState& state, double dt) {
    // Bear market: wave packet drifts downward
    double drift_velocity = -0.02;
    double spreading_rate = 0.015;
    
    std::vector<std::complex<double>> new_amplitudes(num_basis_states_);
    
    for (int i = 0; i < num_basis_states_; ++i) {
        int drift_idx = std::max(i + static_cast<int>(drift_velocity * num_basis_states_ * dt), 0);
        
        double phase = std::arg(state.amplitudes[i]) - state.dimension_index * dt;
        double amp = std::abs(state.amplitudes[i]) * (1.0 + spreading_rate * dt);
        
        new_amplitudes[drift_idx] += std::complex<double>(
            amp * std::cos(phase),
            amp * std::sin(phase)
        );
    }
    
    state.amplitudes = std::move(new_amplitudes);
}

void DimensionManager::evolve_crash_market(QuantumState& state, double dt) {
    // Crash: rapid downward movement with heavy tails
    double drift_velocity = -0.08;
    double spreading_rate = 0.05;
    
    std::vector<std::complex<double>> new_amplitudes(num_basis_states_);
    
    for (int i = 0; i < num_basis_states_; ++i) {
        int drift_idx = std::max(i + static_cast<int>(drift_velocity * num_basis_states_ * dt), 0);
        
        double phase = std::arg(state.amplitudes[i]) - 2 * state.dimension_index * dt;
        double amp = std::abs(state.amplitudes[i]) * (1.0 + spreading_rate * dt);
        
        new_amplitudes[drift_idx] += std::complex<double>(
            amp * std::cos(phase),
            amp * std::sin(phase)
        );
    }
    
    state.amplitudes = std::move(new_amplitudes);
}

void DimensionManager::evolve_choppy_market(QuantumState& state, double dt) {
    // Choppy: oscillatory behavior with no clear direction
    double oscillation_freq = 0.5;
    double spreading_rate = 0.005;
    
    std::vector<std::complex<double>> new_amplitudes(num_basis_states_);
    
    for (int i = 0; i < num_basis_states_; ++i) {
        // Oscillate
        double oscillation = std::sin(oscillation_freq * dt * num_basis_states_);
        int shift_idx = std::max(0, std::min(num_basis_states_ - 1,
                            i + static_cast<int>(oscillation * 5)));
        
        double phase = std::arg(state.amplitudes[i]) + state.dimension_index * dt * 0.5;
        double amp = std::abs(state.amplitudes[i]) * (1.0 + spreading_rate * dt);
        
        new_amplitudes[shift_idx] += std::complex<double>(
            amp * std::cos(phase),
            amp * std::sin(phase)
        );
    }
    
    state.amplitudes = std::move(new_amplitudes);
}

// ============================================================
// UTILITY FUNCTIONS
// ============================================================

void DimensionManager::normalize_state(QuantumState& state) {
    double norm = 0.0;
    for (const auto& amp : state.amplitudes) {
        norm += std::norm(amp);
    }
    norm = std::sqrt(norm);
    
    if (norm > 0) {
        for (auto& amp : state.amplitudes) {
            amp /= norm;
        }
    }
    
    state.normalization = norm;
    state.entropy = calculate_entropy(state);
}

double DimensionManager::calculate_entropy(const QuantumState& state) {
    double entropy = 0.0;
    for (const auto& amp : state.amplitudes) {
        double prob = std::norm(amp);
        if (prob > 1e-10) {
            entropy -= prob * std::log(prob);
        }
    }
    return entropy;
}

double DimensionManager::calculate_von_neumann_entropy() {
    return superposition_state_.entropy;
}

double DimensionManager::sample_from_distribution(const std::vector<double>& probs) {
    std::random_device rd;
    std::mt19937 gen(rd());
    std::discrete_distribution<int> dist(probs.begin(), probs.end());
    return dist(gen);
}

std::vector<std::pair<double, double>> DimensionManager::get_probability_distribution() {
    std::vector<std::pair<double, double>> distribution;
    
    for (int i = 0; i < num_basis_states_; ++i) {
        double price = current_price_ * (1.0 + (i - num_basis_states_/2.0) / num_basis_states_);
        double prob = std::norm(superposition_state_.amplitudes[i]);
        distribution.push_back({price, prob});
    }
    
    return distribution;
}

void DimensionManager::update_with_market_data(double current_price, double volatility,
                                               const std::vector<double>& recent_prices) {
    current_price_ = current_price;
    current_volatility_ = volatility;
    
    // Update dimension weights based on recent price action
    std::vector<double> dimension_scores(num_dimensions_, 0.0);
    
    for (const auto& price : recent_prices) {
        double return_val = (price - current_price_) / current_price_;
        
        for (int i = 0; i < num_dimensions_; ++i) {
            const auto& dim = dimensions_[i];
            
            if (dim.market_regime.find("BULL") != std::string::npos && return_val > 0) {
                dimension_scores[i] += return_val;
            } else if (dim.market_regime.find("BEAR") != std::string::npos && return_val < 0) {
                dimension_scores[i] += std::abs(return_val);
            } else if (dim.market_regime.find("CHOPPY") != std::string::npos && std::abs(return_val) < 0.01) {
                dimension_scores[i] += 0.1;
            }
        }
    }
    
    // Update weights
    double total_score = std::accumulate(dimension_scores.begin(), dimension_scores.end(), 0.0) + 1e-10;
    for (int i = 0; i < num_dimensions_; ++i) {
        dimensions_[i].probability_weight = (dimension_scores[i] + 1.0) / (total_score + num_dimensions_);
    }
}

} // namespace quantum
} // namespace quantum_trading
