//+------------------------------------------------------------------+
//| ForexQuantumBot_LIVE_V3.mq5                                      |
//| The "Actuator" - Zero-Latency Bridge for Python CoreIntelligence |
//| CEO: Qwen Code | Created: 2026-04-14                             |
//+------------------------------------------------------------------+
#property copyright "Forex Quantum Bot - Live Trading V3"
#property version   "3.00"
#property description "Event-Driven Snapshot Broadcaster & Robust Executor"
#property strict

#include <Trade\Trade.mqh>

//+------------------------------------------------------------------+
//| INPUTS                                                           |
//+------------------------------------------------------------------+
input group "=== CONNECTION ==="
input string   InpSocketHost = "127.0.0.1";
input int      InpSocketPort = 5555;
input int      InpConnectionTimeout = 3000;
input int      InpReconnectDelay = 1000;

input group "=== TRADING ==="
input string   InpSymbol = "BTCUSD";
input ENUM_TIMEFRAMES InpTimeframe = PERIOD_M5;
input int      InpMagicNumber = 20260414;
input int      InpMaxSpreadPoints = 150;

input group "=== INDICATORS ==="
input int      InpATRPeriod = 14;
input int      InpRSIPeriod = 14;
input int      InpEMA9Period = 9;
input int      InpEMA21Period = 21;
input int      InpEMA50Period = 50;
input int      InpEMA200Period = 200;
input int      InpMACDFast = 12;
input int      InpMACDSlow = 26;
input int      InpMACDSignal = 9;

//+------------------------------------------------------------------+
//| GLOBALS                                                          |
//+------------------------------------------------------------------+
int socket_handle = INVALID_HANDLE;
bool socket_connected = false;
datetime last_reconnect_attempt = 0;

int atr_handle, rsi_handle, ema9_handle, ema21_handle, ema50_handle, ema200_handle, macd_handle;
double atr_buffer[], rsi_buffer[], ema9_buffer[], ema21_buffer[], ema50_buffer[], ema200_buffer[], macd_main_buffer[], macd_signal_buffer[];

CTrade trade;
string data_buffer = "";
datetime last_snapshot_time = 0;
int consecutive_send_failures = 0;

//+------------------------------------------------------------------+
//| INIT                                                             |
//+------------------------------------------------------------------+
int OnInit()
{
   trade.SetExpertMagicNumber(InpMagicNumber);
   trade.SetDeviationInPoints(InpMaxSpreadPoints);
   trade.SetTypeFilling(ORDER_FILLING_FOK);
   trade.SetAsyncMode(false);
   
   atr_handle = iATR(_Symbol, InpTimeframe, InpATRPeriod);
   rsi_handle = iRSI(_Symbol, InpTimeframe, InpRSIPeriod, PRICE_CLOSE);
   ema9_handle = iMA(_Symbol, InpTimeframe, InpEMA9Period, 0, MODE_EMA, PRICE_CLOSE);
   ema21_handle = iMA(_Symbol, InpTimeframe, InpEMA21Period, 0, MODE_EMA, PRICE_CLOSE);
   ema50_handle = iMA(_Symbol, InpTimeframe, InpEMA50Period, 0, MODE_EMA, PRICE_CLOSE);
   ema200_handle = iMA(_Symbol, InpTimeframe, InpEMA200Period, 0, MODE_EMA, PRICE_CLOSE);
   macd_handle = iMACD(_Symbol, InpTimeframe, InpMACDFast, InpMACDSlow, InpMACDSignal, PRICE_CLOSE);
   
   if(atr_handle == INVALID_HANDLE || rsi_handle == INVALID_HANDLE || ema200_handle == INVALID_HANDLE)
   {
      Print("CRITICAL ERROR: Failed to load indicators.");
      return INIT_FAILED;
   }
   
   ArraySetAsSeries(atr_buffer, true);
   ArraySetAsSeries(rsi_buffer, true);
   ArraySetAsSeries(ema9_buffer, true);
   ArraySetAsSeries(ema21_buffer, true);
   ArraySetAsSeries(ema50_buffer, true);
   ArraySetAsSeries(ema200_buffer, true);
   ArraySetAsSeries(macd_main_buffer, true);
   ArraySetAsSeries(macd_signal_buffer, true);
   
   Print("Initializing Quantum LIVE V3 Bridge...");
   ConnectToPython();
   
   // Create a 1ms timer for ultra-fast socket reading (HFT Standard)
   EventSetMillisecondTimer(1);
   
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   EventKillTimer();
   DisconnectFromPython();
   IndicatorRelease(atr_handle);
   IndicatorRelease(rsi_handle);
   IndicatorRelease(ema9_handle);
   IndicatorRelease(ema21_handle);
   IndicatorRelease(ema50_handle);
   IndicatorRelease(ema200_handle);
   IndicatorRelease(macd_handle);
   Print("Bridge V3 Offline.");
}

//+------------------------------------------------------------------+
//| TIMER & TICK EVENTS                                              |
//+------------------------------------------------------------------+
void OnTimer()
{
   ManageConnection();
   if(socket_connected)
   {
      ReadSocketData(); // Read signals from Python instantly
   }
}

void OnTick()
{
   if(!socket_connected) return;
   
   // We only send a full snapshot max once per second to avoid TCP buffer bloat.
   // HFT logic (if needed) evaluates the snapshot in Python, while local trailing stops handle tick-level exits.
   datetime now = TimeCurrent();
   if(now - last_snapshot_time >= 1)
   {
      last_snapshot_time = now;
      SendMarketSnapshot();
   }
}

//+------------------------------------------------------------------+
//| COMMUNICATION                                                    |
//+------------------------------------------------------------------+
bool ConnectToPython()
{
   socket_handle = SocketCreate();
   if(socket_handle == INVALID_HANDLE) return false;
   
   if(!SocketConnect(socket_handle, InpSocketHost, InpSocketPort, InpConnectionTimeout))
   {
      SocketClose(socket_handle);
      socket_handle = INVALID_HANDLE;
      return false;
   }
   
   socket_connected = true;
   consecutive_send_failures = 0;
   Print("V3 Bridge Connected to Python Core!");
   
   // Send Handshake
   string handshake = StringFormat("HANDSHAKE|QuantumLiveV3|%d|%s\n", InpMagicNumber, _Symbol);
   SocketSendString(handshake);
   
   return true;
}

void DisconnectFromPython()
{
   if(socket_handle != INVALID_HANDLE) SocketClose(socket_handle);
   socket_handle = INVALID_HANDLE;
   socket_connected = false;
   data_buffer = "";
}

void ManageConnection()
{
   if(!socket_connected)
   {
      datetime now = TimeCurrent();
      if(now - last_reconnect_attempt >= InpReconnectDelay / 1000)
      {
         last_reconnect_attempt = now;
         ConnectToPython();
      }
   }
}

double GetIndVal(int handle, double &buffer[])
{
   if(CopyBuffer(handle, 0, 0, 1, buffer) > 0) return buffer[0];
   return 0.0;
}

void SendMarketSnapshot()
{
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   long vol = SymbolInfoInteger(_Symbol, SYMBOL_VOLUME);
   double spread = ask - bid;
   
   double atr = GetIndVal(atr_handle, atr_buffer);
   double rsi = GetIndVal(rsi_handle, rsi_buffer);
   double ema9 = GetIndVal(ema9_handle, ema9_buffer);
   double ema21 = GetIndVal(ema21_handle, ema21_buffer);
   double ema50 = GetIndVal(ema50_handle, ema50_buffer);
   double ema200 = GetIndVal(ema200_handle, ema200_buffer);
   
   double macd = 0.0, macd_sig = 0.0;
   if(CopyBuffer(macd_handle, 0, 0, 1, macd_main_buffer) > 0) macd = macd_main_buffer[0];
   if(CopyBuffer(macd_handle, 1, 0, 1, macd_signal_buffer) > 0) macd_sig = macd_signal_buffer[0];
   
   // TICK|SYMBOL|BID|ASK|VOL|SPREAD|ATR|RSI|EMA9|EMA21|EMA50|EMA200|MACD|MACD_SIG|TIME
   string payload = StringFormat("TICK|%s|%.5f|%.5f|%d|%.5f|%.5f|%.5f|%.5f|%.5f|%.5f|%.5f|%.5f|%.5f|%s\n",
                                 _Symbol, bid, ask, vol, spread,
                                 atr, rsi, ema9, ema21, ema50, ema200, macd, macd_sig,
                                 TimeToString(TimeCurrent()));
                                 
   if(!SocketSendString(payload))
   {
      consecutive_send_failures++;
      if(consecutive_send_failures > 5)
      {
         Print("TCP Buffer Error: Disconnecting to flush state.");
         DisconnectFromPython();
      }
   }
   else
   {
      consecutive_send_failures = 0;
   }
}

bool SocketSendString(string msg)
{
   if(!socket_connected) return false;
   uchar bytes[];
   int len = StringToCharArray(msg, bytes);
   return (SocketSend(socket_handle, bytes, len - 1) > 0);
}

//+------------------------------------------------------------------+
//| SIGNAL PROCESSING (Robust Order Execution)                       |
//+------------------------------------------------------------------+
void ReadSocketData()
{
   uint readable = SocketIsReadable(socket_handle);
   if(readable == 0) return;
   
   uchar recv_data[];
   ArrayResize(recv_data, readable);
   int bytes_read = SocketRead(socket_handle, recv_data, readable, 100); // 100ms read
   
   if(bytes_read > 0)
   {
      string message = CharArrayToString(recv_data, 0, bytes_read);
      data_buffer += message;
      
      while(StringFind(data_buffer, "\n") >= 0)
      {
         int pos = StringFind(data_buffer, "\n");
         string line = StringSubstr(data_buffer, 0, pos);
         data_buffer = StringSubstr(data_buffer, pos + 1);
         
         StringTrimLeft(line); StringTrimRight(line);
         if(StringLen(line) > 0) ProcessCommand(line);
      }
   }
   else if (bytes_read < 0)
   {
       int err = GetLastError();
       if(err != 10035) // Ignore WSAEWOULDBLOCK
       {
           Print("Socket read error: ", err);
           DisconnectFromPython();
       }
   }
}

void ProcessCommand(string cmd)
{
   Print("DEBUG: Processing command: ", cmd);
   
   string parts[];
   int count = StringSplit(cmd, '|', parts);
   if(count < 2) return;
   
   string action = parts[0];
   
   if(action == "SIGNAL")
   {
      if(count < 8) return;
      string sym = parts[1];
      string dir = parts[2];
      double vol = StringToDouble(parts[3]);
      double sl = StringToDouble(parts[4]);
      double tp = StringToDouble(parts[5]);
      int magic = (int)StringToInteger(parts[6]);
      ExecuteTrade(sym, dir, vol, sl, tp, magic);
   }
   else if(action == "BUY" || action == "SELL")
   {
      // BUY|SYMBOL|LOT|SL|TP|MAGIC|TIMESTAMP
      if(count < 7)
      {
         Print("ERROR: Malformed ", action, " received. Expected 7 parts, got ", count, ". Cmd: ", cmd);
         return;
      }
      
      string sym = parts[1];
      string dir = action; // Ação já é a direção
      double vol = StringToDouble(parts[2]);
      double sl = StringToDouble(parts[3]);
      double tp = StringToDouble(parts[4]);
      int magic = (int)StringToInteger(parts[5]);
      
      Print("DEBUG: Parsed ", action, ": ", sym, " Vol:", vol, " SL:", sl, " TP:", tp);
      
      ExecuteTrade(sym, dir, vol, sl, tp, magic);
   }
}

void ExecuteTrade(string sym, string dir, double vol, double sl, double tp, int magic)
{
   // 1. Validate parameters to prevent MQL5 OrderSend Crash
   if(vol <= 0 || sl <= 0 || tp <= 0)
   {
      Print("REJECTED: Invalid parameters for ", dir, ". Vol: ", vol, " SL: ", sl, " TP: ", tp);
      SocketSendString(StringFormat("ORDER_REJECTED|%s|Invalid Parameters\n", sym));
      return;
   }
   
   double ask = SymbolInfoDouble(sym, SYMBOL_ASK);
   double bid = SymbolInfoDouble(sym, SYMBOL_BID);
   
   // 2. Validate SL/TP polarity mathematically
   if(dir == "BUY")
   {
      if(sl >= ask || tp <= ask)
      {
         Print("REJECTED BUY: Invalid SL/TP Polarity. Ask:", ask, " SL:", sl, " TP:", tp);
         SocketSendString(StringFormat("ORDER_REJECTED|%s|Invalid Polarity\n", sym));
         return;
      }
      
      Print(">>> EXECUTING BUY: ", vol, " lots @ Market | SL: ", sl, " TP: ", tp);
      ResetLastError();
      if(trade.Buy(vol, sym, 0, sl, tp, "Quantum V3 Core"))
      {
         Print("SUCCESS: Order ", trade.ResultOrder());
         SocketSendString(StringFormat("ORDER_FILLED|%s|%s|BUY|%.2f|%.5f|%.5f|%.5f|%s\n",
                           IntegerToString(trade.ResultOrder()), sym, vol, trade.ResultPrice(), sl, tp, TimeToString(TimeCurrent())));
      }
      else
      {
         Print("FAILED BUY: MT5 Retcode ", trade.ResultRetcode(), " - ", trade.ResultRetcodeDescription(), " LastError: ", GetLastError());
         SocketSendString(StringFormat("ORDER_FAILED|%s|%s\n", sym, trade.ResultRetcodeDescription()));
      }
   }
   else if(dir == "SELL")
   {
      if(sl <= bid || tp >= bid)
      {
         Print("REJECTED SELL: Invalid SL/TP Polarity. Bid:", bid, " SL:", sl, " TP:", tp);
         SocketSendString(StringFormat("ORDER_REJECTED|%s|Invalid Polarity\n", sym));
         return;
      }
      
      Print(">>> EXECUTING SELL: ", vol, " lots @ Market | SL: ", sl, " TP: ", tp);
      ResetLastError();
      if(trade.Sell(vol, sym, 0, sl, tp, "Quantum V3 Core"))
      {
         Print("SUCCESS: Order ", trade.ResultOrder());
         SocketSendString(StringFormat("ORDER_FILLED|%s|%s|SELL|%.2f|%.5f|%.5f|%.5f|%s\n",
                           IntegerToString(trade.ResultOrder()), sym, vol, trade.ResultPrice(), sl, tp, TimeToString(TimeCurrent())));
      }
      else
      {
         Print("FAILED SELL: MT5 Retcode ", trade.ResultRetcode(), " - ", trade.ResultRetcodeDescription(), " LastError: ", GetLastError());
         SocketSendString(StringFormat("ORDER_FAILED|%s|%s\n", sym, trade.ResultRetcodeDescription()));
      }
   }
}
