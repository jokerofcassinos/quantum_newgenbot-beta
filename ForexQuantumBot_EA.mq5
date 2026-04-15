//+------------------------------------------------------------------+
//|                                      ForexQuantumBot_EA.mq5       |
//|                                    Forex Quantum Bot Bridge        |
//|                                    Created: 2026-04-12             |
//+------------------------------------------------------------------+
#property copyright "Forex Quantum Bot"
#property link      ""
#property version   "1.00"
#property description "MT5 Bridge for Forex Quantum Bot Python System"
#property description "Receives signals from Python via files and executes trades"

#include <Trade\Trade.mqh>
#include <Trade\AccountInfo.mqh>

//--- Note: Use AccountInfoDouble() instead of CAccountInfo for compatibility

//--- Input parameters
input string   InPythonSignalFile = "C:\\ForexQuantumBot\\signals\\trade_signal.json";  // Python signal file
input string   InPythonResponseFile = "C:\\ForexQuantumBot\\signals\\trade_response.json";  // Response file
input int      InMagicNumber = 123456;  // Magic number
input double   InMaxRiskPercent = 1.0;  // Max risk per trade (%)
input int      InMaxPositions = 1;  // Max concurrent positions
input bool     InEnableLogging = true;  // Enable logging

//--- Trade object
CTrade trade;

//--- Global variables
datetime last_signal_time = 0;
int total_trades = 0;
int winning_trades = 0;
int losing_trades = 0;

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
   
   //--- Log initialization
   if(InEnableLogging)
   {
      Print("ForexQuantumBot EA initialized");
      Print("Magic Number: ", InMagicNumber);
      Print("Max Risk: ", InMaxRiskPercent, "%");
      Print("Max Positions: ", InMaxPositions);
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
      Print("ForexQuantumBot EA deinitialized. Reason: ", reason);
      Print("Total trades: ", total_trades);
      Print("Winning: ", winning_trades, " | Losing: ", losing_trades);
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
      return;
   
   //--- Check if max positions reached
   if(CountOpenPositions() >= InMaxPositions)
      return;
   
   //--- Check for signal file
   if(FileIsExist(InPythonSignalFile))
   {
      ProcessSignal();
      last_signal_time = current_time;
   }
   
   //--- Manage open positions (trailing stop, breakeven)
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
         Print("Failed to open signal file: ", InPythonSignalFile);
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
   double confidence = StringToDouble(ExtractJsonValue(signal_content, "confidence"));
   
   if(direction == "" || volume <= 0)
   {
      if(InEnableLogging)
         Print("Invalid signal: direction=", direction, " volume=", volume);
      return;
   }
   
   //--- Normalize volume
   volume = NormalizeVolume(volume);
   
   //--- Execute trade
   bool result = false;
   ulong ticket = 0;
   
   if(direction == "BUY")
   {
      double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      result = trade.Buy(volume, _Symbol, ask, sl, tp, "QuantumBot BUY");
      ticket = trade.ResultOrder();
   }
   else if(direction == "SELL")
   {
      double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      result = trade.Sell(volume, _Symbol, bid, sl, tp, "QuantumBot SELL");
      ticket = trade.ResultOrder();
   }
   
   //--- Log result
   if(result)
   {
      total_trades++;
      if(InEnableLogging)
      {
         Print("✅ Trade executed: ", direction, " ", volume, " lots @ ", 
               (direction=="BUY" ? SymbolInfoDouble(_Symbol, SYMBOL_ASK) : SymbolInfoDouble(_Symbol, SYMBOL_BID)));
         Print("   SL: ", sl, " | TP: ", tp, " | Ticket: ", ticket);
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
//| Manage open positions                                              |
//+------------------------------------------------------------------+
void ManagePositions()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0)
         continue;
      
      if(PositionGetString(POSITION_SYMBOL) != _Symbol)
         continue;
      
      if(PositionGetInteger(POSITION_MAGIC) != InMagicNumber)
         continue;
      
      //--- Check for breakeven
      double open_price = PositionGetDouble(POSITION_PRICE_OPEN);
      double current_sl = PositionGetDouble(POSITION_SL);
      
      if(PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY)
      {
         double current_price = SymbolInfoDouble(_Symbol, SYMBOL_BID);
         double profit_points = (current_price - open_price) / _Point;
         
         //--- Move to breakeven at 1:1 R:R
         if(profit_points > 0 && current_sl < open_price)
         {
            double risk_points = (open_price - current_sl) / _Point;
            if(risk_points > 0 && profit_points >= risk_points)
            {
               trade.PositionModify(ticket, open_price, PositionGetDouble(POSITION_TP));
               if(InEnableLogging)
                  Print("🔒 SL moved to breakeven for ticket: ", ticket);
            }
         }
      }
      else if(PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_SELL)
      {
         double current_price = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
         double profit_points = (open_price - current_price) / _Point;
         
         if(profit_points > 0 && (current_sl == 0 || current_sl > open_price))
         {
            double risk_points = (current_sl - open_price) / _Point;
            if(risk_points > 0 && profit_points >= risk_points)
            {
               trade.PositionModify(ticket, open_price, PositionGetDouble(POSITION_TP));
               if(InEnableLogging)
                  Print("🔒 SL moved to breakeven for ticket: ", ticket);
            }
         }
      }
   }
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
      if(ticket == 0)
         continue;
      
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
      Print("Failed to create response file: ", InPythonResponseFile);
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
               Print("📊 Deal closed: PnL=$", DoubleToString(total_profit, 2), 
                     " | Commission=$", DoubleToString(commission, 2),
                     " | Total: W=", winning_trades, " L=", losing_trades);
            }
         }
      }
   }
}
//+------------------------------------------------------------------+


