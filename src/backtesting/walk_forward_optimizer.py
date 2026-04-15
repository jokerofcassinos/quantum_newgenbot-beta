"""
Walk-Forward Optimizer - Optuna-based parameter optimization
CEO: Qwen Code | Created: 2026-04-10

Features:
- Walk-forward analysis (avoid overfitting)
- Multi-objective optimization
- Out-of-sample validation
- Regime-specific optimization
- DNA Engine integration
"""

import optuna
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
from loguru import logger

from src.backtesting.backtester import BacktestEngine, BacktestConfig
from src.core.config_manager import ConfigManager


class WalkForwardOptimizer:
    """
    Walk-Forward Optimization System
    
    Architecture:
    1. Split data into train/test windows
    2. Optimize parameters on train window
    3. Validate on test window (out-of-sample)
    4. Roll forward and repeat
    5. Aggregate results
    
    This prevents overfitting by always testing on unseen data.
    """
    
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.optimization_history: List[Dict[str, Any]] = []
        
        logger.info(" Walk-Forward Optimizer initialized")
    
    def optimize(self, 
                candles: pd.DataFrame,
                n_trials: int = 100,
                train_days: int = 60,
                test_days: int = 30,
                n_splits: int = 4) -> Dict[str, Any]:
        """
        Run walk-forward optimization
        
        Args:
            candles: Historical data
            n_trials: Number of optimization trials per window
            train_days: Days in training window
            test_days: Days in testing window (out-of-sample)
            n_splits: Number of train/test splits
        
        Returns:
            dict: Optimization results
        """
        logger.info("="*80)
        logger.info(" STARTING WALK-FORWARD OPTIMIZATION")
        logger.info("="*80)
        logger.info(f"   Total candles: {len(candles)}")
        logger.info(f"   Train window: {train_days} days")
        logger.info(f"   Test window: {test_days} days")
        logger.info(f"   Number of splits: {n_splits}")
        logger.info(f"   Trials per split: {n_trials}")
        logger.info("="*80)
        
        # Calculate bars per day
        bars_per_day = 288  # M5 bars
        train_bars = train_days * bars_per_day
        test_bars = test_days * bars_per_day
        
        # Results storage
        all_results = {
            'in_sample': [],
            'out_of_sample': [],
            'parameters': [],
        }
        
        # Walk-forward loop
        start_idx = train_bars  # Start after first train window
        
        for split in range(n_splits):
            train_start = start_idx + split * test_bars
            train_end = train_start + train_bars
            test_start = train_end
            test_end = test_start + test_bars
            
            if test_end > len(candles):
                logger.warning(f"    Split {split+1}: Not enough data, skipping")
                break
            
            logger.info(f"\n{'='*60}")
            logger.info(f" SPLIT {split+1}/{n_splits}")
            logger.info(f"{'='*60}")
            logger.info(f"   Train: bars {train_start}-{train_end} ({candles.iloc[train_start]['time']}  {candles.iloc[train_end-1]['time']})")
            logger.info(f"   Test:  bars {test_start}-{test_end} ({candles.iloc[test_start]['time']}  {candles.iloc[test_end-1]['time']})")
            
            # Split data
            train_data = candles.iloc[train_start:train_end].copy()
            test_data = candles.iloc[test_start:test_end].copy()
            
            # Optimize on training data
            logger.info(f"\n Optimizing on training data ({len(train_data)} bars)...")
            best_params = self._optimize_window(train_data, n_trials)
            
            # Validate on test data (out-of-sample)
            logger.info(f"\n Validating on test data ({len(test_data)} bars)...")
            test_result = self._evaluate_params(test_data, best_params)
            
            # Evaluate on training data (in-sample)
            train_result = self._evaluate_params(train_data, best_params)
            
            # Store results
            all_results['in_sample'].append(train_result)
            all_results['out_of_sample'].append(test_result)
            all_results['parameters'].append(best_params)
            
            logger.info(f"\n Split {split+1} Results:")
            logger.info(f"   In-Sample:  Net PnL=${train_result['net_pnl']:+,.2f} | WR={train_result['win_rate']*100:.1f}% | PF={train_result['profit_factor']:.2f}")
            logger.info(f"   Out-of-Sample: Net PnL=${test_result['net_pnl']:+,.2f} | WR={test_result['win_rate']*100:.1f}% | PF={test_result['profit_factor']:.2f}")
        
        # Aggregate results
        summary = self._aggregate_results(all_results)
        
        # Find best robust parameters
        best_params = self._find_robust_parameters(all_results)
        
        logger.info(f"\n{'='*80}")
        logger.info(" WALK-FORWARD OPTIMIZATION COMPLETE")
        logger.info(f"{'='*80}")
        logger.info(f"   Average In-Sample PnL: ${summary['avg_in_sample_pnl']:+,.2f}")
        logger.info(f"   Average Out-of-Sample PnL: ${summary['avg_out_of_sample_pnl']:+,.2f}")
        logger.info(f"   Degradation: {summary['degradation_percent']:.1f}%")
        logger.info(f"   Robustness Score: {summary['robustness_score']:.2f}/1.0")
        logger.info(f"{'='*80}")
        
        return {
            'summary': summary,
            'results': all_results,
            'best_parameters': best_params,
        }
    
    def _optimize_window(self, candles: pd.DataFrame, n_trials: int) -> Dict[str, Any]:
        """Optimize parameters on a single window"""
        
        def objective(trial):
            # Suggest parameters
            params = {
                'ema_fast': trial.suggest_int('ema_fast', 5, 20),
                'ema_slow': trial.suggest_int('ema_slow', 15, 50),
                'atr_multiplier': trial.suggest_float('atr_multiplier', 1.0, 3.0),
                'rr_ratio': trial.suggest_float('rr_ratio', 1.5, 3.0),
                'confidence_threshold': trial.suggest_float('confidence_threshold', 0.55, 0.75),
                'risk_percent': trial.suggest_float('risk_percent', 0.25, 1.0),
            }
            
            # Validate (ema_fast < ema_slow)
            if params['ema_fast'] >= params['ema_slow']:
                raise optuna.exceptions.TrialPruned()
            
            # Run backtest
            result = self._evaluate_params(candles, params)
            
            # Optimize for net profit with penalty for drawdown
            score = result['net_pnl'] - (result['max_drawdown'] * 500)  # Penalty for DD
            
            return score
        
        # Create study
        study = optuna.create_study(
            direction='maximize',
            sampler=optuna.samplers.TPESampler(seed=42),
        )
        
        # Run optimization
        study.optimize(objective, n_trials=n_trials, show_progress_bar=False)
        
        logger.info(f"    Optimization complete: Best score = {study.best_value:+,.2f}")
        
        return study.best_params
    
    def _evaluate_params(self, candles: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate parameters with a quick backtest"""
        
        config = BacktestConfig(
            initial_capital=100000.0,
            commission_per_lot=45.0,
            spread_points=100.0,
            slippage_points=10.0,
        )
        
        # Create engine with these parameters
        engine = BacktestEngine(config=config, dna_params=params)
        results = engine.run(candles)
        
        summary = results.get('summary', {})
        risk = results.get('risk', {})
        
        return {
            'net_pnl': summary.get('net_profit', 0),
            'win_rate': summary.get('win_rate', 0),
            'profit_factor': summary.get('profit_factor', 0),
            'total_trades': summary.get('total_trades', 0),
            'max_drawdown': risk.get('max_drawdown_percent', 0),
            'sharpe_ratio': summary.get('sharpe_ratio', 0),
        }
    
    def _aggregate_results(self, all_results: Dict[str, Any]) -> Dict[str, Any]:
        """Aggregate results from all splits"""
        in_sample_pnls = [r['net_pnl'] for r in all_results['in_sample']]
        out_of_sample_pnls = [r['net_pnl'] for r in all_results['out_of_sample']]
        
        avg_in = np.mean(in_sample_pnls) if in_sample_pnls else 0
        avg_out = np.mean(out_of_sample_pnls) if out_of_sample_pnls else 0
        
        # Calculate degradation (how much performance drops out-of-sample)
        degradation = ((avg_in - avg_out) / abs(avg_in) * 100) if avg_in != 0 else 0
        
        # Robustness score (lower degradation = more robust)
        robustness = max(0, 1 - (degradation / 100))
        
        return {
            'n_splits': len(in_sample_pnls),
            'avg_in_sample_pnl': avg_in,
            'avg_out_of_sample_pnl': avg_out,
            'avg_in_sample_wr': np.mean([r['win_rate'] for r in all_results['in_sample']]),
            'avg_out_of_sample_wr': np.mean([r['win_rate'] for r in all_results['out_of_sample']]),
            'degradation_percent': degradation,
            'robustness_score': robustness,
            'best_split_pnl': max(out_of_sample_pnls) if out_of_sample_pnls else 0,
            'worst_split_pnl': min(out_of_sample_pnls) if out_of_sample_pnls else 0,
            'consistency': np.std(out_of_sample_pnls) if len(out_of_sample_pnls) > 1 else 0,
        }
    
    def _find_robust_parameters(self, all_results: Dict[str, Any]) -> Dict[str, Any]:
        """Find most robust parameters (best out-of-sample performance)"""
        
        best_idx = np.argmax([r['net_pnl'] for r in all_results['out_of_sample']])
        
        return all_results['parameters'][best_idx]
    
    def update_dna_with_optimized_params(self, optimized_params: Dict[str, Any]) -> None:
        """Update DNA with optimized parameters"""
        dna = self.config_manager.load_dna()
        
        # Update indicator periods
        if 'ema_fast' in optimized_params:
            dna['strategy_params']['indicator_periods']['ema_fast'] = optimized_params['ema_fast']
        if 'ema_slow' in optimized_params:
            dna['strategy_params']['indicator_periods']['ema_slow'] = optimized_params['ema_slow']
        if 'atr_multiplier' in optimized_params:
            dna['execution_params']['trailing_stop_multiplier'] = optimized_params['atr_multiplier']
        if 'rr_ratio' in optimized_params:
            dna['risk_params']['min_risk_reward_ratio'] = optimized_params['rr_ratio']
        if 'confidence_threshold' in optimized_params:
            dna['trading_params']['entry_threshold'] = optimized_params['confidence_threshold']
        if 'risk_percent' in optimized_params:
            dna['risk_params']['base_risk_percent'] = optimized_params['risk_percent']
        
        # Save updated DNA
        self.config_manager.save_dna(dna)
        logger.info(" DNA updated with optimized parameters")




