# LIVE TRADING V3: ARCHITECTURE & SYNCHRONIZATION BLUEPRINT
*Date: 2026-04-14 | Author: Executive AI (CEO)*

## 1. THE PARITY GAP (Why V2 Failed)
The forensic analysis of `run_backtest_complete_v2.py` (which generated 103k PnL) versus `run_live_trading_v2.py` revealed a fundamental architectural gap:
- **Backtest (The Brain):** Operates on vectorized blocks of data (Pandas/Numpy), computing indicators for the entire dataset upfront. The `_generate_signal_fast` method evaluates 12 Execution Agents simultaneously with specific, hardcoded logic optimized via Ghost Audits (e.g., confidence inversion, asymmetrical SELL boosts, and 15x risk multipliers).
- **Live V2 (The Flawed Body):** Attempted to recreate the backtest logic using abstract classes (`BaseStrategy`, `StrategyOrchestrator`) on a tick-by-tick basis. It suffered from constant instantiations, unaligned data contracts (`TradingSignal` vs `AdvancedSignal`), and a rigid Veto Cascade that silenced valid trades due to micro-volatility noise from the MT5 TCP Socket.

## 2. THE V3 SOLUTION: STATE-SPACE ALIGNMENT
To achieve 103k PnL in live trading, V3 abandons the "Tick-by-Tick Recomputation" paradigm and adopts a **"State-Synchronization / Event-Driven"** model.

### Pillar 1: The Zero-Latency Event Bus (Data Ingestion)
- **Elimination of `while True` Loops:** The Python system will no longer poll. It will wait for MT5.
- **Push/Pull Architecture:** The EA (`ForexQuantumBot_EA_V3.mq5`) will compute all indicators (ATR, RSI, EMA9-200, MACD) natively using MQL5 `CopyBuffer` and send a structured payload (`SNAPSHOT|...`) upon every new M5 candle close (or significant tick).
- **Python DataEngine V3:** Acts only as a receiver and formatter. It takes the MT5 snapshot and instantly formats it into a single Pandas DataFrame row, perfectly mimicking the data structure the backtest uses.

### Pillar 2: The Decoupled Core Intelligence (The Brain)
- **`src/core/core_intelligence.py`:** We will extract `_generate_signal_fast` from the backtest and place it here.
- **True Parity:** Both the Backtest and Live V3 will import and call `core_intelligence.evaluate(snapshot)`. If the backtest says BUY, the Live system will say BUY. Zero logical deviation.
- **Ghost Audit Integration:** The exact confidence tuning (boosting medium confidence, penalizing extreme confidence, and favoring SELLs) will be hardcoded into this core module.

### Pillar 3: Robust Execution Protocol (ZeroMQ / Advanced Sockets)
- **Signal Protocol:** `SIGNAL|SYMBOL|DIRECTION|VOLUME|SL|TP|MAGIC|TIMESTAMP\n`
- **SL/TP Validation:** The core will enforce that TP is mathematically valid (TP < Entry for SELL, TP > Entry for BUY) *before* hitting the socket.
- **Execution Acknowledgment:** The Python `TradeExecutor` will hold a state machine (`PENDING -> EXECUTED -> TRACKING`) and wait for the EA's `ORDER_FILLED` callback.

### Pillar 4: PhD-Level Telemetry (The Matrix Log)
The terminal will display a structured, cycle-by-cycle matrix instead of spamming raw ticks:
```text
[CYCLE: 2026-04-14 22:00] | BTCUSD @ 74000.00
|-- INDICATORS: RSI=58.2 | ATR=160.5 | Trend=Bullish
|-- VOTING MATRIX: 
    | MSNR: BUY (0.8) | IFVG: WAIT | Therm: SELL (0.6) | ...
|-- M8 FIBONACCI: Confirmed (0.95)
|-- ORCHESTRATOR DECISION: BUY | Consensus: 0.86
|-- RISK ENGINE: Vol=1.0 Lot | SL=73750 | TP=74750
[ACTION] -> SIGNAL SENT TO MT5
```

## 3. IMPLEMENTATION ROADMAP
1. **Scaffold `live_v3/`:** Create the clean directory structure.
2. **Extract `core_intelligence.py`:** Isolate the winning backtest logic.
3. **Build `DataEngineV3` & `TradeExecutorV3`:** Implement the Event Bus and robust socket handling.
4. **Update `ForexQuantumBot_EA_V3.mq5`:** Ensure it sends complete snapshots and handles the exact 7-part SIGNAL protocol.
5. **Launch `run_quantum_live_v3.py`:** The final, unified entry point.