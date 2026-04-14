//+------------------------------------------------------------------+
//| ForexQuantumBot_EA_V3.mq5                                        |
//| TCP Socket HFT Bridge + Smart TP/Trailing + Risk Limits          |
//|                                                                  |
//| Herança:                                                         |
//| - TCP Socket do legacy DubaiMatrixASI_HFT_Bridge.mq5            |
//| - Smart TP/Trailing do ForexQuantumBot_EA_V2.mq5                |
//| - Risk Limits do ForexQuantumBot_EA.mq5 (mql5/Experts)          |
//| - Anti-Slippage do legacy                                        |
//+------------------------------------------------------------------+
#property copyright "Forex Quantum Bot - Live Trading V3"
#property version   "3.00"
#property description "TCP Socket HFT Bridge + Smart Management + Risk Controls"
#property strict

//+------------------------------------------------------------------+
//| INCLUDES                                                         |
//+------------------------------------------------------------------+
#include <Trade\Trade.mqh>

//+------------------------------------------------------------------+
//| INPUT GROUPS                                                     |
//+------------------------------------------------------------------+
input group "=== CONNECTION ==="
input string   InpSocketHost = "127.0.0.1";              // Python server host
input int      InpSocketPort = 5555;                     // Python server port
input int      InpConnectionTimeout = 3000;              // Connection timeout (ms)
input int      InpReconnectAttempts = 10;                // Max reconnect attempts
input int      InpReconnectDelay = 1000;                 // Reconnect delay (ms)

input group "=== TRADING ==="
input string   InpSymbol = "BTCUSD";                     // Trading symbol
input ENUM_TIMEFRAMES InpTimeframe = PERIOD_M5;          // Chart timeframe
input double   InpLotSize = 0.01;                        // Fixed lot size
input int      InpMagicNumber = 20260413;                // Magic number
input int      InpMaxPositions = 1;                      // Max simultaneous positions
input bool     InpAutoTrade = true;                      // Enable auto trading

input group "=== RISK MANAGEMENT ==="
input double   InpMaxDailyLoss = 5000.0;                 // Max daily loss ($)
input double   InpMaxTotalLoss = 10000.0;                // Max total loss ($)
input int      InpMaxTradesPerDay = 10;                  // Max trades per day
input int      InpMinTradeIntervalSeconds = 300;         // Min interval between trades (s)
input int      InpMaxSpreadPoints = 50;                  // Max spread allowed (points)

input group "=== SMART TP/TRAILING ==="
input bool     InpUseSmartTP = true;                     // Use smart take profit
input bool     InpUseTrailingATR = true;                 // Use ATR trailing stop
input double   InpTrailingATRMult = 2.0;                 // Trailing ATR multiplier
input int      InpTrailingATRPeriod = 14;                // ATR period for trailing
input bool     InpUseBreakeven = true;                   // Use breakeven
input double   InpBreakevenMinProfit = 100.0;            // Min profit for breakeven ($)

input group "=== INDICATORS ==="
input int      InpATRPeriod = 14;                        // ATR period
input int      InpRSIPeriod = 14;                        // RSI period
input int      InpEMA9Period = 9;                        // EMA 9 period
input int      InpEMA21Period = 21;                      // EMA 21 period
input int      InpEMA50Period = 50;                      // EMA 50 period
input int      InpEMA200Period = 200;                    // EMA 200 period
input int      InpMACDFast = 12;                         // MACD fast
input int      InpMACDSlow = 26;                         // MACD slow
input int      InpMACDSignal = 9;                        // MACD signal

input group "=== LOGGING ==="
input bool     InpEnableDetailedLogs = true;             // Enable detailed logs
input int      InpLogLevel = 1;                          // Log level (0=NONE, 1=INFO, 2=DEBUG)

//+------------------------------------------------------------------+
//| GLOBAL VARIABLES                                                 |
//+------------------------------------------------------------------+
// Socket
int socket_handle = INVALID_HANDLE;
bool socket_connected = false;
datetime last_heartbeat = 0;
datetime last_reconnect_attempt = 0;
int reconnect_attempts = 0;
int consecutive_send_failures = 0;  // Track consecutive send failures

// Indicators
int atr_handle = INVALID_HANDLE;
int rsi_handle = INVALID_HANDLE;
int ema9_handle = INVALID_HANDLE;
int ema21_handle = INVALID_HANDLE;
int ema50_handle = INVALID_HANDLE;
int ema200_handle = INVALID_HANDLE;
int macd_handle = INVALID_HANDLE;

double atr_buffer[];
double rsi_buffer[];
double ema9_buffer[];
double ema21_buffer[];
double ema50_buffer[];
double ema200_buffer[];
double macd_main_buffer[];
double macd_signal_buffer[];

// Trading state
CTrade trade;
datetime last_trade_time = 0;
int trades_today = 0;
double daily_pnl = 0.0;
datetime today_date = 0;

// Data buffer
string data_buffer = "";
datetime last_tick_send_time = 0;

// Anti-slippage
double last_known_price = 0.0;
datetime last_price_update = 0;

//+------------------------------------------------------------------+
//| EXPERT INITIALIZATION                                            |
//+------------------------------------------------------------------+
int OnInit()
{
   // Set trade parameters
   trade.SetExpertMagicNumber(InpMagicNumber);
   trade.SetDeviationInPoints(InpMaxSpreadPoints);
   trade.SetTypeFilling(ORDER_FILLING_FOK);
   trade.SetAsyncMode(false);
   
   // Create indicator handles ONCE (bug fix: V2 was creating every tick!)
   atr_handle = iATR(_Symbol, InpTimeframe, InpATRPeriod);
   rsi_handle = iRSI(_Symbol, InpTimeframe, InpRSIPeriod, PRICE_CLOSE);
   ema9_handle = iMA(_Symbol, InpTimeframe, InpEMA9Period, 0, MODE_EMA, PRICE_CLOSE);
   ema21_handle = iMA(_Symbol, InpTimeframe, InpEMA21Period, 0, MODE_EMA, PRICE_CLOSE);
   ema50_handle = iMA(_Symbol, InpTimeframe, InpEMA50Period, 0, MODE_EMA, PRICE_CLOSE);
   ema200_handle = iMA(_Symbol, InpTimeframe, InpEMA200Period, 0, MODE_EMA, PRICE_CLOSE);
   macd_handle = iMACD(_Symbol, InpTimeframe, InpMACDFast, InpMACDSlow, InpMACDSignal, PRICE_CLOSE);
   
   // Check handles
   if(atr_handle == INVALID_HANDLE || 
      rsi_handle == INVALID_HANDLE ||
      ema9_handle == INVALID_HANDLE ||
      ema21_handle == INVALID_HANDLE ||
      ema50_handle == INVALID_HANDLE ||
      ema200_handle == INVALID_HANDLE ||
      macd_handle == INVALID_HANDLE)
   {
      Print("ERROR: Failed to create indicator handles");
      return INIT_FAILED;
   }
   
   // Initialize arrays
   ArraySetAsSeries(atr_buffer, true);
   ArraySetAsSeries(rsi_buffer, true);
   ArraySetAsSeries(ema9_buffer, true);
   ArraySetAsSeries(ema21_buffer, true);
   ArraySetAsSeries(ema50_buffer, true);
   ArraySetAsSeries(ema200_buffer, true);
   ArraySetAsSeries(macd_main_buffer, true);
   ArraySetAsSeries(macd_signal_buffer, true);
   
   // Reset daily stats
   ResetDailyStats();
   
   // Connect to Python
   Print("ForexQuantumBot_EA_V3 initializing...");
   Print("Connecting to Python at ", InpSocketHost, ":", InpSocketPort);

   if(!ConnectToPython())
   {
      Print("WARNING: Initial connection failed, will retry in OnTick");
   }
   else
   {
      // Wait for Python to set up receive thread
      Sleep(500);
   }
   
   Print("ForexQuantumBot_EA_V3 initialized successfully");
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| EXPERT DEINITIALIZATION                                          |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   // Release indicator handles
   if(atr_handle != INVALID_HANDLE) IndicatorRelease(atr_handle);
   if(rsi_handle != INVALID_HANDLE) IndicatorRelease(rsi_handle);
   if(ema9_handle != INVALID_HANDLE) IndicatorRelease(ema9_handle);
   if(ema21_handle != INVALID_HANDLE) IndicatorRelease(ema21_handle);
   if(ema50_handle != INVALID_HANDLE) IndicatorRelease(ema50_handle);
   if(ema200_handle != INVALID_HANDLE) IndicatorRelease(ema200_handle);
   if(macd_handle != INVALID_HANDLE) IndicatorRelease(macd_handle);
   
   // Disconnect socket
   DisconnectFromPython();
   
   Print("ForexQuantumBot_EA_V3 deinitialized, reason: ", reason);
}

//+------------------------------------------------------------------+
//| EXPERT TICK FUNCTION                                             |
//+------------------------------------------------------------------+
void OnTick()
{
   static int tick_count = 0;
   tick_count++;
   
   // Only log every 50 ticks to avoid noise
   if(tick_count % 50 == 0)
      Print("DEBUG: OnTick #", tick_count, " socket=", socket_handle, " conn=", socket_connected, " fail_count=", consecutive_send_failures);

   // Check if new day
   CheckNewDay();

   // Manage socket connection
   ManageConnection();

   // If connected, send market data
   if(socket_connected)
   {
      SendMarketData();
   }

   // Check for incoming signals from Python
   CheckForSignals();

   // Manage open positions (Smart TP, Trailing, Breakeven)
   ManagePositions();
}

//+------------------------------------------------------------------+
//| CONNECTION FUNCTIONS                                             |
//+------------------------------------------------------------------+
bool ConnectToPython()
{
   // Create socket
   socket_handle = SocketCreate();
   
   if(socket_handle == INVALID_HANDLE)
   {
      Print("ERROR: Failed to create socket");
      return false;
   }
   
   // Connect to Python server
   bool connected = SocketConnect(socket_handle, InpSocketHost, InpSocketPort, InpConnectionTimeout);
   
   if(!connected)
   {
      Print("ERROR: Failed to connect to Python server");
      SocketClose(socket_handle);
      socket_handle = INVALID_HANDLE;
      return false;
   }
   
   socket_connected = true;
   Print("Connected to Python server at ", InpSocketHost, ":", InpSocketPort);

   // Send handshake (non-blocking - don't wait for ack)
   string handshake = StringFormat("HANDSHAKE|ForexQuantumBot_EA_V3|v3.00|%d|%s\n",
                                   InpMagicNumber, _Symbol);

   if(SocketSendString(handshake))
   {
      Print("Handshake sent: ", handshake);
      // Don't wait for ack - just continue
      last_heartbeat = TimeCurrent();
      return true;
   }
   else
   {
      Print("ERROR: Failed to send handshake");
      return false;
   }
}

void DisconnectFromPython()
{
   if(socket_handle != INVALID_HANDLE)
   {
      SocketClose(socket_handle);
      socket_handle = INVALID_HANDLE;
   }
   socket_connected = false;
   Print("Disconnected from Python server");
}

void ManageConnection()
{
   // Check if need to reconnect
   if(!socket_connected)
   {
      datetime now = TimeCurrent();
      
      // Check if enough time passed since last attempt
      if(now - last_reconnect_attempt >= InpReconnectDelay / 1000)
      {
         // Check if still have attempts
         if(reconnect_attempts < InpReconnectAttempts)
         {
            Print("Attempting to reconnect (", reconnect_attempts + 1, "/", InpReconnectAttempts, ")...");
            
            if(ConnectToPython())
            {
               reconnect_attempts = 0;
               consecutive_send_failures = 0;  // Reset failure counter
               // Reset tick timer to prevent immediate send
               last_tick_send_time = TimeCurrent();
               Print("Reconnection successful");
            }
            else
            {
               reconnect_attempts++;
               last_reconnect_attempt = now;
            }
         }
      }
      return;
   }

   // Heartbeat check removido - legacy não usa heartbeat timeout
   // Detecção de desconexão é feita via falhas de envio (consecutive_send_failures)
}

//+------------------------------------------------------------------+
//| DATA SENDING FUNCTIONS                                           |
//+------------------------------------------------------------------+
void SendMarketData()
{
   // Send data every 1 second max (avoid spam)
   datetime now = TimeCurrent();
   if(now - last_tick_send_time < 1)
   {
      return;
   }
   last_tick_send_time = now;
   
   // Get market data
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   long volume = SymbolInfoInteger(_Symbol, SYMBOL_VOLUME);
   double spread = ask - bid;
   
   // Update anti-slippage tracker
   last_known_price = (bid + ask) / 2;
   last_price_update = now;
   
   // Get indicator values
   double atr = GetIndicatorValue(atr_handle, atr_buffer, 0);
   double rsi = GetIndicatorValue(rsi_handle, rsi_buffer, 0);
   double ema9 = GetIndicatorValue(ema9_handle, ema9_buffer, 0);
   double ema21 = GetIndicatorValue(ema21_handle, ema21_buffer, 0);
   double ema50 = GetIndicatorValue(ema50_handle, ema50_buffer, 0);
   double ema200 = GetIndicatorValue(ema200_handle, ema200_buffer, 0);
   
   double macd_values[];
   ArraySetAsSeries(macd_values, true);
   double macd = 0.0;
   double macd_sig = 0.0;
   if(CopyBuffer(macd_handle, 0, 0, 1, macd_values) > 0)
      macd = macd_values[0];
   if(CopyBuffer(macd_handle, 1, 0, 1, macd_values) > 0)
      macd_sig = macd_values[0];
   
   // Format and send ONLY TICK data (simplified - one send per OnTick)
   string tick_data = StringFormat("TICK|%s|%.2f|%.2f|%d|%.2f|%.5f|%.2f|%.2f|%.2f|%.2f|%.2f|%.5f|%.5f|%s\n",
                                   _Symbol,
                                   bid,
                                   ask,
                                   volume,
                                   spread,
                                   atr,
                                   rsi,
                                   ema9,
                                   ema21,
                                   ema50,
                                   ema200,
                                   macd,
                                   macd_sig,
                                   TimeToString(now));
   
   if(!SocketSendString(tick_data))
   {
      consecutive_send_failures++;
      Print("WARNING: Failed to send tick, failure #", consecutive_send_failures);
      
      // Only disconnect after 10+ consecutive failures (era 3)
      if(consecutive_send_failures >= 10)
      {
         Print("ERROR: ", consecutive_send_failures, " consecutive failures, disconnecting");
         socket_connected = false;
      }
      return;
   }
   
   // Reset failure counter on success
   consecutive_send_failures = 0;
   
   // Detailed logs
   if(InpEnableDetailedLogs)
   {
      Print("TICK sent: ", _Symbol, " bid=", bid, " ask=", ask, " spread=", spread);
   }
}

void SendPositionsData()
{
   // Count positions
   int positions = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket > 0 && 
         PositionGetString(POSITION_SYMBOL) == _Symbol && 
         PositionGetInteger(POSITION_MAGIC) == InpMagicNumber)
      {
         positions++;
      }
   }
   
   // Send positions header
   string pos_header = StringFormat("POSITIONS|%d|", positions);
   SocketSendString(pos_header);
   
   // Send each position
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket > 0 && 
         PositionGetString(POSITION_SYMBOL) == _Symbol && 
         PositionGetInteger(POSITION_MAGIC) == InpMagicNumber)
      {
         string pos_data = StringFormat("%d|%s|%s|%.2f|%.2f|%.2f|%.2f|%.2f|%.2f|%.2f|%.2f|%d|",
                                        ticket,
                                        PositionGetString(POSITION_SYMBOL),
                                        PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY ? "BUY" : "SELL",
                                        PositionGetDouble(POSITION_VOLUME),
                                        PositionGetDouble(POSITION_PRICE_OPEN),
                                        PositionGetDouble(POSITION_SL),
                                        PositionGetDouble(POSITION_TP),
                                        PositionGetDouble(POSITION_PRICE_CURRENT),
                                        PositionGetDouble(POSITION_PROFIT),
                                        PositionGetDouble(POSITION_SWAP),
                                        0.0,
                                        PositionGetInteger(POSITION_MAGIC));
         
         SocketSendString(pos_data);
      }
   }
   
   SocketSendString("\n");
}

//+------------------------------------------------------------------+
//| SIGNAL RECEIVING FUNCTIONS                                       |
//+------------------------------------------------------------------+
void CheckForSignals()
{
   if(!socket_connected)
      return;

   // Verificar SE há dados disponíveis ANTES de ler (como legacy)
   if(SocketIsReadable(socket_handle) == 0)
      return;  // Sem dados - sair silenciosamente

   // Ler dados disponíveis
   uchar recv_data[];
   int bytes_read = SocketRead(socket_handle, recv_data, 4096, 200);  // 200ms timeout (era 100ms)

   if(bytes_read < 0)
   {
      // Timeout ou erro - NÃO desconectar
      return;
   }
   
   if(bytes_read > 0)
   {
      string message = CharArrayToString(recv_data);
      data_buffer += message;
      
      // Process complete messages (newline delimited)
      while(StringFind(data_buffer, "\n") >= 0)
      {
         int pos = StringFind(data_buffer, "\n");
         string line = StringSubstr(data_buffer, 0, pos);
         data_buffer = StringSubstr(data_buffer, pos + 1);

         StringTrimLeft(line);
         StringTrimRight(line);

         if(StringLen(line) > 0)
         {
            ProcessSignal(line);
         }
      }
   }
}

void ProcessSignal(string message)
{
   // Parse pipe-delimited message
   string parts[];
   int num_parts = StringSplit(message, '|', parts);
   
   if(num_parts < 2)
   {
      Print("WARNING: Invalid signal format: ", message);
      return;
   }
   
   string command = parts[0];
   
   if(command == "HANDSHAKE_OK")
   {
      Print("Handshake OK: ", message);
      return;
   }
   
   if(command == "HEARTBEAT")
   {
      last_heartbeat = TimeCurrent();
      return;
   }
   
   // Trading signals
   if(!InpAutoTrade)
   {
      if(InpEnableDetailedLogs)
         Print("Auto trading disabled, ignoring signal: ", command);
      return;
   }
   
   if(command == "BUY")
   {
      ProcessBuySignal(parts);
   }
   else if(command == "SELL")
   {
      ProcessSellSignal(parts);
   }
   else if(command == "CLOSE")
   {
      ProcessCloseSignal(parts);
   }
   else if(command == "MODIFY")
   {
      ProcessModifySignal(parts);
   }
}

void ProcessBuySignal(string &parts[])
{
   // BUY|symbol|lot|sl|tp|magic|timestamp
   if(ArraySize(parts) < 7)
   {
      Print("ERROR: Invalid BUY signal format");
      return;
   }
   
   string symbol = parts[1];
   double lot = StringToDouble(parts[2]);
   double sl = StringToDouble(parts[3]);
   double tp = StringToDouble(parts[4]);
   int magic = (int)StringToInteger(parts[5]);
   
   // Validate risk limits
   if(!CheckRiskLimits())
   {
      Print("WARNING: BUY rejected by risk limits");
      return;
   }
   
   // Check spread
   double spread = SymbolInfoDouble(symbol, SYMBOL_ASK) - SymbolInfoDouble(symbol, SYMBOL_BID);
   int spread_points = (int)(spread / SymbolInfoDouble(symbol, SYMBOL_POINT));
   
   if(spread_points > InpMaxSpreadPoints)
   {
      Print("WARNING: BUY rejected, spread too alto: ", spread_points, " > ", InpMaxSpreadPoints);
      return;
   }
   
   // Anti-slippage check
   double current_price = SymbolInfoDouble(symbol, SYMBOL_ASK);
   if(MathAbs(current_price - last_known_price) / last_known_price > 0.005)  // 0.5% max deviation
   {
      Print("WARNING: BUY rejected, price deviation too high");
      return;
   }
   
   // Execute BUY
   Print("Executing BUY: ", symbol, " lot=", lot, " SL=", sl, " TP=", tp);
   
   if(trade.Buy(lot, symbol, 0, sl, tp, "ForexQuantumBot V3"))
   {
      Print("BUY order executed successfully, ticket: ", trade.ResultOrder());
      
      // Send confirmation
      string confirm = StringFormat("ORDER_FILLED|%d|%s|BUY|%.2f|%.2f|%.2f|%.2f|%s\n",
                                    trade.ResultOrder(),
                                    symbol,
                                    lot,
                                    trade.ResultPrice(),
                                    sl,
                                    tp,
                                    TimeToString(TimeCurrent()));
      SocketSendString(confirm);
      
      // Update stats
      last_trade_time = TimeCurrent();
      trades_today++;
   }
   else
   {
      Print("ERROR: BUY order failed, retcode: ", trade.ResultRetcode(), 
            ", comment: ", trade.ResultRetcodeDescription());
   }
}

void ProcessSellSignal(string &parts[])
{
   // SELL|symbol|lot|sl|tp|magic|timestamp
   if(ArraySize(parts) < 7)
   {
      Print("ERROR: Invalid SELL signal format");
      return;
   }
   
   string symbol = parts[1];
   double lot = StringToDouble(parts[2]);
   double sl = StringToDouble(parts[3]);
   double tp = StringToDouble(parts[4]);
   int magic = (int)StringToInteger(parts[5]);
   
   // Validate risk limits
   if(!CheckRiskLimits())
   {
      Print("WARNING: SELL rejected by risk limits");
      return;
   }
   
   // Check spread
   double spread = SymbolInfoDouble(symbol, SYMBOL_ASK) - SymbolInfoDouble(symbol, SYMBOL_BID);
   int spread_points = (int)(spread / SymbolInfoDouble(symbol, SYMBOL_POINT));
   
   if(spread_points > InpMaxSpreadPoints)
   {
      Print("WARNING: SELL rejected, spread too alto: ", spread_points);
      return;
   }
   
   // Execute SELL
   Print("Executing SELL: ", symbol, " lot=", lot, " SL=", sl, " TP=", tp);
   
   if(trade.Sell(lot, symbol, 0, sl, tp, "ForexQuantumBot V3"))
   {
      Print("SELL order executed successfully, ticket: ", trade.ResultOrder());
      
      // Send confirmation
      string confirm = StringFormat("ORDER_FILLED|%d|%s|SELL|%.2f|%.2f|%.2f|%.2f|%s\n",
                                    trade.ResultOrder(),
                                    symbol,
                                    lot,
                                    trade.ResultPrice(),
                                    sl,
                                    tp,
                                    TimeToString(TimeCurrent()));
      SocketSendString(confirm);
      
      // Update stats
      last_trade_time = TimeCurrent();
      trades_today++;
   }
   else
   {
      Print("ERROR: SELL order failed, retcode: ", trade.ResultRetcode());
   }
}

void ProcessCloseSignal(string &parts[])
{
   // CLOSE|ticket|timestamp
   if(ArraySize(parts) < 3)
   {
      Print("ERROR: Invalid CLOSE signal format");
      return;
   }
   
   ulong ticket = (ulong)StringToInteger(parts[1]);
   
   Print("Closing position: ticket=", ticket);
   
   if(trade.PositionClose(ticket))
   {
      Print("Position closed successfully");
   }
   else
   {
      Print("ERROR: Failed to close position, retcode: ", trade.ResultRetcode());
   }
}

void ProcessModifySignal(string &parts[])
{
   // MODIFY|ticket|new_sl|new_tp|timestamp
   if(ArraySize(parts) < 5)
   {
      Print("ERROR: Invalid MODIFY signal format");
      return;
   }
   
   ulong ticket = (ulong)StringToInteger(parts[1]);
   double new_sl = StringToDouble(parts[2]);
   double new_tp = StringToDouble(parts[3]);
   
   Print("Modifying position: ticket=", ticket, " SL=", new_sl, " TP=", new_tp);
   
   if(trade.PositionModify(ticket, new_sl, new_tp))
   {
      Print("Position modified successfully");
   }
   else
   {
      Print("ERROR: Failed to modify position, retcode: ", trade.ResultRetcode());
   }
}

//+------------------------------------------------------------------+
//| POSITION MANAGEMENT (Smart TP, Trailing, Breakeven)             |
//+------------------------------------------------------------------+
void ManagePositions()
{
   // Iterate through positions
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket <= 0)
         continue;
      
      if(PositionGetString(POSITION_SYMBOL) != _Symbol)
         continue;
      
      if(PositionGetInteger(POSITION_MAGIC) != InpMagicNumber)
         continue;
      
      // Apply Smart TP/Trailing/Breakeven
      if(InpUseBreakeven)
         ApplyBreakeven(ticket);
      
      if(InpUseTrailingATR)
         ApplyTrailingATR(ticket);
   }
}

void ApplyBreakeven(ulong ticket)
{
   if(!PositionSelectByTicket(ticket))
      return;
   
   double open_price = PositionGetDouble(POSITION_PRICE_OPEN);
   double current_sl = PositionGetDouble(POSITION_SL);
   double current_price = PositionGetDouble(POSITION_PRICE_CURRENT);
   ENUM_POSITION_TYPE type = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
   
   double profit = PositionGetDouble(POSITION_PROFIT);
   
   // Check if profit exceeds threshold
   if(profit >= InpBreakevenMinProfit)
   {
      // Move SL to breakeven
      if(type == POSITION_TYPE_BUY && current_sl < open_price)
      {
         trade.PositionModify(ticket, open_price, PositionGetDouble(POSITION_TP));
         if(InpEnableDetailedLogs)
            Print("Breakeven applied to position ", ticket);
      }
      else if(type == POSITION_TYPE_SELL && (current_sl == 0 || current_sl > open_price))
      {
         trade.PositionModify(ticket, open_price, PositionGetDouble(POSITION_TP));
         if(InpEnableDetailedLogs)
            Print("Breakeven applied to position ", ticket);
      }
   }
}

void ApplyTrailingATR(ulong ticket)
{
   if(!PositionSelectByTicket(ticket))
      return;
   
   // Get ATR value
   double atr = GetIndicatorValue(atr_handle, atr_buffer, 0);
   if(atr == 0)
      return;
   
   double trailing_distance = atr * InpTrailingATRMult;
   
   double current_price = PositionGetDouble(POSITION_PRICE_CURRENT);
   double open_price = PositionGetDouble(POSITION_PRICE_OPEN);
   double current_sl = PositionGetDouble(POSITION_SL);
   ENUM_POSITION_TYPE type = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
   
   if(type == POSITION_TYPE_BUY)
   {
      double new_sl = current_price - trailing_distance;
      
      // Only move SL up, never down
      if(new_sl > current_sl && new_sl > open_price)
      {
         trade.PositionModify(ticket, new_sl, PositionGetDouble(POSITION_TP));
         if(InpEnableDetailedLogs)
            Print("Trailing ATR applied to BUY ", ticket, ": SL=", new_sl);
      }
   }
   else if(type == POSITION_TYPE_SELL)
   {
      double new_sl = current_price + trailing_distance;
      
      // Only move SL down, never up
      if((new_sl < current_sl || current_sl == 0) && new_sl < open_price)
      {
         trade.PositionModify(ticket, new_sl, PositionGetDouble(POSITION_TP));
         if(InpEnableDetailedLogs)
            Print("Trailing ATR applied to SELL ", ticket, ": SL=", new_sl);
      }
   }
}

//+------------------------------------------------------------------+
//| RISK MANAGEMENT                                                  |
//+------------------------------------------------------------------+
bool CheckRiskLimits()
{
   // Check max positions
   if(CountOpenPositions() >= InpMaxPositions)
   {
      Print("WARNING: Max positions reached");
      return false;
   }
   
   // Check daily loss
   if(daily_pnl <= -InpMaxDailyLoss)
   {
      Print("WARNING: Daily loss limit reached: ", daily_pnl);
      return false;
   }
   
   // Check max trades per day
   if(trades_today >= InpMaxTradesPerDay)
   {
      Print("WARNING: Max trades per day reached: ", trades_today);
      return false;
   }
   
   // Check min trade interval
   datetime now = TimeCurrent();
   if(now - last_trade_time < InpMinTradeIntervalSeconds)
   {
      Print("WARNING: Min trade interval not met");
      return false;
   }
   
   // Check total loss
   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   double total_loss = balance - equity;
   
   if(total_loss >= InpMaxTotalLoss)
   {
      Print("WARNING: Total loss limit reached: ", total_loss);
      return false;
   }
   
   return true;
}

int CountOpenPositions()
{
   int count = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket > 0 && 
         PositionGetString(POSITION_SYMBOL) == _Symbol && 
         PositionGetInteger(POSITION_MAGIC) == InpMagicNumber)
      {
         count++;
      }
   }
   return count;
}

void CheckNewDay()
{
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   
   datetime today = StringToTime(StringFormat("%04d.%02d.%02d", dt.year, dt.mon, dt.day));
   
   if(today != today_date)
   {
      Print("New day detected, resetting daily stats");
      ResetDailyStats();
      today_date = today;
   }
}

void ResetDailyStats()
{
   trades_today = 0;
   daily_pnl = 0.0;
   last_trade_time = 0;
   
   // Calculate current daily PnL from history
   datetime today_start = StringToTime(TimeToString(TimeCurrent(), TIME_DATE));
   
   HistorySelect(today_start, TimeCurrent());
   
   for(int i = HistoryDealsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = HistoryDealGetTicket(i);
      if(ticket > 0)
      {
         if(HistoryDealGetString(ticket, DEAL_SYMBOL) == _Symbol &&
            HistoryDealGetInteger(ticket, DEAL_MAGIC) == InpMagicNumber)
         {
            daily_pnl += HistoryDealGetDouble(ticket, DEAL_PROFIT);
         }
      }
   }
   
   Print("Daily stats reset. Current daily PnL: ", daily_pnl);
}

//+------------------------------------------------------------------+
//| HELPER FUNCTIONS                                                 |
//+------------------------------------------------------------------+
double GetIndicatorValue(int handle, double &buffer[], int shift)
{
   if(handle == INVALID_HANDLE)
      return 0.0;
   
   if(CopyBuffer(handle, 0, shift, 1, buffer) > 0)
   {
      return buffer[0];
   }
   
   return 0.0;
}

bool SocketSendString(string message)
{
   if(socket_handle == INVALID_HANDLE || !socket_connected)
      return false;
   
   uchar bytes[];
   int len = StringToCharArray(message, bytes);
   
   // StringToCharArray inclui null terminator, então enviar len-1 bytes
   if(SocketSend(socket_handle, bytes, len - 1) > 0)
   {
      return true;
   }
   
   return false;
}

//+------------------------------------------------------------------+
//| TIMER FUNCTION (optional, can use for background tasks)         |
//+------------------------------------------------------------------+
void OnTimer()
{
   // Can be used for periodic tasks if needed
}

//+------------------------------------------------------------------+
//| TRADE FUNCTION (called when trade operation completes)          |
//+------------------------------------------------------------------+
void OnTrade()
{
   // Can be used for trade confirmation if needed
}
//+------------------------------------------------------------------+
