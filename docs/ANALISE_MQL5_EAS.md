# ANALISE ULTRA PROFUNDA - Expert Advisors MQL5

**Data:** 2026-04-13
**Projeto:** Forex Quantum Bot + Legacy DubaiMatrixASI
**Arquivos Analisados:** 4 arquivos .mq5

---

## INDICE

1. [Visao Geral dos EAs](#1-visao-geral-dos-eas)
2. [Analise Individual de Cada EA](#2-analise-individual-de-cada-ea)
   - 2.1 ForexQuantumBot_EA.mq5 (mql5/Experts/)
   - 2.2 ForexQuantumBot_EA.mq5 (raiz)
   - 2.3 ForexQuantumBot_EA_V2.mq5
   - 2.4 DubaiMatrixASI_HFT_Bridge.mq5 (legacy)
3. [Sistemas de Comunicacao](#3-sistemas-de-comunicacao)
4. [Extracao de Dados de Mercado](#4-extracao-de-dados-de-mercado)
5. [Execucao de Ordens](#5-execucao-de-ordens)
6. [Gerenciamento de Posicoes](#6-gerenciamento-de-posicoes)
7. [Indicadores Tecnicos](#7-indicadores-tecnicos)
8. [Buffers e Estruturas de Dados](#8-buffers-e-estruturas-de-dados)
9. [Eventos e Handlers](#9-eventos-e-handlers)
10. [Error Handling](#10-error-handling)
11. [Logs no MQL5](#11-logs-no-mql5)
12. [Comparacao EA Atual vs Legacy](#12-comparacao-ea-atual-vs-legacy)
13. [Protocolo de Comunicacao Ideal](#13-protocolo-de-comunicacao-ideal)
14. [Melhorias Necessarias](#14-melhorias-necessarias)
15. [Codigo Reutilizavel do Legacy](#15-codigo-reutilizavel-do-legacy)

---

## 1. VISAO GERAL DOS EAS

Foram identificados **4 arquivos .mq5** no total:

| # | Arquivo | Localizacao | Versao | Tipo |
|---|---------|-------------|--------|------|
| 1 | `ForexQuantumBot_EA.mq5` | `mql5/Experts/` | 1.01 | CSV Bridge |
| 2 | `ForexQuantumBot_EA.mq5` | Raiz do projeto | 1.00 | JSON File Bridge |
| 3 | `ForexQuantumBot_EA_V2.mq5` | Raiz do projeto | 2.00 | JSON File Bridge (Avancado) |
| 4 | `DubaiMatrixASI_HFT_Bridge.mq5` | `D:\old_projects\DubaiMatrixASI-main\mql5\` | 1.00 | TCP Socket HFT |

**Resumo dos Paradigmas de Comunicacao:**
- **EA 1 (mql5/Experts/)**: Usa arquivos **CSV** com handshake de conexao
- **EAs 2 e 3 (raiz)**: Usam arquivos **JSON** simples
- **EA 4 (legacy)**: Usa **TCP Sockets nativos** do MQL5 (baixa latencia)

---

## 2. ANALISE INDIVIDUAL DE CADA EA

### 2.1 ForexQuantumBot_EA.mq5 (mql5/Experts/)

**Path:** `D:\forex-project2k26\mql5\Experts\ForexQuantumBot_EA.mq5`

#### 2.1.1 Cabecalho e Propriedades

```mql5
#property copyright "Forex Quantum Bot - Qwen Code"
#property version   "1.01"
#property description "AI Quantum Trading System - C++ Monte Carlo + Neural Networks"
#property strict
```

- Usa `#property strict` -- validacao estrita do compilador MQL5
- Versao 1.01

#### 2.1.2 Grupos de Inputs (Input Parameters)

```mql5
input group "=== TRADING SETTINGS ==="
input string   InpSymbol = "BTCUSD";
input ENUM_TIMEFRAMES InpTimeframe = PERIOD_M5;
input double   InpLotSize = 0.01;
input int      InpMagicNumber = 20260412;
input int      InpMaxPositions = 1;

input group "=== RISK MANAGEMENT ==="
input double   InpRiskPercent = 0.5;
input double   InpMaxDailyLoss = 5000.0;
input double   InpMaxTotalLoss = 10000.0;
input int      InpMaxTradesPerDay = 10;
input int      InpMinTradeInterval = 300;      // 5 minutos

input group "=== STOP LOSS & TAKE PROFIT ==="
input int      InpStopLossPoints = 300;
input int      InpTakeProfitPoints = 600;       // 2:1 R:R
input bool     InpUseTrailingStop = true;
input int      InpTrailingStart = 200;
input int      InpTrailingDistance = 150;

input group "=== CONNECTION SETTINGS ==="
input string   InpSignalFile = "quantum_signals\\trade_signal.csv";
input string   InpHandshakeFile = "quantum_signals\\connection.txt";
input string   InpLogToFile = "quantum_signals\\ea_log.txt";
input bool     InpAutoTrade = false;            // Default: manual
input int      InpSignalCheckInterval = 300;    // 5 minutos

input group "=== NOTIFICATIONS ==="
input bool     InpSendNotifications = true;
input bool     InpLogDetails = true;
```

**Caracteristicas Notaveis:**
- `input group` -- organiza parametros no painel do MetaTrader
- `InpAutoTrade = false` por padrao -- modo manual por default (seguranca)
- **Handshake mechanism**: `connection.txt` verifica se Python esta ativo
- Limites de risco diarios e totais
- Intervalo minimo entre trades (anti-overtrading)

#### 2.1.3 Variaveis Globais

```mql5
int magicNumber;
double dailyPnL = 0.0;
double totalPnL = 0.0;
int tradesToday = 0;
datetime lastTradeTime = 0;
datetime todayStart = 0;
bool tradingEnabled = true;
bool connectionValidated = false;
datetime lastSignalCheck = 0;
```

#### 2.1.4 Estrutura TradeSignal

```mql5
struct TradeSignal {
   datetime timestamp;
   string direction;
   double confidence;
   double entry_price;
   double stop_loss;
   double take_profit;
   string profile;
   string regime;
   int signal_count;
};

TradeSignal currentSignal;
```

**Campos do Signal CSV:**
| Coluna | Tipo | Descricao |
|--------|------|-----------|
| 0 | datetime | Timestamp do sinal |
| 1 | string | BUY/SELL |
| 2 | double | Confianca (0-1) |
| 3 | double | Preco de entrada |
| 4 | double | Stop Loss |
| 5 | double | Take Profit |
| 6 | string | Profile (nome do agente) |
| 7 | string | Regime de mercado |

#### 2.1.5 OnInit() - Inicializacao

```mql5
int OnInit() {
   magicNumber = InpMagicNumber;
   todayStart = TimeCurrent();

   // Step 1: Validate MT5 connection
   if(!ValidateMT5Connection()) return INIT_FAILED;

   // Step 2: Check signal file access
   if(!CheckSignalFileAccess()) // warning only

   // Step 3: Check Python handshake
   if(CheckPythonHandshake()) // validates PYTHON_CONNECTED=true

   // Step 4: Reset daily stats
   ResetDailyStats();

   return INIT_SUCCEEDED;
}
```

**Fluxo de validacao em 4 passos:**
1. **ValidateMT5Connection()** -- Verifica:
   - `TerminalInfoInteger(TERMINAL_CONNECTED)`
   - `TerminalInfoInteger(TERMINAL_TRADE_ALLOWED)`
   - `SymbolSelect(InpSymbol, true)`
   - `SymbolInfoTick()` -- valida bid/ask > 0
2. **CheckSignalFileAccess()** -- Tenta abrir CSV para leitura
3. **CheckPythonHandshake()** -- Le `connection.txt` procurando `PYTHON_CONNECTED=true` e `PYTHON_STATUS=READY`
4. **ResetDailyStats()** -- Zera contadores do dia

#### 2.1.6 OnTick() - Loop Principal

```mql5
void OnTick() {
   UpdateDailyStats();          // Verifica virada do dia

   if(!tradingEnabled) return;  // Check risco
   if(!CheckRiskLimits()) return;

   // Check sinais a cada InpSignalCheckInterval
   if(TimeCurrent() - lastSignalCheck >= InpSignalCheckInterval) {
      lastSignalCheck = TimeCurrent();
      CheckForSignals();
   }

   ManagePositions();           // PnL tracking
   if(InpUseTrailingStop) UpdateTrailingStops();
}
```

**Fluxo do OnTick:**
1. Atualiza estatisticas diarias (detecta mudanca de dia)
2. Verifica se trading esta habilitado
3. Verifica limites de risco (daily loss, total loss)
4. A cada 300s (5 min), checa arquivo de sinais CSV
5. Gerencia posicoes abertas (PnL)
6. Atualiza trailing stops

#### 2.1.7 CheckForSignals() - Leitura de Sinais

```mql5
void CheckForSignals() {
   int handle = FileOpen(InpSignalFile, FILE_READ|FILE_CSV|FILE_ANSI, ',');
   if(handle == INVALID_HANDLE) return;  // No signal

   // Parse CSV: timestamp, direction, confidence, entry, sl, tp, profile, regime
   string timestamp_str = FileReadString(handle);
   string direction = FileReadString(handle);
   // ... mais 6 campos

   // Validacoes:
   // 1. Direction deve ser BUY ou SELL
   // 2. Confidence >= 0.6
   // 3. Signal age <= 600s (10 minutos)
   // 4. Trade interval >= InpMinTradeInterval
   // 5. tradesToday < InpMaxTradesPerDay

   if(InpAutoTrade) ExecuteTrade(currentSignal);
   else Print("Manual mode - signal logged");
}
```

**Validacoes de sinal:**
- Direcao valida (BUY/SELL)
- Confianca minima de 60%
- Sinal nao pode ter mais de 10 minutos
- Respeita intervalo minimo entre trades
- Limite de trades por dia

#### 2.1.8 ExecuteTrade() - Execucao com OrderSend Nativo

```mql5
void ExecuteTrade(TradeSignal &signal) {
   double lotSize = CalculateLotSize(signal);

   MqlTick tick;
   SymbolInfoTick(InpSymbol, tick);

   MqlTradeRequest request = {};
   MqlTradeResult result = {};

   request.action = TRADE_ACTION_DEAL;
   request.symbol = InpSymbol;
   request.volume = lotSize;
   request.type = (signal.direction == "BUY") ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   request.price = NormalizeDouble((signal.direction=="BUY") ? tick.ask : tick.bid, digits);
   request.sl = NormalizeDouble(signal.stop_loss, digits);
   request.tp = NormalizeDouble(signal.take_profit, digits);
   request.deviation = 100;
   request.magic = magicNumber;
   request.comment = "QuantumBot-" + signal.profile;

   if(OrderSend(request, result)) {
      if(result.retcode == TRADE_RETCODE_DONE) {
         lastTradeTime = TimeCurrent();
         tradesToday++;
      }
   }
}
```

**Diferenca critica:** Este EA usa `OrderSend()` nativo do MQL5 diretamente, nao a classe `CTrade`.

#### 2.1.9 CalculateLotSize() - Money Management

```mql5
double CalculateLotSize(TradeSignal &signal) {
   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   double riskAmount = balance * InpRiskPercent / 100.0;

   double slDistance = MathAbs(signal.entry_price - signal.stop_loss);
   double tickValue = SymbolInfoDouble(InpSymbol, SYMBOL_TRADE_TICK_VALUE);
   double tickSize = SymbolInfoDouble(InpSymbol, SYMBOL_TRADE_TICK_SIZE);

   double lotSize = riskAmount / (slDistance / tickSize * tickValue);

   // Normaliza para lot step, min, max
   lotSize = MathFloor(lotSize / lotStep) * lotStep;
   lotSize = MathMax(lotSize, minLot);
   lotSize = MathMin(lotSize, maxLot);

   return lotSize;
}
```

**Formula de risco:** `lot = riskAmount / (SL_distance / tickSize * tickValue)`

#### 2.1.10 UpdateTrailingStop()

```mql5
void UpdateTrailingStops() {
   // Para cada posicao:
   // 1. Calcula profit em pontos
   // 2. Se profit >= TrailingStart (200 pontos):
   //    - BUY: newSL = currentPrice - TrailingDistance*point
   //    - SELL: newSL = currentPrice + TrailingDistance*point
   // 3. Se newSL > currentSL (melhora SL): modifica
}
```

#### 2.1.11 Funcoes Auxiliares

| Funcao | Descricao |
|--------|-----------|
| `ValidateMT5Connection()` | Verifica terminal, trading, symbol, tick |
| `CheckSignalFileAccess()` | Testa acesso ao arquivo CSV |
| `CheckPythonHandshake()` | Le connection.txt com FILE_COMMON fallback |
| `ManagePositions()` | Itera posicoes, calcula PnL, acumula dailyPnL/totalPnL |
| `ModifyPosition()` | Usa `TRADE_ACTION_SLTP` para modificar SL/TP |
| `CountPositions()` | Conta posicoes com magic number |
| `CheckRiskLimits()` | Verifica daily loss e total loss |
| `UpdateDailyStats()` | Detecta virada do dia, reseta stats |
| `ResetDailyStats()` | Zera dailyPnL, tradesToday, reativa trading |

#### 2.1.12 Resumo

| Atributo | Valor |
|----------|-------|
| Protocolo | **Arquivo CSV** |
| Handshake | `connection.txt` com flags |
| Execucao | `OrderSend()` nativo |
| Lot Size | Baseado em risco % do SL |
| Trailing Stop | Sim (ponto fixo) |
| Breakeven | Nao |
| Smart TP | Nao |
| Risk Limits | Daily loss + Total loss |
| Notification | `SendNotification()` MT5 |

---

### 2.2 ForexQuantumBot_EA.mq5 (raiz)

**Path:** `D:\forex-project2k26\ForexQuantumBot_EA.mq5`

#### 2.2.1 Cabecalho

```mql5
#property copyright "Forex Quantum Bot"
#property version   "1.00"
#property description "MT5 Bridge for Forex Quantum Bot Python System"
#property description "Receives signals from Python via files and executes trades"
```

- Usa `#include <Trade\Trade.mqh>` e `<Trade\AccountInfo.mqh>`
- Usa classe `CTrade` em vez de `OrderSend` direto

#### 2.2.2 Inputs

```mql5
input string   InPythonSignalFile = "C:\\ForexQuantumBot\\signals\\trade_signal.json";
input string   InPythonResponseFile = "C:\\ForexQuantumBot\\signals\\trade_response.json";
input int      InMagicNumber = 123456;
input double   InMaxRiskPercent = 1.0;
input int      InMaxPositions = 1;
input bool     InEnableLogging = true;
```

**Diferencas vs EA mql5/Experts:**
- Formato **JSON** em vez de CSV
- **Response file** -- escreve confirmacao de volta para Python
- Sem handshake, sem risk limits diarios, sem trailing stop configurado

#### 2.2.3 OnInit()

```mql5
int OnInit() {
   trade.SetExpertMagicNumber(InMagicNumber);
   trade.SetDeviationInPoints(50);
   trade.SetTypeFilling(ORDER_FILLING_IOC);
   trade.SetAsyncMode(false);

   Print("ForexQuantumBot EA initialized");
   return(INIT_SUCCEEDED);
}
```

Simples -- apenas configura o objeto `CTrade`.

#### 2.2.4 OnTick()

```mql5
void OnTick() {
   // Check a cada 5 segundos
   if(TimeCurrent() - last_signal_time < 5) return;

   // Check max positions
   if(CountOpenPositions() >= InMaxPositions) return;

   // Check signal file
   if(FileIsExist(InPythonSignalFile)) {
      ProcessSignal();
      last_signal_time = TimeCurrent();
   }

   ManagePositions();  // Breakeven only
}
```

**Diferencas vs EA mql5/Experts:**
- Polling a cada **5 segundos** (nao 300s)
- `FileIsExist()` antes de abrir (evita erro)
- Sem trailing stop, sem risk limits diarios

#### 2.2.5 ProcessSignal() - JSON Parsing Manual

```mql5
void ProcessSignal() {
   int handle = FileOpen(InPythonSignalFile, FILE_READ|FILE_TXT);
   string signal_content = "";
   while(!FileIsEnding(handle))
      signal_content += FileReadString(handle);
   FileClose(handle);

   FileDelete(InPythonSignalFile);  // Delete after read

   // JSON parsing manual:
   string direction = ExtractJsonValue(signal_content, "direction");
   double volume = StringToDouble(ExtractJsonValue(signal_content, "volume"));
   double sl = StringToDouble(ExtractJsonValue(signal_content, "stop_loss"));
   double tp = StringToDouble(ExtractJsonValue(signal_content, "take_profit"));
   double confidence = StringToDouble(ExtractJsonValue(signal_content, "confidence"));

   // Execute:
   if(direction == "BUY") trade.Buy(volume, _Symbol, ask, sl, tp, "QuantumBot BUY");
   else if(direction == "SELL") trade.Sell(volume, _Symbol, bid, sl, tp, "QuantumBot SELL");

   // Response:
   WriteResponse(ticket, success, message);
}
```

**Formato JSON esperado:**
```json
{
  "direction": "BUY",
  "volume": 0.01,
  "stop_loss": 1.08500,
  "take_profit": 1.09500,
  "confidence": 0.85
}
```

#### 2.2.6 ExtractJsonValue() - Parser JSON Manual

```mql5
string ExtractJsonValue(string json, string key) {
   string search_key = "\"" + key + "\":";
   int key_pos = StringFind(json, search_key, 0);
   if(key_pos == -1) return "";

   // Skip whitespace
   // If value starts with " -> quoted string
   // Else -> numeric value until , } or whitespace
}
```

**Parser simples** -- funciona para JSON basico, mas nao suporta:
- Arrays
- Nested objects
- Escape characters em strings
- Valores booleanos (true/false como strings)

#### 2.2.7 ManagePositions() - Breakeven Only

```mql5
void ManagePositions() {
   for(int i = PositionsTotal()-1; i >= 0; i--) {
      // Filtra por symbol e magic number

      // BUY: if profit > 0 && SL < open_price:
      //   risk = open_price - current_SL
      //   if profit >= risk: move SL to breakeven

      // SELL: similar logic
   }
}
```

**Logica de breakeven:**
- Move SL para preco de entrada quando lucro >= risco inicial (1:1 R:R)
- Protecao basica -- nao trailing stop

#### 2.2.8 WriteResponse()

```mql5
void WriteResponse(ulong ticket, bool success, string message) {
   int handle = FileOpen(InPythonResponseFile, FILE_WRITE|FILE_TXT);

   string response = "{\n";
   response += "  \"ticket\": " + IntegerToString(ticket) + ",\n";
   response += "  \"success\": " + (success ? "true" : "false") + ",\n";
   response += "  \"message\": \"" + message + "\",\n";
   response += "  \"timestamp\": \"" + TimeToString(TimeCurrent()) + "\"\n";
   response += "}\n";

   FileWriteString(handle, response);
   FileClose(handle);
}
```

#### 2.2.9 OnTradeTransaction() - Trade Event Handler

```mql5
void OnTradeTransaction(const MqlTradeTransaction& trans,
                        const MqlTradeRequest& request,
                        const MqlTradeResult& result) {
   if(trans.type == TRADE_TRANSACTION_DEAL_ADD) {
      if(trans.deal_type == DEAL_TYPE_SELL || trans.deal_type == DEAL_TYPE_BUY) {
         // Get deal from history
         double profit = HistoryDealGetDouble(deal_ticket, DEAL_PROFIT);
         double commission = HistoryDealGetDouble(deal_ticket, DEAL_COMMISSION);
         double swap = HistoryDealGetDouble(deal_ticket, DEAL_SWAP);

         if(total_profit > 0) winning_trades++;
         else losing_trades++;
      }
   }
}
```

**Importante:** Este handler captura eventos de trade em tempo real -- mais eficiente que polling.

#### 2.2.10 Resumo

| Atributo | Valor |
|----------|-------|
| Protocolo | **Arquivo JSON** |
| Response | JSON de volta para Python |
| Execucao | `CTrade.Buy()` / `CTrade.Sell()` |
| Filling | `ORDER_FILLING_IOC` |
| Breakeven | Sim (1:1 R:R) |
| Trailing Stop | Nao |
| Smart TP | Nao |
| OnTradeTransaction | Sim (deal tracking) |
| Trade stats | winning_trades, losing_trades |

---

### 2.3 ForexQuantumBot_EA_V2.mq5

**Path:** `D:\forex-project2k26\ForexQuantumBot_EA_V2.mq5`

#### 2.3.1 Cabecalho

```mql5
#property copyright "Forex Quantum Bot - Production EA"
#property version   "2.00"
#property description "Complete MT5 Expert Advisor for Python Live Trading Bridge"
#property description "Features: Smart TP, Trailing Stops, Breakeven, Real-time Logging"
```

Versao mais avancada -- evolution do EA raiz v1.

#### 2.3.2 Inputs (Expandidos)

```mql5
input string   InPythonSignalFile   = "C:\\ForexQuantumBot\\signals\\trade_signal.json";
input string   InPythonResponseFile = "C:\\ForexQuantumBot\\signals\\trade_response.json";
input int      InMagicNumber        = 123456;
input double   InMaxRiskPercent     = 1.0;
input int      InMaxPositions       = 1;
input bool     InEnableLogging      = true;
input double   InTrailingATR        = 1.5;         // NOVO
input bool     InUseSmartTP         = true;        // NOVO
input double   InTP1Ratio           = 0.0;         // NOVO
input double   InTP2Ratio           = 0.50;        // NOVO
input double   InTP3Ratio           = 0.0;         // NOVO
input double   InTrailRatio         = 0.50;        // NOVO
```

**Novidades V2:**
- **Smart TP**: Multi-target (TP1, TP2, TP3) com ratios configuraveis
- **Trailing ATR**: Trailing stop baseado em ATR (adaptativo)
- **TP2**: Fecha 50% da posicao no meio do caminho

#### 2.3.3 Estrutura PositionState

```mql5
struct PositionState {
   ulong  ticket;
   string direction;
   double entry_price;
   double sl;
   double tp;
   double volume;
   double tp2_price;
   double tp2_closed_volume;
   bool   tp2_hit;
   bool   breakeven_active;
   double peak_price;
   datetime open_time;
};

PositionState current_position;
bool has_position = false;
```

**Tracking avancado de posicao** -- mantem estado local completo.

#### 2.3.4 OnInit() - Expanded

```mql5
int OnInit() {
   trade.SetExpertMagicNumber(InMagicNumber);
   trade.SetDeviationInPoints(50);
   trade.SetTypeFilling(ORDER_FILLING_IOC);
   trade.SetAsyncMode(false);

   session_start_balance = AccountInfoDouble(ACCOUNT_BALANCE);

   Print("FOREX QUANTUM BOT EA V2.0 - INITIALIZED");
   Print("Smart TP: ", InUseSmartTP ? "ON" : "OFF");
   Print("Trailing ATR: ", InTrailingATR);

   return(INIT_SUCCEEDED);
}
```

#### 2.3.5 ProcessSignal() - Enhanced

```mql5
void ProcessSignal() {
   // JSON parsing (mesmo metodo do V1)
   string direction = ExtractJsonValue(..., "direction");
   double volume = StringToDouble(ExtractJsonValue(..., "volume"));
   double sl = StringToDouble(ExtractJsonValue(..., "stop_loss"));
   double tp = StringToDouble(ExtractJsonValue(..., "take_profit"));
   double entry = StringToDouble(ExtractJsonValue(..., "entry_price"));
   double confidence = StringToDouble(ExtractJsonValue(..., "confidence"));
   int buy_votes = (int)StringToInteger(ExtractJsonValue(..., "buy_votes"));
   int sell_votes = (int)StringToInteger(ExtractJsonValue(..., "sell_votes"));
   int neutral_votes = (int)StringToInteger(ExtractJsonValue(..., "neutral_votes"));

   // Execute trade
   // Track position state
   has_position = true;
   current_position.ticket = ticket;
   current_position.tp2_price = CalculateTP2Price(price, sl, direction);
   // ...
}
```

**Novos campos no JSON do sinal:**
- `entry_price`
- `buy_votes`, `sell_votes`, `neutral_votes` (votacao dos agentes)

#### 2.3.6 ManagePositions() - V2 Complexo

```mql5
void ManagePositions() {
   if(!has_position) return;

   // 1. Get current price (BID para BUY, ASK para SELL)

   // 2. Update peak price (melhor preco atingido)

   // 3. Calculate unrealized PnL

   // 4. SMART TP - Check TP2 hit
   if(InUseSmartTP && !current_position.tp2_hit) {
      // Se preco >= TP2: fecha 50% da posicao
      ClosePartialPosition(ticket, volume * InTP2Ratio, "Smart TP2");
   }

   // 5. BREAKEVEN - Move SL para entry quando 1R
   if(!current_position.breakeven_active) {
      if(profit_distance >= risk_distance) {
         MoveSLToBreakeven(ticket, entry_price);
      }
   }

   // 6. TRAILING ATR - Depois do TP2 ou se SmartTP off
   if(current_position.tp2_hit || !InUseSmartTP) {
      double atr = GetATR(14);
      double trail_distance = atr * InTrailingATR;
      // Move SL com base no ATR
   }

   // 7. Log status a cada 60 segundos

   // 8. Check if position still open
   if(!PositionSelectByTicket(current_position.ticket)) {
      // Position closed
      has_position = false;
      ZeroMemory(current_position);
   }
}
```

**Fluxo de gerenciamento V2:**
1. Atualiza preco maximo (peak)
2. Calcula PnL nao realizado
3. **Smart TP**: Fecha 50% no TP2 (1:2 R:R)
4. **Breakeven**: Move SL para entry no 1R
5. **Trailing ATR**: Apos TP2, trailing adaptativo
6. Log a cada 60s
7. Detecta fechamento automatico

#### 2.3.7 Funcoes Auxiliares V2

| Funcao | Descricao |
|--------|-----------|
| `CalculateTP2Price()` | `entry + risk_distance * 2.0` (1:2 R:R) |
| `ClosePartialPosition()` | Fecha volume parcial com `trade.Sell()`/`trade.Buy()` |
| `MoveSLToBreakeven()` | Wrapper para `ModifyPositionSL()` |
| `ModifyPositionSL()` | `trade.PositionModify(ticket, new_sl, current_tp)` |
| `CalculateClosedPnL()` | Busca no historico por deal com mesmo comment |
| `GetATR(14)` | Cria handle `iATR()`, copia buffer, retorna valor atual |
| `NormalizeVolume()` | Igual ao V1 |
| `ExtractJsonValue()` | Igual ao V1 |
| `WriteResponse()` | Igual ao V1 |

#### 2.3.8 GetATR() - Implementacao de Indicador

```mql5
double GetATR(int period) {
   double atr[];
   ArraySetAsSeries(atr, true);

   int handle = iATR(_Symbol, PERIOD_CURRENT, period);
   if(handle == INVALID_HANDLE) return 0;

   if(CopyBuffer(handle, 0, 0, 1, atr) <= 0) return 0;

   return atr[0];
}
```

**Nota:** Cria um novo handle a cada chamada -- ineficiente. Idealmente o handle deveria ser criado no `OnInit()` e reutilizado.

#### 2.3.9 OnTradeTransaction() - V2

Mesma estrutura do V1, mas com logs formatados:
```mql5
Print("📊 DEAL CLOSED | PnL: $", DoubleToString(total_profit, 2),
      " | Commission: $", DoubleToString(commission, 2),
      " | Total: W=", winning_trades, " L=", losing_trades);
```

#### 2.3.10 Resumo

| Atributo | Valor |
|----------|-------|
| Protocolo | **Arquivo JSON** |
| Response | JSON |
| Execucao | `CTrade.Buy()` / `CTrade.Sell()` |
| Filling | `ORDER_FILLING_IOC` |
| Breakeven | Sim (1:1 R:R) |
| Trailing Stop | **Sim (ATR-based)** |
| Smart TP | **Sim (multi-target)** |
| Partial Close | **Sim (50% no TP2)** |
| Position Tracking | **Struct completa** |
| Peak Price Tracking | **Sim** |
| Indicadores | **ATR(14)** |
| OnTradeTransaction | Sim |
| Session Stats | `session_start_balance` |

---

### 2.4 DubaiMatrixASI_HFT_Bridge.mq5 (LEGACY)

**Path:** `D:\old_projects\DubaiMatrixASI-main\mql5\DubaiMatrixASI_HFT_Bridge.mq5`

#### 2.4.1 Cabecalho

```mql5
#property copyright "DubaiMatrixASI"
#property link      "Omega-Level Architecture"
#property version   "1.00"
#property strict
```

**Este e o EA mais diferente de todos** -- usa TCP Sockets nativos do MQL5.

#### 2.4.2 Inputs

```mql5
input string   InpPythonIP    = "127.0.0.1";  // IP do Python
input int      InpPythonPort  = 5555;         // Porta
input int      InpMagicNumber = 88888888;
input int      InpSlippage    = 10;
```

Minimo e direto -- IP, porta, magic number, slippage.

#### 2.4.3 Declaracoes Forward

```mql5
void ExecuteLimitOrder(string side, string symbol, double lot, double price, double sl, double tp, string strike_id);
void ExecuteSonarProbe(string symbol, string side, double lot, double price, int duration_ms);
void ExecuteTrade(string action, string symbol, double lot, double sl, double tp, string strike_id);
void ExecuteClose(ulong ticket);
void ExecuteCloseAll(string symbol, int type);
```

**5 tipos de operacao:**
1. **ExecuteTrade** -- Market order (BUY/SELL)
2. **ExecuteLimitOrder** -- Pending order (BUY_LIMIT/SELL_LIMIT)
3. **ExecuteSonarProbe** -- Ordens temporarias para sondagem
4. **ExecuteClose** -- Fecha uma posicao
5. **ExecuteCloseAll** -- Fecha todas as posicoes de um tipo

#### 2.4.4 OnInit()

```mql5
int OnInit() {
   Print("DubaiMatrixASI HFT Bridge Inicializando...");
   ConnectToASI();  // Socket connect

   // Timer de 1ms para latencia ultra-baixa
   EventSetMillisecondTimer(1);

   return(INIT_SUCCEEDED);
}
```

**Timer de 1ms** -- muito mais agressivo que os outros EAs.

#### 2.4.5 OnTick() - Tick Streaming via TCP

```mql5
void OnTick() {
   if(socket_handle == INVALID_HANDLE) return;

   MqlTick last_tick;
   if(SymbolInfoTick(_Symbol, last_tick)) {
      string tick_data = "TICK|" + _Symbol + "|" +
                         DoubleToString(last_tick.bid, _Digits) + "|" +
                         DoubleToString(last_tick.ask, _Digits) + "|" +
                         DoubleToString(last_tick.last, _Digits) + "|" +
                         DoubleToString(last_tick.volume_real, 2) + "|" +
                         IntegerToString(last_tick.time_msc) + "\n";

      SendTCP(tick_data);
   }
}
```

**IMPORTANTE:** Este EA **envia ticks em tempo real para o Python** via TCP.

**Formato do tick:**
```
TICK|EURUSD|1.08500|1.08502|1.08501|0.50|1713000000123\n
```

| Campo | Descricao |
|-------|-----------|
| TICK | Header |
| Symbol | EURUSD, etc |
| Bid | Melhor preco de venda |
| Ask | Melhor preco de compra |
| Last | Ultimo preco |
| volume_real | Volume do tick |
| time_msc | Timestamp em milissegundos |

#### 2.4.6 OnTimer() - Leitura de Comandos

```mql5
void OnTimer() {
   if(socket_handle == INVALID_HANDLE) {
      // Reconexao a cada 1000ms
      static uint last_reconnect = 0;
      if(GetTickCount() - last_reconnect > 1000) {
         ConnectToASI();
         last_reconnect = GetTickCount();
      }
      return;
   }

   uint bytes_readable = SocketIsReadable(socket_handle);
   if(bytes_readable > 0) {
      uchar buffer[];
      int read_len = SocketRead(socket_handle, buffer, bytes_readable, 10);  // 10ms timeout
      if(read_len > 0) {
         string commands = CharArrayToString(buffer, 0, read_len);
         ParseCommands(commands);
      }
   }
}
```

**Fluxo:**
1. Verifica se socket esta conectado
2. Se nao: tenta reconectar a cada 1s
3. Se sim: le bytes disponiveis
4. Parseia comandos recebidos

#### 2.4.7 Socket Functions

```mql5
void ConnectToASI() {
   socket_handle = SocketCreate();
   if(socket_handle != INVALID_HANDLE) {
      bool connected = SocketConnect(socket_handle, InpPythonIP, InpPythonPort, 500);  // 500ms timeout
   }
}

void SendTCP(string msg) {
   uchar data[];
   StringToCharArray(msg, data);
   int sent = SocketSend(socket_handle, data, ArraySize(data)-1);
}
```

**APIs de Socket MQL5:**
- `SocketCreate()` -- Cria socket TCP
- `SocketConnect(handle, ip, port, timeout)` -- Conecta
- `SocketSend(handle, buffer, len)` -- Envia dados
- `SocketRead(handle, buffer, max_len, timeout)` -- Le dados
- `SocketIsReadable(handle)` -- Retorna bytes disponiveis
- `SocketClose(handle)` -- Fecha socket

#### 2.4.8 ParseCommands()

```mql5
void ParseCommands(string raw_data) {
   string lines[];
   int count = StringSplit(raw_data, '\n', lines);

   for(int i=0; i<count; i++) {
      if(StringLen(lines[i]) > 0)
         ProcessSingleCommand(lines[i]);
   }
}
```

Suporta **multiplas linhas de comando** por leitura.

#### 2.4.9 ProcessSingleCommand() - Protocolo de Comandos

```
Formato geral: "ACTION|PARAM1|PARAM2|...\n"
```

| Comando | Formato | Descricao |
|---------|---------|-----------|
| `PING` | `PING` | Health check (responde PONG) |
| `BUY` | `BUY|SYMBOL|LOT|SL|TP[|STRIKE_ID]` | Market buy |
| `SELL` | `SELL|SYMBOL|LOT|SL|TP[|STRIKE_ID]` | Market sell |
| `OPEN` | `OPEN\|SIDE\|SYMBOL\|LOT\|SL\|TP\|STRIKE_ID` | Generic open |
| `LIMIT` | `LIMIT\|SIDE\|SYMBOL\|LOT\|PRICE\|SL\|TP[|STRIKE_ID]` | Pending order |
| `SONAR` | `SONAR\|SYMBOL\|SIDE\|LOT\|PRICE\|DURATION_MS` | Temporary probe |
| `CLOSE` | `CLOSE|TICKET` | Fecha posicao especifica |
| `CLOSE_ALL` | `CLOSE_ALL\|SYMBOL\|TYPE` | Fecha todas (0=BUY, 1=SELL) |

#### 2.4.10 ExecuteTrade() - Market Order

```mql5
void ExecuteTrade(string action, string symbol, double lot, double sl, double tp, string strike_id) {
   MqlTradeRequest request;
   MqlTradeResult  result;
   ZeroMemory(request);
   ZeroMemory(result);

   request.action   = TRADE_ACTION_DEAL;
   request.symbol   = symbol;
   request.volume   = lot;
   request.type     = (action == "BUY") ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;

   MqlTick last_tick;
   SymbolInfoTick(symbol, last_tick);
   request.price    = (action == "BUY") ? last_tick.ask : last_tick.bid;

   request.sl       = sl;
   request.tp       = tp;
   request.deviation= InpSlippage;
   request.magic    = InpMagicNumber;
   request.type_filling = ORDER_FILLING_IOC;
   request.comment  = "ASI_" + action;

   bool success = OrderSend(request, result);
   if(success) {
      string msg = "RESULT|" + action + "|SUCCESS|" + IntegerToString(result.deal) +
                   "|" + DoubleToString(result.price, _Digits) + "|" + strike_id + "\n";
      SendTCP(msg);
   } else {
      string msg = "RESULT|" + action + "|ERROR|" + IntegerToString(result.retcode) + "\n";
      SendTCP(msg);
   }
}
```

**Resposta via TCP:** `RESULT|BUY|SUCCESS|123456|1.08500|STRIKE_001\n`

#### 2.4.11 ExecuteClose() - Anti-Slippage Protection

```mql5
void ExecuteClose(ulong ticket) {
   if(!PositionSelectByTicket(ticket)) {
      SendTCP("RESULT|CLOSE|ERROR|NOT_FOUND\n");
      return;
   }

   double current_profit = PositionGetDouble(POSITION_PROFIT);

   // PROTECAO ANTI-SLIPPAGE:
   if(current_profit <= 0.0) {
      Print("CLOSE ABORTADO: Preco derreteu (Slippage)");
      SendTCP("RESULT|CLOSE|ERROR|SLIPPAGE_PROTECTION\n");
      return;
   }

   // ... executa fechamento
}
```

**Feature unica:** Se o Python mandou fechar baseado num lucro que ele viu, mas no MQL5 o lucro ja ficou negativo (devido a latencia/spread), o fechamento e abortado.

#### 2.4.12 ExecuteLimitOrder() - Pending Orders

```mql5
void ExecuteLimitOrder(string side, string symbol, double lot, double price, double sl, double tp, string strike_id) {
   request.action   = TRADE_ACTION_PENDING;
   request.type     = (side == "BUY") ? ORDER_TYPE_BUY_LIMIT : ORDER_TYPE_SELL_LIMIT;
   request.price    = price;
   request.type_filling = ORDER_FILLING_RETURN;
   request.comment  = "ASI_LIMIT";
}
```

**Diferenca:** Usa `ORDER_FILLING_RETURN` (padrao para pending orders).

#### 2.4.13 ExecuteSonarProbe() - Sonic Pings

```mql5
void ExecuteSonarProbe(string symbol, string side, double lot, double price, int duration_ms) {
   request.action   = TRADE_ACTION_PENDING;
   request.type     = (side == "BUY") ? ORDER_TYPE_BUY_LIMIT : ORDER_TYPE_SELL_LIMIT;
   request.price    = price;
   request.magic    = 999;  // Sonar Magic Number (diferente)
   request.comment  = "SONAR_PROBE";
   request.type_time  = ORDER_TIME_SPECIFIED;
   request.expiration = TimeCurrent() + (duration_ms / 1000) + 1;
}
```

**Conceito:** Ordens pendentes temporarias que expiram rapidamente -- usadas para sondar liquidez.

#### 2.4.14 ExecuteCloseAll() - Mass Close

```mql5
void ExecuteCloseAll(string symbol, int type) {
   for(int i=PositionsTotal()-1; i>=0; i--) {
      ulong ticket = PositionGetTicket(i);
      if(PositionSelectByTicket(ticket)) {
         if(PositionGetString(POSITION_SYMBOL) == symbol &&
            PositionGetInteger(POSITION_TYPE) == type &&
            (PositionGetInteger(POSITION_MAGIC) == InpMagicNumber || InpMagicNumber == 0)) {
            ExecuteClose(ticket);
            closed++;
         }
      }
   }
   SendTCP("RESULT|CLOSE_ALL|SUCCESS|" + IntegerToString(closed) + "\n");
}
```

Varre de tras para frente para evitar pular indices ao fechar.

#### 2.4.15 Resumo

| Atributo | Valor |
|----------|-------|
| Protocolo | **TCP Socket nativo** |
| Latencia | **1ms timer** |
| Tick Streaming | **Sim (bid/ask/last/volume/timestamp)** |
| Execucao | `OrderSend()` nativo |
| Filling | IOC (market), RETURN (pending) |
| Comandos | BUY, SELL, OPEN, LIMIT, SONAR, CLOSE, CLOSE_ALL, PING |
| Anti-Slippage | **Sim (aborta se lucro <= 0)** |
| Sonar Probes | **Sim (ordens temporarias)** |
| Strike ID | **Sim (tracking de ordens)** |
| Reconexao automatica | **Sim (a cada 1s)** |
| Trailing Stop | Nao |
| Breakeven | Nao |
| Smart TP | Nao |

---

## 3. SISTEMAS DE COMUNICACAO

### 3.1 Visao Comparativa

| Sistema | Arquivo | Direcao | Latencia | Confiabilidade |
|---------|---------|---------|----------|----------------|
| CSV File | EA mql5/Experts | Python->EA | ~5s | Media |
| JSON File (simple) | EA raiz v1 | Python<->EA | ~5s | Media |
| JSON File (enhanced) | EA raiz v2 | Python<->EA | ~5s | Media |
| TCP Socket | Legacy DubaiMatrix | Python<->EA | ~1ms | Alta |

### 3.2 Protocolo CSV (EA mql5/Experts)

```
trade_signal.csv:
2026-04-12 10:30:00,BUY,0.85,1.08500,1.08200,1.09100,QuantumAgent,RangeBound

connection.txt:
PYTHON_CONNECTED=true
PYTHON_STATUS=READY
```

**Vantagens:**
- Simples de implementar em Python (`csv` module)
- Handshake de conexao

**Desvantagens:**
- Sem resposta de confirmacao (one-way)
- Polling lento (300s)
- Sem controle de concorrencia
- Sem tratamento de corrupcao de arquivo

### 3.3 Protocolo JSON File (EAs raiz)

```json
// trade_signal.json (Python -> EA)
{
  "direction": "BUY",
  "volume": 0.01,
  "stop_loss": 1.08200,
  "take_profit": 1.09100,
  "entry_price": 1.08500,
  "confidence": 0.85,
  "buy_votes": 3,
  "sell_votes": 1,
  "neutral_votes": 0
}

// trade_response.json (EA -> Python)
{
  "ticket": 123456,
  "success": true,
  "message": "Order executed",
  "timestamp": "2026-04-12 10:30:05"
}
```

**Vantagens:**
- Bidirecional (sinal + resposta)
- Estruturado
- EA deleta sinal file apos leitura (evita re-execucao)

**Desvantagens:**
- Parser JSON manual (fragil)
- Race conditions possiveis
- Polling a cada 5s (ainda lento)
- File I/O overhead

### 3.4 Protocolo TCP Socket (Legacy)

```
// Python -> EA (comandos)
BUY|EURUSD|0.01|1.08200|1.09100|STRIKE_001\n
SELL|EURUSD|0.01|1.09100|1.08200|STRIKE_002\n
LIMIT|BUY|EURUSD|0.01|1.08000|1.07700|1.09000|LIMIT_001\n
CLOSE|123456\n
CLOSE_ALL|EURUSD|0\n
PING\n

// EA -> Python (ticks + resultados)
TICK|EURUSD|1.08500|1.08502|1.08501|0.50|1713000000123\n
RESULT|BUY|SUCCESS|123456|1.08500|STRIKE_001\n
RESULT|SELL|ERROR|10013\n
PONG|OK\n
```

**Vantagens:**
- Latencia de milissegundos
- Tick streaming em tempo real
- Bidirecional nativo
- Multiplas operacoes (market, pending, close, sonar)
- Reconexao automatica
- Health check (PING/PONG)
- Anti-slippage protection

**Desvantagens:**
- Requer `allow_webrequest` e sockets habilitados no MT5
- Mais complexo de implementar
- Pode ser bloqueado por firewalls

### 3.5 Funcoes MQL5 de Socket Disponiveis

| Funcao | Descricao | Disponivel em |
|--------|-----------|---------------|
| `SocketCreate()` | Cria socket TCP | MT5 build 2240+ |
| `SocketConnect(handle, ip, port, timeout)` | Conecta | MT5 build 2240+ |
| `SocketSend(handle, data[], len)` | Envia bytes | MT5 build 2240+ |
| `SocketRead(handle, data[], max_len, timeout)` | Le bytes | MT5 build 2240+ |
| `SocketIsReadable(handle)` | Bytes disponiveis | MT5 build 2240+ |
| `SocketClose(handle)` | Fecha socket | MT5 build 2240+ |

---

## 4. EXTRACAO DE DADOS DE MERCADO

### 4.1 Dados Disponiveis via MQL5 API

Todos os EAs utilizam as seguintes APIs para extrair dados:

| API | Descricao | Usada em |
|-----|-----------|----------|
| `SymbolInfoTick(symbol, tick)` | Tick atual (bid, ask, last, volume, time_msc) | **Todos** |
| `SymbolInfoDouble(symbol, SYMBOL_ASK)` | Preco ask | EAs raiz |
| `SymbolInfoDouble(symbol, SYMBOL_BID)` | Preco bid | EAs raiz |
| `SymbolInfoDouble(symbol, SYMBOL_POINT)` | Tamanho do ponto | EA mql5/Experts |
| `SymbolInfoDouble(symbol, SYMBOL_DIGITS)` | Casas decimais | EA mql5/Experts |
| `SymbolInfoDouble(symbol, SYMBOL_VOLUME_STEP)` | Step de lote | Todos |
| `SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN)` | Lote minimo | Todos |
| `SymbolInfoDouble(symbol, SYMBOL_VOLUME_MAX)` | Lote maximo | Todos |
| `SymbolInfoDouble(symbol, SYMBOL_TRADE_CONTRACT_SIZE)` | Tamanho do contrato | EA V2 |
| `SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_VALUE)` | Valor do tick | EA mql5/Experts |
| `SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_SIZE)` | Tamanho do tick | EA mql5/Experts |
| `SymbolInfoInteger(symbol, SYMBOL_TRADE_MODE)` | Modo de trading | Nenhum |
| `AccountInfoDouble(ACCOUNT_BALANCE)` | Saldo da conta | Todos |
| `AccountInfoDouble(ACCOUNT_EQUITY)` | Equity | Nenhum |
| `AccountInfoDouble(ACCOUNT_MARGIN_FREE)` | Margem livre | Nenhum |
| `AccountInfoDouble(ACCOUNT_PROFIT)` | Lucro total | Nenhum |
| `TerminalInfoInteger(TERMINAL_CONNECTED)` | Terminal online | EA mql5/Experts |
| `TerminalInfoInteger(TERMINAL_TRADE_ALLOWED)` | Trading permitido | EA mql5/Experts |
| `PositionGetDouble(POSITION_PROFIT)` | Lucro da posicao | EAs raiz |
| `PositionGetDouble(POSITION_SWAP)` | Swap da posicao | EAs raiz |
| `PositionGetDouble(POSITION_PRICE_OPEN)` | Preco de abertura | Todos |
| `PositionGetDouble(POSITION_SL)` | SL atual | Todos |
| `PositionGetDouble(POSITION_TP)` | TP atual | Todos |

### 4.2 Dados Enviados pelo Legacy (TCP)

O DubaiMatrixASI envia via TCP:

```
TICK|SYMBOL|BID|ASK|LAST|VOLUME_REAL|TIME_MSC
```

**Campos extras que poderiam ser enviados:**
- Spread (ask - bid)
- Equity da conta
- Margem utilizada
- Numero de posicoes abertas
- PnL do dia
- Status dos indicadores (RSI, MACD, etc)

### 4.3 Como Extrair TODOS os Dados Necessarios

```mql5
// Dados de mercado:
MqlTick tick;
SymbolInfoTick(_Symbol, tick);
// tick.bid, tick.ask, tick.last, tick.volume, tick.time_msc
// tick.spread = tick.ask - tick.ask

// Dados da conta:
double balance = AccountInfoDouble(ACCOUNT_BALANCE);
double equity = AccountInfoDouble(ACCOUNT_EQUITY);
double margin = AccountInfoDouble(ACCOUNT_MARGIN);
double free_margin = AccountInfoDouble(ACCOUNT_MARGIN_FREE);
double profit = AccountInfoDouble(ACCOUNT_PROFIT);

// Dados de posicoes:
for(int i = PositionsTotal()-1; i >= 0; i--) {
   ulong ticket = PositionGetTicket(i);
   string symbol = PositionGetString(POSITION_SYMBOL);
   double open_price = PositionGetDouble(POSITION_PRICE_OPEN);
   double sl = PositionGetDouble(POSITION_SL);
   double tp = PositionGetDouble(POSITION_TP);
   double profit = PositionGetDouble(POSITION_PROFIT);
   double swap = PositionGetDouble(POSITION_SWAP);
   double volume = PositionGetDouble(POSITION_VOLUME);
   datetime open_time = (datetime)PositionGetInteger(POSITION_TIME);
}

// Dados do historico:
HistorySelect(date_from, date_to);
for(int i = HistoryDealsTotal()-1; i >= 0; i--) {
   ulong deal = HistoryDealGetTicket(i);
   double profit = HistoryDealGetDouble(deal, DEAL_PROFIT);
   double commission = HistoryDealGetDouble(deal, DEAL_COMMISSION);
   double swap = HistoryDealGetDouble(deal, DEAL_SWAP);
   string symbol = HistoryDealGetString(deal, DEAL_SYMBOL);
}

// Indicadores (via handles):
int rsi_handle = iRSI(_Symbol, PERIOD_CURRENT, 14, PRICE_CLOSE);
double rsi_buffer[];
ArraySetAsSeries(rsi_buffer, true);
CopyBuffer(rsi_handle, 0, 0, 1, rsi_buffer);
// rsi_buffer[0] = valor atual do RSI
```

---

## 5. EXECUCAO DE ORDENS

### 5.1 Metodos de Execucao Identificados

| Metodo | EA | Descricao |
|--------|----|-----------|
| `CTrade.Buy()` | EAs raiz | Wrapper de alto nivel |
| `CTrade.Sell()` | EAs raiz | Wrapper de alto nivel |
| `CTrade.PositionModify()` | EA V2 | Modifica SL/TP |
| `OrderSend(request, result)` | EA mql5/Experts, Legacy | API nativa de baixo nivel |

### 5.2 Tipos de Ordem Suportados

| Tipo | EA mql5/Experts | EA raiz V1 | EA V2 | Legacy |
|------|-----------------|------------|-------|--------|
| Market BUY | Sim | Sim | Sim | Sim |
| Market SELL | Sim | Sim | Sim | Sim |
| Pending BUY_LIMIT | Nao | Nao | Nao | Sim |
| Pending SELL_LIMIT | Nao | Nao | Nao | Sim |
| Modify SL/TP | Sim | Sim | Sim | Nao |
| Close Position | Nao | Nao | Sim (partial) | Sim |
| Close All | Nao | Nao | Nao | Sim |
| Sonar Probe | Nao | Nao | Nao | Sim |

### 5.3 Filling Modes

| Mode | Uso | Descricao |
|------|-----|-----------|
| `ORDER_FILLING_IOC` | EAs raiz | Immediate or Cancel -- preenche o que puder, cancela o resto |
| `ORDER_FILLING_FOK` | Nenhum | Fill or Kill -- ou preenche tudo ou cancela |
| `ORDER_FILLING_RETURN` | Legacy (pending) | Return -- preenche parcial, mantem o resto |

### 5.4 Fluxo de Execucao (Legacy - mais completo)

```
1. Python envia: "BUY|EURUSD|0.01|1.08200|1.09100|STRIKE_001\n"
2. EA recebe via OnTimer() -> SocketRead()
3. ParseCommands() -> ProcessSingleCommand() -> ExecuteTrade()
4. SymbolInfoTick() para obter preco atual
5. Preenche MqlTradeRequest
6. OrderSend(request, result)
7. Envia resposta: "RESULT|BUY|SUCCESS|123456|1.08500|STRIKE_001\n"
8. Python recebe e atualiza estado
```

### 5.5 Codigos de Retorno do OrderSend

| Codigo | Constante | Significado |
|--------|-----------|-------------|
| 10008 | TRADE_RETCODE_DONE | Ordem executada com sucesso |
| 10009 | TRADE_RETCODE_DONE_PARTIAL | Preenchimento parcial |
| 10013 | TRADE_RETCODE_INVALID | Parametros invalidos |
| 10014 | TRADE_RETCODE_INVALID_VOLUME | Volume invalido |
| 10015 | TRADE_RETCODE_INVALID_PRICE | Preco invalido |
| 10016 | TRADE_RETCODE_INVALID_STOPS | Stops invalidos |
| 10019 | TRADE_RETCODE_MARKET_CLOSED | Mercado fechado |
| 10027 | TRADE_RETCODE_CONNECTION | Sem conexao |
| 10030 | TRADE_RETCODE_REQUOTE | Requote |
| 10031 | TRADE_RETCODE_ORDER_ACCEPTED | Ordem aceita (async mode) |

---

## 6. GERENCIAMENTO DE POSICOES

### 6.1 Funcoes de Gerenciamento por EA

| Funcao | EA mql5/Experts | EA raiz V1 | EA V2 | Legacy |
|--------|-----------------|------------|-------|--------|
| Trailing Stop | Sim (ponto fixo) | Nao | Sim (ATR) | Nao |
| Breakeven | Nao | Sim | Sim | Nao |
| Smart TP | Nao | Nao | Sim (TP2) | Nao |
| Partial Close | Nao | Nao | Sim | Nao |
| PnL Tracking | Sim | Nao | Sim | Nao |
| Peak Price | Nao | Nao | Sim | Nao |

### 6.2 Logica de Trailing Stop (EA mql5/Experts)

```
IF profit_points >= InpTrailingStart (200):
   BUY:  newSL = currentPrice - InpTrailingDistance (150) * point
   SELL: newSL = currentPrice + InpTrailingDistance (150) * point

   IF newSL melhora (compra: > currentSL, venda: < currentSL):
      ModifyPosition(ticket, newSL, currentTP)
```

### 6.3 Logica de Breakeven (EAs raiz)

```
IF direction == BUY:
   profit_points = (current_price - open_price) / _Point
   risk_points = (open_price - current_sl) / _Point

   IF profit_points >= risk_points AND current_sl < open_price:
      trade.PositionModify(ticket, open_price, current_tp)
```

### 6.4 Logica de Smart TP (EA V2)

```
TP2 = entry + (entry - SL) * 2.0  // 1:2 R:R

IF price >= TP2 AND !tp2_hit:
   close_volume = volume * InTP2Ratio (50%)
   ClosePartialPosition(ticket, close_volume)
   tp2_hit = true

   // Apos TP2, ativa trailing ATR
   atr = GetATR(14)
   trail_distance = atr * InTrailingATR (1.5)
   new_sl = current_price - trail_distance
   ModifyPositionSL(ticket, new_sl)
```

---

## 7. INDICADORES TECNICOS

### 7.1 Indicadores Implementados

| Indicador | EA | Periodo | Uso |
|-----------|----|---------|-----|
| **ATR** | V2 | 14 | Trailing stop adaptativo |

### 7.2 Indicadores que Podem Ser Adicionados

Baseado nos EAs, estes sao os indicadores mais uteis para trading:

```mql5
// ATR - Average True Range (volatilidade)
int handle = iATR(_Symbol, PERIOD_CURRENT, 14);

// RSI - Relative Strength Index (sobrecompra/sobrevenda)
int handle = iRSI(_Symbol, PERIOD_CURRENT, 14, PRICE_CLOSE);

// MACD - Moving Average Convergence Divergence (tendencia)
int handle = iMACD(_Symbol, PERIOD_CURRENT, 12, 26, 9, PRICE_CLOSE);

// Bollinger Bands (volatilidade + suportes/resistencias)
int handle = iBands(_Symbol, PERIOD_CURRENT, 20, 2, 0, PRICE_CLOSE);

// EMA - Exponential Moving Average (tendencia)
int handle = iMA(_Symbol, PERIOD_CURRENT, 21, 0, MODE_EMA, PRICE_CLOSE);

// Stochastic (momentum)
int handle = iStochastic(_Symbol, PERIOD_CURRENT, 5, 3, 3, MODE_SMA, STO_LOWHIGH);

// Ichimoku (sistema completo)
int handle = iIchimoku(_Symbol, PERIOD_CURRENT, 9, 26, 52);

// ADX - Average Directional Index (forca da tendencia)
int handle = iADX(_Symbol, PERIOD_CURRENT, 14);
```

### 7.3 Padrao de Uso de Indicadores

```mql5
// 1. Criar handle no OnInit() (mais eficiente)
int atr_handle = iATR(_Symbol, PERIOD_CURRENT, 14);

// 2. No OnTick(), copiar buffer
double atr_buffer[];
ArraySetAsSeries(atr_buffer, true);
CopyBuffer(atr_handle, 0, 0, 3, atr_buffer);

// 3. Usar valores
double atr_current = atr_buffer[0];
double atr_prev = atr_buffer[1];
double atr_prev2 = atr_buffer[2];

// 4. No OnDeinit(), liberar handle
IndicatorRelease(atr_handle);
```

---

## 8. BUFFERS E ESTRUTURAS DE DADOS

### 8.1 Estruturas Definidas

#### TradeSignal (EA mql5/Experts)

```mql5
struct TradeSignal {
   datetime timestamp;       // 8 bytes
   string direction;         // dynamic
   double confidence;        // 8 bytes
   double entry_price;       // 8 bytes
   double stop_loss;         // 8 bytes
   double take_profit;       // 8 bytes
   string profile;           // dynamic
   string regime;            // dynamic
   int signal_count;         // 4 bytes
};
```

#### PositionState (EA V2)

```mql5
struct PositionState {
   ulong  ticket;              // 8 bytes
   string direction;           // dynamic
   double entry_price;         // 8 bytes
   double sl;                  // 8 bytes
   double tp;                  // 8 bytes
   double volume;              // 8 bytes
   double tp2_price;           // 8 bytes
   double tp2_closed_volume;   // 8 bytes
   bool   tp2_hit;             // 1 byte
   bool   breakeven_active;    // 1 byte
   double peak_price;          // 8 bytes
   datetime open_time;         // 8 bytes
};
```

### 8.2 Buffers de Indicadores

```mql5
double atr[];
ArraySetAsSeries(atr, true);  // Index 0 = mais recente
CopyBuffer(handle, 0, 0, 1, atr);  // Copia 1 valor
```

### 8.3 Estruturas Nativas MQL5 Usadas

| Estrutura | Campos Principais |
|-----------|-------------------|
| `MqlTick` | bid, ask, last, volume, time_msc, flags |
| `MqlTradeRequest` | action, symbol, volume, type, price, sl, tp, deviation, magic, comment |
| `MqlTradeResult` | retcode, deal, order, volume, price, comment |
| `MqlTradeTransaction` | type, order, symbol, deal_type, price, volume |
| `MqlDateTime` | year, mon, day, hour, min, sec, day_of_week, day_of_year |

---

## 9. EVENTOS E HANDLERS

### 9.1 Handlers Implementados por EA

| Handler | EA mql5/Experts | EA raiz V1 | EA V2 | Legacy |
|---------|-----------------|------------|-------|--------|
| `OnInit()` | Sim | Sim | Sim | Sim |
| `OnTick()` | Sim | Sim | Sim | Sim |
| `OnDeinit()` | Sim | Sim | Sim | Sim |
| `OnTradeTransaction()` | Nao | Sim | Sim | Nao |
| `OnTimer()` | Nao | Nao | Nao | Sim (1ms) |

### 9.2 Descricao dos Handlers

#### OnInit()
- Chamado uma vez quando o EA e carregado
- Setup de objetos, validacoes, criacao de handles
- Retorna `INIT_SUCCEEDED` ou `INIT_FAILED`

#### OnTick()
- Chamado a cada novo tick do mercado
- Loop principal de trading
- Mais frequente em timeframe menor

#### OnDeinit()
- Chamado quando o EA e removido ou terminal fecha
- `reason` indica motivo: REASON_REMOVE, REASON_RECOMPILE, etc.
- Cleanup de recursos

#### OnTradeTransaction()
- Chamado quando ocorre transacao de trade
- `trans.type`: TRADE_TRANSACTION_DEAL_ADD, POSITION_MODIFY, etc.
- Mais eficiente que polling para tracking de trades
- Usado para atualizar win/loss stats

#### OnTimer()
- Chamado no intervalo definido por `EventSetTimer()` ou `EventSetMillisecondTimer()`
- Usado no legacy para leitura de socket
- Permite operacoes independentes de ticks

### 9.3 Funcoes de Evento

| Funcao | Descricao |
|--------|-----------|
| `EventSetTimer(seconds)` | Timer em segundos |
| `EventSetMillisecondTimer(ms)` | Timer em milissegundos |
| `EventKillTimer()` | Destroi o timer |
| `EventChartCustom()` | Evento customizado para chart |

---

## 10. ERROR HANDLING

### 10.1 Padroes de Error Handling Identificados

#### Check de Handle Invalido
```mql5
int handle = FileOpen(path, FILE_READ|FILE_TXT);
if(handle == INVALID_HANDLE) {
   Print("Failed to open file: ", path);
   return;
}
```

#### Check de Socket
```mql5
socket_handle = SocketCreate();
if(socket_handle == INVALID_HANDLE) {
   Print("Socket creation failed");
   return;
}

bool connected = SocketConnect(socket_handle, ip, port, 500);
if(!connected) {
   SocketClose(socket_handle);
   socket_handle = INVALID_HANDLE;
}
```

#### Check de OrderSend
```mql5
if(OrderSend(request, result)) {
   if(result.retcode == TRADE_RETCODE_DONE) {
      // Success
   } else {
      Print("Order failed with code: ", result.retcode);
   }
} else {
   int error = GetLastError();
   Print("OrderSend failed! Error: ", error);
}
```

#### Check de Position
```mql5
if(!PositionSelectByTicket(ticket)) {
   // Position nao existe mais
   return;
}
```

#### Anti-Slippage (Legacy)
```mql5
double current_profit = PositionGetDouble(POSITION_PROFIT);
if(current_profit <= 0.0) {
   Print("CLOSE ABORTADO: Slippage protection");
   return;  // Nao fecha
}
```

### 10.2 Codigos de Erro Comuns

| Codigo | Significado |
|--------|-------------|
| 0 | Sem erro |
| 4001 | ERR_WRONG_INTERNAL_NAME |
| 4002 | ERR_INVALID_PARAMETER |
| 4003 | ERR_ARRAY_INDEX_OUT_OF_RANGE |
| 4014 | ERR_FUNCTION_NOT_ALLOWED |
| 4024 | ERR_FILE_CANNOT_OPEN |
| 4025 | ERR_FILE_INVALID_HANDLE |
| 4026 | ERR_UNKNOWN_FILE |
| 4051 | ERR_INVALID_PARAMETER |
| 4107 | ERR_TRADE_INVALID_STOPS |
| 4108 | ERR_TRADE_INVALID_VOLUME |
| 4109 | ERR_TRADE_MARKET_CLOSED |
| 4110 | ERR_TRADE_TOO_MANY_REQUESTS |
| 4111 | ERR_TRADE_INVALID_PRICE |
| 4112 | ERR_TRADE_POSITION_NOT_FOUND |

### 10.3 Melhorias de Error Handling Necessarias

1. **Retry logic** para OrderSend falhado
2. **Circuit breaker** para erros consecutivos
3. **Timeout** para leitura de arquivo
4. **Validacao de JSON** robusta
5. **Logging de erros** em arquivo separado
6. **Alertas** para erros criticos

---

## 11. LOGS NO MQL5

### 11.1 Metodos de Logging Usados

| Metodo | EA | Descricao |
|--------|----|-----------|
| `Print()` | Todos | Log no terminal do MT5 |
| `SendNotification()` | EA mql5/Experts | Push notification mobile |
| File logging (planejado) | EA mql5/Experts | `InpLogToFile` definido mas nao implementado |

### 11.2 Emojis Usados nos Logs

| EA | Emojis |
|----|--------|
| EA mql5/Experts | 🚀, 📡, ✅, ❌, ⚠️, 📊, 📥, 📤, 📐, 🛑, ⏰, ⏸️, 🔬 |
| EAs raiz | ✅, ❌, 🔒, 📊, ⚠️, 🎫, 📊, 📦, 💰, 🛑, 🎯, 🗳️, 📈, 📉 |
| Legacy | 🚀, 🔴, ✅, ⚡, ❌, 💀, ⚠️, 📡 |

### 11.3 Formato de Logs

**EA V2 (mais detalhado):**
```
============================================================
FOREX QUANTUM BOT EA V2.0 - INITIALIZED
============================================================
Magic Number: 123456
Max Risk: 1.0%
Max Positions: 1
Smart TP: ON
Trailing ATR: 1.5
Session Start Balance: $10000.00
============================================================

✅ ORDER EXECUTED
   🎫 Ticket: 123456
   📊 Direction: BUY
   📦 Volume: 0.01 lots
   💰 Entry: 1.08500
   🛑 SL: 1.08200
   🎯 TP: 1.09100
   🎯 TP2: 1.09700 (50%)
   🗳️ Votes: BUY=3 | SELL=1 | NEUTRAL=0
   🎯 Confidence: 0.85

📦 POSITION | BUY | Ticket: 123456 | PnL: $15.50 | Peak: $18.20 | SL: 1.08350 | TP2: 1.09700 | Duration: 12 min
```

**Legacy (conciso):**
```
🚀 DubaiMatrixASI HFT Bridge Inicializando...
Tentando conectar a TCP 127.0.0.1:5555
✅ Conexão Data-Stream Matrix (TCP) Estabilizada. ASI operante.
⚡ ASI COMMAND: BUY 0.01 EURUSD
✅ DEFERIDO: 123456 @ 1.08500 | Strike: STRIKE_001
```

---

## 12. COMPARACAO EA ATUAL VS LEGACY

### 12.1 Matriz Comparativa

| Feature | EA mql5/Experts | EA Raiz V1 | EA V2 | Legacy DubaiMatrix |
|---------|-----------------|------------|-------|-------------------|
| **Protocolo** | CSV File | JSON File | JSON File | TCP Socket |
| **Latencia** | ~300s | ~5s | ~5s | ~1ms |
| **Bidirecional** | Nao | Sim | Sim | Sim |
| **Tick Streaming** | Nao | Nao | Nao | Sim |
| **Market Orders** | Sim | Sim | Sim | Sim |
| **Pending Orders** | Nao | Nao | Nao | Sim |
| **Partial Close** | Nao | Nao | Sim | Sim |
| **Close All** | Nao | Nao | Nao | Sim |
| **Trailing Stop** | Sim (ponto fixo) | Nao | Sim (ATR) | Nao |
| **Breakeven** | Nao | Sim | Sim | Nao |
| **Smart TP** | Nao | Nao | Sim | Nao |
| **Anti-Slippage** | Nao | Nao | Nao | Sim |
| **Sonar Probes** | Nao | Nao | Nao | Sim |
| **Strike ID** | Nao | Nao | Nao | Sim |
| **Risk Limits** | Daily + Total | Nao | Nao | Nao |
| **Handshake** | Sim | Nao | Nao | PING/PONG |
| **Reconexao** | Nao | Nao | Nao | Sim |
| **Stats** | Win/Loss | Win/Loss | Win/Loss | Nao |
| **Notificacoes** | Push | Nao | Nao | Nao |

### 12.2 Pontos Fortes de Cada EA

**EA mql5/Experts:**
- Risk management mais robusto (daily loss, total loss)
- Handshake de conexao
- Trailing stop
- Validacao de terminal completa

**EA Raiz V1:**
- Simples e funcional
- Response file para Python
- Breakeven automatico
- OnTradeTransaction para tracking

**EA V2:**
- Smart TP (multi-target)
- Trailing ATR (adaptativo)
- Partial close
- Position state tracking completo
- Peak price tracking

**Legacy DubaiMatrix:**
- Latencia ultra-baixa (TCP)
- Tick streaming em tempo real
- Comandos avancados (limit, sonar, close_all)
- Anti-slippage protection
- Reconexao automatica
- Strike ID tracking

### 12.3 Pontos Fracos de Cada EA

**EA mql5/Experts:**
- Polling muito lento (300s)
- Sem resposta de confirmacao
- Parser CSV basico
- JSON parsing nao existe

**EA Raiz V1:**
- Sem trailing stop
- Sem risk limits
- Parser JSON fragil
- Sem anti-slippage

**EA V2:**
- ATR handle criado a cada chamada (ineficiente)
- Sem risk limits
- Sem reconexao
- Sem tick streaming

**Legacy:**
- Sem gerenciamento de posicoes (trailing, breakeven)
- Sem risk limits
- Sem stats de win/loss
- Sem validacao de terminal

---

## 13. PROTOCOLO DE COMUNICACAO IDEAL

### 13.1 Recomendacao

O **protocolo TCP Socket do Legacy** e o mais adequado para um sistema de trading em tempo real. Porem, deve ser **combinado** com as features dos EAs atuais:

```
PROTOCOLO IDEAL = TCP Socket (Legacy) + Smart TP/Breakeven (V2) + Risk Limits (mql5/Experts)
```

### 13.2 Formato do Protocolo Ideal

```
// Python -> EA
{type}|{payload}\n

// Tipos:
SIGNAL|BUY|EURUSD|0.01|1.08500|1.08200|1.09100|0.85|3|1|0|STRIKE_001
SIGNAL|SELL|EURUSD|0.01|1.08500|1.09100|1.08200|0.75|1|3|0|STRIKE_002
LIMIT|BUY|EURUSD|0.01|1.08000|1.07700|1.09000|LIMIT_001
CLOSE|123456
CLOSE_ALL|EURUSD|0
TRAILING|ON|1.5    // ATR multiplier
BREAKEVEN|ON        // Enable breakeven
RISK|MAX_DAILY_LOSS|5000
RISK|MAX_POSITIONS|3
PAUSE|              // Pause trading
RESUME|             // Resume trading
PING

// EA -> Python
TICK|EURUSD|1.08500|1.08502|1.08501|0.50|1713000000123
RESULT|BUY|SUCCESS|123456|1.08500|STRIKE_001
RESULT|SELL|ERROR|10013
POSITION|123456|EURUSD|BUY|0.01|1.08500|1.08350|1.09100|15.50
STATUS|BALANCE|10000.00|EQUITY|10015.50|MARGIN|50.00
PONG|OK
BREAKEVEN|123456|1.08500
TRAILING|123456|1.08400
TP2_HIT|123456|1.09100
CLOSED|123456|15.50|0.05|-0.10
ALERT|DAILY_LOSS_LIMIT|4500
```

### 13.3 Implementacao do Protocolo Ideal

```mql5
//+------------------------------------------------------------------+
//| EA Ideal - Combinando o melhor de todos                           |
//+------------------------------------------------------------------+

// Do Legacy: TCP Socket + Timer 1ms + comandos avancados
// Do V2: Smart TP + Trailing ATR + PositionState
// Do mql5/Experts: Risk limits + Handshake + Trailing fixo

// Inputs combinados
input string   InpPythonIP         = "127.0.0.1";
input int      InpPythonPort       = 5555;
input int      InpMagicNumber      = 123456;
input double   InpMaxRiskPercent   = 1.0;
input double   InpMaxDailyLoss     = 5000.0;
input double   InpMaxTotalLoss     = 10000.0;
input int      InpMaxPositions     = 3;
input bool     InpUseSmartTP       = true;
input double   InpTP2Ratio         = 0.50;
input double   InpTrailingATR      = 1.5;
input bool     InpUseBreakeven     = true;
input int      InpAntiSlippage     = 10;

// Variaveis globais
int socket_handle = INVALID_HANDLE;
double dailyPnL = 0.0;
double totalPnL = 0.0;
int tradesToday = 0;
bool tradingEnabled = true;
PositionState current_position;
datetime todayStart = 0;

int OnInit() {
   // Do Legacy: conecta socket + timer
   ConnectToPython();
   EventSetMillisecondTimer(1);

   // Do mql5/Experts: valida terminal
   if(!ValidateTerminal()) return INIT_FAILED;

   // Do V2: session tracking
   session_start_balance = AccountInfoDouble(ACCOUNT_BALANCE);

   return INIT_SUCCEEDED;
}

void OnTick() {
   // Do Legacy: envia tick
   SendTickToPython();
}

void OnTimer() {
   // Do Legacy: le comandos
   ReadCommands();

   // Do V2: gerencia posicao
   ManagePosition();
}

void OnTradeTransaction(...) {
   // Do EAs raiz: tracking de win/loss
   TrackDealStats(trans);
}
```

---

## 14. MELHORIAS NECESSARIAS

### 14.1 Prioridade Alta (Critical)

| # | Melhoria | Problema | Solucao |
|---|----------|----------|---------|
| 1 | **TCP Socket** | File I/O e lento (~5s) | Migrar para TCP como o legacy |
| 2 | **JSON Parser Robusto** | Parser manual e fragil | Usar biblioteca ou implementar parser completo |
| 3 | **Anti-Slippage** | Fecha posicoes no prejuizo | Implementar logica do legacy |
| 4 | **Handle de Indicadores no OnInit** | V2 cria handle a cada tick | Mover `iATR()` para `OnInit()` |
| 5 | **Risk Limits** | V1 e V2 nao tem limites | Copiar de mql5/Experts |

### 14.2 Prioridade Media (Important)

| # | Melhoria | Problema | Solucao |
|---|----------|----------|---------|
| 6 | **Reconexao Automatica** | Socket pode cair | Copiar logica do legacy |
| 7 | **Partial Close** | So V2 implementa | Manter no V2 e migrar |
| 8 | **Strike ID Tracking** | Sem tracking de ordens | Copiar do legacy |
| 9 | **Equity/Margin Monitoring** | Nao monitora | Adicionar checks |
| 10 | **File Logging** | `InpLogToFile` nao usado | Implementar `FileWrite` para log |

### 14.3 Prioridade Baixa (Nice to Have)

| # | Melhoria | Problema | Solucao |
|---|----------|----------|---------|
| 11 | **Mais Indicadores** | So ATR | Adicionar RSI, MACD, etc |
| 12 | **Multi-Symbol** | So 1 simbolo | Suportar multiplos |
| 13 | **Pending Orders** | So market | Adicionar limits |
| 14 | **Sonar Probes** | Nao existe | Copiar do legacy |
| 15 | **Push Notifications** | So mql5/Experts | Manter e expandir |

### 14.4 Bugs Encontrados

| Bug | Arquivo | Descricao | Impacto |
|-----|---------|-----------|---------|
| 1 | EA V2 | `GetATR()` cria handle a cada chamada | Performance degradation |
| 2 | EA V1/V2 | `ExtractJsonValue` nao suporta arrays/nested | JSON complexo falha |
| 3 | EA V1/V2 | `FileDelete()` antes de verificar sucesso | Perda de sinal se execucao falhar |
| 4 | EA mql5/Experts | `InpLogToFile` definido mas nao usado | Sem log em arquivo |
| 5 | EA mql5/Experts | PnL acumulado em loop sem reset | Double counting possivel |
| 6 | EA V2 | `CalculateClosedPnL()` busca por comment, nao ticket | Match incorreto possivel |

---

## 15. CODIGO REUTILIZAVEL DO LEGACY

### 15.1 Modulos para Extrair

#### 15.1.1 Socket Communication

```mql5
// Do legacy - pronto para uso
int socket_handle = INVALID_HANDLE;

void ConnectToPython(string ip, int port) {
   if(socket_handle != INVALID_HANDLE) SocketClose(socket_handle);
   socket_handle = SocketCreate();
   if(socket_handle != INVALID_HANDLE) {
      SocketConnect(socket_handle, ip, port, 500);
   }
}

void SendTCP(string msg) {
   if(socket_handle != INVALID_HANDLE) {
      uchar data[];
      StringToCharArray(msg, data);
      SocketSend(socket_handle, data, ArraySize(data)-1);
   }
}

string ReadTCP() {
   if(socket_handle == INVALID_HANDLE) return "";
   uint bytes = SocketIsReadable(socket_handle);
   if(bytes > 0) {
      uchar buffer[];
      SocketRead(socket_handle, buffer, bytes, 10);
      return CharArrayToString(buffer, 0, ArraySize(buffer));
   }
   return "";
}
```

#### 15.1.2 Anti-Slippage Protection

```mql5
// Do legacy - protege fechamentos
bool SafeClose(ulong ticket) {
   if(!PositionSelectByTicket(ticket)) return false;

   double current_profit = PositionGetDouble(POSITION_PROFIT);
   if(current_profit <= 0.0) {
      Print("CLOSE ABORTADO: Slippage protection | Profit: ", current_profit);
      return false;
   }

   // ... executa close
   return true;
}
```

#### 15.1.3 Command Parser

```mql5
// Do legacy - parser de protocolo pipe-delimited
void ProcessSingleCommand(string cmd) {
   string parts[];
   int count = StringSplit(cmd, '|', parts);
   if(count < 1) return;

   string action = parts[0];
   if(action == "PING") { SendTCP("PONG|OK\n"); return; }
   if(action == "BUY" || action == "SELL") { /* execute */ }
   if(action == "CLOSE") { /* close position */ }
   if(action == "CLOSE_ALL") { /* close all */ }
   if(action == "LIMIT") { /* pending order */ }
}
```

#### 15.1.4 Tick Streaming

```mql5
// Do legacy - envia ticks em tempo real
void SendTickToPython(string symbol) {
   MqlTick tick;
   if(SymbolInfoTick(symbol, tick)) {
      string data = "TICK|" + symbol + "|" +
                    DoubleToString(tick.bid, (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS)) + "|" +
                    DoubleToString(tick.ask, (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS)) + "|" +
                    DoubleToString(tick.volume_real, 2) + "|" +
                    IntegerToString(tick.time_msc) + "\n";
      SendTCP(data);
   }
}
```

#### 15.1.5 Reconexao Automatica

```mql5
// Do legacy - reconecta a cada 1s se desconectado
void OnTimer() {
   if(socket_handle == INVALID_HANDLE) {
      static uint last_reconnect = 0;
      if(GetTickCount() - last_reconnect > 1000) {
         ConnectToPython(InpPythonIP, InpPythonPort);
         last_reconnect = GetTickCount();
      }
      return;
   }
   // ... le dados
}
```

### 15.2 Codigo Reutilizavel dos EAs Atuais

#### 15.2.1 Smart TP (V2)

```mql5
// Do V2 - fecha parcial no TP2
double CalculateTP2Price(double entry, double sl, string direction) {
   double risk = MathAbs(entry - sl);
   return (direction == "BUY") ? entry + risk * 2.0 : entry - risk * 2.0;
}

bool ClosePartialPosition(ulong ticket, double close_volume, string comment) {
   if(!PositionSelectByTicket(ticket)) return false;
   string symbol = PositionGetString(POSITION_SYMBOL);
   long type = PositionGetInteger(POSITION_TYPE);
   double price = (type == POSITION_TYPE_BUY) ?
                  SymbolInfoDouble(symbol, SYMBOL_BID) :
                  SymbolInfoDouble(symbol, SYMBOL_ASK);
   if(type == POSITION_TYPE_BUY)
      return trade.Sell(close_volume, symbol, price, 0, 0, comment);
   else
      return trade.Buy(close_volume, symbol, price, 0, 0, comment);
}
```

#### 15.2.2 Breakeven (V1/V2)

```mql5
// Do V1/V2 - move SL para breakeven
bool MoveToBreakeven(ulong ticket, double entry_price) {
   if(!PositionSelectByTicket(ticket)) return false;
   double current_tp = PositionGetDouble(POSITION_TP);
   return trade.PositionModify(ticket, entry_price, current_tp);
}
```

#### 15.2.3 Risk Limits (mql5/Experts)

```mql5
// Do mql5/Experts - limita perdas
bool CheckRiskLimits(double dailyPnL, double totalPnL, double maxDaily, double maxTotal) {
   if(dailyPnL < -maxDaily) {
      Print("Daily loss limit reached");
      return false;
   }
   if(totalPnL < -maxTotal) {
      Print("Total loss limit reached");
      return false;
   }
   return true;
}
```

#### 15.2.4 Lot Size Calculator (mql5/Experts)

```mql5
// Do mql5/Experts - calcula lote baseado em risco
double CalculateLotSize(double balance, double riskPercent, double slDistance, string symbol) {
   double riskAmount = balance * riskPercent / 100.0;
   double tickValue = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_VALUE);
   double tickSize = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_SIZE);
   double lotSize = riskAmount / (slDistance / tickSize * tickValue);

   double lotStep = SymbolInfoDouble(symbol, SYMBOL_VOLUME_STEP);
   double minLot = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);
   double maxLot = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MAX);

   lotSize = MathFloor(lotSize / lotStep) * lotStep;
   return MathMax(minLot, MathMin(maxLot, lotSize));
}
```

---

## APENDICE A: FORMATOS DE ARQUIVO

### A.1 CSV Signal (EA mql5/Experts)

```
2026-04-12 10:30:00,BUY,0.85,1.08500,1.08200,1.09100,QuantumAgent,RangeBound
```

### A.2 JSON Signal (EAs raiz)

```json
{
  "direction": "BUY",
  "volume": 0.01,
  "stop_loss": 1.08200,
  "take_profit": 1.09100,
  "entry_price": 1.08500,
  "confidence": 0.85,
  "buy_votes": 3,
  "sell_votes": 1,
  "neutral_votes": 0
}
```

### A.3 JSON Response (EAs raiz)

```json
{
  "ticket": 123456,
  "success": true,
  "message": "Order executed",
  "timestamp": "2026-04-12 10:30:05"
}
```

### A.4 TCP Protocol (Legacy)

```
Comando: ACTION|SYMBOL|LOT|SL|TP[|STRIKE_ID]\n
Tick:    TICK|SYMBOL|BID|ASK|LAST|VOLUME|TIME_MS\n
Result:  RESULT|ACTION|SUCCESS|DEAL|PRICE[|STRIKE]\n
Health:  PING -> PONG|OK\n
```

---

## APENDICE B: API MQL5 DE REFERENCIA

### B.1 Funcoes de Trading

| Funcao | Descricao | Retorno |
|--------|-----------|---------|
| `OrderSend(request, result)` | Envia ordem | bool |
| `PositionsTotal()` | Total de posicoes | int |
| `PositionGetTicket(index)` | Ticket da posicao | ulong |
| `PositionSelectByTicket(ticket)` | Seleciona posicao | bool |
| `PositionGetString(prop)` | Propriedade string | string |
| `PositionGetInteger(prop)` | Propriedade int | long |
| `PositionGetDouble(prop)` | Propriedade double | double |
| `HistorySelect(from, to)` | Seleciona historico | bool |
| `HistoryDealsTotal()` | Total de deals | int |
| `HistoryDealGetTicket(index)` | Ticket do deal | ulong |
| `HistoryDealSelect(ticket)` | Seleciona deal | bool |
| `HistoryDealGetDouble(ticket, prop)` | Propriedade do deal | double |

### B.2 Funcoes de Informacao

| Funcao | Descricao | Retorno |
|--------|-----------|---------|
| `SymbolInfoTick(symbol, tick)` | Tick atual | bool |
| `SymbolInfoDouble(symbol, prop)` | Info double | double |
| `SymbolInfoInteger(symbol, prop)` | Info int | long |
| `SymbolInfoString(symbol, prop)` | Info string | string |
| `AccountInfoDouble(prop)` | Info da conta | double |
| `AccountInfoInteger(prop)` | Info da conta | long |
| `TerminalInfoInteger(prop)` | Info do terminal | bool |

### B.3 Funcoes de Indicadores

| Funcao | Descricao | Retorno |
|--------|-----------|---------|
| `iATR(symbol, timeframe, period)` | Handle ATR | int |
| `iRSI(symbol, timeframe, period, applied)` | Handle RSI | int |
| `iMACD(symbol, tf, fast, slow, signal, applied)` | Handle MACD | int |
| `iBands(symbol, tf, period, deviation, shift, applied)` | Handle Bands | int |
| `iMA(symbol, tf, period, shift, method, applied)` | Handle MA | int |
| `CopyBuffer(handle, buffer_num, start, count, array[])` | Copia buffer | int |
| `IndicatorRelease(handle)` | Libera handle | bool |

### B.4 Funcoes de Arquivo

| Funcao | Descricao | Retorno |
|--------|-----------|---------|
| `FileIsExist(path)` | Verifica existencia | bool |
| `FileOpen(path, flags, delimiter)` | Abre arquivo | int |
| `FileReadString(handle)` | Le string | string |
| `FileWriteString(handle, string)` | Escreve string | uint |
| `FileClose(handle)` | Fecha arquivo | void |
| `FileDelete(path)` | Deleta arquivo | bool |
| `FileIsEnding(handle)` | Fim do arquivo | bool |

**Flags de arquivo:**
- `FILE_READ` - Leitura
- `FILE_WRITE` - Escrita
- `FILE_TXT` - Texto
- `FILE_CSV` - CSV
- `FILE_ANSI` - ANSI encoding
- `FILE_COMMON` - Pasta Common (compartilhada com Python)

### B.5 Funcoes de Socket

| Funcao | Descricao | Retorno |
|--------|-----------|---------|
| `SocketCreate()` | Cria socket | int (handle) |
| `SocketConnect(handle, ip, port, timeout)` | Conecta | bool |
| `SocketSend(handle, data[], len)` | Envia dados | int (bytes) |
| `SocketRead(handle, data[], max_len, timeout)` | Le dados | int (bytes) |
| `SocketIsReadable(handle)` | Bytes disponiveis | uint |
| `SocketClose(handle)` | Fecha socket | void |

### B.6 Funcoes de Sistema

| Funcao | Descricao | Retorno |
|--------|-----------|---------|
| `TimeCurrent()` | Hora atual | datetime |
| `TimeToString(time, mode)` | Formata hora | string |
| `StringToTime(string)` | Parse hora | datetime |
| `GetLastError()` | Ultimo erro | int |
| `GetTickCount()` | Contador de ms | uint |
| `Print(...)` | Log no terminal | void |
| `SendNotification(msg)` | Push notification | bool |
| `ZeroMemory(var)` | Zera memoria | void |
| `NormalizeDouble(value, digits)` | Normaliza double | double |
| `MathAbs(value)` | Valor absoluto | double |
| `MathFloor(value)` | Arredonda para baixo | double |
| `MathMax(a, b)` | Maximo | double |
| `MathMin(a, b)` | Minimo | double |
| `StringFind(str, substr, start)` | Busca substring | int |
| `StringSplit(str, delimiter, result[])` | Split string | int |
| `CharArrayToString(arr, start, count)` | Char[] -> string | string |
| `StringToCharArray(str, arr)` | String -> char[] | int |

---

## APENDICE C: CHECKLIST DE IMPLEMENTACAO DO EA IDEAL

### C.1 Fase 1 - Comunicacao TCP

- [ ] Implementar `SocketCreate()` e `SocketConnect()` no `OnInit()`
- [ ] Implementar `EventSetMillisecondTimer(1)` para leitura
- [ ] Implementar `OnTimer()` com `SocketRead()` e `ParseCommands()`
- [ ] Implementar envio de ticks no `OnTick()`
- [ ] Implementar reconexao automatica
- [ ] Implementar PING/PONG health check

### C.2 Fase 2 - Execucao de Ordens

- [ ] Implementar `ExecuteTrade()` para market orders
- [ ] Implementar `ExecuteLimitOrder()` para pending orders
- [ ] Implementar `ExecuteClose()` com anti-slippage
- [ ] Implementar `ExecuteCloseAll()` para mass close
- [ ] Implementar resposta via TCP (RESULT|...)
- [ ] Implementar Strike ID tracking

### C.3 Fase 3 - Gerenciamento de Posicoes

- [ ] Implementar `PositionState` struct (do V2)
- [ ] Implementar Smart TP com partial close (do V2)
- [ ] Implementar Breakeven (do V1/V2)
- [ ] Implementar Trailing ATR (do V2)
- [ ] Implementar Peak Price tracking (do V2)
- [ ] Corrigir `GetATR()` para criar handle no `OnInit()`

### C.4 Fase 4 - Risk Management

- [ ] Implementar daily loss limit (do mql5/Experts)
- [ ] Implementar total loss limit (do mql5/Experts)
- [ ] Implementar max trades per day (do mql5/Experts)
- [ ] Implementar min trade interval (do mql5/Experts)
- [ ] Implementar lot size calculator (do mql5/Experts)
- [ ] Implementar max positions check

### C.5 Fase 5 - Monitoring e Logging

- [ ] Implementar `OnTradeTransaction()` para stats
- [ ] Implementar win/loss tracking
- [ ] Implementar PnL reporting via TCP
- [ ] Implementar status reporting (balance, equity, margin)
- [ ] Implementar alertas via TCP
- [ ] Implementar log em arquivo

### C.6 Fase 6 - Validacao

- [ ] Implementar `ValidateTerminal()` (do mql5/Experts)
- [ ] Implementar symbol validation
- [ ] Implementar tick validation
- [ ] Implementar circuit breaker para erros consecutivos
- [ ] Testar reconexao
- [ ] Testar anti-slippage

---

## RESUMO EXECUTIVO

### O que Funciona

1. **TCP Socket (Legacy)** -- Melhor sistema de comunicacao. Latencia de 1ms, bidirecional, tick streaming.
2. **Smart TP + Trailing ATR (V2)** -- Melhor gerenciamento de posicoes. Fecha parcial, trailing adaptativo.
3. **Risk Limits (mql5/Experts)** -- Melhor protecao de capital. Daily loss, total loss, max trades.
4. **Breakeven (V1/V2)** -- Protecao basica eficiente. Move SL para entry no 1R.
5. **Anti-Slippage (Legacy)** -- Protecao unica. Aborta fechamento se lucro derreteu.
6. **OnTradeTransaction (V1/V2)** -- Tracking eficiente de trades em tempo real.
7. **Strike ID (Legacy)** -- Tracking de ordens para correlacao Python<->MQL5.

### O que Precisa de Melhoria

1. **File-based communication** -- Deve ser substituido por TCP
2. **JSON Parser manual** -- Deve ser substituido por parser robusto
3. **ATR handle creation** -- Deve ser movido para OnInit()
4. **Missing features no Legacy** -- trailing, breakeven, smart TP
5. **Missing features no Atual** -- pending orders, sonar, close_all

### Recomendacao Final

**Construir um EA unico combinando:**
- TCP Socket do Legacy (comunicacao)
- Smart TP + Trailing ATR do V2 (gerenciamento)
- Risk Limits do mql5/Experts (protecao)
- Anti-Slippage do Legacy (seguranca)
- OnTradeTransaction dos EAtuais (monitoring)
- Strike ID do Legacy (tracking)

**Protocolo ideal:** TCP pipe-delimited com tipos: SIGNAL, LIMIT, CLOSE, CLOSE_ALL, TRAILING, BREAKEVEN, RISK, PAUSE, RESUME, PING.

---

*Documento gerado em 2026-04-13. Analise baseada em 4 arquivos .mq5 totais identificados no projeto atual e legacy.*
