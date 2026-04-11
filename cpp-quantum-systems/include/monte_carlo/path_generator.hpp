#ifndef PATH_GENERATOR_HPP
#define PATH_GENERATOR_HPP

#include <vector>
#include "monte_carlo/advanced_simulator.hpp"

namespace quantum_trading {
namespace monte_carlo {

class PathGenerator {
public:
    PathGenerator(int num_paths = 100000, int num_steps = 252);
    std::vector<std::vector<double>> generate_paths(const MarketState& state, int threads = 4);

private:
    int num_paths_;
    int num_steps_;
};

} // namespace monte_carlo
} // namespace quantum_trading

#endif // PATH_GENERATOR_HPP
