#ifndef DENSITY_ESTIMATOR_HPP
#define DENSITY_ESTIMATOR_HPP

#include <vector>

namespace quantum_trading {
namespace monte_carlo {

class DensityEstimator {
public:
    DensityEstimator();
    std::vector<double> estimate_kernel_density(const std::vector<double>& samples, int grid_points = 1000);
};

} // namespace monte_carlo
} // namespace quantum_trading

#endif // DENSITY_ESTIMATOR_HPP
