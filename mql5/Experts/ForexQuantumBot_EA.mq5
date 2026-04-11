//+------------------------------------------------------------------+
//|                                       ForexQuantumBot_EA.mq5      |
//|                                    Forex Quantum Bot - MQL5 EA    |
//|                                    CEO: Qwen Code | 2026-04-12    |
//+------------------------------------------------------------------+
#property copyright "Forex Quantum Bot - Qwen Code"
#property version   "1.01"
#property description "AI Quantum Trading System - C++ Monte Carlo + Neural Networks"
#property strict

//+------------------------------------------------------------------+
//| Input Parameters                                                  |
//+------------------------------------------------------------------+
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
input int      InpMinTradeInterval = 300;      // Min Interval (5 minutes for M5)

input group "=== STOP LOSS & TAKE PROFIT ==="
input int      InpStopLossPoints = 300;        
input int      InpTakeProfitPoints = 600;      
input bool     InpUseTrailingStop = true;      
input int      InpTrailingStart = 200;         
input int      InpTrailingDistance = 150;      

input group "=== CONNECTION SETTINGS ==="
input string   InpSignalFile = "D:\\forex-project2k26\\data\\signals\\trade_signal.csv";
input string   InpHandshakeFile = "D:\\forex-project2k26\\data\\signals\\connection.txt";
input string   InpLogToFile = "D:\\forex-project2k26\\data\\signals\\ea_log.txt";
input bool     InpAutoTrade = false;           
input int      InpSignalCheckInterval = 300;   // 5 minutes (matches M5 timeframe)

input group "=== NOTIFICATIONS ==="
input bool     InpSendNotifications = true;    
input bool     InpLogDetails = true;           

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
bool connectionValidated = false;
datetime lastSignalCheck = 0;

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

//+------------------------------------------------------------------+
//| Expert initialization function                                    |
//+------------------------------------------------------------------+
int OnInit() {
   magicNumber = InpMagicNumber;
   todayStart = TimeCurrent();
   
   Print("============================================================");
   Print("🚀 FOREX QUANTUM BOT - EA v1.01");
   Print("============================================================");
   
   // Step 1: Validate connection with MT5
   Print("📡 Step 1: Validating MT5 connection...");
   if(!ValidateMT5Connection()) {
      Print("❌ MT5 connection validation FAILED!");
      return INIT_FAILED;
   }
   Print("✅ MT5 connection validated");
   
   // Step 2: Check signal file access
   Print("📡 Step 2: Checking signal file access...");
   if(!CheckSignalFileAccess()) {
      Print("⚠️ Signal file not accessible - will retry on tick");
   } else {
      Print("✅ Signal file accessible");
   }
   
   // Step 3: Write connection handshake file
   Print("📡 Step 3: Writing handshake file...");
   WriteHandshakeFile();
   
   // Step 4: Initialize tracking
   ResetDailyStats();
   
   Print("============================================================");
   Print("✅ EA INITIALIZED - ALL SYSTEMS GO");
   Print("============================================================");
   Print("   Symbol: ", InpSymbol);
   Print("   Timeframe: ", EnumToString(InpTimeframe));
   Print("   Auto Trade: ", InpAutoTrade ? "ENABLED" : "DISABLED");
   Print("   Signal Check: Every ", InpSignalCheckInterval, "s");
   Print("============================================================");
   
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Validate MT5 connection                                           |
//+------------------------------------------------------------------+
bool ValidateMT5Connection() {
   // Check if terminal is connected
   if(!TerminalInfoInteger(TERMINAL_CONNECTED)) {
      Print("❌ Terminal not connected to network");
      return false;
   }
   
   // Check if trading is allowed
   if(!TerminalInfoInteger(TERMINAL_TRADE_ALLOWED)) {
      Print("❌ Trading not allowed on this terminal");
      return false;
   }
   
   // Check if algo trading is enabled
   if(!TerminalInfoInteger(TERMINAL_TRADE_ALLOWED)) {
      Print("⚠️ Algo trading may be disabled");
   }
   
   // Verify symbol exists
   if(!SymbolSelect(InpSymbol, true)) {
      Print("❌ Symbol ", InpSymbol, " not available");
      return false;
   }
   
   // Get valid tick
   MqlTick tick;
   if(!SymbolInfoTick(InpSymbol, tick)) {
      Print("❌ Cannot get tick for ", InpSymbol);
      return false;
   }
   
   // Validate tick data
   if(tick.bid <= 0 || tick.ask <= 0) {
      Print("❌ Invalid tick data");
      return false;
   }
   
   Print("   Connection: ✅");
   Print("   Trading: ✅");
   Print("   Symbol: ✅");
   Print("   Tick Data: ✅");
   Print("   Bid: ", DoubleToString(tick.bid, 2));
   Print("   Ask: ", DoubleToString(tick.ask, 2));
   
   return true;
}

//+------------------------------------------------------------------+
//| Check signal file access                                          |
//+------------------------------------------------------------------+
bool CheckSignalFileAccess() {
   int handle = FileOpen(InpSignalFile, FILE_READ|FILE_CSV|FILE_ANSI, ',');
   if(handle == INVALID_HANDLE) {
      return false;
   }
   FileClose(handle);
   return true;
}

//+------------------------------------------------------------------+
//| Write handshake file for Python                                   |
//+------------------------------------------------------------------+
void WriteHandshakeFile() {
   int handle = FileOpen(InpHandshakeFile, FILE_WRITE|FILE_TXT|FILE_ANSI);
   if(handle != INVALID_HANDLE) {
      FileWriteString(handle, "EA_CONNECTED=true\n");
      FileWriteString(handle, "EA_MAGIC=" + IntegerToString(magicNumber) + "\n");
      FileWriteString(handle, "EA_SYMBOL=" + InpSymbol + "\n");
      FileWriteString(handle, "EA_TIMEFRAME=" + EnumToString(InpTimeframe) + "\n");
      FileWriteString(handle, "EA_AUTOTRADE=" + (InpAutoTrade ? "true" : "false") + "\n");
      FileWriteString(handle, "EA_START_TIME=" + TimeToString(TimeCurrent()) + "\n");
      FileWriteString(handle, "STATUS=READY\n");
      FileClose(handle);
      
      Print("✅ Handshake file written: ", InpHandshakeFile);
   } else {
      Print("⚠️ Could not write handshake file");
   }
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                  |
//+------------------------------------------------------------------+
void OnDeinit(const int reason) {
   Print("============================================================");
   Print("🛑 EA SHUTTING DOWN");
   Print("   Reason: ", reason);
   Print("   Total PnL: $", DoubleToString(totalPnL, 2));
   Print("   Daily PnL: $", DoubleToString(dailyPnL, 2));
   Print("   Trades Today: ", tradesToday);
   Print("============================================================");
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
   
   // Check for new signals (at interval)
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
   // Read signal file
   int handle = FileOpen(InpSignalFile, FILE_READ|FILE_CSV|FILE_ANSI, ',');
   if(handle == INVALID_HANDLE) {
      if(InpLogDetails) {
         Print("⏳ No signal file found - waiting...");
      }
      return;
   }
   
   // Parse CSV
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
   
   // Validate signal
   if(currentSignal.direction != "BUY" && currentSignal.direction != "SELL") {
      return;
   }
   
   if(currentSignal.confidence < 0.6) {
      Print("📊 Signal confidence too low: ", DoubleToString(currentSignal.confidence, 2));
      return;
   }
   
   // Check signal age (max 10 minutes for M5)
   if(TimeCurrent() - currentSignal.timestamp > 600) {
      Print("⏰ Signal too old (", (TimeCurrent() - currentSignal.timestamp), "s) - ignoring");
      return;
   }
   
   // Check trade interval
   if(TimeCurrent() - lastTradeTime < InpMinTradeInterval) {
      int remaining = InpMinTradeInterval - (TimeCurrent() - lastTradeTime);
      Print("⏰ Trade cooldown - ", remaining, "s remaining");
      return;
   }
   
   // Check max trades per day
   if(tradesToday >= InpMaxTradesPerDay) {
      Print("⚠️ Max trades per day reached: ", tradesToday);
      return;
   }
   
   // Log signal received
   Print("📥 SIGNAL RECEIVED:");
   Print("   Direction: ", currentSignal.direction);
   Print("   Confidence: ", DoubleToString(currentSignal.confidence, 2));
   Print("   Entry: ", DoubleToString(currentSignal.entry_price, 2));
   Print("   SL: ", DoubleToString(currentSignal.stop_loss, 2));
   Print("   TP: ", DoubleToString(currentSignal.take_profit, 2));
   Print("   Profile: ", currentSignal.profile);
   Print("   Auto Trade: ", InpAutoTrade ? "YES" : "NO (Manual Mode)");
   
   // Execute if auto trading enabled
   if(InpAutoTrade) {
      Print("🚀 AUTO TRADE ENABLED - EXECUTING...");
      ExecuteTrade(currentSignal);
   } else {
      Print("⏸️ Manual mode - signal logged but not executed");
      
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
      Print("⚠️ Max positions reached: ", positionCount);
      return;
   }
   
   // Calculate lot size
   double lotSize = CalculateLotSize(signal);
   if(lotSize <= 0) {
      Print("❌ Invalid lot size: ", DoubleToString(lotSize, 2));
      return;
   }
   
   // Get current market price
   MqlTick tick;
   if(!SymbolInfoTick(InpSymbol, tick)) {
      Print("❌ Cannot get current tick");
      return;
   }
   
   double entryPrice = (signal.direction == "BUY") ? tick.ask : tick.bid;
   int digits = (int)SymbolInfoInteger(InpSymbol, SYMBOL_DIGITS);
   
   // Prepare order
   MqlTradeRequest request = {};
   MqlTradeResult result = {};
   
   request.action = TRADE_ACTION_DEAL;
   request.symbol = InpSymbol;
   request.volume = lotSize;
   request.type = (signal.direction == "BUY") ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   request.price = NormalizeDouble(entryPrice, digits);
   request.sl = NormalizeDouble(signal.stop_loss, digits);
   request.tp = NormalizeDouble(signal.take_profit, digits);
   request.deviation = 100;
   request.magic = magicNumber;
   request.comment = "QuantumBot-" + signal.profile;
   
   Print("📤 SENDING ORDER:");
   Print("   Type: ", (signal.direction == "BUY") ? "BUY" : "SELL");
   Print("   Volume: ", DoubleToString(lotSize, 2));
   Print("   Price: ", DoubleToString(request.price, digits));
   Print("   SL: ", DoubleToString(request.sl, digits));
   Print("   TP: ", DoubleToString(request.tp, digits));
   
   // Send order
   if(OrderSend(request, result)) {
      Print("📥 ORDER RESPONSE:");
      Print("   Retcode: ", result.retcode);
      Print("   Order: ", result.order);
      Print("   Deal: ", result.deal);
      Print("   Comment: ", result.comment);
      
      if(result.retcode == TRADE_RETCODE_DONE) {
         lastTradeTime = TimeCurrent();
         tradesToday++;
         
         Print("✅ TRADE EXECUTED SUCCESSFULLY!");
         Print("   Ticket: ", result.order);
         Print("   Direction: ", signal.direction);
         Print("   Volume: ", DoubleToString(lotSize, 2));
         Print("   Entry: ", DoubleToString(request.price, digits));
         Print("   SL: ", DoubleToString(request.sl, digits));
         Print("   TP: ", DoubleToString(request.tp, digits));
         
         if(InpSendNotifications) {
            SendNotification("✅ Trade Executed\n" +
                            "Ticket: " + IntegerToString(result.order) + "\n" +
                            "Direction: " + signal.direction + "\n" +
                            "Volume: " + DoubleToString(lotSize, 2) + "\n" +
                            "Entry: $" + DoubleToString(request.price, digits));
         }
      } else {
         Print("❌ Order failed with code: ", result.retcode);
         Print("   Comment: ", result.comment);
      }
   } else {
      int error = GetLastError();
      Print("❌ OrderSend failed! Error: ", error);
      
      if(InpSendNotifications) {
         SendNotification("❌ Trade Failed\nError: " + IntegerToString(error));
      }
   }
}

//+------------------------------------------------------------------+
//| Calculate lot size                                                |
//+------------------------------------------------------------------+
double CalculateLotSize(TradeSignal &signal) {
   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   double riskAmount = balance * InpRiskPercent / 100.0;
   
   double slDistance = MathAbs(signal.entry_price - signal.stop_loss);
   if(slDistance == 0) {
      slDistance = InpStopLossPoints * SymbolInfoDouble(InpSymbol, SYMBOL_POINT);
   }
   
   double tickValue = SymbolInfoDouble(InpSymbol, SYMBOL_TRADE_TICK_VALUE);
   double tickSize = SymbolInfoDouble(InpSymbol, SYMBOL_TRADE_TICK_SIZE);
   
   double lotSize = riskAmount / (slDistance / tickSize * tickValue);
   
   double lotStep = SymbolInfoDouble(InpSymbol, SYMBOL_VOLUME_STEP);
   double minLot = SymbolInfoDouble(InpSymbol, SYMBOL_VOLUME_MIN);
   double maxLot = SymbolInfoDouble(InpSymbol, SYMBOL_VOLUME_MAX);
   
   lotSize = MathFloor(lotSize / lotStep) * lotStep;
   lotSize = MathMax(lotSize, minLot);
   lotSize = MathMin(lotSize, maxLot);
   
   if(InpLogDetails) {
      Print("📐 Lot Size: ");
      Print("   Balance: $", DoubleToString(balance, 2));
      Print("   Risk: $", DoubleToString(riskAmount, 2));
      Print("   Lot: ", DoubleToString(lotSize, 2));
   }
   
   return lotSize;
}

//+------------------------------------------------------------------+
//| Manage positions                                                  |
//+------------------------------------------------------------------+
void ManagePositions() {
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
      
      double profit = PositionGetDouble(POSITION_PROFIT);
      double swap = PositionGetDouble(POSITION_SWAP);
      double netProfit = profit + swap;
      
      totalPnL += netProfit;
      dailyPnL += netProfit;
      
      if(InpLogDetails && (MathAbs(netProfit) > 10)) {
         Print("📊 Position #", ticket, " PnL: $", DoubleToString(netProfit, 2));
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
      
      double profitPoints = 0;
      if(posType == POSITION_TYPE_BUY) {
         profitPoints = (currentPrice - openPrice) / point;
      } else {
         profitPoints = (openPrice - currentPrice) / point;
      }
      
      if(profitPoints >= InpTrailingStart) {
         double newSL = 0;
         
         if(posType == POSITION_TYPE_BUY) {
            newSL = currentPrice - InpTrailingDistance * point;
            if(newSL > currentSL && newSL > openPrice) {
               ModifyPosition(ticket, NormalizeDouble(newSL, digits), 
                            PositionGetDouble(POSITION_TP));
            }
         } else {
            newSL = currentPrice + InpTrailingDistance * point;
            if((newSL < currentSL || currentSL == 0) && newSL < openPrice) {
               ModifyPosition(ticket, NormalizeDouble(newSL, digits), 
                            PositionGetDouble(POSITION_TP));
            }
         }
      }
   }
}

//+------------------------------------------------------------------+
//| Modify position                                                   |
//+------------------------------------------------------------------+
void ModifyPosition(ulong ticket, double sl, double tp) {
   MqlTradeRequest request = {};
   MqlTradeResult result = {};
   
   request.action = TRADE_ACTION_SLTP;
   request.position = ticket;
   request.sl = sl;
   request.tp = tp;
   
   if(!OrderSend(request, result)) {
      Print("❌ Failed to modify position #", ticket);
   }
}

//+------------------------------------------------------------------+
//| Count positions                                                   |
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
//| Check risk limits                                                 |
//+------------------------------------------------------------------+
bool CheckRiskLimits() {
   if(dailyPnL < -InpMaxDailyLoss) {
      Print("🛑 Daily loss limit reached: $", DoubleToString(dailyPnL, 2));
      tradingEnabled = false;
      return false;
   }
   
   if(totalPnL < -InpMaxTotalLoss) {
      Print("🛑 Total loss limit reached: $", DoubleToString(totalPnL, 2));
      tradingEnabled = false;
      return false;
   }
   
   return true;
}

//+------------------------------------------------------------------+
//| Update daily stats                                                |
//+------------------------------------------------------------------+
void UpdateDailyStats() {
   MqlDateTime dt_today, dt_start;
   TimeToStruct(TimeCurrent(), dt_today);
   TimeToStruct(todayStart, dt_start);
   
   if(dt_today.day != dt_start.day) {
      Print("📅 New day - resetting stats");
      ResetDailyStats();
   }
}

//+------------------------------------------------------------------+
//| Reset daily stats                                                 |
//+------------------------------------------------------------------+
void ResetDailyStats() {
   todayStart = TimeCurrent();
   dailyPnL = 0.0;
   tradesToday = 0;
   tradingEnabled = true;
}
//+------------------------------------------------------------------+
