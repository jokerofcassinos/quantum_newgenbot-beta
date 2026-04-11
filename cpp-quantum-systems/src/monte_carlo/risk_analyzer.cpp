// Risk Analyzer stub
#include "monte_carlo/risk_analyzer.hpp"

namespace quantum_trading {
namespace monte_carlo {

RiskAnalyzer::RiskAnalyzer() {}

double RiskAnalyzer::calculate_var(const std::vector<double>& pnl, double confidence) {
    std::vector<double> sorted_pnl = pnl;
    std::sort(sorted_pnl.begin(), sorted_pnl.end());
    int idx = static_cast<int>(confidence * sorted_pnl.size());
    return sorted_pnl[std::min(idx, (int)sorted_pnl.size()-1)];
}

double RiskAnalyzer::calculate_cvar(const std::vector<double>& pnl, double confidence) {
    double var = calculate_var(pnl, confidence);
    double sum = 0.0, count = 0.0;
    for (double val : pnl) {
        if (val < var) {
            sum += val;
            count++;
        }
    }
    return count > 0 ? sum / count : var;
}

} // namespace monte_carlo
} // namespace quantum_trading
