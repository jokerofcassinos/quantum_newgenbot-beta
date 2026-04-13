//+------------------------------------------------------------------+
//|                                  ForexQuantumBot_EA_V2.mq5        |
//|                        Complete Production EA for Live Trading    |
//|                        Created: 2026-04-12 | CEO: Forex Quantum   |
//+------------------------------------------------------------------+
#property copyright "Forex Quantum Bot - Production EA"
#property link      ""
#property version   "2.00"
#property description "Complete MT5 Expert Advisor for Python Live Trading Bridge"
#property description "Features: Smart TP, Trailing Stops, Breakeven, Real-time Logging"

#include <Trade\Trade.mqh>
#include <Trade\AccountInfo.mqh>

//--- Input parameters
input string   InPythonSignalFile   = "C:\\ForexQuantumBot\\signals\\trade_signal.json";   // Python signal file
input string   InPythonResponseFile = "C:\\ForexQuantumBot\\signals\\trade_response.json"; // Response file
input int      InMagicNumber        = 123456;                                              // Magic number
input double   InMaxRiskPercent     = 1.0;                                                 // Max risk per trade (%)
input int      InMaxPositions       = 1;                                                   // Max concurrent positions
input bool     InEnableLogging      = true;                                                // Enable logging
input double   InTrailingATR        = 1.5;                                                 // Trailing stop ATR multiplier
input bool     InUseSmartTP         = true;                                                // Use Smart TP (multi-target)
input double   InTP1Ratio           = 0.0;                                                 // TP1 portion (0.0 = disabled)
input double   InTP2Ratio           = 0.50;                                                // TP2 portion
input double   InTP3Ratio           = 0.0;                                                 // TP3 portion
input double   InTrailRatio         = 0.50;                                                // Trailing portion

//--- Trade object
CTrade trade;

//--- Global variables
datetime last_signal_time = 0;
int total_trades = 0;
int winning_trades = 0;
int losing_trades = 0;
double session_start_balance = 0.0;

//--- Position state tracking
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

//+------------------------------------------------------------------+
//| Expert initialization function                                     |
//+------------------------------------------------------------------+
int OnInit()
{
   //--- Setup trade object
   trade.SetExpertMagicNumber(InMagicNumber);
   trade.SetDeviationInPoints(50);
   trade.SetTypeFilling(ORDER_FILLING_IOC);
   trade.SetAsyncMode(false);
   
   //--- Initialize session balance
   session_start_balance = AccountInfoDouble(ACCOUNT_BALANCE);
   
   //--- Log initialization
   if(InEnableLogging)
   {
      Print("============================================================");
      Print("FOREX QUANTUM BOT EA V2.0 - INITIALIZED");
      Print("============================================================");
      Print("Magic Number: ", InMagicNumber);
      Print("Max Risk: ", InMaxRiskPercent, "%");
      Print("Max Positions: ", InMaxPositions);
      Print("Smart TP: ", InUseSmartTP ? "ON" : "OFF");
      Print("Trailing ATR: ", InTrailingATR);
      Print("Session Start Balance: $", DoubleToString(session_start_balance, 2));
   }
   
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                   |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   if(InEnableLogging)
   {
      Print("============================================================");
      Print("FOREX QUANTUM BOT EA - DEINITIALIZED");
      Print("Reason: ", reason);
      Print("Total Trades: ", total_trades);
      Print("Winning: ", winning_trades, " | Losing: ", losing_trades);
      if(total_trades > 0)
         Print("Win Rate: ", DoubleToString((double)winning_trades / total_trades * 100, 1), "%");
      Print("============================================================");
   }
}

//+------------------------------------------------------------------+
//| Expert tick function                                               |
//+------------------------------------------------------------------+
void OnTick()
{
   //--- Check for new signals every 5 seconds
   datetime current_time = TimeCurrent();
   if(current_time - last_signal_time < 5)
   {
      // Still manage open positions even if no new signal
      ManagePositions();
      return;
   }
   
   //--- Check if max positions reached
   if(CountOpenPositions() >= InMaxPositions && !has_position)
      return;
   
   //--- Check for signal file from Python
   if(FileIsExist(InPythonSignalFile))
   {
      ProcessSignal();
      last_signal_time = current_time;
   }
   
   //--- Manage open positions (trailing stop, breakeven, Smart TP)
   ManagePositions();
}

//+------------------------------------------------------------------+
//| Process trading signal from Python                                 |
//+------------------------------------------------------------------+
void ProcessSignal()
{
   //--- Read signal file
   int handle = FileOpen(InPythonSignalFile, FILE_READ|FILE_TXT);
   if(handle == INVALID_HANDLE)
   {
      if(InEnableLogging)
         Print("⚠️ Failed to open signal file: ", InPythonSignalFile);
      return;
   }
   
   string signal_content = "";
   while(!FileIsEnding(handle))
   {
      signal_content += FileReadString(handle);
   }
   FileClose(handle);
   
   //--- Delete signal file after reading
   FileDelete(InPythonSignalFile);
   
   //--- Parse signal (simple JSON parsing)
   string direction = ExtractJsonValue(signal_content, "direction");
   double volume = StringToDouble(ExtractJsonValue(signal_content, "volume"));
   double sl = StringToDouble(ExtractJsonValue(signal_content, "stop_loss"));
   double tp = StringToDouble(ExtractJsonValue(signal_content, "take_profit"));
   double entry = StringToDouble(ExtractJsonValue(signal_content, "entry_price"));
   double confidence = StringToDouble(ExtractJsonValue(signal_content, "confidence"));
   int buy_votes = (int)StringToInteger(ExtractJsonValue(signal_content, "buy_votes"));
   int sell_votes = (int)StringToInteger(ExtractJsonValue(signal_content, "sell_votes"));
   int neutral_votes = (int)StringToInteger(ExtractJsonValue(signal_content, "neutral_votes"));
   
   if(direction == "" || volume <= 0)
   {
      if(InEnableLogging)
         Print("⚠️ Invalid signal: direction=", direction, " volume=", volume);
      return;
   }
   
   //--- Normalize volume
   volume = NormalizeVolume(volume);
   
   //--- Execute trade
   bool result = false;
   ulong ticket = 0;
   double price = 0;
   
   if(direction == "BUY")
   {
      price = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      result = trade.Buy(volume, _Symbol, price, sl, tp, "QuantumBot BUY");
      ticket = trade.ResultOrder();
   }
   else if(direction == "SELL")
   {
      price = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      result = trade.Sell(volume, _Symbol, price, sl, tp, "QuantumBot SELL");
      ticket = trade.ResultOrder();
   }
   
   //--- Log result
   if(result)
   {
      total_trades++;
      
      //--- Track position state
      has_position = true;
      current_position.ticket = ticket;
      current_position.direction = direction;
      current_position.entry_price = price;
      current_position.sl = sl;
      current_position.tp = tp;
      current_position.volume = volume;
      current_position.tp2_price = CalculateTP2Price(price, sl, direction);
      current_position.tp2_closed_volume = 0;
      current_position.tp2_hit = false;
      current_position.breakeven_active = false;
      current_position.peak_price = price;
      current_position.open_time = TimeCurrent();
      
      if(InEnableLogging)
      {
         Print("✅ ORDER EXECUTED");
         Print("   🎫 Ticket: ", ticket);
         Print("   📊 Direction: ", direction);
         Print("   📦 Volume: ", DoubleToString(volume, 2), " lots");
         Print("   💰 Entry: ", DoubleToString(price, 2));
         Print("   🛑 SL: ", DoubleToString(sl, 2));
         Print("   🎯 TP: ", DoubleToString(tp, 2));
         if(InUseSmartTP)
            Print("   🎯 TP2: ", DoubleToString(current_position.tp2_price, 2), " (", DoubleToString(InTP2Ratio*100, 0), "%)");
         Print("   🗳️ Votes: BUY=", buy_votes, " | SELL=", sell_votes, " | NEUTRAL=", neutral_votes);
         Print("   🎯 Confidence: ", DoubleToString(confidence, 2));
      }
      
      //--- Write response
      WriteResponse(ticket, true, "Order executed");
   }
   else
   {
      if(InEnableLogging)
      {
         Print("❌ Trade failed: ", direction, " | Error: ", GetLastError());
      }
      
      //--- Write error response
      WriteResponse(0, false, "Order failed: " + IntegerToString(GetLastError()));
   }
}

//+------------------------------------------------------------------+
//| Manage open positions (Smart TP, Trailing, Breakeven)              |
//+------------------------------------------------------------------+
void ManagePositions()
{
   if(!has_position)
      return;
   
   //--- Get current price
   double current_price = (current_position.direction == "BUY") ? 
                          SymbolInfoDouble(_Symbol, SYMBOL_BID) : 
                          SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   
   //--- Update peak price
   if(current_position.direction == "BUY" && current_price > current_position.peak_price)
      current_position.peak_price = current_price;
   else if(current_position.direction == "SELL" && current_price < current_position.peak_price)
      current_position.peak_price = current_price;
   
   //--- Calculate unrealized PnL
   double pnl = 0;
   if(current_position.direction == "BUY")
      pnl = (current_price - current_position.entry_price) * current_position.volume * SymbolInfoDouble(_Symbol, SYMBOL_TRADE_CONTRACT_SIZE);
   else
      pnl = (current_position.entry_price - current_price) * current_position.volume * SymbolInfoDouble(_Symbol, SYMBOL_TRADE_CONTRACT_SIZE);
   
   //--- Smart TP: Check TP2 hit
   if(InUseSmartTP && !current_position.tp2_hit)
   {
      bool tp2_hit = false;
      if(current_position.direction == "BUY" && current_price >= current_position.tp2_price)
         tp2_hit = true;
      else if(current_position.direction == "SELL" && current_price <= current_position.tp2_price)
         tp2_hit = true;
      
      if(tp2_hit)
      {
         //--- Close TP2 portion
         double close_volume = NormalizeDouble(current_position.volume * InTP2Ratio, 2);
         if(close_volume > 0)
         {
            bool closed = ClosePartialPosition(current_position.ticket, close_volume, "Smart TP2");
            if(closed)
            {
               current_position.tp2_hit = true;
               current_position.tp2_closed_volume = close_volume;
               current_position.volume -= close_volume;
               
               if(InEnableLogging)
                  Print("🎯 TP2 HIT! Closed ", DoubleToString(close_volume, 2), " lots at ", DoubleToString(current_price, 2));
            }
         }
      }
   }
   
   //--- Move to breakeven when price reaches 1R
   if(!current_position.breakeven_active)
   {
      double risk_distance = MathAbs(current_position.entry_price - current_position.sl);
      double profit_distance = MathAbs(current_price - current_position.entry_price);
      
      if(profit_distance >= risk_distance && risk_distance > 0)
      {
         bool moved = MoveSLToBreakeven(current_position.ticket, current_position.entry_price);
         if(moved)
         {
            current_position.breakeven_active = true;
            current_position.sl = current_position.entry_price;
            
            if(InEnableLogging)
               Print("🔒 SL moved to BREAKEVEN at ", DoubleToString(current_position.entry_price, 2));
         }
      }
   }
   
   //--- Trailing stop update (for remaining portion after TP2)
   if(current_position.tp2_hit || !InUseSmartTP)
   {
      double atr = GetATR(14);
      if(atr > 0)
      {
         double trail_distance = atr * InTrailingATR;
         double new_sl = 0;
         
         if(current_position.direction == "BUY")
         {
            new_sl = current_price - trail_distance;
            if(new_sl > current_position.sl + _Point * 10)  // Min move: 10 points
            {
               bool modified = ModifyPositionSL(current_position.ticket, new_sl);
               if(modified)
               {
                  current_position.sl = new_sl;
                  if(InEnableLogging)
                     Print("📈 Trailing SL updated to ", DoubleToString(new_sl, 2));
               }
            }
         }
         else if(current_position.direction == "SELL")
         {
            new_sl = current_price + trail_distance;
            if(new_sl < current_position.sl - _Point * 10)  // Min move: 10 points
            {
               bool modified = ModifyPositionSL(current_position.ticket, new_sl);
               if(modified)
               {
                  current_position.sl = new_sl;
                  if(InEnableLogging)
                     Print("📉 Trailing SL updated to ", DoubleToString(new_sl, 2));
               }
            }
         }
      }
   }
   
   //--- Log position status periodically
   static datetime last_log_time = 0;
   if(TimeCurrent() - last_log_time >= 60)  // Every minute
   {
      last_log_time = TimeCurrent();
      
      if(InEnableLogging)
      {
         Print("📦 POSITION | ", current_position.direction, " | Ticket: ", current_position.ticket, 
               " | PnL: $", DoubleToString(pnl, 2), " | Peak: $", DoubleToString(
               (current_position.direction == "BUY") ? 
               (current_position.peak_price - current_position.entry_price) * current_position.volume * SymbolInfoDouble(_Symbol, SYMBOL_TRADE_CONTRACT_SIZE) :
               (current_position.entry_price - current_position.peak_price) * current_position.volume * SymbolInfoDouble(_Symbol, SYMBOL_TRADE_CONTRACT_SIZE), 2),
               " | SL: ", DoubleToString(current_position.sl, 2),
               " | TP2: ", current_position.tp2_hit ? "HIT" : DoubleToString(current_position.tp2_price, 2),
               " | Duration: ", (TimeCurrent() - current_position.open_time) / 60, " min");
      }
   }
   
   //--- Check if position is still open in MT5
   if(!PositionSelectByTicket(current_position.ticket))
   {
      //--- Position was closed (by SL, TP, or manual)
      double closed_pnl = CalculateClosedPnL();
      
      if(closed_pnl > 0)
         winning_trades++;
      else
         losing_trades++;
      
      if(InEnableLogging)
      {
         Print("📦 POSITION CLOSED | Ticket: ", current_position.ticket, 
               " | PnL: $", DoubleToString(closed_pnl, 2),
               " | Duration: ", (TimeCurrent() - current_position.open_time) / 60, " min");
      }
      
      has_position = false;
      ZeroMemory(current_position);
   }
}

//+------------------------------------------------------------------+
//| Calculate TP2 price based on R:R                                   |
//+------------------------------------------------------------------+
double CalculateTP2Price(double entry, double sl, string direction)
{
   double risk_distance = MathAbs(entry - sl);
   
   if(direction == "BUY")
      return entry + risk_distance * 2.0;  // 1:2 R:R
   else
      return entry - risk_distance * 2.0;
}

//+------------------------------------------------------------------+
//| Close partial position                                             |
//+------------------------------------------------------------------+
bool ClosePartialPosition(ulong ticket, double close_volume, string comment)
{
   if(!PositionSelectByTicket(ticket))
      return false;
   
   string symbol = PositionGetString(POSITION_SYMBOL);
   long type = PositionGetInteger(POSITION_TYPE);
   double price = (type == POSITION_TYPE_BUY) ? SymbolInfoDouble(symbol, SYMBOL_BID) : SymbolInfoDouble(symbol, SYMBOL_ASK);
   
   trade.SetExpertMagicNumber(InMagicNumber);
   
   if(type == POSITION_TYPE_BUY)
      return trade.Sell(close_volume, symbol, price, 0, 0, comment);
   else
      return trade.Buy(close_volume, symbol, price, 0, 0, comment);
}

//+------------------------------------------------------------------+
//| Move SL to breakeven                                               |
//+------------------------------------------------------------------+
bool MoveSLToBreakeven(ulong ticket, double breakeven_price)
{
   return ModifyPositionSL(ticket, breakeven_price);
}

//+------------------------------------------------------------------+
//| Modify position SL                                                 |
//+------------------------------------------------------------------+
bool ModifyPositionSL(ulong ticket, double new_sl)
{
   if(!PositionSelectByTicket(ticket))
      return false;
   
   string symbol = PositionGetString(POSITION_SYMBOL);
   double current_tp = PositionGetDouble(POSITION_TP);
   
   trade.SetExpertMagicNumber(InMagicNumber);
   return trade.PositionModify(ticket, new_sl, current_tp);
}

//+------------------------------------------------------------------+
//| Calculate closed position PnL                                      |
//+------------------------------------------------------------------+
double CalculateClosedPnL()
{
   HistorySelect(0, TimeCurrent());
   
   for(int i = HistoryDealsTotal() - 1; i >= 0; i--)
   {
      ulong deal_ticket = HistoryDealGetTicket(i);
      if(deal_ticket == 0) continue;
      
      if(HistoryDealGetInteger(deal_ticket, DEAL_ORDER) == current_position.ticket ||
         HistoryDealGetString(deal_ticket, DEAL_COMMENT) == "QuantumBot BUY" ||
         HistoryDealGetString(deal_ticket, DEAL_COMMENT) == "QuantumBot SELL")
      {
         double profit = HistoryDealGetDouble(deal_ticket, DEAL_PROFIT);
         double commission = HistoryDealGetDouble(deal_ticket, DEAL_COMMISSION);
         double swap = HistoryDealGetDouble(deal_ticket, DEAL_SWAP);
         return profit + commission + swap;
      }
   }
   
   return 0;
}

//+------------------------------------------------------------------+
//| Get ATR value                                                      |
//+------------------------------------------------------------------+
double GetATR(int period)
{
   double atr[];
   ArraySetAsSeries(atr, true);
   
   int handle = iATR(_Symbol, PERIOD_CURRENT, period);
   if(handle == INVALID_HANDLE)
      return 0;
   
   if(CopyBuffer(handle, 0, 0, 1, atr) <= 0)
      return 0;
   
   return atr[0];
}

//+------------------------------------------------------------------+
//| Count open positions for this EA                                   |
//+------------------------------------------------------------------+
int CountOpenPositions()
{
   int count = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      
      if(PositionGetString(POSITION_SYMBOL) == _Symbol && 
         PositionGetInteger(POSITION_MAGIC) == InMagicNumber)
      {
         count++;
      }
   }
   return count;
}

//+------------------------------------------------------------------+
//| Normalize volume to lot step                                       |
//+------------------------------------------------------------------+
double NormalizeVolume(double volume)
{
   double lot_step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   double min_lot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double max_lot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   
   volume = MathFloor(volume / lot_step) * lot_step;
   volume = MathMax(min_lot, MathMin(max_lot, volume));
   
   return NormalizeDouble(volume, 2);
}

//+------------------------------------------------------------------+
//| Extract value from simple JSON                                     |
//+------------------------------------------------------------------+
string ExtractJsonValue(string json, string key)
{
   string search_key = "\"" + key + "\":";
   int key_pos = StringFind(json, search_key, 0);
   
   if(key_pos == -1)
      return "";
   
   int value_start = key_pos + StringLen(search_key);
   
   //--- Skip whitespace
   while(value_start < StringLen(json) && 
         (StringGetCharacter(json, value_start) == ' ' || 
          StringGetCharacter(json, value_start) == '\t' ||
          StringGetCharacter(json, value_start) == '\n'))
   {
      value_start++;
   }
   
   //--- Check if value is quoted string
   if(StringGetCharacter(json, value_start) == '"')
   {
      value_start++;
      int value_end = StringFind(json, "\"", value_start);
      if(value_end == -1)
         return "";
      return StringSubstr(json, value_start, value_end - value_start);
   }
   
   //--- Numeric value
   int value_end = value_start;
   while(value_end < StringLen(json))
   {
      ushort ch = StringGetCharacter(json, value_end);
      if(ch == ',' || ch == '}' || ch == ' ' || ch == '\n')
         break;
      value_end++;
   }
   
   return StringSubstr(json, value_start, value_end - value_start);
}

//+------------------------------------------------------------------+
//| Write response to file                                             |
//+------------------------------------------------------------------+
void WriteResponse(ulong ticket, bool success, string message)
{
   int handle = FileOpen(InPythonResponseFile, FILE_WRITE|FILE_TXT);
   if(handle == INVALID_HANDLE)
   {
      Print("❌ Failed to create response file: ", InPythonResponseFile);
      return;
   }
   
   string response = "{\n";
   response += "  \"ticket\": " + IntegerToString(ticket) + ",\n";
   response += "  \"success\": " + (success ? "true" : "false") + ",\n";
   response += "  \"message\": \"" + message + "\",\n";
   response += "  \"timestamp\": \"" + TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS) + "\"\n";
   response += "}\n";
   
   FileWriteString(handle, response);
   FileClose(handle);
}

//+------------------------------------------------------------------+
//| OnTradeTransaction handler for tracking                            |
//+------------------------------------------------------------------+
void OnTradeTransaction(const MqlTradeTransaction& trans,
                        const MqlTradeRequest& request,
                        const MqlTradeResult& result)
{
   if(trans.type == TRADE_TRANSACTION_DEAL_ADD)
   {
      if(trans.deal_type == DEAL_TYPE_SELL || trans.deal_type == DEAL_TYPE_BUY)
      {
         //--- Position closed - get profit from deal history
         HistorySelect(0, TimeCurrent());
         ulong deal_ticket = trans.deal;
         
         if(HistoryDealSelect(deal_ticket))
         {
            double profit = HistoryDealGetDouble(deal_ticket, DEAL_PROFIT);
            double commission = HistoryDealGetDouble(deal_ticket, DEAL_COMMISSION);
            double swap = HistoryDealGetDouble(deal_ticket, DEAL_SWAP);
            double total_profit = profit + commission + swap;
            
            if(total_profit > 0)
               winning_trades++;
            else
               losing_trades++;
            
            if(InEnableLogging)
            {
               Print("📊 DEAL CLOSED | PnL: $", DoubleToString(total_profit, 2), 
                     " | Commission: $", DoubleToString(commission, 2),
                     " | Total: W=", winning_trades, " L=", losing_trades);
            }
         }
      }
   }
}
//+------------------------------------------------------------------+
