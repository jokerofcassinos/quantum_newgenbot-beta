// Core utilities
#include "core/core_utils.hpp"
#include <cmath>
#include <numeric>

namespace quantum_trading {

// Random Engine
RandomEngine::RandomEngine() : gen_(std::random_device{}()) {}

double RandomEngine::generate_normal() {
    std::normal_distribution<double> dist(0.0, 1.0);
    return dist(gen_);
}

double RandomEngine::generate_uniform(double min, double max) {
    std::uniform_real_distribution<double> dist(min, max);
    return dist(gen_);
}

// Math Utils
double MathUtils::clamp(double val, double min, double max) {
    return std::max(min, std::min(max, val));
}

double MathUtils::log_return(double price_now, double price_prev) {
    return std::log(price_now / price_prev);
}

// Statistical Models
double StatisticalModels::calculate_mean(const std::vector<double>& data) {
    if (data.empty()) return 0.0;
    return std::accumulate(data.begin(), data.end(), 0.0) / data.size();
}

double StatisticalModels::calculate_variance(const std::vector<double>& data) {
    double mean = calculate_mean(data);
    double sum = 0.0;
    for (double val : data) {
        sum += (val - mean) * (val - mean);
    }
    return sum / (data.size() - 1);
}

} // namespace quantum_trading
