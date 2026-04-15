# MAPEAMENTO COMPLETO DA CADEIA NEURAL DO BACKTEST

**Data:** 13 de abril de 2026
**Fonte:** `D:\forex-project2k26\run_backtest_complete_v2.py` (1621 linhas)
**Resultado:** 103k de profit

---

## RESUMO DA CADEIA NEURAL

O backtest usa uma cadeia neural MASSIVA com **50+ componentes** integrados:

```
DATA → INDICATORS → REGIME → STRATEGIES → VOTING → VETO → VALIDATION → EXECUTION → MANAGEMENT
```

---

## 1. SISTEMAS PRINCIPAIS (12 componentes)

### 1.1 Neural Trade Auditor
- **Arquivo:** `src.monitoring.neural_trade_auditor.NeuralTradeAuditor`
- **Função:** Auditoria completa de cada trade (entry/exit state)
- **Captura:** Regime, indicators, price action, momentum, risk context, DNA state, Smart Order Manager

### 1.2 Trade Pattern Analyzer
- **Arquivo:** `src.monitoring.trade_pattern_analyzer.TradePatternAnalyzer`
- **Função:** Detecta padrões de erros (perdas por hora, regime, sessão, estratégia)

### 1.3 Veto Orchestrator
- **Arquivo:** `src.monitoring.veto_orchestrator.VetoOrchestrator`
- **Função:** Veto básico baseado em contexto de mercado (regime, sessão, perdas consecutivas)

### 1.4 Advanced Veto v2
- **Arquivo:** `src.monitoring.advanced_veto_v2.AdvancedVetoV2`
- **Função:** Veto avançado (RSI extremes, Bollinger extremes, divergência RSI)

### 1.5 Smart Order Manager
- **Arquivo:** `src.execution.smart_order_manager.SmartOrderManager`
- **Função:** Gerenciamento inteligente de ordens (Virtual TP, Dynamic SL)

### 1.6 Backtest Risk Manager
- **Arquivo:** `src.risk.backtest_risk_manager.BacktestRiskManager`
- **Função:** Validação de risco pré-trade (risk_amount, reward_amount, capital)

### 1.7 Anti-Metralhadora
- **Arquivo:** `src.risk.anti_metralhadora.AntiMetralhadora`
- **Função:** Prevenção de overtrading (min interval, max trades/day, quality score, cooldown)
- **Params:** min_interval=5min, max_trades=25/day, min_quality=0.40, max_consecutive_losses=3

### 1.8 Position Manager Smart TP
- **Arquivo:** `src.execution.position_manager_smart_tp.PositionManagerSmartTP`
- **Função:** Multi-target exits (TP2 50% @ 1:2 R:R, Trailing 50% @ 1.5 ATR)

### 1.9 Commission Floor
- **Arquivo:** `src.execution.commission_floor.CommissionFloor`
- **Função:** Previne fechamento prematuro antes de cobrir comissões

### 1.10 Risk Quantum Engine
- **Arquivo:** `src.risk.risk_quantum_engine.RiskQuantumEngine`
- **Função:** Position sizing com 5 fatores (Kelly fraction, max_position=5.0, base_risk=1%)

### 1.11 Profit Erosion Tiers
- **Arquivo:** `src.risk.profit_erosion_tiers.ProfitErosionTiers`
- **Função:** Proteção de lucro multi-nível

### 1.12 Execution Validator + GreatFilter
- **Arquivos:** `src.risk.execution_validator.ExecutionValidator`, `src.risk.great_filter.GreatFilter`
- **Função:** Validação pré-trade de qualidade de entrada

---

## 2. SISTEMAS AVANÇADOS (Phase 2 - 8 componentes)

### 2.1 Thermodynamic Exit
- **Arquivo:** `src.execution.thermodynamic_exit.ThermodynamicExit`
- **Função:** 5-sensor profit management

### 2.2 M8 Fibonacci System
- **Arquivo:** `src.strategies.m8_fibonacci_system.M8FibonacciSystem`
- **Função:** Análise em timeframe 8-min Phi (Fibonacci)

### 2.3 Regime Detector
- **Arquivo:** `src.analysis.regime_detector.RegimeDetector`
- **Função:** Detecção de regime (Hurst + ADX + Vol + Structure)

### 2.4 Recursive Self-Debate
- **Arquivo:** `src.monitoring.recursive_self_debate.RecursiveSelfDebate`
- **Função:** Metacognitive validation (debate signal confidence)

### 2.5 VPIN Microstructure
- **Arquivo:** `src.analysis.vpin_microstructure.VPINMicrostructure`
- **Função:** Detecção de atividade institucional

### 2.6 Black Swan Stress Test
- **Arquivo:** `src.risk.black_swan_stress_test.BlackSwanStressTest`
- **Função:** Simulação fat-tail

### 2.7 Kinematics Phase Space
- **Arquivo:** `src.analysis.kinematics_phase_space.KinematicsPhaseSpace`
- **Função:** Velocity/acceleration features

### 2.8 Akashic Core
- **Arquivo:** `src.memory.akashic_core.AkashicCore`
- **Função:** HDC pattern memory

---

## 3. SISTEMAS PHASE 3 (4 componentes)

### 3.1 Expectancy Engine
- **Arquivo:** `src.analysis.expectancy_engine.ExpectancyEngine`
- **Função:** Pre-trade expected value

### 3.2 Multi-Timeframe Alignment
- **Arquivo:** `src.analysis.multi_timeframe_alignment.MultiTimeframeAlignment`
- **Função:** Cross-TF confirmation

### 3.3 Session-Based Risk Profiles
- **Arquivo:** `src.risk.session_based_risk_profiles.SessionBasedRiskProfiles`
- **Função:** Session risk adjustment (Asian/London/NY)

### 3.4 Volatility Regime Adaptation
- **Arquivo:** `src.risk.volatility_regime_adaptation.VolatilityRegimeAdaptation`
- **Função:** Volatility adaptation

---

## 4. SISTEMA PHASE 4 (1 componente)

### 4.1 ML Signal Quality Predictor
- **Arquivo:** `src.ml.ml_signal_quality_predictor.MLSignalQualityPredictor`
- **Função:** ML win probability prediction

---

## 5. GHOST AUDIT ENGINE

### 5.1 Ghost Audit Engine
- **Arquivo:** `src.monitoring.ghost_audit_engine.GhostAuditEngine`
- **Função:** Shadow trading para análise de vetos

---

## 6. FLUXO DE DECISÃO COMPLETO (loop principal)

```python
for i in range(warmup, total):
    if current_position is None:
        # 1. Check cooldown after losses
        if consecutive_losses >= 3 and bars_since_loss < cooldown:
            continue
        
        # 2. Generate signal (12 strategies voting)
        signal = _generate_signal_fast(i)
        
        if signal:
            # 3. Session veto
            session_veto = apply_session_veto()
            if not session_veto['approved']:
                total_vetoes += 1
                ghost_audit.create_ghost()
                continue
            
            # 4. Confidence inversion (ghost audit finding)
            invert_confidence(signal)
            
            # 5. SELL vs BUY asymmetry (ghost audit finding)
            apply_directional_bias(signal)
            
            # 6. Basic veto
            basic_veto = veto_orchestrator.check()
            if not basic_veto.approved:
                total_vetoes += 1
                ghost_audit.create_ghost()
                continue
            
            # 7. Advanced veto v2
            veto_result = advanced_veto_v2.check()
            if not veto_result['approved']:
                total_vetoes += 1
                ghost_audit.create_ghost()
                continue
            
            # 8. Risk Manager validation
            risk_validation = risk_manager.validate()
            if not risk_validation['approved']:
                total_vetoes += 1
                ghost_audit.create_ghost()
                continue
            
            # 9. Anti-Metralhadora check
            allowed, reason = anti_metralhadora.should_allow_trade()
            if not allowed:
                total_vetoes += 1
                ghost_audit.create_ghost()
                continue
            
            # 10. Ghost audit volatility filter
            if ATR < 50% average:
                total_vetoes += 1
                ghost_audit.create_ghost()
                continue
            
            # 11. Regime Detection
            regime = regime_detector.detect_regime()
            signal['regime'] = regime
            
            # 12. Kinematics Phase Space
            kinematics = kinematics.calculate()
            signal['kinematics'] = kinematics
            
            # 13. M8 Fibonacci System
            m8 = m8_fibonacci.analyze()
            signal['m8_analysis'] = m8
            if m8 disagrees strongly:
                total_vetoes += 1
                continue
            
            # 14. VPIN Microstructure (audit only, no veto)
            vpin = vpin.calculate()
            signal['vpin'] = vpin
            
            # 15. Volatility Regime Adaptation
            vol = volatility_regime.classify()
            signal['volatility_regime'] = vol['regime']
            if vol['regime'] == 'extreme':
                total_vetoes += 1
                continue
            
            # 16. Recursive Self-Debate
            debate_approved, debate_signal, debate_conf = recursive_debate.debate()
            if debate_conf > signal_conf + 0.10:
                signal['direction'] = debate_signal
            
            # 17. ML Signal Quality (Phase 4)
            ml_prob = ml_predictor.predict()
            signal['ml_win_prob'] = ml_prob
            
            # 18. Expectancy Engine
            expectancy = expectancy_engine.calculate()
            signal['expectancy'] = expectancy
            
            # 19. Multi-Timeframe Alignment
            mtf = multi_tf.analyze()
            signal['mtf_alignment'] = mtf
            
            # 20. Session-Based Risk Profiles
            session_risk = session_risk.get_profile()
            signal['session_risk'] = session_risk
            
            # 21. Position sizing (Risk Quantum)
            volume = risk_quantum.calculate_size(signal)
            signal['volume'] = volume
            
            # 22. Execution Validator + GreatFilter
            exec_valid = execution_validator.validate()
            great_filter_result = great_filter.validate()
            if not exec_valid or not great_filter_result:
                total_vetoes += 1
                continue
            
            # 23. Open position
            _open_position(signal)
            
            # 24. Audit capture
            auditor.capture_entry state()
    
    else:
        # Manage open position
        # - Check SL/TP
        # - Trailing stop
        # - Partial exit
        # - Smart TP
        action = _manage_position()
        
        if action:
            _close_position(action)
            auditor.capture_exit_state()
            risk_manager.record_trade()
            anti_metralhadora.record_trade()
```

---

## 7. INDICADORES PRÉ-COMPUTADOS

O backtest pré-computa TODOS os indicadores para performance:

```python
# Pre-computed arrays
self._close = candles['close'].values
self._high = candles['high'].values
self._low = candles['low'].values
self._volume = candles['volume'].values
self._times = candles['time'].values

# Indicators
self._ema9 = EMA(9)
self._ema21 = EMA(21)
self._ema50 = EMA(50)
self._sma20 = SMA(20)
self._rsi = RSI(14)
self._atr = ATR(14)
self._bb_upper, self._bb_mid, self._bb_lower = BollingerBands(20, 2)
self._macd, self._macd_signal, self._macd_histogram = MACD(12, 26, 9)
```

---

## 8. 12 ESTRATÉGIAS DE VOTAÇÃO

```python
strategies = [
    'momentum',           # Strategy 1
    'liquidity',          # Strategy 2
    'thermodynamic',      # Strategy 3
    'physics',            # Strategy 4
    'order_block',        # Strategy 5
    'fvg',                # Strategy 6
    'msnr',               # Strategy 7
    'msnr_alchemist',     # Strategy 8
    'ifvg',               # Strategy 9
    'order_flow',         # Strategy 10
    'supply_demand',      # Strategy 11
    'fibonacci',          # Strategy 12
    'iceberg',            # Strategy 13
]
```

---

## 9. PARÂMETROS CRÍTICOS

### Risk Management
- Initial capital: $100,000
- Risk per trade: 1%
- Max position size: 5.0
- Min position size: 0.01
- Kelly fraction: 0.25
- Base risk percent: 1.0%

### Anti-Metralhadora
- Min interval: 5 minutes
- Max trades per day: 25
- Min quality score: 0.40
- Max consecutive losses: 3
- Loss cooldown: 30 minutes

### Position Management
- TP2 portion: 50% @ 1:2 R:R
- Trailing portion: 50% @ 1.5 ATR
- SL max: 300 points

### Session Profiles
- Asian: max_trades=5, risk_multiplier=0.5
- London: max_trades=10, risk_multiplier=1.0
- NY: max_trades=10, risk_multiplier=1.0
- NY Overlap: max_trades=12, risk_multiplier=1.2

---

## 10. PRÓXIMOS PASSOS PARA FASE 2

Para replicar esta cadeia neural no live trading:

1. **Criar módulo `live_trading/neural_chain.py`**
   - Portar TODOS os 25+ componentes
   - Adaptar para dados reais em streaming
   - Manter MESMA lógica matemática

2. **Integrar com MT5 Bridge**
   - Receber dados reais
   - Calcular indicadores incrementalmente
   - Executar cadeia completa

3. **Integrar com Data Engine**
   - Usar buffers circulares
   - Manter histórico para cálculos
   - Atualizar em tempo real

4. **Logs de cada componente**
   - Cada sistema loga seu estado
   - Dashboard mostra todos em tempo real

---

**Total de componentes a portar: 25+**
**Total de estratégias: 13**
**Total de vetos/validações: 10+**
**Total de indicadores: 10+**



