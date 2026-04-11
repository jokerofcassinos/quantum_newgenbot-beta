#include "monte_carlo/advanced_simulator.hpp"
#include <cmath>
#include <numeric>
#include <algorithm>
#include <stdexcept>
#include <iostream>
#include <thread>
#include <mutex>
#include <atomic>
#include <unordered_map>
#include <complex>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

namespace quantum_trading {
namespace monte_carlo {

// ============================================================
// CONSTRUCTOR AND INITIALIZATION
// ============================================================

AdvancedSimulator::AdvancedSimulator(int num_paths, int num_steps, double dt)
    : num_paths_(num_paths), num_steps_(num_steps), dt_(dt),
      cache_valid_(false), num_threads_(omp_get_max_threads()) {
    
    // Initialize random engines (one per thread)
    random_engines_.resize(num_threads_);
    uniform_dist_.resize(num_threads_);
    
    unsigned int seed = std::random_device{}();
    for (int i = 0; i < num_threads_; ++i) {
        random_engines_[i].seed(seed + i * 1000);
        uniform_dist_[i] = std::uniform_real_distribution<double>(0.0, 1.0);
    }
    
    // Initialize default market state
    market_state_ = MarketState{
        .spot_price = 73000.0,
        .volatility = 0.65,
        .interest_rate = 0.05,
        .dividend_yield = 0.0,
        .regime = RegimeType::BULL_LOW_VOL,
        .jump_intensity = 0.1,
        .jump_mean = -0.02,
        .jump_vol = 0.05,
        .skewness = -0.3,
        .kurtosis = 3.5
    };
    
    vol_model_ = VolatilityModel::HESTON;
    jump_model_ = JumpModel::MERTON;
    distribution_ = DistributionType::STUDENT_T;
    
    // Initialize transition matrix for regime switching
    transition_matrix_ = {
        // BULL_LOW, BULL_HIGH, BEAR_LOW, BEAR_HIGH, CHOPPY, CRASH
        {0.80,    0.10,     0.05,    0.03,     0.02,    0.00},  // From BULL_LOW
        {0.05,    0.60,     0.10,    0.15,     0.08,    0.02},  // From BULL_HIGH
        {0.10,    0.05,     0.70,    0.10,     0.04,    0.01},  // From BEAR_LOW
        {0.03,    0.05,     0.15,    0.60,     0.12,    0.05},  // From BEAR_HIGH
        {0.15,    0.10,     0.10,    0.05,     0.55,    0.05},  // From CHOPPY
        {0.05,    0.05,     0.20,    0.15,     0.10,    0.45}   // From CRASH
    };
}

AdvancedSimulator::~AdvancedSimulator() {}

void AdvancedSimulator::set_market_state(const MarketState& state) {
    market_state_ = state;
    cache_valid_ = false;
}

void AdvancedSimulator::set_volatility_model(VolatilityModel model) {
    vol_model_ = model;
    cache_valid_ = false;
}

void AdvancedSimulator::set_jump_model(JumpModel model) {
    jump_model_ = model;
    cache_valid_ = false;
}

void AdvancedSimulator::set_distribution(DistributionType dist) {
    distribution_ = dist;
    cache_valid_ = false;
}

std::vector<PathInfo> AdvancedSimulator::get_sample_paths(int num_paths) {
    return std::vector<PathInfo>();  // Stub
}

std::vector<double> AdvancedSimulator::estimate_density(int grid_points) {
    return std::vector<double>();  // Stub
}

std::tuple<double, double> AdvancedSimulator::calculate_greeks(double bump_size) {
    return {0.0, 0.0};  // Stub
}

double AdvancedSimulator::calculate_probability(double target_price) {
    if (!cache_valid_) return 0.5;
    int count = std::count_if(cached_result_.final_prices.begin(), cached_result_.final_prices.end(),
        [target_price](double p) { return p > target_price; });
    return (double)count / cached_result_.final_prices.size();
}

std::vector<double> AdvancedSimulator::get_quantile_path(std::vector<double> quantiles) {
    return std::vector<double>();  // Stub
}

std::unordered_map<RegimeType, double> AdvancedSimulator::get_regime_probabilities() {
    // Return equal probability for all regimes (stub)
    std::unordered_map<RegimeType, double> probs;
    probs[RegimeType::BULL_LOW_VOL] = 0.2;
    probs[RegimeType::BULL_HIGH_VOL] = 0.15;
    probs[RegimeType::BEAR_LOW_VOL] = 0.15;
    probs[RegimeType::BEAR_HIGH_VOL] = 0.15;
    probs[RegimeType::CHOPPY_RANGING] = 0.2;
    probs[RegimeType::CRASH] = 0.15;
    return probs;
}

std::vector<std::pair<RegimeType, RegimeType>> AdvancedSimulator::get_regime_transitions() {
    return std::vector<std::pair<RegimeType, RegimeType>>();  // Stub
}

void AdvancedSimulator::calibrate_to_market(const std::vector<double>& historical_prices,
                                           const std::vector<double>& historical_vols) {
    // Calibration stub
    if (!historical_prices.empty()) {
        market_state_.spot_price = historical_prices.back();
    }
    if (!historical_vols.empty()) {
        double sum = std::accumulate(historical_vols.begin(), historical_vols.end(), 0.0);
        market_state_.volatility = sum / historical_vols.size();
    }
}

void AdvancedSimulator::generate_paths_parallel(std::vector<PathInfo>& paths, int thread_id, int num_paths_per_thread) {
    // Stub - implemented in simulation core
}

// ============================================================
// QUANTUM-ENHANCED SIMULATION
// ============================================================

SimulationResult AdvancedSimulator::run_simulation(int num_threads) {
    if (num_threads < 0) {
        num_threads = num_threads_;
    }
    
    omp_set_num_threads(num_threads);
    
    std::vector<double> final_prices(num_paths_);
    std::vector<double> max_prices(num_paths_);
    std::vector<double> min_prices(num_paths_);
    std::vector<double> avg_prices(num_paths_);
    std::vector<double> realized_vols(num_paths_);
    std::vector<int> jump_counts(num_paths_);
    
    // Parallel path generation
    #pragma omp parallel for
    for (int path_idx = 0; path_idx < num_paths_; ++path_idx) {
        int thread_id = omp_get_thread_num();
        
        double S = market_state_.spot_price;
        double vol = market_state_.volatility;
        RegimeType current_regime = market_state_.regime;
        
        double max_p = S;
        double min_p = S;
        double sum_p = S;
        double sum_log_ret_sq = 0.0;
        int num_jumps = 0;
        
        double prev_S = S;
        
        for (int step = 0; step < num_steps_; ++step) {
            // Regime switching
            double u_regime = uniform_dist_[thread_id](random_engines_[thread_id]);
            current_regime = simulate_regime_transition(current_regime, u_regime);
            MarketState state = get_state_for_regime(current_regime);
            
            // Price simulation
            double u1 = uniform_dist_[thread_id](random_engines_[thread_id]);
            double u2 = uniform_dist_[thread_id](random_engines_[thread_id]);
            double u3 = uniform_dist_[thread_id](random_engines_[thread_id]);
            
            switch (vol_model_) {
                case VolatilityModel::BLACK_SCHOLES:
                    S = simulate_black_scholes(S, state.volatility, dt_, u1, u2);
                    break;
                case VolatilityModel::HESTON:
                    S = simulate_heston(S, vol, dt_, u1, u2, u3);
                    vol = std::max(vol, 0.0001);
                    break;
                case VolatilityModel::SABR:
                    S = simulate_sabr(S, state.volatility, 0.7, -0.3, 0.4, dt_, u1, u2);
                    break;
                default:
                    S = simulate_black_scholes(S, state.volatility, dt_, u1, u2);
            }
            
            // Add jumps if model includes them
            if (jump_model_ != JumpModel::NONE) {
                double S_with_jumps = simulate_jump_diffusion(S, state.volatility, dt_, u1, u2, u3);
                if (std::abs(S_with_jumps - S) > S * 0.001) {
                    num_jumps++;
                }
                S = S_with_jumps;
            }
            
            // Track statistics
            max_p = std::max(max_p, S);
            min_p = std::min(min_p, S);
            sum_p += S;
            
            double log_ret = std::log(S / prev_S);
            sum_log_ret_sq += log_ret * log_ret;
            prev_S = S;
        }
        
        final_prices[path_idx] = S;
        max_prices[path_idx] = max_p;
        min_prices[path_idx] = min_p;
        avg_prices[path_idx] = sum_p / (num_steps_ + 1);
        realized_vols[path_idx] = std::sqrt(sum_log_ret_sq / num_steps_ * 252);
        jump_counts[path_idx] = num_jumps;
    }
    
    // Calculate statistics
    SimulationResult result;
    result.final_prices = std::move(final_prices);
    
    result.mean_price = calculate_mean(result.final_prices);
    result.std_dev = calculate_std(result.final_prices, result.mean_price);
    result.skewness = calculate_skewness(result.final_prices, result.mean_price, result.std_dev);
    result.excess_kurtosis = calculate_kurtosis(result.final_prices, result.mean_price, result.std_dev);
    
    result.var_95 = calculate_var(result.final_prices, 0.05);
    result.var_99 = calculate_var(result.final_prices, 0.01);
    result.cvar_95 = calculate_cvar(result.final_prices, 0.05);
    result.cvar_99 = calculate_cvar(result.final_prices, 0.01);
    
    result.max_price = *std::max_element(max_prices.begin(), max_prices.end());
    result.min_price = *std::min_element(min_prices.begin(), min_prices.end());
    
    double threshold = market_state_.spot_price;
    result.probability_profit = std::count_if(result.final_prices.begin(), result.final_prices.end(),
        [threshold](double p) { return p > threshold; }) / (double)num_paths_;
    
    double loss_threshold = threshold * 0.95;
    result.probability_loss_greater_than_5pct = std::count_if(result.final_prices.begin(), result.final_prices.end(),
        [loss_threshold](double p) { return p < loss_threshold; }) / (double)num_paths_;
    
    cached_result_ = result;
    cache_valid_ = true;
    
    return result;
}

// ============================================================
// VOLATILITY MODELS
// ============================================================

double AdvancedSimulator::simulate_black_scholes(double S0, double vol, double dt, double u1, double u2) {
    double Z = generate_normal(u1, u2);
    double drift = (market_state_.interest_rate - market_state_.dividend_yield - 0.5 * vol * vol) * dt;
    double diffusion = vol * std::sqrt(dt) * Z;
    return S0 * std::exp(drift + diffusion);
}

double AdvancedSimulator::simulate_heston(double S0, double v0, double dt, double u1, double u2, double u3) {
    // Heston model parameters
    double kappa = 2.0;     // Mean reversion speed
    double theta = 0.04;    // Long-term variance
    double sigma = 0.3;     // Vol of vol
    double rho = -0.7;      // Correlation
    
    double Z1 = generate_normal(u1, u2);
    double Z2 = rho * Z1 + std::sqrt(1 - rho * rho) * generate_normal(u2, u3);
    
    // Variance process (CIR)
    double v1 = v0 + kappa * (theta - v0) * dt + sigma * std::sqrt(v0 * dt) * Z2;
    v1 = std::max(v1, 0.0);  // Ensure non-negative
    
    // Price process
    double drift = (market_state_.interest_rate - market_state_.dividend_yield - 0.5 * v1) * dt;
    double diffusion = std::sqrt(v1 * dt) * Z1;
    double S1 = S0 * std::exp(drift + diffusion);
    
    return S1;
}

double AdvancedSimulator::simulate_sabr(double F0, double alpha, double beta, double rho, double volvol, double dt, double u1, double u2) {
    // SABR model implementation
    double Z1 = generate_normal(u1, u2);
    double Z2 = rho * Z1 + std::sqrt(1 - rho * rho) * generate_normal(u2, u1);
    
    double vol = alpha + volvol * std::sqrt(dt) * Z2;
    vol = std::max(vol, 0.0001);
    
    double drift = (market_state_.interest_rate - market_state_.dividend_yield) * dt;
    double diffusion = vol * std::pow(F0, beta - 1) * std::sqrt(dt) * Z1;
    
    return F0 * std::exp(drift + diffusion);
}

// ============================================================
// JUMP DIFFUSION
// ============================================================

double AdvancedSimulator::simulate_jump_diffusion(double S, double vol, double dt, double u1, double u2, double u3) {
    if (jump_model_ == JumpModel::NONE) {
        return S;
    }
    
    // Poisson jump process
    double lambda = market_state_.jump_intensity;
    double jump_prob = 1.0 - std::exp(-lambda * dt);
    
    if (u3 < jump_prob) {
        double jump_size = generate_jump_size(u1, u2);
        S *= std::exp(jump_size);
    }
    
    return S;
}

// ============================================================
// REGIME SWITCHING
// ============================================================

RegimeType AdvancedSimulator::simulate_regime_transition(RegimeType current_regime, double u1) {
    int current_idx = static_cast<int>(current_regime);
    double cumulative_prob = 0.0;
    
    for (int next_idx = 0; next_idx < 6; ++next_idx) {
        cumulative_prob += transition_matrix_[current_idx][next_idx];
        if (u1 < cumulative_prob) {
            return static_cast<RegimeType>(next_idx);
        }
    }
    
    return current_regime;  // Stay in current regime
}

MarketState AdvancedSimulator::get_state_for_regime(RegimeType regime) {
    MarketState state = market_state_;
    
    switch (regime) {
        case RegimeType::BULL_LOW_VOL:
            state.volatility = 0.40;
            state.interest_rate = 0.06;
            state.jump_intensity = 0.05;
            state.skewness = 0.2;
            state.kurtosis = 3.0;
            break;
        case RegimeType::BULL_HIGH_VOL:
            state.volatility = 0.80;
            state.interest_rate = 0.05;
            state.jump_intensity = 0.15;
            state.skewness = -0.1;
            state.kurtosis = 4.5;
            break;
        case RegimeType::BEAR_LOW_VOL:
            state.volatility = 0.50;
            state.interest_rate = 0.03;
            state.jump_intensity = 0.10;
            state.skewness = -0.4;
            state.kurtosis = 3.5;
            break;
        case RegimeType::BEAR_HIGH_VOL:
            state.volatility = 1.00;
            state.interest_rate = 0.02;
            state.jump_intensity = 0.25;
            state.skewness = -0.6;
            state.kurtosis = 5.5;
            break;
        case RegimeType::CHOPPY_RANGING:
            state.volatility = 0.60;
            state.interest_rate = 0.04;
            state.jump_intensity = 0.08;
            state.skewness = 0.0;
            state.kurtosis = 3.2;
            break;
        case RegimeType::CRASH:
            state.volatility = 1.50;
            state.interest_rate = 0.01;
            state.jump_intensity = 0.50;
            state.skewness = -1.0;
            state.kurtosis = 8.0;
            break;
    }
    
    return state;
}

// ============================================================
// STATISTICAL CALCULATIONS
// ============================================================

double AdvancedSimulator::calculate_mean(const std::vector<double>& data) {
    return std::accumulate(data.begin(), data.end(), 0.0) / data.size();
}

double AdvancedSimulator::calculate_std(const std::vector<double>& data, double mean) {
    double sum_sq = 0.0;
    for (double val : data) {
        double diff = val - mean;
        sum_sq += diff * diff;
    }
    return std::sqrt(sum_sq / (data.size() - 1));
}

double AdvancedSimulator::calculate_skewness(const std::vector<double>& data, double mean, double std) {
    double sum_cube = 0.0;
    for (double val : data) {
        double diff = (val - mean) / std;
        sum_cube += diff * diff * diff;
    }
    return sum_cube / data.size();
}

double AdvancedSimulator::calculate_kurtosis(const std::vector<double>& data, double mean, double std) {
    double sum_fourth = 0.0;
    for (double val : data) {
        double diff = (val - mean) / std;
        sum_fourth += diff * diff * diff * diff;
    }
    return (sum_fourth / data.size()) - 3.0;  // Excess kurtosis
}

double AdvancedSimulator::calculate_var(const std::vector<double>& data, double confidence) {
    std::vector<double> sorted_data = data;
    std::sort(sorted_data.begin(), sorted_data.end());
    int index = static_cast<int>(confidence * sorted_data.size());
    return sorted_data[index];
}

double AdvancedSimulator::calculate_cvar(const std::vector<double>& data, double confidence) {
    double var = calculate_var(data, confidence);
    double sum = 0.0;
    int count = 0;
    for (double val : data) {
        if (val < var) {
            sum += val;
            count++;
        }
    }
    return count > 0 ? sum / count : var;
}

// ============================================================
// RANDOM NUMBER GENERATION
// ============================================================

double AdvancedSimulator::generate_normal(double u1, double u2) {
    // Box-Muller transform
    return std::sqrt(-2.0 * std::log(u1)) * std::cos(2.0 * M_PI * u2);
}

double AdvancedSimulator::generate_jump_size(double u1, double u2) {
    double Z = generate_normal(u1, u2);
    return market_state_.jump_mean + market_state_.jump_vol * Z;
}

// ============================================================
// QUANTUM-ENHANCED SIMULATION
// ============================================================

std::vector<std::complex<double>> AdvancedSimulator::calculate_wave_function() {
    // Quantum superposition of all possible price states
    int num_states = 1024;  // Discretized price space
    std::vector<std::complex<double>> psi(num_states);
    
    double min_price = market_state_.spot_price * 0.5;
    double max_price = market_state_.spot_price * 1.5;
    double price_step = (max_price - min_price) / num_states;
    
    // Initialize Gaussian wave packet centered at current price
    double sigma = market_state_.spot_price * market_state_.volatility * std::sqrt(252 * dt_);
    
    #pragma omp parallel for
    for (int i = 0; i < num_states; ++i) {
        double price = min_price + i * price_step;
        double x = price - market_state_.spot_price;
        
        // Gaussian wave function
        double amplitude = std::exp(-x * x / (4 * sigma * sigma));
        double phase = 0.0;  // Can be enhanced with momentum
        
        psi[i] = std::complex<double>(amplitude, 0.0);
    }
    
    // Normalize
    double norm = 0.0;
    for (const auto& val : psi) {
        norm += std::norm(val);
    }
    norm = std::sqrt(norm);
    
    for (auto& val : psi) {
        val /= norm;
    }
    
    return psi;
}

std::vector<double> AdvancedSimulator::collapse_to_classical_paths() {
    auto psi = calculate_wave_function();
    
    std::vector<double> classical_probabilities(psi.size());
    for (size_t i = 0; i < psi.size(); ++i) {
        classical_probabilities[i] = std::norm(psi[i]);
    }
    
    return classical_probabilities;
}

} // namespace monte_carlo
} // namespace quantum_trading
