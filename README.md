# 🚀 FOREX QUANTUM BOT

## 📊 VISÃO GERAL

Bot de trading quântico de nova geração para **BTCUSD** com arquitetura **AGI-like multi-agente** e **DNA adaptativo** (zero parâmetros hardcoded).

### 🎯 Meta Inicial
- **Capital FTMO Demo:** $100,000 USD
- **Profit Target Phase 1:** 10% ($10,000)
- **Profit Target Phase 2:** 5% ($5,000)
- **Min Trading Days:** 10 dias
- **Max Daily Loss:** 5% ($5,000)
- **Max Total Loss:** 10% ($10,000)

### 🧬 Diferencial Único
**DNA Engine** - Sistema que auto-ajusta TODOS os parâmetros em tempo real:
- Zero parâmetros hardcoded
- Adaptação contínua a regimes de mercado
- Memória de configurações otimizadas
- Análise em larga escala (técnica + on-chain + sentimento + macro)

---

## 🏗️ ARQUITETURA

```
┌─────────────────────────────────────────────────┐
│              ORCHESTRATOR (Core)                │
│                                                 │
│  ┌──────────────┐      ┌──────────────────┐    │
│  │   DNA Engine │◄────►│  Strategy Engine │    │
│  │  (Adaptativo)│      │   (BTCUSD)       │    │
│  └──────────────┘      └────────┬─────────┘    │
│         │                       │              │
│         ▼                       ▼              │
│  ┌──────────────────────────────────────┐      │
│  │        Risk Management               │      │
│  │     (FTMO Rules + Survival)          │      │
│  └───────────────┬──────────────────────┘      │
│                  │                             │
│                  ▼                             │
│  ┌──────────────────────────────┐              │
│  │    MT5 Execution Engine      │              │
│  │      (BTCUSD Only)           │              │
│  └──────────────┬───────────────┘              │
│                 │                              │
│                 ▼                              │
│  ┌──────────────────────────┐                  │
│  │  Monitoring & Telegram   │                  │
│  └──────────────────────────┘                  │
│                                                 │
│  ┌─────────────┐    ┌──────────────────┐       │
│  │ Backtesting │    │ Large-Scale Data │       │
│  │   System    │    │   Analysis       │       │
│  └─────────────┘    └──────────────────┘       │
└─────────────────────────────────────────────────┘
```

---

## 📂 ESTRUTURA DO PROJETO

```
forex-project2k26/
├── docs/                    # Documentação executiva
│   ├── executive-overview.md
│   ├── memory-dictionary.md
│   ├── dna-engine.md
│   └── master-todo.md
│
├── agents/                  # Definições de agentes
│   ├── market-researcher.md
│   ├── risk-manager.md
│   └── ... (em criação)
│
├── workflows/               # Manuais de execução
├── config/                  # Configurações (JSON)
│   └── dna/                 # DNA adaptativo
│
├── src/                     # Código fonte
│   ├── core/                # Núcleo do sistema
│   ├── strategies/          # Estratégias BTCUSD
│   ├── risk/                # Gestão de risco
│   ├── execution/mt5/       # Execução MT5
│   ├── data/                # Coleta de dados
│   ├── dna/                 # DNA Engine (CRÍTICO)
│   ├── dashboard/           # Interface web
│   ├── monitoring/          # Monitoramento e alertas
│   └── utils/               # Utilitários
│
├── tests/                   # Testes
├── data/                    # Dados históricos
└── logs/                    # Logs do sistema
```

---

## 🛠️ STACK TECNOLÓGICO

| Área | Tecnologia |
|------|-----------|
| **Core** | Python 3.10+ |
| **Trading** | MetaTrader5 (MT5) |
| **Análise Técnica** | TA-Lib, pandas-ta |
| **Dados** | pandas, numpy, scipy |
| **Database** | SQLite |
| **Dashboard** | FastAPI + HTML/CSS/JS |
| **Notificações** | Telegram Bot API |
| **Web Scraping** | requests, BeautifulSoup, aiohttp |
| **Otimização** | Optuna, scikit-learn |
| **Versionamento** | GitHub |

---

## 🚀 INSTALAÇÃO

### 1. Pré-requisitos
- Python 3.10+
- MetaTrader 5 instalado
- Conta FTMO (demo para testes)
- Telegram Bot Token (para notificações)

### 2. Instalar dependências
```bash
pip install -r requirements.txt
```

### 3. Configurar TA-Lib (Windows)
1. Baixar TA-Lib C library: https://github.com/cgohlke/talib-build/releases
2. Instalar wheel correspondente ao seu Python
3. Depois: `pip install ta-lib`

### 4. Configurar MT5
1. Instalar MetaTrader 5
2. Login na conta FTMO demo
3. Habilitar algoritmic trading
4. Adicionar BTCUSD aos símbolos

### 5. Configurar Telegram
1. Criar bot via @BotFather no Telegram
2. Obter token e chat ID
3. Salvar em `config/telegram-config.json`

---

## 📋 PRÓXIMOS PASSOS

Veja `docs/master-todo.md` para lista completa de tarefas.

### Prioridades Atuais:
1. ✅ Estrutura de diretórios
2. ✅ Documentação executiva
3. ⬜ DNA Engine (código principal)
4. ⬜ Integração MT5
5. ⬜ Risk Management system
6. ⬜ Strategy Engine
7. ⬜ Backtesting system
8. ⬜ Dashboard e monitoring

---

## 📞 COMUNICAÇÃO

### Telegram
- Trades executados
- Alertas de risco
- Mutações de DNA
- Relatórios diários

### Dashboard Web
- Performance em tempo real
- Posições abertas
- DNA atual (parâmetros dinâmicos)
- Regime de mercado
- Métricas FTMO

---

## 🔐 SEGURANÇA

- **NUNCA** commitar tokens/secrets
- **SEMPRE** usar variáveis de ambiente
- **SEMPRE** fazer backup via Git
- **NUNCA** operar em conta real sem validação completa

---

## 📜 LICENÇA

Projeto privado - Forex Quantum Bot

---

**Versão:** 0.0.1-alpha  
**Criado em:** 10 de Abril de 2026  
**CEO:** Qwen Code (IA)  
**Fundador:** [Você]
