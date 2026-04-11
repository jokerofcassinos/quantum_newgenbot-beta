//+------------------------------------------------------------------+
//|                                       ForexQuantumBot_EA.mq5      |
//|                                    Forex Quantum Bot - MQL5 EA    |
//|                                    CEO: Qwen Code | 2026-04-12    |
//|                                                                   |
//| Expert Advisor que integra sistemas quânticos C++ e Python         |
//| com execução nativa no MT5 via sinais externos                     |
//+------------------------------------------------------------------+
#property copyright "Forex Quantum Bot - Qwen Code"
#property version   "1.00"
#property description "AI Quantum Trading System - C++ Monte Carlo + Neural Networks"
#property strict

//+------------------------------------------------------------------+
//| Input Parameters                                                  |
//+------------------------------------------------------------------+
input group "=== TRADING SETTINGS ==="
input string   InpSymbol = "BTCUSD";           // Trading Symbol
input ENUM_TIMEFRAMES InpTimeframe = PERIOD_M5; // Analysis Timeframe
input double   InpLotSize = 0.01;              // Base Lot Size
input int      InpMagicNumber = 20260412;      // Magic Number
input int      InpMaxPositions = 1;            // Max Simultaneous Positions

input group "=== RISK MANAGEMENT ==="
input double   InpRiskPercent = 0.5;           // Risk % per Trade
input double   InpMaxDailyLoss = 5000.0;       // Max Daily Loss ($)
input double   InpMaxTotalLoss = 10000.0;      // Max Total Loss ($)
input int      InpMaxTradesPerDay = 10;        // Max Trades per Day
input int      InpMinTradeInterval = 1800;     // Min Interval Between Trades (seconds)

input group "=== STOP LOSS & TAKE PROFIT ==="
input int      InpStopLossPoints = 300;        // Stop Loss (points)
input int      InpTakeProfitPoints = 600;      // Take Profit (points)
input bool     InpUseTrailingStop = true;      // Use Trailing Stop
input int      InpTrailingStart = 200;         // Trailing Start (points)
input int      InpTrailingDistance = 150;      // Trailing Distance (points)

input group "=== SIGNAL INTEGRATION ==="
input string   InpSignalFile = "D:\\forex-project2k26\\data\\signals\\trade_signal.csv"; // Signal file path
input bool     InpAutoTrade = false;           // Auto Trade (false = signals only)
input int      InpSignalCheckInterval = 60;    // Signal Check Interval (seconds)

input group "=== NOTIFICATIONS ==="
input bool     InpSendNotifications = true;    // Send Push Notifications
input bool     InpLogDetails = true;           // Log Detailed Info

//+------------------------------------------------------------------+
//| Global Variables                                                  |
//+------------------------------------------------------------------+
int magicNumber;
double dailyPnL = 0.0;
double totalPnL = 0.0;
int tradesToday = 0;
datetime lastTradeTime = 0;
datetime todayStart = 0;
bool tradingEnabled = true;

// Trade signal structure
struct TradeSignal {
   datetime timestamp;
   string direction;      // "BUY" or "SELL"
   double confidence;
   double entry_price;
   double stop_loss;
   double take_profit;
   string profile;
   string regime;
   int signal_count;
};

TradeSignal currentSignal;

//+------------------------------------------------------------------+
//| Expert initialization function                                    |
//+------------------------------------------------------------------+
int OnInit() {
   magicNumber = InpMagicNumber;
   todayStart = TimeCurrent();
   
   Print("============================================================");
   Print("🚀 FOREX QUANTUM BOT - MQL5 EA INITIALIZING");
   Print("============================================================");
   Print("   Symbol: ", InpSymbol);
   Print("   Timeframe: ", EnumToString(InpTimeframe));
   Print("   Magic Number: ", magicNumber);
   Print("   Auto Trade: ", InpAutoTrade ? "ENABLED" : "DISABLED (Signals Only)");
   Print("   Risk %: ", DoubleToString(InpRiskPercent, 2));
   Print("   Max Daily Loss: $", DoubleToString(InpMaxDailyLoss, 2));
   Print("   Max Total Loss: $", DoubleToString(InpMaxTotalLoss, 2));
   Print("============================================================");
   
   // Verify symbol
   if(!SymbolSelect(InpSymbol, true)) {
      Print("❌ Error: Symbol ", InpSymbol, " not available!");
      return INIT_FAILED;
   }
   
   // Check symbol info
   MqlTick tick;
   if(!SymbolInfoTick(InpSymbol, tick)) {
      Print("❌ Error: Cannot get tick for ", InpSymbol);
      return INIT_FAILED;
   }
   
   Print("✅ Symbol verified: ", InpSymbol);
   Print("   Bid: ", DoubleToString(tick.bid, 2));
   Print("   Ask: ", DoubleToString(tick.ask, 2));
   Print("   Spread: ", DoubleToString(tick.ask - tick.bid, 2));
   
   // Initialize daily tracking
   ResetDailyStats();
   
   Print("✅ EA initialized successfully!");
   Print("============================================================");
   
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                  |
//+------------------------------------------------------------------+
void OnDeinit(const int reason) {
   Print("============================================================");
   Print("🛑 FOREX QUANTUM BOT - EA SHUTTING DOWN");
   Print("============================================================");
   Print("   Reason: ", reason);
   Print("   Total PnL: $", DoubleToString(totalPnL, 2));
   Print("   Daily PnL: $", DoubleToString(dailyPnL, 2));
   Print("   Trades Today: ", tradesToday);
   Print("============================================================");
   
   // Close all positions if needed
   if(reason == REASON_REMOVE) {
      Print("⚠️ EA removed - positions will remain open");
   }
}

//+------------------------------------------------------------------+
//| Expert tick function                                              |
//+------------------------------------------------------------------+
void OnTick() {
   // Update daily stats
   UpdateDailyStats();
   
   // Check if trading is enabled
   if(!tradingEnabled) {
      return;
   }
   
   // Check risk limits
   if(!CheckRiskLimits()) {
      return;
   }
   
   // Check for new signals
   static datetime lastSignalCheck = 0;
   if(TimeCurrent() - lastSignalCheck >= InpSignalCheckInterval) {
      lastSignalCheck = TimeCurrent();
      CheckForSignals();
   }
   
   // Manage open positions
   ManagePositions();
   
   // Update trailing stops
   if(InpUseTrailingStop) {
      UpdateTrailingStops();
   }
}

//+------------------------------------------------------------------+
//| Check for trade signals from external file                        |
//+------------------------------------------------------------------+
void CheckForSignals() {
   // Read signal file generated by Python system
   int handle = FileOpen(InpSignalFile, FILE_READ|FILE_CSV|FILE_ANSI, ',');
   if(handle == INVALID_HANDLE) {
      // File doesn't exist yet - normal, no signals
      return;
   }
   
   // Parse CSV signal file
   string timestamp_str = FileReadString(handle);
   string direction = FileReadString(handle);
   string confidence_str = FileReadString(handle);
   string entry_str = FileReadString(handle);
   string sl_str = FileReadString(handle);
   string tp_str = FileReadString(handle);
   string profile = FileReadString(handle);
   string regime = FileReadString(handle);
   
   FileClose(handle);
   
   // Parse values
   currentSignal.timestamp = StringToTime(timestamp_str);
   currentSignal.direction = direction;
   currentSignal.confidence = StringToDouble(confidence_str);
   currentSignal.entry_price = StringToDouble(entry_str);
   currentSignal.stop_loss = StringToDouble(sl_str);
   currentSignal.take_profit = StringToDouble(tp_str);
   currentSignal.profile = profile;
   currentSignal.regime = regime;
   
   // Check signal age (max 5 minutes old)
   if(TimeCurrent() - currentSignal.timestamp > 300) {
      if(InpLogDetails) {
         Print("⏰ Signal too old - ignoring");
      }
      return;
   }
   
   // Validate signal
   if(currentSignal.direction != "BUY" && currentSignal.direction != "SELL") {
      return;
   }
   
   if(currentSignal.confidence < 0.6) {
      if(InpLogDetails) {
         Print("📊 Signal confidence too low: ", DoubleToString(currentSignal.confidence, 2));
      }
      return;
   }
   
   // Check trade interval
   if(TimeCurrent() - lastTradeTime < InpMinTradeInterval) {
      if(InpLogDetails) {
         Print("⏰ Trade cooldown - waiting...");
      }
      return;
   }
   
   // Check max trades per day
   if(tradesToday >= InpMaxTradesPerDay) {
      if(InpLogDetails) {
         Print("⚠️ Max trades per day reached: ", tradesToday);
      }
      return;
   }
   
   // Execute trade if auto trading enabled
   if(InpAutoTrade) {
      ExecuteTrade(currentSignal);
   } else {
      // Log signal for manual review
      Print("📊 NEW SIGNAL (Manual Mode):");
      Print("   Direction: ", currentSignal.direction);
      Print("   Confidence: ", DoubleToString(currentSignal.confidence, 2));
      Print("   Entry: ", DoubleToString(currentSignal.entry_price, 2));
      Print("   SL: ", DoubleToString(currentSignal.stop_loss, 2));
      Print("   TP: ", DoubleToString(currentSignal.take_profit, 2));
      Print("   Profile: ", currentSignal.profile);
      Print("   Regime: ", currentSignal.regime);
      
      if(InpSendNotifications) {
         SendNotification("🔬 Quantum Bot Signal\n" +
                         "Direction: " + currentSignal.direction + "\n" +
                         "Confidence: " + DoubleToString(currentSignal.confidence, 2) + "\n" +
                         "Entry: $" + DoubleToString(currentSignal.entry_price, 2) + "\n" +
                         "Profile: " + currentSignal.profile);
      }
   }
}

//+------------------------------------------------------------------+
//| Execute trade based on signal                                     |
//+------------------------------------------------------------------+
void ExecuteTrade(TradeSignal &signal) {
   // Check current positions
   int positionCount = CountPositions();
   if(positionCount >= InpMaxPositions) {
      if(InpLogDetails) {
         Print("⚠️ Max positions reached: ", positionCount);
      }
      return;
   }
   
   // Calculate lot size based on risk
   double lotSize = CalculateLotSize(signal);
   if(lotSize <= 0) {
      Print("❌ Invalid lot size calculation");
      return;
   }
   
   // Normalize prices
   int digits = (int)SymbolInfoInteger(InpSymbol, SYMBOL_DIGITS);
   double entry = signal.entry_price;
   double sl = signal.stop_loss;
   double tp = signal.take_profit;
   
   entry = NormalizeDouble(entry, digits);
   sl = NormalizeDouble(sl, digits);
   tp = NormalizeDouble(tp, digits);
   
   // Execute order
   MqlTradeRequest request = {};
   MqlTradeResult result = {};
   
   request.action = TRADE_ACTION_DEAL;
   request.symbol = InpSymbol;
   request.volume = lotSize;
   request.type = (signal.direction == "BUY") ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   request.price = (signal.direction == "BUY") ? 
                   SymbolInfoDouble(InpSymbol, SYMBOL_ASK) : 
                   SymbolInfoDouble(InpSymbol, SYMBOL_BID);
   request.sl = sl;
   request.tp = tp;
   request.deviation = 100;
   request.magic = magicNumber;
   request.comment = "QuantumBot-" + signal.profile;
   
   if(OrderSend(request, result)) {
      if(result.retcode == TRADE_RETCODE_DONE) {
         // Trade executed successfully
         lastTradeTime = TimeCurrent();
         tradesToday++;
         
         Print("✅ TRADE EXECUTED:");
         Print("   Ticket: ", result.order);
         Print("   Direction: ", signal.direction);
         Print("   Volume: ", DoubleToString(lotSize, 2));
         Print("   Entry: ", DoubleToString(request.price, digits));
         Print("   SL: ", DoubleToString(sl, digits));
         Print("   TP: ", DoubleToString(tp, digits));
         Print("   Profile: ", signal.profile);
         Print("   Regime: ", signal.regime);
         Print("   Confidence: ", DoubleToString(signal.confidence, 2));
         
         if(InpSendNotifications) {
            SendNotification("✅ Trade Executed\n" +
                            "Ticket: " + IntegerToString(result.order) + "\n" +
                            "Direction: " + signal.direction + "\n" +
                            "Volume: " + DoubleToString(lotSize, 2) + "\n" +
                            "Entry: $" + DoubleToString(request.price, digits) + "\n" +
                            "P&L: Monitoring...");
         }
      } else {
         Print("❌ Order send error: ", result.retcode, " - ", result.comment);
      }
   } else {
      Print("❌ Order send failed: ", GetLastError());
   }
}

//+------------------------------------------------------------------+
//| Calculate lot size based on risk management                       |
//+------------------------------------------------------------------+
double CalculateLotSize(TradeSignal &signal) {
   // Get account balance
   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   
   // Calculate risk amount
   double riskAmount = balance * InpRiskPercent / 100.0;
   
   // Calculate stop loss distance in points
   double slDistance = MathAbs(signal.entry_price - signal.stop_loss);
   if(slDistance == 0) {
      slDistance = InpStopLossPoints * SymbolInfoDouble(InpSymbol, SYMBOL_POINT);
   }
   
   // Get tick value
   double tickValue = SymbolInfoDouble(InpSymbol, SYMBOL_TRADE_TICK_VALUE);
   double tickSize = SymbolInfoDouble(InpSymbol, SYMBOL_TRADE_TICK_SIZE);
   
   // Calculate lot size
   double lotSize = riskAmount / (slDistance / tickSize * tickValue);
   
   // Normalize to symbol lot step
   double lotStep = SymbolInfoDouble(InpSymbol, SYMBOL_VOLUME_STEP);
   double minLot = SymbolInfoDouble(InpSymbol, SYMBOL_VOLUME_MIN);
   double maxLot = SymbolInfoDouble(InpSymbol, SYMBOL_VOLUME_MAX);
   
   lotSize = MathFloor(lotSize / lotStep) * lotStep;
   lotSize = MathMax(lotSize, minLot);
   lotSize = MathMin(lotSize, maxLot);
   
   if(InpLogDetails) {
      Print("📐 Lot Size Calculation:");
      Print("   Balance: $", DoubleToString(balance, 2));
      Print("   Risk %: ", DoubleToString(InpRiskPercent, 2));
      Print("   Risk Amount: $", DoubleToString(riskAmount, 2));
      Print("   SL Distance: ", DoubleToString(slDistance, 2));
      Print("   Calculated Lot: ", DoubleToString(lotSize, 2));
   }
   
   return lotSize;
}

//+------------------------------------------------------------------+
//| Manage open positions                                             |
//+------------------------------------------------------------------+
void ManagePositions() {
   for(int i = PositionsTotal() - 1; i >= 0; i--) {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      
      if(PositionGetInteger(POSITION_MAGIC) != magicNumber) continue;
      if(PositionGetString(POSITION_SYMBOL) != InpSymbol) continue;
      
      // Check if position should be closed
      ENUM_POSITION_TYPE posType = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
      double currentPrice = (posType == POSITION_TYPE_BUY) ? 
                           SymbolInfoDouble(InpSymbol, SYMBOL_BID) : 
                           SymbolInfoDouble(InpSymbol, SYMBOL_ASK);
      double openPrice = PositionGetDouble(POSITION_PRICE_OPEN);
      
      double profit = PositionGetDouble(POSITION_PROFIT);
      double commission = PositionGetDouble(POSITION_COMMISSION) + PositionGetDouble(POSITION_SWAP);
      double netProfit = profit + commission;
      
      // Update PnL tracking
      totalPnL += netProfit;
      dailyPnL += netProfit;
      
      // Log position status
      if(InpLogDetails && (MathAbs(netProfit) > 10)) {
         Print("📊 Position #", ticket, ":");
         Print("   Type: ", (posType == POSITION_TYPE_BUY) ? "BUY" : "SELL");
         Print("   Current PnL: $", DoubleToString(netProfit, 2));
      }
   }
}

//+------------------------------------------------------------------+
//| Update trailing stops                                             |
//+------------------------------------------------------------------+
void UpdateTrailingStops() {
   for(int i = PositionsTotal() - 1; i >= 0; i--) {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      
      if(PositionGetInteger(POSITION_MAGIC) != magicNumber) continue;
      if(PositionGetString(POSITION_SYMBOL) != InpSymbol) continue;
      
      ENUM_POSITION_TYPE posType = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
      double currentPrice = (posType == POSITION_TYPE_BUY) ? 
                           SymbolInfoDouble(InpSymbol, SYMBOL_BID) : 
                           SymbolInfoDouble(InpSymbol, SYMBOL_ASK);
      double openPrice = PositionGetDouble(POSITION_PRICE_OPEN);
      double currentSL = PositionGetDouble(POSITION_SL);
      
      int digits = (int)SymbolInfoInteger(InpSymbol, SYMBOL_DIGITS);
      double point = SymbolInfoDouble(InpSymbol, SYMBOL_POINT);
      
      // Calculate profit in points
      double profitPoints = 0;
      if(posType == POSITION_TYPE_BUY) {
         profitPoints = (currentPrice - openPrice) / point;
      } else {
         profitPoints = (openPrice - currentPrice) / point;
      }
      
      // Check if trailing should start
      if(profitPoints >= InpTrailingStart) {
         double newSL = 0;
         
         if(posType == POSITION_TYPE_BUY) {
            newSL = currentPrice - InpTrailingDistance * point;
            if(newSL > currentSL && newSL > openPrice) {
               // Modify position
               ModifyPosition(ticket, NormalizeDouble(newSL, digits), 
                            PositionGetDouble(POSITION_TP));
            }
         } else {
            newSL = currentPrice + InpTrailingDistance * point;
            if((newSL < currentSL || currentSL == 0) && newSL < openPrice) {
               // Modify position
               ModifyPosition(ticket, NormalizeDouble(newSL, digits), 
                            PositionGetDouble(POSITION_TP));
            }
         }
      }
   }
}

//+------------------------------------------------------------------+
//| Modify position SL/TP                                             |
//+------------------------------------------------------------------+
void ModifyPosition(ulong ticket, double sl, double tp) {
   MqlTradeRequest request = {};
   MqlTradeResult result = {};
   
   request.action = TRADE_ACTION_SLTP;
   request.position = ticket;
   request.sl = sl;
   request.tp = tp;
   
   if(!OrderSend(request, result)) {
      Print("❌ Failed to modify position #", ticket, ": ", GetLastError());
   } else {
      Print("✅ Trailing stop updated for #", ticket);
      Print("   New SL: ", DoubleToString(sl, 2));
   }
}

//+------------------------------------------------------------------+
//| Count open positions                                              |
//+------------------------------------------------------------------+
int CountPositions() {
   int count = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--) {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      
      if(PositionGetInteger(POSITION_MAGIC) == magicNumber && 
         PositionGetString(POSITION_SYMBOL) == InpSymbol) {
         count++;
      }
   }
   return count;
}

//+------------------------------------------------------------------+
//| Check risk limits                                                  |
//+------------------------------------------------------------------+
bool CheckRiskLimits() {
   // Check daily loss limit
   if(dailyPnL < -InpMaxDailyLoss) {
      Print("🛑 Daily loss limit reached: $", DoubleToString(dailyPnL, 2));
      tradingEnabled = false;
      
      if(InpSendNotifications) {
         SendNotification("🛑 DAILY LOSS LIMIT REACHED\n" +
                         "Daily PnL: $" + DoubleToString(dailyPnL, 2) + "\n" +
                         "Trading halted for today.");
      }
      return false;
   }
   
   // Check total loss limit
   if(totalPnL < -InpMaxTotalLoss) {
      Print("🛑 Total loss limit reached: $", DoubleToString(totalPnL, 2));
      tradingEnabled = false;
      
      if(InpSendNotifications) {
         SendNotification("🛑 TOTAL LOSS LIMIT REACHED\n" +
                         "Total PnL: $" + DoubleToString(totalPnL, 2) + "\n" +
                         "Trading halted permanently.");
      }
      return false;
   }
   
   return true;
}

//+------------------------------------------------------------------+
//| Update daily statistics                                           |
//+------------------------------------------------------------------+
void UpdateDailyStats() {
   // Check if day has changed
   MqlDateTime dt_today, dt_start;
   TimeToStruct(TimeCurrent(), dt_today);
   TimeToStruct(todayStart, dt_start);
   
   if(dt_today.day != dt_start.day) {
      Print("📅 New day detected - resetting daily stats");
      ResetDailyStats();
   }
}

//+------------------------------------------------------------------+
//| Reset daily statistics                                            |
//+------------------------------------------------------------------+
void ResetDailyStats() {
   todayStart = TimeCurrent();
   dailyPnL = 0.0;
   tradesToday = 0;
   tradingEnabled = true;
   
   Print("📊 Daily stats reset");
}

//+------------------------------------------------------------------+
//| Trade transaction handler                                         |
//+------------------------------------------------------------------+
void OnTradeTransaction(const MqlTradeTransaction &trans,
                        const MqlTradeRequest &request,
                        const MqlTradeResult &result) {
   if(trans.type == TRADE_TRANSACTION_DEAL_ADD) {
      if(trans.deal_type == DEAL_TYPE_BUY || trans.deal_type == DEAL_TYPE_SELL) {
         Print("💰 Deal executed:");
         Print("   Deal: ", trans.deal);
         Print("   Type: ", (trans.deal_type == DEAL_TYPE_BUY) ? "BUY" : "SELL");
         Print("   Volume: ", DoubleToString(trans.volume, 2));
         Print("   Price: ", DoubleToString(trans.price, 2));
         Print("   Profit: $", DoubleToString(trans.profit, 2));
      }
   }
}
//+------------------------------------------------------------------+
