# 🧠 MEMORY DICTIONARY - FOREX QUANTUM BOT

## 📖 PROPÓSITO
Este arquivo serve como o **cérebro central** do projeto. Aqui está toda a memória de:
- Módulos criados e suas funções
- Decisões técnicas e motivos
- Conceitos e definições
- Relações entre componentes
- Lições aprendidas

---

## 🔑 CONCEITOS FUNDAMENTAIS

### Scalping Agressivo (BTCUSD)
**Definição:** Estratégia de trading que visa lucros rápidos em curtos períodos (segundos/minutos) com alta frequência de operações e alavancagem elevada, aplicada EXCLUSIVAMENTE em BTCUSD.

**Características BTCUSD:**
- Tempo de hold: Segundos a poucos minutos
- Alvo de lucro: 50-500 pontos BTC por operação
- Frequência: Alta (10-50+ trades/dia)
- Alavancagem: 1:100 a 1:500+
- Risco por trade: 0.5-2% do capital (DINÂMICO - DNA Engine ajusta)
- Spread típico: 10-30 pontos
- Volatilidade: Extremamente alta vs forex tradicional
- Horário de maior volume: 24/7 (pico em overlap NY/London)

**Diferenças Críticas vs Forex:**
- Mercado 24/7 (sem fechamento)
- Volatilidade 3-5x maior que pares forex
- Gaps menos frequentes (mercado contínuo)
- Influência forte de notícias crypto
- Correlação com mercado crypto geral

### Account FTMO
**Definição:** Empresa de prop trading que requer passar em challenge para obter conta financiada.

**Requisitos Típicos:**
- Profit target: 10% (Phase 1), 5% (Phase 2)
- Max daily loss: 5%
- Max overall loss: 10%
- Minimum trading days: 10
- Consistency rule: Nenhum dia > 30% do profit total

### Sistema AGI-like
**Definição:** Sistema que simula inteligência artificial geral através de múltiplos agentes especializados trabalhando em conjunto de forma autônoma.

**Componentes:**
- Agentes independentes mas conectados
- Tomada de decisão autônoma
- Aprendizado contínuo (futuro)
- Adaptação dinâmica de mercado

### DNA Engine (Sistema Adaptativo)
**Definição:** Núcleo dinâmico que auto-ajusta TODOS os parâmetros do bot em tempo real, sem intervenção humana.

**Princípios:**
- ZERO parâmetros hardcoded
- Auto-otimização contínua baseada em análise em larga escala
- Memória de regimes de mercado
- Mutação controlada com validação de segurança
- Limites absolutos de sobrevivência (exceção necessária)

**Componentes:**
- DNA Strands (conjuntos de parâmetros)
- DNA Mutation Engine (mecanismo de mudança)
- DNA Validation (validação de segurança)
- DNA Memory (memória de regimes)
- Regime Detection (detecção de condições de mercado)

---

## 📦 MÓDULOS DO SISTEMA

### 1. CORE SYSTEM
**Status:** 🟡 Em Desenvolvimento  
**Local:** `src/core/`  
**Função:** Núcleo central que orquestra todos os outros módulos

**Componentes:**
- `main.py` - Ponto de entrada do sistema
- `orchestrator.py` - Coordena agentes e módulos
- `config_manager.py` - Gerencia configurações
- `logger.py` - Sistema de logging

**Dependências:** Todos os módulos principais

---

### 2. MT5 INTEGRATION
**Status:** 🔴 Não Iniciado  
**Local:** `src/execution/mt5/`  
**Função:** Interface com MetaTrader 5

**Componentes:**
- `mt5_connector.py` - Conexão com MT5
- `order_manager.py` - Execução de ordens
- `position_tracker.py` - Rastreamento de posições
- `market_data.py` - Coleta de dados de mercado

**API:** MetaTrader5 Python package

---

### 3. RISK MANAGEMENT
**Status:** 🔴 Não Iniciado  
**Local:** `src/risk/`  
**Função:** Controle de risco e sobrevivência do account

**Componentes:**
- `position_sizing.py` - Cálculo de tamanho de posição
- `stop_loss_manager.py` - Gestão de stops
- `drawdown_monitor.py` - Monitoramento de drawdown
- `exposure_calculator.py` - Cálculo de exposição
- `ftmo_rules.py` - Regras específicas FTMO

**Regras Críticas:**
- Max daily loss: 5%
- Max total loss: 10%
- Max exposure: Definido por estratégia
- Risk per trade: 0.5-2%

---

### 4. STRATEGY ENGINE
**Status:** 🔴 Não Iniciado  
**Local:** `src/strategies/`  
**Função:** Motor de estratégias de trading com DNA adaptativo

**Componentes:**
- `base_strategy.py` - Classe base para estratégias
- `btcusd_scalping_strategy.py` - Estratégia de scalping para BTCUSD
- `dna_engine.py` - Motor de adaptação dinâmica (CRÍTICO)
- `indicator_manager.py` - Indicadores técnicos dinâmicos
- `signal_generator.py` - Geração de sinais
- `pattern_recognition.py` - Reconhecimento de padrões
- `regime_detector.py` - Detecção de regime de mercado

**INDICADORES DINÂMICOS:**
- Períodos e configurações NÃO são hardcoded
- DNA Engine ajusta conforme regime de mercado
- Sistema de pesos dinâmicos para cada estratégia
- Auto-otimização baseada em performance recente

---

### 5. BACKTESTING SYSTEM
**Status:** ✅ Completo  
**Local:** `src/backtesting/`  
**Função:** Testar estratégias em dados históricos com custos realistas

**Componentes:**
- `backtester.py` - Motor de backtesting event-driven (500+ linhas)
- `timeframe_synthesizer.py` - Reconstrução inteligente de M1 (350+ linhas)
- `report_generator.py` - Dashboard HTML glassmorphism (400+ linhas)

**Funcionalidades:**
- ✅ Brownian bridge M1 reconstruction from M5/M15/H1
- ✅ Volume distribution por sessão (Asian/London/NY)
- ✅ FTMO commission modeling ($45/lot/side)
- ✅ Dynamic spread + slippage simulation
- ✅ Complete performance metrics (Sharpe, Sortino, Calmar)
- ✅ FTMO compliance tracking (5%/10% rules)
- ✅ Interactive HTML reports with Plotly charts
- ✅ DNA Engine integration (saves results to memory)

**Métricas Calculadas:**
- Net Profit, Win Rate, Profit Factor
- Sharpe Ratio, Recovery Factor
- Max Drawdown (% e $)
- Costs breakdown (commission/spread/slippage)
- FTMO pass/fail verdict

---

### 6. DATA COLLECTION
**Status:** 🔴 Não Iniciado  
**Local:** `src/data/`  
**Função:** Coleta e processamento de dados

**Componentes:**
- `market_data_fetcher.py` - Dados de mercado
- `news_scraper.py` - Notícias forex
- `economic_calendar.py` - Calendário econômico
- `sentiment_analyzer.py` - Análise de sentimento
- `data_processor.py` - Processamento de dados

**Fontes de Dados:**
- MT5 (preço/volume)
- Forex Factory (notícias)
- Investing.com (calendário)
- Twitter/Reddit (sentimento)

---

### 7. MONITORING & ALERTS
**Status:** 🔴 Não Iniciado  
**Local:** `src/monitoring/`  
**Função:** Monitoramento e notificações

**Componentes:**
- `telegram_notifier.py` - Notificações Telegram
- `dashboard_updater.py` - Atualização do dashboard
- `alert_manager.py` - Gestão de alertas
- `performance_tracker.py` - Tracking de performance
- `health_monitor.py` - Monitor de saúde do sistema

**Notificações:**
- Trades executados
- Alertas de risco
- Metas alcançadas
- Problemas técnicos
- Relatórios diários

---

### 8. DASHBOARD
**Status:** 🔴 Não Iniciado  
**Local:** `src/dashboard/`  
**Função:** Interface web para visualização

**Componentes:**
- `app.py` - Aplicação web (Flask/FastAPI)
- `templates/` - Templates HTML
- `static/` - CSS/JS
- `api_routes.py` - Rotas de API
- `charts.py` - Gráficos interativos

**Funcionalidades:**
- Performance em tempo real
- Posições abertas
- Histórico de trades
- Métricas de risco
- Configurações

---

## 🔗 RELAÇÕES ENTRE MÓDULOS

```
┌─────────────────────────────────────────┐
│          ORCHESTRATOR (Core)            │
│                                         │
│  ┌───────────┐    ┌──────────────┐     │
│  │ Strategy  │───▶│    Risk      │     │
│  │  Engine   │    │ Management   │     │
│  └───────────┘    └───────┬──────┘     │
│         │                 │            │
│         ▼                 ▼            │
│  ┌───────────────────────────┐         │
│  │    MT5 Integration        │         │
│  │   (Order Execution)       │         │
│  └───────────┬───────────────┘         │
│              │                         │
│              ▼                         │
│  ┌──────────────────────┐              │
│  │ Monitoring & Alerts  │              │
│  └──────────────────────┘              │
│                                        │
│  ┌─────────────┐   ┌──────────────┐   │
│  │ Backtesting │   │ Data Collect │   │
│  └─────────────┘   └──────────────┘   │
└────────────────────────────────────────┘
```

---

## 📝 DECISION LOG

### 2026-04-10
**Decisão:** Iniciar com conta demo FTMO  
**Motivo:** Começar pelo mais difícil garante robustez  
**Impacto:** Sistema será extremamente testado antes de produção

**Decisão:** Python como linguagem core  
**Motivo:** Ecossistema rico, bibliotecas de trading, fácil desenvolvimento  
**Impacto:** Desenvolvimento mais rápido, C++ para performance crítica

**Decisão:** Arquitetura multi-agente  
**Motivo:** Escalabilidade, modularidade, conceito AGI  
**Impacto:** Complexidade inicial maior, mas facilita expansão

---

## 🎓 LIÇÕES APRENDIDAS

### De Tentativas Anteriores (1 ano)
1. **Risco > Profit** - Sobreviver é mais importante que lucrar
2. **Dados reais > Dados perfeitos** - Slippage e spreads importam
3. **Simplicidade > Complexidade** - Começar simples, evoluir gradual
4. **Backtesting honesto** - Não overfit, considerar condições reais
5. **Psicologia conta** - Mesmo em bots, configuração emocional importa

### Princípios para Sucesso
1. **Regra de Ouro:** Nunca arriscar mais que 2% por trade
2. **Consistência:** Operações consistentes > Home runs raros
3. **Adaptação:** Mercado muda, sistema deve adaptar
4. **Transparência:** Logs detalhados de tudo
5. **Iteração:** Melhorar continuamente, não buscar perfeição imediata

---

## 🚫 MÓDULOS DESCARTADOS

*Nenhum módulo descartado ainda*

---

## 🔄 HISTÓRICO DE MUDANÇAS

| Data | Módulo | Mudança | Motivo |
|------|--------|---------|--------|
| 2026-04-10 | Todos | Criação inicial | Fundação do projeto |

---

## 📚 REFERÊNCIAS CRUZADAS

- Para visão geral: `docs/executive-overview.md`
- Para agentes: `agents/README.md`
- Para workflows: `workflows/`
- Para configurações: `config/`

---

**Última atualização:** 10 de Abril de 2026  
**Versão:** 1.0.0  
**Mantido por:** Qwen Code (CEO)
