# PLANEJAMENTO PHD: LIVE TRADING COMPLETO COM CADEIA NEURAL

**Data:** 13 de abril de 2026
**Nivel:** Arquitetura de Sistemas de Trading - PhD Senior
**Objetivo:** Transformar live trading inutilizável em sistema com paridade ao backtest de 103k

---

## INDICE

1. [Sintese das Análises](#1-sintese-das-análises)
2. [Gap Critico: Backtest vs Live Trading](#2-gap-critico-backtest-vs-live-trading)
3. [Arquitetura Proposta para Live Trading](#3-arquitetura-proposta-para-live-trading)
4. [Plano de Implementacao em Fases](#4-plano-de-implementacao-em-fases)
5. [Especificacao Tecnica Detalhada](#5-especificacao-tecnica-detalhada)
6. [Sistema de Logs em Tempo Real](#6-sistema-de-logs-em-tempo-real)
7. [Ponte MT5 <-> Bot Ultra-Robusta](#7-ponte-mt5-bot-ultra-robusta)
8. [Cadeia Neural Completa no Live](#8-cadeia-neural-completa-no-live)
9. [Validacao e Testes](#9-validacao-e-testes)

---

## 1. SINTENSE DAS ANÁLISES

### 1.1 Projeto Atual (D:\forex-project2k26)

**Backtest (run_backtest_complete_v2.py):**
- Sistema neural COMPLETO com 140+ agentes
- Cadeia: RegimeDetector -> NeuralSwarm -> QuantumThought -> TrinityCore -> SniperExecutor
- 120+ parâmetros Omega dinâmicos
- Monte Carlo simulation
- Genetic forge para otimização
- Sistemas de risco avançados
- Processamento de dados sintéticos massivo
- **Resultado: 103k de profit**

**Live Trading (run_live_trading.py e main.py):**
- Sistema EXTREMAMENTE simples
- Pouca lógica de análise
- Falta cadeia neural completa
- Extração de dados MT5 precária
- Logs insuficientes
- Comunicação MT5 simples e mal funciona
- **Resultado: Inutilizável**

### 1.2 Projeto Legacy (D:\old_projects\DubaiMatrixASI-main)

**Arquitetura Superior:**
- **100+ arquivos Python, 29 C++, 140+ agentes**
- **Comunicação TCP Socket** (porta 5555) com latência sub-50ms
- **Sistema de logs com 5 handlers** simultâneos
- **Data Engine** como background worker para extração contínua
- **MT5 Bridge** completo com HFT socket
- **120+ parâmetros Omega** auto-ajustáveis
- **Ciclo de consciência:** 250ms (PERCEPCAO -> ANALISE -> DELIBERACAO -> DECISAO -> ACAO -> REFLEXAO)

### 1.3 EAs MQL5

**Problemas Identificados:**
1. EA atual usa **JSON file polling** (5s) - lento demais
2. Legacy usa **TCP Socket** (1ms timer) - superior
3. Bug crítico: ATR handle criado a cada tick no V2
4. Parser JSON frágil
5. PnL double counting
6. File delete prematuro

**EA Ideal =** TCP Socket (legacy) + Smart TP/Trailing (V2) + Risk Limits (mql5/Experts) + Anti-Slippage (legacy)

---

## 2. GAP CRITICO: BACKTEST VS LIVE TRADING

### 2.1 O que Backtest TEM e Live NÃO TEM

| Sistema | Backtest | Live Atual | Gap |
|---------|----------|------------|-----|
| NeuralSwarm (140+ agentes) | ✅ | ❌ | CRÍTICO |
| QuantumThought | ✅ | ❌ | CRÍTICO |
| TrinityCore (decisão) | ✅ | ❌ | CRÍTICO |
| RegimeDetector | ✅ | ❌ | CRÍTICO |
| Monte Carlo Simulation | ✅ | ❌ | CRÍTICO |
| Genetic Forge | ✅ | ❌ | ALTO |
| Omega Params (120+) | ✅ | ❌ | CRÍTICO |
| SniperExecutor | ✅ | ❌ | CRÍTICO |
| Risk Quantum | ✅ | ❌ | CRÍTICO |
| PositionManager | ✅ | ❌ | ALTO |
| OrderFlowMatrix | ✅ | ❌ | ALTO |
| Data Engine (background) | ✅ | ❌ | CRÍTICO |
| Logs 5 handlers | ✅ | ❌ | ALTO |
| TCP Socket HFT | ❌ (sintético) | ❌ | CRÍTICO |
| Extração dados reais | ❌ (sintético) | ❌ (precário) | CRÍTICO |

### 2.2 Transição Sintético -> Real

**Backtest usa:**
- Dados sintéticos gerados offline
- Indicadores calculados em batch
- Simulação perfeita sem latência

**Live precisa:**
- Dados reais extraídos em tempo real do MT5
- Indicadores calculados streaming
- Tratamento de latência, slippage, desconexões
- **MESMA LÓGICA do backtest, mas com dados reais**

---

## 3. ARQUITETURA PROPOSTA PARA LIVE TRADING

### 3.1 Diagrama de Arquitetura

```
┌─────────────────────────────────────────────────────────────────────┐
│                        META TRADER 5 (MT5)                          │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  EA: ForexQuantumBot_EA_V3.mq5 (TCP Socket HFT)               │  │
│  │  - OnTick: Envia dados via TCP socket (porta 5555)            │  │
│  │  - Recebe sinais de trading do Python                         │  │
│  │  - Executa ordens com Smart TP, Trailing ATR, Anti-Slippage   │  │
│  │  - Envia: preço, volume, spread, indicators, positions        │  │
│  └───────────────────────────────────────────────────────────────┘  │
└──────────────────────────┬──────────────────────────────────────────┘
                           │ TCP Socket (porta 5555)
                           │ Protocolo: pipe-delimited
                           │ Latência alvo: <50ms
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     PYTHON LIVE TRADING SYSTEM                      │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  LAYER 1: DATA EXTRACTION (mt5_bridge.py + data_engine.py)   │  │
│  │  - TCP Socket Server (recebe dados do MT5)                    │  │
│  │  - Background worker para extração contínua                   │  │
│  │  - Fallback: MT5 Python API se socket falhar                  │  │
│  │  - Buffers circulares para auditoria                          │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                           │                                         │
│                           ▼                                         │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  LAYER 2: REAL-TIME LOGGING SYSTEM (logger.py)                │  │
│  │  - 5 handlers simultâneos:                                    │  │
│  │    * Console (colorido por nível)                             │  │
│  │    * File (rotating, 10MB max)                                │  │
│  │    * Audit (circular buffer para compliance)                  │  │
│  │    * Socket (envia para dashboard externo)                    │  │
│  │    * Memory (in-memory para acesso rápido)                    │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                           │                                         │
│                           ▼                                         │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  LAYER 3: MARKET ANALYSIS CHAIN                               │  │
│  │  ┌─────────────────────────────────────────────────────────┐  │  │
│  │  │  3a. RegimeDetector                                     │  │  │
│  │  │     - Detecta regime de mercado (trending, ranging, etc)│  │  │
│  │  │     - Usa dados reais do buffer                         │  │  │
│  │  └─────────────────────────────────────────────────────────┘  │  │
│  │                            │                                  │  │
│  │                            ▼                                  │  │
│  │  ┌─────────────────────────────────────────────────────────┐  │  │
│  │  │  3b. NeuralSwarm (140+ agentes)                         │  │  │
│  │  │     - Cada agente analisa aspecto diferente              │  │  │
│  │  │     - Trend, Momentum, Volume, Volatility, etc          │  │  │
│  │  │     - Byzantine consensus para tolerância a falhas       │  │  │
│  │  └─────────────────────────────────────────────────────────┘  │  │
│  │                            │                                  │  │
│  │                            ▼                                  │  │
│  │  ┌─────────────────────────────────────────────────────────┐  │  │
│  │  │  3c. QuantumThought                                     │  │  │
│  │  │     - Convergência de sinais do swarm                   │  │  │
│  │  │     - Monte Carlo simulation (500 paths)                │  │  │
│  │  │     - Probability distribution analysis                  │  │  │
│  │  └─────────────────────────────────────────────────────────┘  │  │
│  │                            │                                  │  │
│  │                            ▼                                  │  │
│  │  ┌─────────────────────────────────────────────────────────┐  │  │
│  │  │  3d. TrinityCore                                        │  │  │
│  │  │     - Decisão final: BUY / SELL / WAIT                  │  │  │
│  │  │     - Validação com OmegaParams (120+ params)            │  │  │
│  │  │     - Risk validation                                   │  │  │
│  │  └─────────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                           │                                         │
│                           ▼                                         │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  LAYER 4: EXECUTION (sniper_executor.py + position_manager)  │  │
│  │  - SniperExecutor: Executa com precisão                       │  │
│  │  - PositionManager: Gerencia posições abertas                 │  │
│  │  - RiskQuantum: Valida risco antes de executar                │  │
│  │  - Envia sinal de volta para MT5 via TCP Socket               │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                           │                                         │
│                           ▼                                         │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  LAYER 5: EVOLUTION (self_optimizer.py + mutation_engine)    │  │
│  │  - Self-optimizer: Ajusta parâmetros em tempo real            │  │
│  │  - MutationEngine: Evolui estratégias                         │  │
│  │  - PerformanceTracker: Monitora performance                   │  │
│  │  - BiologicalImmunity: Previne overfitting                    │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     REAL-TIME TERMINAL OUTPUT                     │
│  - Logs de TODOS os sistemas em tempo real (1 por 1)               │
│  - Dashboard com métricas de performance                           │
│  - Alertas de erros e anomalias                                    │
│  - Status de conexão MT5                                           │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.2 Fluxo de Dados Completo

```
1. MT5 OnTick
   ↓
2. EA envia dados via TCP Socket: "PRICE|105230.50|VOLUME|1234|SPREAD|15|..."
   ↓
3. Python TCP Socket Server recebe
   ↓
4. Data Engine processa e armazena em buffers circulares
   ↓
5. Logger registra recebamento dos dados
   ↓
6. RegimeDetector analisa regime atual
   ↓
7. Logger registra regime detectado
   ↓
8. NeuralSwarm executa 140+ agentes em paralelo
   ↓
9. Logger registra sinais de cada agente (batch)
   ↓
10. QuantumThought converge sinais + Monte Carlo
    ↓
11. Logger registra probabilidade de convergência
    ↓
12. TrinityCore decide BUY/SELL/WAIT
    ↓
13. Logger registra decisão e motivos
    ↓
14. RiskQuantum valida risco
    ↓
15. Logger registra validação de risco
    ↓
16. SniperExecutor prepara ordem
    ↓
17. Logger registra detalhes da ordem
    ↓
18. Envia sinal via TCP Socket para MT5: "BUY|0.01|SL|104500|TP|106000"
    ↓
19. EA no MT5 recebe e executa ordem
    ↓
20. EA confirma execução e envia ack
    ↓
21. Logger registra execução confirmada
    ↓
22. PositionManager atualiza estado
    ↓
23. PerformanceTracker registra trade
    ↓
24. Self-Optimizer ajusta parâmetros se necessário
    ↓
25. Logger registra ajustes
    ↓
26. Volta ao passo 1 (ciclo contínuo a cada tick)
```

---

## 4. PLANO DE IMPLEMENTACAO EM FASES

### FASE 0: Infraestrutura Base (SEMANA 1)
**Objetivo:** Criar fundação sólida para live trading

- [ ] 0.1 Implementar TCP Socket Server (mt5_bridge.py)
  - Porta 5555, protocolo pipe-delimited
  - Reconexão automática
  - Heartbeat a cada 1s
  - Timeout e fallback para MT5 API
  
- [ ] 0.2 Implementar Data Engine (data_engine.py)
  - Background worker para extração contínua
  - Buffers circulares (1000 ticks)
  - Cálculo de indicadores em streaming
  - Armazenamento de OHLCV real
  
- [ ] 0.3 Implementar EA V3 (ForexQuantumBot_EA_V3.mq5)
  - TCP Socket nativo (herdar do legacy)
  - Smart TP/Trailing (herdar do V2)
  - Risk Limits (herdar do mql5/Experts)
  - Anti-Slippage (herdar do legacy)
  - Corrigir bugs identificados (ATR handle, JSON parser, etc)

- [ ] 0.4 Testar comunicação MT5 <-> Python
  - Ping/pong via socket
  - Latência <50ms
  - Estabilidade por 24h

### FASE 1: Sistema de Logs (SEMANA 1-2)
**Objetivo:** Logs ultra-detalhados em tempo real de TODOS os sistemas

- [ ] 1.1 Implementar Logger com 5 handlers
  - Console handler (colorido por nível)
  - File handler (rotating, 10MB max)
  - Audit handler (circular buffer)
  - Socket handler (dashboard externo)
  - Memory handler (in-memory)
  
- [ ] 1.2 Adicionar logs em TODOS os sistemas
  - Data Extraction: recebamento, processamento, buffers
  - RegimeDetector: regime detectado, confiança, indicadores
  - NeuralSwarm: sinais de cada agente (batch por ciclo)
  - QuantumThought: convergência, Monte Carlo results
  - TrinityCore: decisão, motivos, validações
  - RiskQuantum: validação de risco, métricas
  - SniperExecutor: preparação e execução de ordens
  - PositionManager: atualizações de posição
  - SelfOptimizer: ajustes de parâmetros
  - MT5 Bridge: envio/recebimento de sinais
  
- [ ] 1.3 Terminal em tempo real
  - Dashboard com logs de cada sistema
  - Métricas de performance (PnL, drawdown, win rate)
  - Status de conexão MT5
  - Alertas de erros

### FASE 2: Cadeia Neural Completa (SEMANA 2-3)
**Objetivo:** Implementar NO LIVE toda a cadeia neural do backtest

- [ ] 2.1 Port RegimeDetector para live
  - Adaptar para dados reais em streaming
  - Manter mesma lógica do backtest
  
- [ ] 2.2 Port NeuralSwarm para live
  - 140+ agentes funcionando com dados reais
  - Byzantine consensus
  - Otimização para baixa latência
  
- [ ] 2.3 Port QuantumThought para live
  - Monte Carlo simulation (500 paths)
  - Probability distribution analysis
  - Adaptar para dados reais
  
- [ ] 2.4 Port TrinityCore para live
  - Mesma lógica de decisão do backtest
  - OmegaParams validation
  - Risk validation
  
- [ ] 2.5 Port SniperExecutor para live
  - Execução de ordens com dados reais
  - Position management
  - Risk validation

### FASE 3: Sistemas de Risco e Evolução (SEMANA 3-4)
**Objetivo:** Risk management e self-optimization em live

- [ ] 3.1 RiskQuantum para live
  - Validação de risco antes de cada trade
  - Drawdown protection
  - Exposure limits
  
- [ ] 3.2 PositionManager para live
  - Gerenciamento de posições abertas
  - Trailing stops dinâmicos
  - Breakeven automation
  
- [ ] 3.3 Self-Optimizer para live
  - Ajuste de parâmetros em tempo real
  - Mutation engine
  - Biological immunity (previne overfitting)

### FASE 4: Validação e Paridade (SEMANA 4-5)
**Objetivo:** Validar paridade entre backtest e live trading

- [ ] 4.1 Teste com dados sintéticos no live
  - Rodar live trading com dados sintéticos (igual backtest)
  - Comparar resultados: devem ser IDÊNTICOS
  
- [ ] 4.2 Teste com dados reais
  - Rodar live trading com dados reais
  - Comparar lógica: deve ser IDENTÊNTICA ao backtest
  - Aceitar diferenças de PnL devido a slippage/latência
  
- [ ] 4.3 Stress testing
  - 24h de operação contínua
  - Teste de reconexão
  - Teste de alta volatilidade
  
- [ ] 4.4 Documentação final
  - Relatório de paridade
  - Métricas de performance
  - Guia de operação

---

## 5. ESPECIFICACAO TECNICA DETALHADA

### 5.1 Protocolo TCP Socket (MT5 <-> Python)

**Formato:** Pipe-delimited
```
Formato geral: "COMMAND|field1|field2|field3|..."
Exemplo dados MT5->Python: "TICK|BTCUSD|105230.50|105235.00|1234|15|2026-04-13 10:30:00"
Exemplo sinal Python->MT5: "BUY|0.01|104500.00|106000.00|20260412"
```

**Comandos MT5->Python:**
- `TICK` - Dados de tick (preço bid/ask, volume, spread, timestamp)
- `BAR` - Dados de barra (OHLCV)
- `INDICATORS` - Indicadores calculados (ATR, RSI, EMA, etc)
- `POSITIONS` - Posições abertas (símbolo, tipo, lote, SL, TP, PnL)
- `ACCOUNT` - Dados da conta (balance, equity, margin, free_margin)
- `HEARTBEAT` - Keep-alive (a cada 1s)
- `ERROR` - Erros no MT5

**Comandos Python->MT5:**
- `BUY` - Sinal de compra (lote, SL, TP, magic)
- `SELL` - Sinal de venda (lote, SL, TP, magic)
- `CLOSE` - Fechar posição (ticket)
- `MODIFY` - Modificar posição (ticket, novo SL, novo TP)
- `GET_DATA` - Solicitar dados específicos
- `PING` - Teste de conectividade

**Handshake:**
```
1. Python conecta no MT5 (porta 5555)
2. Envia: "HANDSHAKE|ForexQuantumBot|v3.00|20260413"
3. MT5 responde: "HANDSHAKE_OK|ForexQuantumBot_EA_V3|v3.00"
4. Inicia ciclo de dados
```

**Reconexão:**
```
1. Timeout de 3s sem heartbeat
2. Python tenta reconectar 5 vezes (intervalo 1s)
3. Se falhar, fallback para MT5 API
4. Log de erro crítico
5. Alerta no terminal
```

### 5.2 Estrutura de Dados (Buffers)

**Circular Buffer (1000 ticks):**
```python
class CircularBuffer:
    - ticks: array[1000] de TickData
    - indicators: array[1000] de IndicatorData
    - positions: array[100] de PositionData
    - account: array[10] de AccountData
    - logs: array[5000] de LogEntry
```

**TickData:**
```python
@dataclass
class TickData:
    timestamp: datetime
    symbol: str
    bid: float
    ask: float
    volume: int
    spread: float
    indicators: dict  # ATR, RSI, EMA, etc
```

### 5.3 Indicadores em Streaming

**Calculados a cada tick:**
- ATR (14)
- RSI (14)
- EMA (9, 21, 50, 200)
- MACD (12, 26, 9)
- Bollinger Bands (20, 2)
- Volume Profile
- VWAP
- Order Flow metrics

**Otimização:**
- Usar cálculo incremental (só atualiza último valor)
- Cache de indicadores de timeframe maior
- C++ para indicadores complexos (herdar do legacy)

---

## 6. SISTEMA DE LOGS EM TEMPO REAL

### 6.1 Estrutura de Logging

**5 Handlers Simultâneos:**

```python
import logging
from logging.handlers import RotatingFileHandler, MemoryHandler

class LiveTradingLogger:
    def __init__(self):
        self.logger = logging.getLogger('LiveTrading')
        self.logger.setLevel(logging.DEBUG)
        
        # Handler 1: Console (colorido)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(ColorFormatter())
        
        # Handler 2: File (rotating)
        file_handler = RotatingFileHandler(
            'logs/live_trading.log',
            maxBytes=10*1024*1024,  # 10MB
            backupCount=10
        )
        file_handler.setLevel(logging.DEBUG)
        
        # Handler 3: Audit (circular buffer)
        audit_handler = MemoryHandler(
            capacity=1000,
            target=logging.FileHandler('logs/audit.log')
        )
        audit_handler.setLevel(logging.WARNING)
        
        # Handler 4: Socket (dashboard externo)
        socket_handler = SocketHandler('localhost', 9020)
        socket_handler.setLevel(logging.INFO)
        
        # Handler 5: Memory (in-memory para acesso rápido)
        memory_handler = MemoryHandler(capacity=5000)
        memory_handler.setLevel(logging.DEBUG)
        
        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)
        self.logger.addHandler(audit_handler)
        self.logger.addHandler(socket_handler)
        self.logger.addHandler(memory_handler)
```

### 6.2 Log por Sistema

**Cada sistema tem seu próprio logger com formato padronizado:**

```python
# Formato: [TIMESTAMP] [SYSTEM] [LEVEL] [MESSAGE]
[2026-04-13 10:30:00.123] [DATA_ENGINE] [INFO] Received tick: BTCUSD bid=105230.50 ask=105235.00
[2026-04-13 10:30:00.125] [REGIME_DETECTOR] [INFO] Regime: TRENDING_UP (confidence=0.78)
[2026-04-13 10:30:00.150] [NEURAL_SWARM] [INFO] Executing 140 agents...
[2026-04-13 10:30:00.450] [NEURAL_SWARM] [INFO] Swarm converged: BUY signal (strength=0.82)
[2026-04-13 10:30:00.455] [QUANTUM_THOUGHT] [INFO] Monte Carlo (500 paths): P(BUY)=0.76
[2026-04-13 10:30:00.500] [TRINITY_CORE] [INFO] Decision: BUY (validated by OmegaParams)
[2026-04-13 10:30:00.505] [RISK_QUANTUM] [INFO] Risk validated: R:R=2.5, exposure=5%
[2026-04-13 10:30:00.510] [SNIPER_EXECUTOR] [INFO] Sending BUY signal to MT5: lot=0.01, SL=104500, TP=106000
[2026-04-13 10:30:00.550] [MT5_BRIDGE] [INFO] Signal sent to MT5, waiting for ack...
[2026-04-13 10:30:00.600] [MT5_BRIDGE] [INFO] Order executed by MT5: ticket=12345678
[2026-04-13 10:30:00.605] [POSITION_MANAGER] [INFO] Position opened: BTCUSD BUY 0.01 @ 105230.50
[2026-04-13 10:30:00.610] [SELF_OPTIMIZER] [INFO] Params adjusted: omega_risk=0.52 (+0.02)
```

### 6.3 Terminal Output

**Dashboard em tempo real no terminal:**

```
═══════════════════════════════════════════════════════════
║          FOREX QUANTUM BOT - LIVE TRADING               ║
═══════════════════════════════════════════════════════════
║ MT5 Status: ✅ CONNECTED | Latency: 23ms                ║
║ Account: Balance=$10,000 | Equity=$10,150 | PnL=+$150  ║
║ Positions: 1 open (BTCUSD BUY 0.01 @ 105230.50)        ║
═══════════════════════════════════════════════════════════

[DATA ENGINE]  ✅ Receiving ticks @ 120/min
[REGIME]       📈 TRENDING_UP (0.78)
[NEURAL SWARM] 🧠 BUY signal (0.82) - 140/140 agents OK
[QUANTUM]      🎯 P(BUY)=0.76 - Monte Carlo 500 paths OK
[TRINITY]      ✅ DECISION: BUY (OmegaParams validated)
[RISK]         ✅ Risk OK - R:R=2.5, Exposure=5%
[EXECUTOR]     🎯 Signal sent to MT5
[POSITION]     📊 1 position open, PnL=+$150
[OPTIMIZER]    🔧 Params adjusted: omega_risk=0.52

Logs: [INFO] 1,234 | [WARN] 12 | [ERROR] 0 | [AUDIT] 56
```

---

## 7. PONTE MT5 <-> BOT ULTRA-ROBUSTA

### 7.1 EA V3 - ForexQuantumBot_EA_V3.mq5

**Estrutura:**

```mql5
//+------------------------------------------------------------------+
//| ForexQuantumBot_EA_V3.mq5                                        |
//| TCP Socket HFT Bridge + Smart TP/Trailing + Risk Limits          |
//+------------------------------------------------------------------+
#property version   "3.00"

// Input groups (herdar de V2 + mql5/Experts + legacy)
input group "=== CONNECTION ==="
input string   InpSocketHost = "127.0.0.1";
input int      InpSocketPort = 5555;
input int      InpTimeoutMs = 3000;

input group "=== TRADING ==="
input string   InpSymbol = "BTCUSD";
input ENUM_TIMEFRAMES InpTimeframe = PERIOD_M5;
input double   InpLotSize = 0.01;
input int      InpMagicNumber = 20260412;
input int      InpMaxPositions = 1;

input group "=== RISK ==="
input double   InpMaxDailyLoss = 5000.0;
input double   InpMaxTotalLoss = 10000.0;
input int      InpMaxTradesPerDay = 10;

input group "=== SMART TP/TRAILING ==="
input bool     InpUseSmartTP = true;
input bool     InpUseTrailingATR = true;
input double   InpTrailingATRMult = 2.0;
input bool     InpUseBreakeven = true;
input double   InpBreakevenProfit = 100.0;
```

**TCP Socket Implementation (herdar do legacy):**

```mql5
// Socket variables
int socket_handle = INVALID_HANDLE;
string socket_host;
int socket_port;

// OnTick: send data every tick
void OnTick() {
    // Collect market data
    double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
    double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
    long volume = SymbolInfoInteger(_Symbol, SYMBOL_VOLUME);
    double spread = ask - bid;
    
    // Get indicators
    double atr = getATR(14);
    double rsi = getRSI(14);
    double ema9 = getEMA(9);
    
    // Format and send
    string data = StringFormat("TICK|%s|%.2f|%.2f|%d|%.2f|%.2f|%.2f|%.2f|%s",
        _Symbol, bid, ask, volume, spread, atr, rsi, ema9,
        TimeToString(TimeCurrent()));
    
    sendToSocket(data);
    
    // Check for incoming signals
    checkForSignals();
    
    // Manage positions (Smart TP, Trailing)
    managePositions();
}

// TCP Socket connection
bool connectToPython() {
    socket_handle = SocketCreate();
    if(socket_handle == INVALID_HANDLE) return false;
    
    bool connected = SocketConnect(socket_handle, socket_host, socket_port, InpTimeoutMs);
    if(connected) {
        // Send handshake
        string handshake = StringFormat("HANDSHAKE|ForexQuantumBot_EA_V3|v3.00|%d", InpMagicNumber);
        SocketSend(socket_handle, StringToCharArray(handshake));
        
        // Wait for ack
        char ack[];
        int bytes = SocketRead(socket_handle, ack, 1024, 3000);
        if(bytes > 0) {
            Print("Handshake OK: ", CharArrayToString(ack));
            return true;
        }
    }
    return false;
}
```

### 7.2 Python TCP Socket Server

```python
import socket
import threading
import queue

class MT5Bridge:
    def __init__(self, host='127.0.0.1', port=5555):
        self.host = host
        self.port = port
        self.server_socket = None
        self.client_socket = None
        self.connected = False
        self.data_queue = queue.Queue()
        self.signal_queue = queue.Queue()
        
    def start(self):
        """Start TCP socket server"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(1)
        
        logger.info(f"[MT5_BRIDGE] Listening on {self.host}:{port}")
        
        # Accept connection in thread
        accept_thread = threading.Thread(target=self.accept_connection)
        accept_thread.daemon = True
        accept_thread.start()
        
    def accept_connection(self):
        """Accept MT5 connection"""
        try:
            self.client_socket, addr = self.server_socket.accept()
            logger.info(f"[MT5_BRIDGE] MT5 connected: {addr}")
            
            # Wait for handshake
            handshake = self.client_socket.recv(1024).decode()
            if 'HANDSHAKE' in handshake:
                logger.info(f"[MT5_BRIDGE] Handshake received: {handshake}")
                self.client_socket.send(b"HANDSHAKE_OK|ForexQuantumBot_Python|v3.00")
                self.connected = True
                
                # Start data receiver
                recv_thread = threading.Thread(target=self.receive_data)
                recv_thread.daemon = True
                recv_thread.start()
                
                # Start heartbeat
                heartbeat_thread = threading.Thread(target=self.send_heartbeat)
                heartbeat_thread.daemon = True
                heartbeat_thread.start()
        except Exception as e:
            logger.error(f"[MT5_BRIDGE] Connection error: {e}")
            self.reconnect()
            
    def receive_data(self):
        """Receive data from MT5 continuously"""
        while self.connected:
            try:
                data = self.client_socket.recv(4096).decode()
                if data:
                    self.data_queue.put(data)
                    logger.debug(f"[MT5_BRIDGE] Received: {data[:100]}...")
                else:
                    logger.warning("[MT5_BRIDGE] Connection closed by MT5")
                    self.reconnect()
                    break
            except Exception as e:
                logger.error(f"[MT5_BRIDGE] Receive error: {e}")
                self.reconnect()
                break
                
    def send_signal(self, signal: str):
        """Send trading signal to MT5"""
        try:
            self.client_socket.send(signal.encode())
            logger.info(f"[MT5_BRIDGE] Signal sent: {signal}")
        except Exception as e:
            logger.error(f"[MT5_BRIDGE] Send error: {e}")
            self.reconnect()
```

---

## 8. CADEIA NEURAL COMPLETA NO LIVE

### 8.1 Adaptação Backtest -> Live

**Backtest (dados sintéticos):**
```python
# run_backtest_complete_v2.py
data = generate_synthetic_data(params)
indicators = calculate_indicators_batch(data)
regime = detect_regime(indicators)
swarm_signals = run_neural_swarm(indicators)
convergence = quantum_thought(swarm_signals)
decision = trinity_core(convergence)
```

**Live (dados reais):**
```python
# run_live_trading_v2.py (NOVO)
data = receive_real_data_from_mt5()  # TCP Socket
indicators = calculate_indicators_streaming(data)  # Incremental
regime = detect_regime_live(indicators)  # Mesma lógica, dados reais
swarm_signals = run_neural_swarm_live(indicators)  # Mesma lógica
convergence = quantum_thought_live(swarm_signals)  # Mesma lógica
decision = trinity_core_live(convergence)  # Mesma lógica
```

**Key Difference:**
- Backtest: batch processing (todo o histórico de uma vez)
- Live: streaming processing (dados chegam em tempo real)
- **Mesma lógica matemática, diferente fluxo de dados**

### 8.2 Implementação da Cadeia

**Arquivo: live_trading/neural_chain.py**

```python
class LiveNeuralChain:
    def __init__(self):
        self.regime_detector = RegimeDetector()
        self.neural_swarm = NeuralSwarm()
        self.quantum_thought = QuantumThought()
        self.trinity_core = TrinityCore()
        self.risk_quantum = RiskQuantum()
        self.sniper_executor = SniperExecutor()
        
        # Load omega params
        self.omega_params = OmegaParameterSpace.load()
        
    def process_tick(self, tick_data):
        """Process single tick through entire neural chain"""
        
        # 1. Calculate indicators (streaming)
        indicators = self.calculate_indicators(tick_data)
        
        # 2. Detect regime
        regime = self.regime_detector.detect(indicators)
        logger.info(f"[REGIME] {regime.regime} (confidence={regime.confidence:.2f})")
        
        # 3. Run neural swarm (140+ agents)
        swarm_result = self.neural_swarm.analyze(indicators, regime)
        logger.info(f"[SWARM] {swarm_result.signal} (strength={swarm_result.strength:.2f})")
        
        # 4. Quantum thought (Monte Carlo convergence)
        convergence = self.quantum_thought.converge(swarm_result, indicators)
        logger.info(f"[QUANTUM] P({convergence.signal})={convergence.probability:.2f}")
        
        # 5. Trinity core decision
        decision = self.trinity_core.decide(convergence, regime, self.omega_params)
        logger.info(f"[TRINITY] Decision: {decision.action} (validated={decision.validated})")
        
        # 6. Risk validation
        risk_validated = self.risk_quantum.validate(decision, indicators)
        logger.info(f"[RISK] Validated: {risk_validated.approved} (R:R={risk_validated.risk_reward})")
        
        # 7. Execute if approved
        if risk_validated.approved:
            order = self.sniper_executor.prepare_order(decision, indicators, risk_validated)
            logger.info(f"[EXECUTOR] Order prepared: {order}")
            return order
        else:
            logger.info(f"[EXECUTOR] Order rejected by risk: {risk_validated.reason}")
            return None
```

---

## 9. VALIDACAO E TESTES

### 9.1 Teste de Paridade (Sintético vs Real)

**Objetivo:** Provar que live trading com dados sintéticos = backtest

```python
def test_parity_synthetic():
    """Run live trading with synthetic data and compare to backtest"""
    
    # 1. Generate synthetic data (same as backtest)
    synthetic_data = generate_synthetic_data(params)
    
    # 2. Run backtest
    backtest_results = run_backtest(synthetic_data)
    
    # 3. Run live trading with same data (simulated MT5 feed)
    live_results = run_live_with_synthetic_data(synthetic_data)
    
    # 4. Compare
    assert backtest_results.trades == live_results.trades
    assert backtest_results.profit ≈ live_results.profit  # tolerance 0.1%
    assert backtest_results.drawdown ≈ live_results.drawdown
    
    print("✅ PARITY TEST PASSED: Live trading = Backtest")
```

### 9.2 Teste com Dados Reais

**Objetivo:** Validar que live trading funciona com dados reais

```python
def test_real_data():
    """Run live trading with real MT5 data"""
    
    # 1. Connect to MT5
    mt5_bridge.connect()
    
    # 2. Run for 24 hours
    results = run_live_for_24h()
    
    # 3. Validate
    assert results.trades_executed > 0
    assert results.errors == 0
    assert results.reconnections < 5
    assert results.latency_p95 < 100ms
    
    print("✅ REAL DATA TEST PASSED")
```

### 9.3 Stress Testing

```python
def test_stress():
    """Stress test the system"""
    
    # 1. 24h continuous operation
    run_live_for_24h()
    
    # 2. Reconnection test (kill MT5, restart)
    kill_mt5()
    wait(10s)
    start_mt5()
    assert system_reconnected_automatically()
    
    # 3. High volatility test (simulate spike)
    simulate_volatility_spike()
    assert system_handled_gracefully()
    
    print("✅ STRESS TEST PASSED")
```

---

## 10. ARQUIVOS A SEREM CRIADOS

### 10.1 Estrutura de Diretórios

```
D:\forex-project2k26\
├── live_trading/
│   ├── __init__.py
│   ├── run_live_trading_v2.py          # NOVO: Entry point completo
│   ├── mt5_bridge.py                    # NOVO: TCP Socket bridge
│   ├── data_engine.py                   # NOVO: Background data extraction
│   ├── neural_chain.py                  # NOVO: Cadeia neural completa
│   ├── logger.py                        # NOVO: Sistema de logs 5 handlers
│   ├── terminal_dashboard.py            # NOVO: Terminal output
│   └── config/
│       ├── omega_params_live.json       # Params para live
│       └── socket_config.json           # Socket config
│
├── mql5/
│   └── Experts/
│       └── ForexQuantumBot_EA_V3.mq5   # NOVO: EA V3 completo
│
├── logs/
│   ├── live_trading.log                 # Generated
│   ├── audit.log                        # Generated
│   └── errors.log                       # Generated
│
└── docs/
    ├── ANALISE_PROJETO_ATUAL.md         # ✅ Criado
    ├── ANALISE_PROJETO_LEGACY.md        # ✅ Criado
    ├── ANALISE_MQL5_EAS.md              # ✅ Criado
    └── PLANEJAMENTO_PHD_LIVE_TRADING.md # ✅ Este arquivo
```

---

## 11. CHECKLIST FINAL

### Pré-Implementação
- [x] Análise profunda do projeto atual
- [x] Análise profunda do projeto legacy
- [x] Análise dos EAs MQL5
- [x] Planejamento PhD criado

### Implementação
- [ ] FASE 0: Infraestrutura base (MT5 bridge, data engine, EA V3)
- [ ] FASE 1: Sistema de logs completo
- [ ] FASE 2: Cadeia neural completa no live
- [ ] FASE 3: Risk e evolution systems
- [ ] FASE 4: Validação e paridade

### Validação
- [ ] Teste de paridade sintético
- [ ] Teste com dados reais
- [ ] Stress testing 24h
- [ ] Documentação final

---

## 12. METRICAS DE SUCESSO

| Metrica | Alvo |
|---------|------|
| Latência MT5 <-> Python | <50ms |
| Uptime contínuo | 24h+ |
| Reconexões automáticas | 100% sucesso |
| Paridade backtest/live (sintético) | 99.9% |
| Logs de todos os sistemas | 100% cobertura |
| Cadeia neural no live | 140 agentes ativos |
| Erros de execução | 0 |
| Drawdown controlado | <5% |

---

**CONCLUSÃO:**

Este planejamento detalha a transformação completa do live trading de um sistema simples e inutilizável para um sistema com paridade ao backtest de 103k. A chave é:

1. **Usar a MESMA LÓGICA do backtest** (cadeia neural completa)
2. **Adaptar o FLUXO DE DADOS** de batch (sintético) para streaming (real)
3. **Implementar infraestrutura robusta** (TCP socket, logs, buffers)
4. **Validar paridade** com testes sintéticos antes de ir para dados reais

O projeto legacy forneceu a arquitetura base (TCP socket, data engine, logs 5 handlers, EA HFT).
O projeto atual forneceu a cadeia neural completa (RegimeDetector, NeuralSwarm, QuantumThought, TrinityCore).

Agora é **IMPLEMENTAR FASE A FASE**.
