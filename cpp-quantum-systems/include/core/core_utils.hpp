#ifndef CORE_HEADERS_HPP
#define CORE_HEADERS_HPP

#include <vector>
#include <random>
#include <cmath>
#include <algorithm>
#include <numeric>

namespace quantum_trading {

class RandomEngine {
public:
    RandomEngine();
    double generate_normal();
    double generate_uniform(double min = 0.0, double max = 1.0);
private:
    std::mt19937 gen_;
};

class MathUtils {
public:
    static double clamp(double val, double min, double max);
    static double log_return(double price_now, double price_prev);
};

class StatisticalModels {
public:
    static double calculate_mean(const std::vector<double>& data);
    static double calculate_variance(const std::vector<double>& data);
};

} // namespace quantum_trading

#endif // CORE_HEADERS_HPP
