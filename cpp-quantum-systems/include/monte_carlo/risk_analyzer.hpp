#ifndef RISK_ANALYZER_HPP
#define RISK_ANALYZER_HPP

#include <vector>
#include <algorithm>

namespace quantum_trading {
namespace monte_carlo {

class RiskAnalyzer {
public:
    RiskAnalyzer();
    double calculate_var(const std::vector<double>& pnl, double confidence = 0.95);
    double calculate_cvar(const std::vector<double>& pnl, double confidence = 0.95);
};

} // namespace monte_carlo
} // namespace quantum_trading

#endif // RISK_ANALYZER_HPP
