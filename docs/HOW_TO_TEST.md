# 📘 GUIA DO USUÁRIO - FOREX QUANTUM BOT

## 🎯 COMO TESTAR NA CONTA DEMO FTMO

---

## 📋 PRÉ-REQUISITOS

Antes de começar, certifique-se de que:

1. ✅ **MT5 está instalado** e rodando
2. ✅ **Logado na conta FTMO Demo** ($100K)
3. ✅ **BTCUSD está disponível** na lista de símbolos
4. ✅ **Python 3.10+** instalado
5. ✅ **Dependências instaladas** (`pip install -r requirements.txt`)

---

## 🚀 PASSO A PASSO PARA TESTAR

### **Passo 1: Abrir MT5**
```
1. Abra o MetaTrader 5
2. Verifique se está logado na conta FTMO Demo
3. Verifique que BTCUSD está visível no Market Watch
4. Deixe o MT5 aberto (não feche!)
```

### **Passo 2: Executar Teste Demo**
```bash
python test_ftmo_demo.py
```

**O que vai acontecer:**
1. ✅ Conexão com MT5 (sua conta FTMO)
2. ✅ Coleta dados BTCUSD em tempo real
3. ✅ Análise técnica (EMA, tendências)
4. ✅ Simula trade hipotético com custos reais
5. ✅ Validação de risco (regras FTMO)
6. ✅ Monitoramento ao vivo (30 segundos)

**⚠️ MODO SEGURO:** Nenhum trade real será executado!

---

## 📊 ENTENDENDO O OUTPUT

### **Seção 1: MT5 Connection**
```
🔌 Connecting to MT5...
   ✅ Connected successfully!
   Account: 1513068916
   Balance: $100,000.00
   Equity: $100,000.00
   Leverage: 1:100
   Server: FTMO-Demo
```
**O que significa:** O bot conectou na sua conta demo FTMO com sucesso!

---

### **Seção 2: Market Data**
```
💰 Getting current BTCUSD price...
   ✅ Bid: $73,034.47
   ✅ Ask: $73,035.47
   ✅ Spread: $1.00 (100 points)
```
**O que significa:** Preço atual do BTCUSD e spread (custo implícito)

```
📊 Getting M5 candles (last 100 bars)...
   ✅ Retrieved 100 candles
   📈 Period: 2026-04-10 12:55 → 2026-04-10 21:10
   💵 Price range: $71,659 - $73,255
```
**O que significa:** Histórico de preços para análise

---

### **Seção 3: Technical Analysis**
```
📊 Technical Analysis:
   Current Price: $72,991.72
   EMA 9: $72,850.30
   EMA 21: $72,600.15
   Trend: 🟢 BULLISH
```
**O que significa:** EMA 9 > EMA 21 = tendência de alta

---

### **Seção 4: Hypothetical Trade**
```
💭 Hypothetical Trade:
   Direction: BUY
   Entry: $72,991.72
   Stop Loss: $72,691.72 (-$300)
   Take Profit: $73,591.72 (+$600)
   Volume: 0.10 lots
   Risk: $30.00
   Reward: $60.00
   R:R: 1:2.00
```
**O que significa:** Trade que o bot FARía com parâmetros realistas

---

### **Seção 5: Realistic Costs**
```
💸 Realistic Costs:
   Commission: $9.00
   Spread Cost: $10.00
   Total Costs: $19.00
   Net Profit if TP hit: $41.00
   Net Loss if SL hit: $49.00
   Net R:R: 1:1.67
```
**O que significa:** Custos REAIS da FTMO ($45/lot/side) + spread

---

### **Seção 6: Risk Validation**
```
🛡️ Risk Validation:
   ✅ Trade APPROVED
   Risk: 0.03%
   R:R: 1:2.00

🎯 FTMO Compliance:
   Daily Loss Limit: ✅ OK
   Total Loss Limit: ✅ OK
   Consistency Rule: ✅ OK
   Current Drawdown: 0.00%
   Status: normal
```
**O que significa:** Trade passa nas regras FTMO!

---

## 🎯 PRÓXIMOS PASSOS APÓS TESTE

### **1. Entender o Fluxo**
Depois de rodar o teste e entender cada seção, você saberá:
- Como o bot conecta ao MT5
- Como coleta dados de mercado
- Como gera sinais de trading
- Como calcula custos reais
- Como valida contra regras FTMO

### **2. Backtesting**
```bash
python run_backtest_simple.py
```
Isso roda simulação em dados históricos e gera relatório HTML.

### **3. Otimização**
```bash
python run_optimization.py
```
Otimiza parâmetros com Optuna (walk-forward).

### **4. Dashboard Web**
```bash
python run_dashboard.py
```
Abra http://localhost:8000 para dashboard em tempo real.

---

## ⚠️ IMPORTANTE - MODO SEGURO

O script `test_ftmo_demo.py` **NÃO executa trades reais**. Ele apenas:
- ✅ Conecta ao MT5
- ✅ Coleta dados
- ✅ Analisa mercado
- ✅ Simula trades hipotéticos
- ✅ Valida risco

**Para habilitar trading real**, você precisa:
1. Editar `src/core/orchestrator_v2.py`
2. Descomentar linhas 230-245 (trade execution)
3. Confirmar que entende os riscos

---

## 📁 ONDE VER RESULTADOS

### **Backtest Reports:**
```
data/backtest-results/
├── backtest_realistic.html  ← Abra no navegador!
├── backtest_fast.html
└── backtest_results.json
```

### **Logs:**
```
logs/
└── bot_2026-04-10.log  ← Logs detalhados
```

---

## 🆘 SOLUÇÃO DE PROBLEMAS

### **"MT5 connection failed"**
```
✅ Solução:
1. Abra o MT5
2. Logue na conta FTMO Demo
3. Execute o teste novamente
```

### **"BTCUSD symbol not available"**
```
✅ Solução:
1. No MT5, clique direito no Market Watch
2. "Show All" symbols
3. Encontre e adicione BTCUSD
```

### **"No candle data available"**
```
✅ Solução:
1. Verifique que BTCUSD está selecionado
2. Aguarde alguns segundos para dados carregarem
3. Execute novamente
```

---

## 💡 DICAS

1. **Leia os logs com atenção** - Eles explicam cada passo
2. **Abra o relatório HTML** - Visualize gráficos interativos
3. **Teste várias vezes** - Entenda o fluxo completamente
4. **Não tenha pressa** - Entender antes de operar é crucial

---

**Boa sorte com seus testes!** 🚀

Se tiver dúvidas, consulte:
- `docs/final-report.md` - Relatório completo do projeto
- `docs/memory-dictionary.md` - Dicionário de conceitos
- `docs/dna-engine.md` - Documentação do DNA adaptativo



