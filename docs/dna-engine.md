# 🧬 DNA ENGINE - SISTEMA ADAPTATIVO

## 📖 VISÃO GERAL

O **DNA Engine** é o coração adaptativo do Forex Quantum Bot. Ele é responsável por **auto-ajustar todos os parâmetros** do sistema em tempo real, sem intervenção humana, baseado em análise complexa e em larga escala do mercado de BTCUSD.

---

## 🎯 FILOSOFIA DE DESIGN

### Princípios Fundamentais:

1. **ZERO HARDCODED PARAMETERS**
   - ❌ NENUM parâmetro fixo no código
   - ✅ TODOS os parâmetros são dinâmicos e ajustáveis
   - ✅ Sistema aprende e evolui continuamente

2. **ADAPTAÇÃO CONTÍNUA**
   - ✅ Analisa condições de mercado em tempo real
   - ✅ Ajusta parâmetros automaticamente
   - ✅ Aprende com acertos e erros
   - ✅ Evolui com o tempo

3. **META-APRENDIZADO**
   - ✅ Sistema ajusta como ele ajusta (meta-parameters)
   - ✅ Velocidade de adaptação dinâmica
   - ✅ Sensibilidade a mudanças de mercado
   - ✅ Memória de regimes anteriores

---

## 🧬 COMPONENTES DO DNA

### 1. **DNA STRANDS** (Parâmetros Ajustáveis)

Cada "strand" é um conjunto de parâmetros relacionados:

#### A. Trading Strand
```json
{
  "trading_params": {
    "timeframe_primary": "M5",
    "timeframe_context": "M15",
    "timeframe_trend": "H1",
    "entry_threshold": 0.75,
    "exit_threshold": 0.65,
    "min_confidence": 0.70,
    "max_spread_tolerance_pips": 15,
    "max_slippage_tolerance_pips": 10,
    "volatility_filter_enabled": true,
    "news_filter_enabled": true,
    "news_filter_minutes_before": 15,
    "news_filter_minutes_after": 10
  }
}
```

#### B. Risk Strand
```json
{
  "risk_params": {
    "base_risk_percent": 1.0,
    "min_risk_percent": 0.25,
    "max_risk_percent": 2.5,
    "risk_adjustment_mode": "aggressive",
    "risk_increase_after_wins": 0.1,
    "risk_decrease_after_losses": 0.25,
    "max_consecutive_losses_before_cooldown": 3,
    "cooldown_duration_minutes": 60,
    "max_daily_loss_percent": 5.0,
    "max_total_drawdown_percent": 10.0,
    "min_risk_reward_ratio": 1.5,
    "ideal_risk_reward_ratio": 2.0,
    "position_sizing_model": "kelly_criterion",
    "correlation_filter_enabled": true
  }
}
```

#### C. Strategy Strand
```json
{
  "strategy_params": {
    "active_strategy": "momentum_scalping_v3",
    "strategy_weights": {
      "momentum_scalping": 0.45,
      "mean_reversion": 0.25,
      "breakout_trading": 0.20,
      "order_flow": 0.10
    },
    "indicator_periods": {
      "ema_fast": 9,
      "ema_slow": 21,
      "ema_trend": 200,
      "rsi_period": 14,
      "macd_fast": 12,
      "macd_slow": 26,
      "macd_signal": 9,
      "atr_period": 14,
      "bollinger_period": 20,
      "bollinger_std": 2.0
    },
    "pattern_recognition_enabled": true,
    "pattern_confidence_threshold": 0.75,
    "confluence_required": true,
    "min_indicators_agreeing": 3
  }
}
```

#### D. Execution Strand
```json
{
  "execution_params": {
    "order_type": "market",
    "max_orders_simultaneous": 3,
    "pyramiding_enabled": true,
    "max_pyramid_levels": 2,
    "pyramid_spacing_pips": 20,
    "pyramid_size_reduction": 0.5,
    "partial_close_enabled": true,
    "partial_close_at_rr": 1.0,
    "partial_close_percent": 0.5,
    "trailing_stop_enabled": true,
    "trailing_stop_type": "atr_based",
    "trailing_stop_multiplier": 1.5,
    "break_even_at_rr": 0.8,
    "commission_per_lot": 3.5,
    "swap_rate_long": -0.75,
    "swap_rate_short": -0.50
  }
}
```

#### E. Market Regime Strand
```json
{
  "market_regime": {
    "current_regime": "trending_bullish",
    "regime_confidence": 0.82,
    "volatility_regime": "medium",
    "atr_14_current": 285.5,
    "atr_14_avg_30d": 312.8,
    "volatility_percentile": 42.5,
    "trend_strength": 0.75,
    "market_phase": "accumulation",
    "dominant_timeframe": "M5",
    "avg_volume_20d": 15234.5,
    "volume_trend": "increasing",
    "liquidity_score": 0.88,
    "spread_avg_pips": 12.5,
    "spread_regime": "normal"
  }
}
```

### 2. **DNA MUTATION ENGINE** (Mecanismo de Mudança)

Responsável por ajustar os parâmetros:

```python
class DNAMutationEngine:
    """
    Mecanismo que muta o DNA do bot baseado em:
    1. Performance recente
    2. Condições de mercado
    3. Regime atual (tendência, volatilidade)
    4. Análise em larga escala
    """
    
    def mutate(self, current_dna, market_analysis, performance_metrics):
        """
        Aplica mutações ao DNA atual
        """
        # 1. Analisar performance recente
        performance_score = self.evaluate_performance(performance_metrics)
        
        # 2. Detectar mudança de regime
        regime_change = self.detect_regime_change(market_analysis)
        
        # 3. Calcular magnitude da mutação
        mutation_magnitude = self.calculate_mutation_magnitude(
            performance_score, regime_change
        )
        
        # 4. Aplicar mutações ponderadas
        new_dna = self.apply_mutations(current_dna, mutation_magnitude)
        
        # 5. Validar novo DNA
        if self.validate_dna(new_dna):
            return new_dna
        else:
            return current_dna  # Rejeitar mutação inválida
```

### 3. **DNA VALIDATION** (Validação de Segurança)

Garante que mutações não comprometam o sistema:

```python
def validate_dna(self, dna):
    """
    Valida se o novo DNA é seguro e funcional
    """
    checks = [
        self.check_risk_limits(dna),           # Não violar limites de risco
        self.check_mathematical_bounds(dna),   # Valores matematicamente válidos
        self.check_logical_consistency(dna),   # Sem contradições internas
        self.check_ftmo_compliance(dna),       # Dentro das regras FTMO
        self.check_extreme_values(dna),        # Sem valores extremos
    ]
    
    return all(checks)
```

### 4. **DNA MEMORY** (Memória de Regimes)

Armazena configurações que funcionaram em regimes similares:

```json
{
  "dna_memory": {
    "trending_bullish_low_vol": {
      "occurrences": 15,
      "success_rate": 0.68,
      "best_params": {
        "risk_percent": 1.5,
        "strategy": "momentum_scalping",
        "trailing_stop_multiplier": 2.0
      },
      "avg_profit_per_trade": 12.5,
      "max_drawdown": 3.2
    },
    "ranging_high_vol": {
      "occurrences": 8,
      "success_rate": 0.55,
      "best_params": {
        "risk_percent": 0.75,
        "strategy": "mean_reversion",
        "trailing_stop_multiplier": 1.5
      },
      "avg_profit_per_trade": 8.3,
      "max_drawdown": 4.8
    }
  }
}
```

---

## 🔬 ANÁLISE EM LARGA ESCALA

### Fontes de Dados para Análise:

1. **Dados de Mercado (MT5)**
   - Price action (tick, M1, M5, M15, H1, H4, D1)
   - Volume
   - Spread
   - Order book (se disponível)

2. **Indicadores Técnicos**
   - 50+ indicadores calculados
   - Combinações dinâmicas
   - Correlações entre indicadores

3. **Dados On-Chain (BTC)**
   - Hash rate
   - Difficulty
   - Exchange flows
   - Whale movements
   - Funding rates

4. **Sentimento de Mercado**
   - Fear & Greed Index
   - Social media (Twitter, Reddit)
   - News sentiment analysis
   - Google Trends

5. **Macro Economia**
   - DXY (Dollar Index)
   - US10Y (Treasury yields)
   - SPX/NDX (correlação)
   - Gold (safe haven flows)

6. **Dados FTMO**
   - Performance histórica
   - Drawdown patterns
   - Win rate por horário
   - Profit factor por regime

---

## 🧠 PROCESSO DE ADAPTAÇÃO

### Ciclo de Adaptação (a cada 5 minutos):

```
┌─────────────────────────────────────────┐
│ 1. COLETAR DADOS EM LARGA ESCALA       │
│    - Market data (últimas 500 candles)  │
│    - Indicadores técnicos (50+)         │
│    - Sentimento e macro                 │
│    - Performance recente do bot         │
└───────────────┬─────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────┐
│ 2. ANALISAR REGIME ATUAL                │
│    - Tendência (bullish/bearish/range)  │
│    - Volatilidade (low/med/high)        │
│    - Liquidez (tight/normal/wide)       │
│    - Momentum (strong/weak)             │
└───────────────┬─────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────┐
│ 3. CONSULTAR DNA MEMORY                 │
│    - Buscar regimes similares           │
│    - Extrair params de maior sucesso    │
│    - ponderar por ocorrência e SR       │
└───────────────┬─────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────┐
│ 4. CALCULAR MUTAÇÕES                    │
│    - Comparar DNA atual com ótimo       │
│    - Calcular delta de mudança          │
│    - Aplicar smoothing (não mudar brusco)│
└───────────────┬─────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────┐
│ 5. VALIDAR NOVO DNA                     │
│    - Check risk limits                  │
│    - Check FTMO compliance              │
│    - Check mathematical bounds          │
│    - Reject if invalid                  │
└───────────────┬─────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────┐
│ 6. APLICAR E LOGAR                      │
│    - Atualizar DNA                      │
│    - Logar mudança e racional           │
│    - Notificar via Telegram             │
│    - Continuar operação                 │
└─────────────────────────────────────────┘
```

---

## 📊 EXEMPLO DE MUTAÇÃO EM AÇÃO

### Cenário: Mercado mudando de tendência

**Situação Inicial:**
```
DNA Atual:
- Regime: trending_bullish
- Strategy: momentum_scalping (peso 0.60)
- Risk: 1.5%
- Trailing: 2.0x ATR
```

**Detecção:**
```
⚠️ DETECTADA MUDANÇA DE REGIME
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Regime anterior: trending_bullish (confiança 0.82)
📊 Regime atual: ranging_neutral (confiança 0.71)
📊 Volatilidade: decreasing (-15% vs média)
📊 Volume: declining (-22% vs média)
📊 Momentum: enfraquecendo (RSI 48, MACD cruzando para baixo)
```

**Mutações Aplicadas:**
```
🧬 MUTAÇÃO DE DNA APLICADA
━━━━━━━━━━━━━━━━━━━━━━━━━
🔄 Mudanças:

1. Strategy Weights:
   - momentum_scalping: 0.60 → 0.30 ⬇️
   - mean_reversion: 0.25 → 0.50 ⬆️
   - breakout_trading: 0.20 → 0.15 ⬇️
   - order_flow: 0.10 → 0.05 ⬇️

2. Risk Parameters:
   - base_risk_percent: 1.5 → 1.0 ⬇️
   - Razão: Menor confiança em mercado ranging

3. Exit Strategy:
   - trailing_stop_multiplier: 2.0 → 1.5 ⬇️
   - partial_close_at_rr: 1.0 → 0.8 ⬇️
   - Razão: Ranges têm reversões rápidas

4. Entry Filters:
   - min_confidence: 0.70 → 0.75 ⬆️
   - min_indicators_agreeing: 3 → 4 ⬆️
   - Razão: Maior seletividade em mercado sem tendência

✅ DNA ATUALIZADO COM SUCESSO
📊 Configuração salva em: DNA Memory (ranging_neutral_low_vol)
⏰ Próxima reavaliação: 5 minutos
```

---

## 🔒 SEGURANÇA E LIMITES

### Limites Absolutos (Hard Limits - Únicos não-hardcoded):

Estes são **limites de segurança** que NUNCA mudam (exceto se você manualmente autorizar):

```json
{
  "absolute_limits": {
    "max_risk_per_trade_percent": 2.5,
    "max_daily_loss_percent": 5.0,
    "max_total_drawdown_percent": 10.0,
    "max_positions_simultaneous": 5,
    "min_risk_reward_ratio": 1.2,
    "ftmo_rules_compliance": true
  }
}
```

**Por quê?**
- Estes são limites de **sobrevivência**, não de performance
- Se todos os parâmetros são dinâmicos, precisamos de um "chão de segurança"
- Você pode ajustá-los manualmente quando quiser, mas o bot não os muda sozinho

---

## 📋 ARMAZENAMENTO

### Estrutura de Arquivos:

```
config/
├── dna/
│   ├── current_dna.json              # DNA atual em uso
│   ├── dna_memory.json               # Memória de regimes
│   ├── dna_evolution_log.json        # Log de todas as mutações
│   ├── absolute_limits.json          # Limites de segurança
│   └── regime_detection_log.json     # Histórico de detecções de regime
```

---

## 🎓 METRICAS DE EFICÁCIA DO DNA

### O que monitorar:

1. **Adaptabilidade**
   - Tempo médio para detectar mudança de regime
   - Tempo para adaptar parâmetros
   - Sucesso rate pós-mutação

2. **Performance por Regime**
   - Win rate por configuração de regime
   - Profit factor por regime
   - Max drawdown por regime

3. **Evolução**
   - Melhoria ao longo do tempo (semana a semana)
   - Diversidade de regimes encontrados
   - Qualidade da DNA Memory

---

**Criado em:** 10 de Abril de 2026  
**Versão:** 1.0.0  
**Status:** Conceito aprovado, implementação pendente  
**Prioridade:** 🔴 CRÍTICA (núcleo do sistema adaptativo)
