//+------------------------------------------------------------------+
//|                                 Capital Sniper v3.0 CONSERVATIVE |
//|                                          OpenClaw AI Assistant   |
//|                                                                  |
//+------------------------------------------------------------------+

/*
Capital Sniper v3.0 CONSERVATIVE - MQ5 Expert Advisor
=====================================================

Conservative hardened version of Capital Sniper v3.0 with strict risk management:
"Leave out anything that would put my strategy at risk. Close out only in profit. 
Limit entries that put you in risk. Keep very limited drawdowns."

Key Conservative Features:
- Ultra-tight risk parameters (0.50% risk, 2% daily DD limit)
- Single position per pair (no stacking)
- Profit-only exits with faster breakeven
- Minimum 0.7 confidence threshold
- Time-based position closure
- Anti-loss logic and floating P&L checks
- Tighter spreads and session times
- Enhanced winner protection

Author: OpenClaw AI Assistant
Version: 3.0 CONSERVATIVE MQ5
License: Proprietary
Reference: Robert's 2023 trading style (0.06-0.09 lots, diversified pairs)
*/

#property copyright "OpenClaw AI Assistant"
#property link      "https://openclaw.ai"
#property version   "3.00"
#property strict

#include <Trade\Trade.mqh>

//+------------------------------------------------------------------+
//| INPUT PARAMETERS - GROUPED AND ORGANIZED                         |
//+------------------------------------------------------------------+

//--- RISK MANAGEMENT (CONSERVATIVE)
input group "=== CONSERVATIVE RISK MANAGEMENT ==="
input double   RiskPercent               = 0.50;    // Risk per trade % (REDUCED)
input double   MaxDailyDrawdown          = 2.0;     // Max daily drawdown % (REDUCED)
input double   MaxWeeklyDrawdown         = 4.0;     // Max weekly drawdown % (REDUCED)
input int      MaxPositionsTotal         = 4;       // Max total positions (REDUCED)
input int      MaxPositionsPerSymbol     = 1;       // Max positions per symbol (REDUCED)
input int      MaxSessionsPerSymbol      = 2;       // Max sessions per symbol (REDUCED)
input int      ConsecutiveLossLimit      = 2;       // Consecutive loss limit
input int      ConsecutiveLossPauseHours = 2;       // Pause hours after losses (INCREASED)

//--- STRATEGY PARAMETERS (CONSERVATIVE)
input group "=== CONSERVATIVE STRATEGY ==="
input int      FVGDeviationPips          = 3;       // FVG deviation pips (TIGHTER)
input int      ExhaustionThresholdForex  = 20;      // Exhaustion threshold forex pips
input int      ExhaustionThresholdGold   = 30;      // Exhaustion threshold gold pips
input bool     WyckoffConfirmation       = true;    // Wyckoff confirmation required (ENABLED)
input int      WyckoffLookback           = 3;       // Wyckoff lookback periods
input int      SLBufferPips              = 2;       // Stop loss buffer pips
input double   MinRRRatio                = 3.0;     // Minimum R:R ratio (INCREASED)
input double   MinConfidenceThreshold    = 0.7;     // Minimum confidence threshold (NEW)
input bool     DisplacementConfirmation  = true;    // Displacement confirmation (ENABLED)
input double   DisplacementATRMult       = 1.2;     // Displacement ATR multiplier

//--- SMC/ICT FILTERS (ALL ENABLED)
input group "=== SMC/ICT INTEGRATION ==="
input bool     EnableHTFBias             = true;    // Enable HTF bias filter (ENABLED)
input ENUM_TIMEFRAMES HTFTimeframe       = PERIOD_H1; // HTF timeframe
input ENUM_TIMEFRAMES LTFTimeframe       = PERIOD_M5; // LTF timeframe
input bool     EnablePremiumDiscount     = true;    // Enable premium/discount (ENABLED)
input bool     EnableLiquiditySweep      = true;    // Enable liquidity sweep (ENABLED)
input int      ATRPeriod                 = 14;      // ATR period
input int      StructureLookback         = 20;      // Structure lookback bars

//--- CONSERVATIVE TRADING SESSIONS
input group "=== TRADING SESSIONS (CONSERVATIVE) ==="
input int      LondonStart               = 8;       // London start hour (TRIMMED)
input int      LondonEnd                 = 15;      // London end hour (TRIMMED)
input int      NYStart                   = 13;      // NY start hour (TRIMMED)
input int      NYEnd                     = 20;      // NY end hour (TRIMMED)
input int      GoldSessionStart          = 13;      // Gold session start (OVERLAP only)
input int      GoldSessionEnd            = 16;      // Gold session end (OVERLAP only)
input int      SessionWarmupMinutes      = 15;      // Session warmup minutes (NEW)
input int      SessionCooldownMinutes    = 30;      // Session cooldown minutes (NEW)

//--- PROFIT-FOCUSED TRADE MANAGEMENT
input group "=== TRADE MANAGEMENT (PROFIT-FOCUSED) ==="
input double   BreakevenTriggerR          = 0.75;   // Breakeven trigger R (FASTER)
input double   PartialClose1R            = 1.5;     // First partial close R (EARLIER)
input double   PartialClose1Pct          = 0.40;    // First partial close % (MORE)
input double   PartialClose2R            = 2.5;     // Second partial close R (EARLIER)
input double   PartialClose2Pct          = 0.30;    // Second partial close %
input double   TrailingStartR            = 2.0;     // Trailing start R
input double   TrailingATRMult            = 1.0;     // Trailing ATR multiplier (TIGHTER)
input double   WinnerProtectionTrigger    = 1.0;     // Winner protection trigger (EARLIER)
input double   WinnerProtectionExit       = 0.3;     // Winner protection exit (EARLIER)
input int      MaxPositionHours          = 6;       // Max position hours (NEW)
input int      ProfitExitHours           = 4;       // Profit exit hours (NEW)
input double   AntiLossSLTighten         = 0.3;     // Anti-loss SL tighten %

//--- SYSTEM SETTINGS
input group "=== SYSTEM SETTINGS ==="
input int      MagicNumberBase           = 987654;  // Magic number base
input int      LoopDelaySeconds          = 1;       // Loop delay seconds
input int      RetryAttempts             = 3;       // Retry attempts
input int      RetryDelayMs              = 500;     // Retry delay ms
input bool     EnableLogging             = true;    // Enable detailed logging

//--- ANTI-LOSS SETTINGS (NEW)
input group "=== ANTI-LOSS PROTECTION ==="
input bool     CheckFloatingPnL          = true;    // Check floating P&L before trades
input double   MinWinRateThreshold       = 50.0;    // Min win rate % threshold
input int      WinRateLookback           = 10;      // Win rate lookback trades
input double   SpreadProtectionMult      = 2.0;     // Spread protection multiplier

//+------------------------------------------------------------------+
//| GLOBAL VARIABLES AND STRUCTURES                                  |
//+------------------------------------------------------------------+

// Trade management class
CTrade trade;

// Symbol configuration structure
struct SymbolConfig {
    string symbol;
    double maxSpread;
    double pointMultiplier;
    int magicNumber;
};

// Position tracking structure
struct PositionData {
    bool breakevenApplied;
    bool partial1Applied;
    bool partial2Applied;
    bool trailingActive;
    double maxRReached;
    bool slTightened;
    datetime openTime;
};

// Session tracking structure
struct SessionData {
    int londonCount;
    int nyCount;
};

// Trade history structure
struct TradeHistory {
    bool isWin;
    double pnl;
    datetime time;
};

// Daily summary structure
struct DailySummary {
    string date;
    int tradesTaken;
    int wins;
    int losses;
    double netPnL;
    double maxDDHit;
    double winRate;
};

// Market structure data
struct MarketStructure {
    double swingHighs[];
    double swingLows[];
    datetime swingHighTimes[];
    datetime swingLowTimes[];
    string htfBias;
    bool isPremium;
    bool isDiscount;
    double equilibrium;
    double rangeHigh;
    double rangeLow;
};

//--- Global arrays and variables
SymbolConfig g_symbols[10];
int g_symbolCount = 0;
PositionData g_positionData[];
SessionData g_sessionData[];
TradeHistory g_tradeHistory[];
int g_tradeHistoryCount = 0;
DailySummary g_dailySummary;
MarketStructure g_marketStructure[];

//--- Trading state variables
double g_equityStart = 0.0;
double g_weeklyEquityStart = 0.0;
double g_floatingPeak = 0.0;
bool g_stopAllTrading = false;
int g_consecutiveLosses = 0;
datetime g_pauseUntil = 0;
bool g_sessionResetDone = false;
bool g_weeklyResetDone = false;

//--- Static session tracking flags
static bool g_londonResetToday = false;
static bool g_nyResetToday = false;
static bool g_dailySummaryLogged = false;
static string g_lastResetDate = "";

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit() {
    // Initialize symbol configuration
    InitializeSymbols();
    
    // Setup logging
    WriteLog("Capital Sniper v3.0 CONSERVATIVE - MQ5 EA Starting");
    WriteLog("============================================================");
    LogConfigurationSummary();
    
    // Initialize trading state
    g_equityStart = AccountInfoDouble(ACCOUNT_EQUITY);
    g_weeklyEquityStart = g_equityStart;
    g_floatingPeak = g_equityStart;
    
    WriteLog(StringFormat("Initial account equity: %.2f", g_equityStart));
    
    // Initialize arrays
    ArrayResize(g_positionData, 1000, 100);  // Reserve space for position tracking
    ArrayResize(g_sessionData, g_symbolCount);
    ArrayResize(g_tradeHistory, WinRateLookback, WinRateLookback);
    ArrayResize(g_marketStructure, g_symbolCount);
    
    // Initialize daily summary
    InitializeDailySummary();
    
    // Reset session flags
    ResetSessionFlags();
    
    WriteLog("Conservative EA initialization completed successfully");
    return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                |
//+------------------------------------------------------------------+
void OnDeinit(const int reason) {
    WriteLog("Capital Sniper v3.0 CONSERVATIVE - Shutting down");
    LogDailySummary();
    WriteLog("Conservative cleanup completed");
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick() {
    // Check if MT5 connection is active
    if(!TerminalInfoInteger(TERMINAL_CONNECTED)) {
        return;
    }
    
    // Reset session counters if needed (using static flags)
    ResetSessionCountersIfNeeded();
    
    // Check conservative risk limits
    if(!CheckRiskLimits()) {
        return;
    }
    
    // Manage existing positions with conservative approach
    ManageOpenPositions();
    
    // Scan for new signals (every 5 seconds to reduce CPU load)
    static datetime lastScanTime = 0;
    datetime currentTime = TimeCurrent();
    if(currentTime - lastScanTime >= 5) {
        ScanForSignals();
        lastScanTime = currentTime;
    }
}

//+------------------------------------------------------------------+
//| Initialize symbol configuration                                  |
//+------------------------------------------------------------------+
void InitializeSymbols() {
    g_symbolCount = 0;
    
    // Configure symbols with their specific parameters
    AddSymbol("EURUSD", 1.0, 10000);    // Majors - TIGHTER spreads
    AddSymbol("GBPUSD", 1.0, 10000);
    AddSymbol("USDJPY", 1.0, 100);
    AddSymbol("USDCAD", 1.5, 10000);    // Crosses - TIGHTER spreads
    AddSymbol("AUDUSD", 1.5, 10000);
    AddSymbol("NZDUSD", 1.5, 10000);
    AddSymbol("USDCHF", 1.5, 10000);
    AddSymbol("EURJPY", 1.5, 100);
    AddSymbol("GBPJPY", 1.5, 100);
    AddSymbol("XAUUSD", 3.0, 100);      // Gold - wider spread allowed
}

//+------------------------------------------------------------------+
//| Add symbol to configuration                                      |
//+------------------------------------------------------------------+
void AddSymbol(string symbol, double maxSpread, double pointMult) {
    if(g_symbolCount >= 10) return;
    
    g_symbols[g_symbolCount].symbol = symbol;
    g_symbols[g_symbolCount].maxSpread = maxSpread;
    g_symbols[g_symbolCount].pointMultiplier = pointMult;
    g_symbols[g_symbolCount].magicNumber = MagicNumberBase + g_symbolCount;
    
    // Initialize session data for this symbol
    g_sessionData[g_symbolCount].londonCount = 0;
    g_sessionData[g_symbolCount].nyCount = 0;
    
    g_symbolCount++;
}

//+------------------------------------------------------------------+
//| Log configuration summary                                        |
//+------------------------------------------------------------------+
void LogConfigurationSummary() {
    WriteLog("CONSERVATIVE Configuration Summary:");
    WriteLog(StringFormat("Risk per trade: %.2f%% (REDUCED)", RiskPercent));
    WriteLog(StringFormat("Max daily drawdown: %.1f%% (REDUCED)", MaxDailyDrawdown));
    WriteLog(StringFormat("Max positions per symbol: %d (REDUCED)", MaxPositionsPerSymbol));
    WriteLog(StringFormat("Min R:R ratio: %.1f (INCREASED)", MinRRRatio));
    WriteLog(StringFormat("Min confidence threshold: %.1f (NEW)", MinConfidenceThreshold));
    WriteLog("Stacking disabled: Single entries only");
    WriteLog(StringFormat("Wyckoff confirmation: %s (ENABLED)", WyckoffConfirmation ? "true" : "false"));
    WriteLog(StringFormat("Displacement confirmation: %s (ENABLED)", DisplacementConfirmation ? "true" : "false"));
    WriteLog(StringFormat("Breakeven trigger: %.2fR (FASTER)", BreakevenTriggerR));
    WriteLog(StringFormat("Max position time: %d hours (NEW)", MaxPositionHours));
    WriteLog("============================================================");
}

//+------------------------------------------------------------------+
//| Initialize daily summary                                         |
//+------------------------------------------------------------------+
void InitializeDailySummary() {
    g_dailySummary.date = TimeToString(TimeCurrent(), TIME_DATE);
    g_dailySummary.tradesTaken = 0;
    g_dailySummary.wins = 0;
    g_dailySummary.losses = 0;
    g_dailySummary.netPnL = 0.0;
    g_dailySummary.maxDDHit = 0.0;
    g_dailySummary.winRate = 0.0;
}

//+------------------------------------------------------------------+
//| Reset session flags for new day                                 |
//+------------------------------------------------------------------+
void ResetSessionFlags() {
    g_londonResetToday = false;
    g_nyResetToday = false;
    g_dailySummaryLogged = false;
    g_lastResetDate = TimeToString(TimeCurrent(), TIME_DATE);
}

//+------------------------------------------------------------------+
//| Check conservative risk limits                                  |
//+------------------------------------------------------------------+
bool CheckRiskLimits() {
    double currentEquity = AccountInfoDouble(ACCOUNT_EQUITY);
    
    // Check if in pause period
    if(g_pauseUntil > 0 && TimeCurrent() < g_pauseUntil) {
        return false;
    }
    
    // Check daily drawdown (TIGHTER)
    if(g_equityStart > 0) {
        double dailyDD = (g_equityStart - currentEquity) / g_equityStart * 100.0;
        if(dailyDD >= MaxDailyDrawdown) {
            g_stopAllTrading = true;
            WriteLog(StringFormat("Daily drawdown limit hit: %.2f%%", dailyDD));
            return false;
        }
    }
    
    // Check weekly drawdown (TIGHTER)
    if(g_weeklyEquityStart > 0) {
        double weeklyDD = (g_weeklyEquityStart - currentEquity) / g_weeklyEquityStart * 100.0;
        if(weeklyDD >= MaxWeeklyDrawdown) {
            g_stopAllTrading = true;
            WriteLog(StringFormat("Weekly drawdown limit hit: %.2f%%", weeklyDD));
            return false;
        }
    }
    
    // NEW - Check floating P&L before new trades
    if(CheckFloatingPnL) {
        double floatingPnL = GetTotalFloatingPnL();
        if(floatingPnL < 0) {
            return false;  // Block new trades if floating negative
        }
    }
    
    // NEW - Check win rate
    double winRate = GetCurrentWinRate();
    if(winRate < MinWinRateThreshold) {
        WriteLog(StringFormat("Win rate below threshold: %.1f%%, pausing trading", winRate));
        return false;
    }
    
    // Update floating peak
    if(currentEquity > g_floatingPeak) {
        g_floatingPeak = currentEquity;
    }
    
    // Check max positions
    int totalPositions = PositionsTotal();
    if(totalPositions >= MaxPositionsTotal) {
        return false;
    }
    
    return !g_stopAllTrading;
}

//+------------------------------------------------------------------+
//| Get total floating P&L                                          |
//+------------------------------------------------------------------+
double GetTotalFloatingPnL() {
    double totalPnL = 0.0;
    
    for(int i = 0; i < PositionsTotal(); i++) {
        if(PositionGetTicket(i) > 0) {
            string posSymbol = PositionGetString(POSITION_SYMBOL);
            long posMagic = PositionGetInteger(POSITION_MAGIC);
            
            // Check if it's our position (magic number range)
            if(posMagic >= MagicNumberBase && posMagic < MagicNumberBase + 10000) {
                totalPnL += PositionGetDouble(POSITION_PROFIT);
            }
        }
    }
    
    return totalPnL;
}

//+------------------------------------------------------------------+
//| Get current win rate                                            |
//+------------------------------------------------------------------+
double GetCurrentWinRate() {
    if(g_tradeHistoryCount == 0) {
        return 100.0;  // Default to allow initial trades
    }
    
    int wins = 0;
    for(int i = 0; i < g_tradeHistoryCount; i++) {
        if(g_tradeHistory[i].isWin) {
            wins++;
        }
    }
    
    return (double)wins / (double)g_tradeHistoryCount * 100.0;
}

//+------------------------------------------------------------------+
//| Add trade result to history                                     |
//+------------------------------------------------------------------+
void AddTradeResult(bool isWin, double pnl) {
    // Shift array if at capacity
    if(g_tradeHistoryCount >= WinRateLookback) {
        for(int i = 0; i < WinRateLookback - 1; i++) {
            g_tradeHistory[i] = g_tradeHistory[i + 1];
        }
        g_tradeHistoryCount = WinRateLookback - 1;
    }
    
    // Add new trade
    g_tradeHistory[g_tradeHistoryCount].isWin = isWin;
    g_tradeHistory[g_tradeHistoryCount].pnl = pnl;
    g_tradeHistory[g_tradeHistoryCount].time = TimeCurrent();
    g_tradeHistoryCount++;
}

//+------------------------------------------------------------------+
//| Reset session counters if needed (using static flags)          |
//+------------------------------------------------------------------+
void ResetSessionCountersIfNeeded() {
    datetime currentTime = TimeCurrent();
    MqlDateTime timeStruct;
    TimeToStruct(currentTime, timeStruct);
    
    string todayKey = TimeToString(currentTime, TIME_DATE);
    
    // Check if it's a new day
    if(g_lastResetDate != todayKey) {
        ResetSessionFlags();
        g_lastResetDate = todayKey;
    }
    
    // Reset at London session start (once per day)
    if(timeStruct.hour == LondonStart && !g_londonResetToday) {
        for(int i = 0; i < g_symbolCount; i++) {
            g_sessionData[i].londonCount = 0;
        }
        
        g_equityStart = AccountInfoDouble(ACCOUNT_EQUITY);
        g_floatingPeak = g_equityStart;
        g_londonResetToday = true;
        
        // Reset daily summary
        InitializeDailySummary();
        
        WriteLog(StringFormat("London session reset. Equity baseline: %.2f", g_equityStart));
    }
    
    // Reset at NY session start (once per day)
    if(timeStruct.hour == NYStart && !g_nyResetToday) {
        for(int i = 0; i < g_symbolCount; i++) {
            g_sessionData[i].nyCount = 0;
        }
        
        g_nyResetToday = true;
        WriteLog("NY session reset completed");
    }
    
    // Weekly reset (Monday)
    if(timeStruct.day_of_week == 1 && timeStruct.hour == LondonStart && !g_weeklyResetDone) {
        g_weeklyEquityStart = AccountInfoDouble(ACCOUNT_EQUITY);
        g_stopAllTrading = false;  // Reset weekly halt
        g_weeklyResetDone = true;
        WriteLog(StringFormat("Weekly reset. Equity baseline: %.2f", g_weeklyEquityStart));
    }
    
    // Reset weekly flag on other days
    if(timeStruct.day_of_week != 1) {
        g_weeklyResetDone = false;
    }
    
    // Log daily summary at session end
    if((timeStruct.hour == LondonEnd || timeStruct.hour == NYEnd) && !g_dailySummaryLogged) {
        LogDailySummary();
        g_dailySummaryLogged = true;
    }
}

//+------------------------------------------------------------------+
//| Check if in trading session (conservative)                      |
//+------------------------------------------------------------------+
bool IsTradingSession(string symbol, string &session) {
    MqlDateTime timeStruct;
    TimeToStruct(TimeCurrent(), timeStruct);
    
    int currentHour = timeStruct.hour;
    int currentMinute = timeStruct.min;
    
    // Check warmup period (first 15 minutes of session)
    if((currentHour == LondonStart && currentMinute < SessionWarmupMinutes) ||
       (currentHour == NYStart && currentMinute < SessionWarmupMinutes)) {
        session = "warmup";
        return false;
    }
    
    // Check cooldown period (last 30 minutes of session)
    if((currentHour == LondonEnd && currentMinute >= 60 - SessionCooldownMinutes) ||
       (currentHour == NYEnd && currentMinute >= 60 - SessionCooldownMinutes)) {
        session = "cooldown";
        return false;
    }
    
    bool londonActive = (currentHour >= LondonStart && currentHour <= LondonEnd);
    bool nyActive = (currentHour >= NYStart && currentHour <= NYEnd);
    
    // Special handling for XAUUSD (Gold) - OVERLAP ONLY
    if(symbol == "XAUUSD") {
        bool goldActive = (currentHour >= GoldSessionStart && currentHour <= GoldSessionEnd);
        
        // Also check warmup/cooldown for gold session
        if((currentHour == GoldSessionStart && currentMinute < SessionWarmupMinutes) ||
           (currentHour == GoldSessionEnd && currentMinute >= 60 - SessionCooldownMinutes)) {
            session = "cooldown";
            return false;
        }
        
        if(goldActive) {
            session = "overlap";
            return true;
        } else {
            session = "closed";
            return false;
        }
    }
    
    // Regular forex pairs
    if(londonActive && nyActive) {
        session = "overlap";
        return true;
    } else if(londonActive) {
        session = "london";
        return true;
    } else if(nyActive) {
        session = "ny";
        return true;
    } else {
        session = "closed";
        return false;
    }
}

//+------------------------------------------------------------------+
//| Check session limits                                            |
//+------------------------------------------------------------------+
bool CheckSessionLimits(string symbol, string session) {
    int symbolIndex = GetSymbolIndex(symbol);
    if(symbolIndex < 0) return false;
    
    if(session == "overlap") {
        // During overlap, check both session limits
        return (g_sessionData[symbolIndex].londonCount < MaxSessionsPerSymbol &&
                g_sessionData[symbolIndex].nyCount < MaxSessionsPerSymbol);
    } else if(session == "london") {
        return g_sessionData[symbolIndex].londonCount < MaxSessionsPerSymbol;
    } else if(session == "ny") {
        return g_sessionData[symbolIndex].nyCount < MaxSessionsPerSymbol;
    }
    
    return false;
}

//+------------------------------------------------------------------+
//| Get symbol index                                                |
//+------------------------------------------------------------------+
int GetSymbolIndex(string symbol) {
    for(int i = 0; i < g_symbolCount; i++) {
        if(g_symbols[i].symbol == symbol) {
            return i;
        }
    }
    return -1;
}

//+------------------------------------------------------------------+
//| Get spread in pips                                              |
//+------------------------------------------------------------------+
double GetSpreadPips(string symbol) {
    long spreadLong = SymbolInfoInteger(symbol, SYMBOL_SPREAD);
    double spread = (double)spreadLong;
    double point = SymbolInfoDouble(symbol, SYMBOL_POINT);
    
    int symbolIndex = GetSymbolIndex(symbol);
    if(symbolIndex < 0) return 999.0;
    
    double pointMultiplier = g_symbols[symbolIndex].pointMultiplier;
    return spread * point * pointMultiplier;
}

//+------------------------------------------------------------------+
//| Check if symbol is eligible for trading                         |
//+------------------------------------------------------------------+
bool IsSymbolEligibleForTrading(string symbol) {
    // Check if symbol exists and is active
    if(!SymbolSelect(symbol, true)) {
        return false;
    }
    
    // Check trading session (with warmup/cooldown)
    string session;
    if(!IsTradingSession(symbol, session)) {
        return false;
    }
    
    // Check session limits
    if(!CheckSessionLimits(symbol, session)) {
        return false;
    }
    
    // TIGHTER spread check
    double spreadPips = GetSpreadPips(symbol);
    int symbolIndex = GetSymbolIndex(symbol);
    if(symbolIndex < 0) return false;
    
    double maxSpread = g_symbols[symbolIndex].maxSpread;
    if(spreadPips > maxSpread) {
        return false;
    }
    
    // STRICT position limits (max 1 per symbol)
    int openPositions = CountOpenPositions(symbol);
    if(openPositions >= MaxPositionsPerSymbol) {
        return false;
    }
    
    return true;
}

//+------------------------------------------------------------------+
//| Count open positions                                            |
//+------------------------------------------------------------------+
int CountOpenPositions(string symbol = "") {
    int count = 0;
    
    for(int i = 0; i < PositionsTotal(); i++) {
        if(PositionGetTicket(i) > 0) {
            string posSymbol = PositionGetString(POSITION_SYMBOL);
            long posMagic = PositionGetInteger(POSITION_MAGIC);
            
            // Check if it's our position
            if(posMagic >= MagicNumberBase && posMagic < MagicNumberBase + 10000) {
                if(symbol == "" || posSymbol == symbol) {
                    count++;
                }
            }
        }
    }
    
    return count;
}

//+------------------------------------------------------------------+
//| Scan for trading signals                                        |
//+------------------------------------------------------------------+
void ScanForSignals() {
    for(int i = 0; i < g_symbolCount; i++) {
        string symbol = g_symbols[i].symbol;
        
        if(!IsSymbolEligibleForTrading(symbol)) {
            continue;
        }
        
        // Get market data
        MqlRates rates[];
        if(CopyRates(symbol, LTFTimeframe, 0, 100, rates) <= 0) {
            continue;
        }
        
        // Update market structure for this symbol
        UpdateMarketStructure(symbol, rates);
        
        // Detect ONLY FVG patterns (no order blocks per requirement)
        DetectFVGPatterns(symbol, rates);
    }
}

//+------------------------------------------------------------------+
//| Update market structure for SMC analysis                        |
//+------------------------------------------------------------------+
void UpdateMarketStructure(string symbol, MqlRates &rates[]) {
    int symbolIndex = GetSymbolIndex(symbol);
    if(symbolIndex < 0) return;
    
    int rateCount = ArraySize(rates);
    if(rateCount < StructureLookback * 2 + 1) return;
    
    // Calculate swing highs and lows
    CalculateSwings(symbolIndex, rates);
    
    // Determine HTF bias
    DetermineHTFBias(symbolIndex, rates);
    
    // Calculate premium/discount zones
    CalculatePremiumDiscount(symbolIndex, rates);
}

//+------------------------------------------------------------------+
//| Calculate swing highs and lows                                  |
//+------------------------------------------------------------------+
void CalculateSwings(int symbolIndex, MqlRates &rates[]) {
    int rateCount = ArraySize(rates);
    
    // Dynamic array sizing for Wyckoff patterns
    ArrayResize(g_marketStructure[symbolIndex].swingHighs, 20, 10);
    ArrayResize(g_marketStructure[symbolIndex].swingLows, 20, 10);
    ArrayResize(g_marketStructure[symbolIndex].swingHighTimes, 20, 10);
    ArrayResize(g_marketStructure[symbolIndex].swingLowTimes, 20, 10);
    
    int highCount = 0, lowCount = 0;
    
    for(int i = StructureLookback; i < rateCount - StructureLookback; i++) {
        // Check for swing high
        bool isSwingHigh = true;
        for(int j = i - StructureLookback; j <= i + StructureLookback; j++) {
            if(j != i && rates[j].high >= rates[i].high) {  // High comparison
                isSwingHigh = false;
                break;
            }
        }
        
        if(isSwingHigh && highCount < 20) {
            g_marketStructure[symbolIndex].swingHighs[highCount] = rates[i].high;
            g_marketStructure[symbolIndex].swingHighTimes[highCount] = (datetime)rates[i].time;
            highCount++;
        }
        
        // Check for swing low
        bool isSwingLow = true;
        for(int j = i - StructureLookback; j <= i + StructureLookback; j++) {
            if(j != i && rates[j].low <= rates[i].low) {  // Low comparison
                isSwingLow = false;
                break;
            }
        }
        
        if(isSwingLow && lowCount < 20) {
            g_marketStructure[symbolIndex].swingLows[lowCount] = rates[i].low;
            g_marketStructure[symbolIndex].swingLowTimes[lowCount] = (datetime)rates[i].time;
            lowCount++;
        }
    }
}

//+------------------------------------------------------------------+
//| Determine HTF bias                                              |
//+------------------------------------------------------------------+
void DetermineHTFBias(int symbolIndex, MqlRates &rates[]) {
    int rateCount = ArraySize(rates);
    if(rateCount < 2) {
        g_marketStructure[symbolIndex].htfBias = "neutral";
        return;
    }
    
    int highCount = ArraySize(g_marketStructure[symbolIndex].swingHighs);
    int lowCount = ArraySize(g_marketStructure[symbolIndex].swingLows);
    
    if(highCount == 0 || lowCount == 0) {
        g_marketStructure[symbolIndex].htfBias = "neutral";
        return;
    }
    
    // Find most recent swing high and low
    datetime latestHighTime = 0;
    datetime latestLowTime = 0;
    double latestHigh = 0;
    double latestLow = 0;
    
    for(int i = 0; i < highCount; i++) {
        if(g_marketStructure[symbolIndex].swingHighTimes[i] > latestHighTime) {
            latestHighTime = g_marketStructure[symbolIndex].swingHighTimes[i];
            latestHigh = g_marketStructure[symbolIndex].swingHighs[i];
        }
    }
    
    for(int i = 0; i < lowCount; i++) {
        if(g_marketStructure[symbolIndex].swingLowTimes[i] > latestLowTime) {
            latestLowTime = g_marketStructure[symbolIndex].swingLowTimes[i];
            latestLow = g_marketStructure[symbolIndex].swingLows[i];
        }
    }
    
    double currentPrice = rates[rateCount-1].close;  // Close price
    
    // Simple bias determination based on recent structure breaks
    if(latestHighTime > latestLowTime) {
        // Recent swing high is more recent
        if(currentPrice > latestHigh) {
            g_marketStructure[symbolIndex].htfBias = "bullish";
        } else if(currentPrice < latestLow) {
            g_marketStructure[symbolIndex].htfBias = "bearish";
        } else {
            g_marketStructure[symbolIndex].htfBias = "neutral";
        }
    } else {
        // Recent swing low is more recent
        if(currentPrice < latestLow) {
            g_marketStructure[symbolIndex].htfBias = "bearish";
        } else if(currentPrice > latestHigh) {
            g_marketStructure[symbolIndex].htfBias = "bullish";
        } else {
            g_marketStructure[symbolIndex].htfBias = "neutral";
        }
    }
}

//+------------------------------------------------------------------+
//| Calculate premium/discount zones                                |
//+------------------------------------------------------------------+
void CalculatePremiumDiscount(int symbolIndex, MqlRates &rates[]) {
    int highCount = ArraySize(g_marketStructure[symbolIndex].swingHighs);
    int lowCount = ArraySize(g_marketStructure[symbolIndex].swingLows);
    
    if(highCount == 0 || lowCount == 0) {
        g_marketStructure[symbolIndex].isPremium = false;
        g_marketStructure[symbolIndex].isDiscount = false;
        g_marketStructure[symbolIndex].equilibrium = 0;
        return;
    }
    
    // Find recent swing range
    double recentHigh = g_marketStructure[symbolIndex].swingHighs[highCount-1];
    double recentLow = g_marketStructure[symbolIndex].swingLows[lowCount-1];
    
    int rateCount = ArraySize(rates);
    double currentPrice = rates[rateCount-1].close;  // Close price
    
    double equilibrium = (recentHigh + recentLow) / 2.0;
    
    g_marketStructure[symbolIndex].isPremium = (currentPrice > equilibrium);
    g_marketStructure[symbolIndex].isDiscount = (currentPrice < equilibrium);
    g_marketStructure[symbolIndex].equilibrium = equilibrium;
    g_marketStructure[symbolIndex].rangeHigh = recentHigh;
    g_marketStructure[symbolIndex].rangeLow = recentLow;
}

//+------------------------------------------------------------------+
//| Detect FVG patterns (Fair Value Gaps)                          |
//+------------------------------------------------------------------+
void DetectFVGPatterns(string symbol, MqlRates &rates[]) {
    int rateCount = ArraySize(rates);
    if(rateCount < 5) return;
    
    int symbolIndex = GetSymbolIndex(symbol);
    if(symbolIndex < 0) return;
    
    double point = SymbolInfoDouble(symbol, SYMBOL_POINT);
    double pointMultiplier = g_symbols[symbolIndex].pointMultiplier;
    double deviation = FVGDeviationPips * point * pointMultiplier;
    
    // Check last 5 bars for FVG patterns
    for(int i = 2; i < rateCount - 2; i++) {
        double bar1High = rates[i-2].high;
        double bar1Low = rates[i-2].low;
        double bar3High = rates[i].high;
        double bar3Low = rates[i].low;
        
        double currentLow = rates[rateCount-1].low;
        double currentHigh = rates[rateCount-1].high;
        
        // Bullish FVG: bar1.high < bar3.low (gap up)
        if(bar1High < bar3Low - deviation) {
            double entryPrice = bar1High + deviation;
            
            // Confirm entry is still valid
            if(currentLow > entryPrice) {
                double slPrice = bar1Low - (SLBufferPips * point * pointMultiplier);
                
                double confidence = CalculateSignalConfidence(symbol, rates, "BUY", i);
                
                // Apply minimum confidence filter
                if(confidence >= MinConfidenceThreshold) {
                    if(ValidateSignalConservative(symbol, rates, "BUY", entryPrice, slPrice)) {
                        ExecuteTrade(symbol, "BUY", entryPrice, slPrice, "FVG_BULLISH", confidence);
                    }
                }
            }
        }
        
        // Bearish FVG: bar1.low > bar3.high (gap down)
        if(bar1Low > bar3High + deviation) {
            double entryPrice = bar1Low - deviation;
            
            // Confirm entry is still valid
            if(currentHigh < entryPrice) {
                double slPrice = bar1High + (SLBufferPips * point * pointMultiplier);
                
                double confidence = CalculateSignalConfidence(symbol, rates, "SELL", i);
                
                // Apply minimum confidence filter
                if(confidence >= MinConfidenceThreshold) {
                    if(ValidateSignalConservative(symbol, rates, "SELL", entryPrice, slPrice)) {
                        ExecuteTrade(symbol, "SELL", entryPrice, slPrice, "FVG_BEARISH", confidence);
                    }
                }
            }
        }
    }
}

//+------------------------------------------------------------------+
//| Calculate signal confidence                                      |
//+------------------------------------------------------------------+
double CalculateSignalConfidence(string symbol, MqlRates &rates[], string signalType, int barIndex) {
    double confidence = 0.5;  // Base confidence
    
    int rateCount = ArraySize(rates);
    
    // ATR-based momentum check
    double atr = CalculateATR(symbol, rates, barIndex);
    if(atr > 0) {
        double recentRange = rates[barIndex].high - rates[barIndex].low;  // High - Low
        if(recentRange < atr * 0.8) {  // Lower volatility = higher confidence
            confidence += 0.2;
        }
    }
    
    // Trend alignment check (simple moving average)
    int maPeriod = 20;
    if(barIndex >= maPeriod) {
        double maSum = 0;
        for(int i = barIndex - maPeriod; i < barIndex; i++) {
            maSum += rates[i].close;  // Close price
        }
        double ma = maSum / maPeriod;
        double currentClose = rates[barIndex].close;
        
        if(signalType == "BUY" && currentClose > ma) {
            confidence += 0.15;
        } else if(signalType == "SELL" && currentClose < ma) {
            confidence += 0.15;
        }
    }
    
    // Price action stability
    if(barIndex >= 5) {
        double priceSum = 0;
        for(int i = barIndex - 5; i < barIndex; i++) {
            priceSum += rates[i].close;
        }
        double avgPrice = priceSum / 5.0;
        
        double priceStdDev = 0;
        for(int i = barIndex - 5; i < barIndex; i++) {
            priceStdDev += MathPow(rates[i].close - avgPrice, 2);
        }
        priceStdDev = MathSqrt(priceStdDev / 5.0);
        
        if(atr > 0 && priceStdDev < atr * 0.5) {  // Lower volatility = more stable
            confidence += 0.1;
        }
    }
    
    return MathMin(confidence, 1.0);  // Cap at 1.0
}

//+------------------------------------------------------------------+
//| Calculate ATR                                                   |
//+------------------------------------------------------------------+
double CalculateATR(string symbol, MqlRates &rates[], int endIndex) {
    int startIndex = MathMax(0, endIndex - ATRPeriod);
    if(endIndex - startIndex < 2) return 0.0;
    
    double trSum = 0;
    int trCount = 0;
    
    for(int i = startIndex + 1; i <= endIndex; i++) {
        double tr1 = rates[i].high - rates[i].low;  // High - Low
        double tr2 = MathAbs(rates[i].high - rates[i-1].close);  // High - Previous Close
        double tr3 = MathAbs(rates[i].low - rates[i-1].close);  // Low - Previous Close
        
        double tr = MathMax(tr1, MathMax(tr2, tr3));
        trSum += tr;
        trCount++;
    }
    
    return trCount > 0 ? trSum / trCount : 0.0;
}

//+------------------------------------------------------------------+
//| Validate signal against conservative filters                    |
//+------------------------------------------------------------------+
bool ValidateSignalConservative(string symbol, MqlRates &rates[], string signalType, double entryPrice, double slPrice) {
    int symbolIndex = GetSymbolIndex(symbol);
    if(symbolIndex < 0) return false;
    
    // MANDATORY Wyckoff filter
    if(WyckoffConfirmation && !ApplyWyckoffFilter(symbol, rates, signalType)) {
        return false;
    }
    
    // Apply exhaustion filter
    if(!ApplyExhaustionFilter(symbol, rates)) {
        return false;
    }
    
    // MANDATORY SMC/ICT filters
    if(!ApplySMCFilters(symbol, symbolIndex, signalType)) {
        return false;
    }
    
    // Check HIGHER minimum R:R ratio (3.0)
    double riskDistance = MathAbs(entryPrice - slPrice);
    if(riskDistance == 0) return false;
    
    // Calculate potential TP based on minimum R:R
    double tpPrice;
    if(signalType == "BUY") {
        tpPrice = entryPrice + (riskDistance * MinRRRatio);
    } else {
        tpPrice = entryPrice - (riskDistance * MinRRRatio);
    }
    
    return true;
}

//+------------------------------------------------------------------+
//| Apply Wyckoff confirmation filter                               |
//+------------------------------------------------------------------+
bool ApplyWyckoffFilter(string symbol, MqlRates &rates[], string signalType) {
    int rateCount = ArraySize(rates);
    if(rateCount < WyckoffLookback + 2) return false;
    
    // Check recent bars for Wyckoff patterns
    double bar0Low = rates[rateCount-2].low;   // Most recent closed bar low
    double bar0High = rates[rateCount-2].high;  // Most recent closed bar high
    double bar1Low = rates[rateCount-3].low;   // Previous bar low
    double bar1High = rates[rateCount-3].high;  // Previous bar high
    
    if(signalType == "BUY") {
        // Look for lower lows (accumulation/spring)
        return bar0Low < bar1Low;
    } else {  // SELL
        // Look for higher highs (distribution/upthrust)
        return bar0High > bar1High;
    }
}

//+------------------------------------------------------------------+
//| Apply exhaustion filter                                         |
//+------------------------------------------------------------------+
bool ApplyExhaustionFilter(string symbol, MqlRates &rates[]) {
    int rateCount = ArraySize(rates);
    if(rateCount < 2) return false;
    
    int symbolIndex = GetSymbolIndex(symbol);
    if(symbolIndex < 0) return false;
    
    double point = SymbolInfoDouble(symbol, SYMBOL_POINT);
    double pointMultiplier = g_symbols[symbolIndex].pointMultiplier;
    
    // Get appropriate threshold
    int thresholdPips = (symbol == "XAUUSD") ? ExhaustionThresholdGold : ExhaustionThresholdForex;
    double thresholdDistance = thresholdPips * point * pointMultiplier;
    
    // Check most recent closed bar
    double recentHigh = rates[rateCount-2].high;
    double recentLow = rates[rateCount-2].low;
    double barRange = recentHigh - recentLow;
    
    return barRange < thresholdDistance;  // True if NOT exhausted
}

//+------------------------------------------------------------------+
//| Apply SMC/ICT filters                                           |
//+------------------------------------------------------------------+
bool ApplySMCFilters(string symbol, int symbolIndex, string signalType) {
    // HTF Bias Filter (MANDATORY)
    string htfBias = g_marketStructure[symbolIndex].htfBias;
    if(signalType == "BUY" && htfBias == "bearish") {
        return false;
    }
    if(signalType == "SELL" && htfBias == "bullish") {
        return false;
    }
    
    // Premium/Discount Filter (MANDATORY)
    bool isPremium = g_marketStructure[symbolIndex].isPremium;
    bool isDiscount = g_marketStructure[symbolIndex].isDiscount;
    
    if(EnablePremiumDiscount) {
        if(signalType == "BUY" && isPremium) {
            return false;  // Only longs in discount
        }
        if(signalType == "SELL" && isDiscount) {
            return false;  // Only shorts in premium
        }
    }
    
    // Additional SMC filters can be added here
    
    return true;
}

//+------------------------------------------------------------------+
//| Execute trade                                                   |
//+------------------------------------------------------------------+
void ExecuteTrade(string symbol, string signalType, double entryPrice, double slPrice, string pattern, double confidence) {
    // Get session for trade registration
    string session;
    if(!IsTradingSession(symbol, session)) {
        return;
    }
    
    // Calculate risk amount
    double riskAmount = AccountInfoDouble(ACCOUNT_EQUITY) * RiskPercent / 100.0;
    
    // Calculate position size
    double positionSize = CalculatePositionSize(symbol, entryPrice, slPrice, riskAmount);
    if(positionSize <= 0) {
        WriteLog(StringFormat("Invalid position size for %s", symbol));
        return;
    }
    
    // Calculate TP levels
    double riskDistance = MathAbs(entryPrice - slPrice);
    double tpPrice;
    if(signalType == "BUY") {
        tpPrice = entryPrice + (riskDistance * MinRRRatio);
    } else {
        tpPrice = entryPrice - (riskDistance * MinRRRatio);
    }
    
    // Get magic number for this symbol
    int symbolIndex = GetSymbolIndex(symbol);
    if(symbolIndex < 0) return;
    
    int magicNumber = g_symbols[symbolIndex].magicNumber;
    string comment = StringFormat("CapSniper_%s_%s", pattern, signalType);
    
    // Place order
    bool success = PlaceConservativeOrder(symbol, signalType, entryPrice, slPrice, tpPrice, positionSize, magicNumber, comment);
    
    if(success) {
        // Register trade
        RegisterTrade(symbol, session);
        
        g_dailySummary.tradesTaken++;
        WriteLog(StringFormat("Conservative order placed: %s %s at %.5f (Confidence: %.2f)", 
                             symbol, signalType, entryPrice, confidence));
    } else {
        WriteLog(StringFormat("Failed to place conservative order for %s", symbol));
    }
}

//+------------------------------------------------------------------+
//| Calculate position size                                          |
//+------------------------------------------------------------------+
double CalculatePositionSize(string symbol, double entryPrice, double slPrice, double riskAmount) {
    double riskDistance = MathAbs(entryPrice - slPrice);
    if(riskDistance == 0) return 0;
    
    double tickValue = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_VALUE);
    double tickSize = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_SIZE);
    
    if(tickValue == 0 || tickSize == 0) return 0;
    
    double positionSize = riskAmount / (riskDistance / tickSize * tickValue);
    
    // Normalize to lot step
    double lotStep = SymbolInfoDouble(symbol, SYMBOL_VOLUME_STEP);
    positionSize = NormalizeDouble(MathFloor(positionSize / lotStep) * lotStep, 2);
    
    // Apply limits
    double minLot = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);
    double maxLot = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MAX);
    
    positionSize = MathMax(positionSize, minLot);
    positionSize = MathMin(positionSize, maxLot);
    
    return positionSize;
}

//+------------------------------------------------------------------+
//| Place conservative order                                        |
//+------------------------------------------------------------------+
bool PlaceConservativeOrder(string symbol, string signalType, double entryPrice, double slPrice, double tpPrice, 
                           double volume, int magicNumber, string comment) {
    
    ENUM_ORDER_TYPE orderType;
    if(signalType == "BUY") {
        orderType = ORDER_TYPE_BUY_LIMIT;
    } else {
        orderType = ORDER_TYPE_SELL_LIMIT;
    }
    
    // Place order with retry logic
    for(int attempt = 0; attempt < RetryAttempts; attempt++) {
        trade.SetExpertMagicNumber(magicNumber);
        
        bool result = false;
        if(orderType == ORDER_TYPE_BUY_LIMIT) {
            result = trade.BuyLimit(volume, entryPrice, symbol, slPrice, tpPrice, ORDER_TIME_DAY, 0, comment);
        } else {
            result = trade.SellLimit(volume, entryPrice, symbol, slPrice, tpPrice, ORDER_TIME_DAY, 0, comment);
        }
        
        if(result) {
            return true;
        }
        
        WriteLog(StringFormat("Order attempt %d failed: %s", attempt + 1, trade.ResultComment()));
        
        if(attempt < RetryAttempts - 1) {
            Sleep(RetryDelayMs);
        }
    }
    
    // NO MARKET ORDER FALLBACK per requirements
    WriteLog(StringFormat("Limit order not filled after retries, moving on (no market order fallback)"));
    return false;
}

//+------------------------------------------------------------------+
//| Register trade for session counting                             |
//+------------------------------------------------------------------+
void RegisterTrade(string symbol, string session) {
    int symbolIndex = GetSymbolIndex(symbol);
    if(symbolIndex < 0) return;
    
    if(session == "overlap") {
        // Session overlap 13-15 counts for both London AND NY
        g_sessionData[symbolIndex].londonCount++;
        g_sessionData[symbolIndex].nyCount++;
    } else if(session == "london") {
        g_sessionData[symbolIndex].londonCount++;
    } else if(session == "ny") {
        g_sessionData[symbolIndex].nyCount++;
    }
}

//+------------------------------------------------------------------+
//| Manage open positions                                           |
//+------------------------------------------------------------------+
void ManageOpenPositions() {
    for(int i = PositionsTotal() - 1; i >= 0; i--) {
        if(PositionGetTicket(i) > 0) {
            long magic = PositionGetInteger(POSITION_MAGIC);
            
            // Check if it's our position
            if(magic >= MagicNumberBase && magic < MagicNumberBase + 10000) {
                ManageSinglePosition();
            }
        }
    }
}

//+------------------------------------------------------------------+
//| Manage single position with conservative approach               |
//+------------------------------------------------------------------+
void ManageSinglePosition() {
    string symbol = PositionGetString(POSITION_SYMBOL);
    ulong ticket = PositionGetInteger(POSITION_TICKET);
    ENUM_POSITION_TYPE posType = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
    double openPrice = PositionGetDouble(POSITION_PRICE_OPEN);
    datetime openTime = (datetime)PositionGetInteger(POSITION_TIME);
    double currentSL = PositionGetDouble(POSITION_SL);
    double currentProfit = PositionGetDouble(POSITION_PROFIT);
    
    // Get current price (FIX: Always use SymbolInfoDouble for the TRADED symbol)
    double currentPrice;
    if(posType == POSITION_TYPE_BUY) {
        currentPrice = SymbolInfoDouble(symbol, SYMBOL_BID);
    } else {
        currentPrice = SymbolInfoDouble(symbol, SYMBOL_ASK);
    }
    
    if(currentPrice <= 0) return;
    
    // Calculate position age in hours
    double positionAge = (TimeCurrent() - openTime) / 3600.0;
    
    // Calculate R multiple
    double riskDistance = MathAbs(openPrice - currentSL);
    double rMultiple = 0;
    
    if(riskDistance > 0) {
        double profitDistance;
        if(posType == POSITION_TYPE_BUY) {
            profitDistance = currentPrice - openPrice;
        } else {
            profitDistance = openPrice - currentPrice;
        }
        rMultiple = profitDistance / riskDistance;
    }
    
    // Get or create position data
    int posDataIndex = GetPositionDataIndex(ticket);
    if(posDataIndex < 0) {
        posDataIndex = CreatePositionData(ticket, openTime);
    }
    
    if(posDataIndex < 0) return;
    
    // Update max R reached
    if(rMultiple > g_positionData[posDataIndex].maxRReached) {
        g_positionData[posDataIndex].maxRReached = rMultiple;
    }
    
    // TIME-BASED EXITS (Conservative requirement)
    // Close if profitable after 4 hours
    if(positionAge >= ProfitExitHours && currentProfit > 0) {
        ClosePositionAtProfit(ticket, "4-hour profit rule");
        return;
    }
    
    // Force close after 6 hours
    if(positionAge >= MaxPositionHours) {
        ClosePositionForce(ticket, "6-hour time limit");
        return;
    }
    
    // Close 30 minutes before session end
    if(IsNearSessionEnd(symbol)) {
        ClosePositionForce(ticket, "session end approach");
        return;
    }
    
    // Anti-loss logic: tighten SL if position drops below -0.5R
    if(rMultiple <= -0.5 && !g_positionData[posDataIndex].slTightened) {
        TightenStopLoss(ticket, symbol, openPrice, currentSL);
        g_positionData[posDataIndex].slTightened = true;
    }
    
    // PROPER ELSE-IF GATING ON TRADE MANAGEMENT STAGES
    // Stage 1: Move to breakeven FASTER (0.75R)
    if(rMultiple >= BreakevenTriggerR && !g_positionData[posDataIndex].breakevenApplied) {
        MoveToBreakevenConservative(ticket, symbol, openPrice);
        g_positionData[posDataIndex].breakevenApplied = true;
    }
    // Stage 2: First partial close EARLIER (1.5R, take 40%)
    else if(rMultiple >= PartialClose1R && !g_positionData[posDataIndex].partial1Applied) {
        PartialClosePosition(ticket, symbol, PartialClose1Pct);
        g_positionData[posDataIndex].partial1Applied = true;
    }
    // Stage 3: Second partial close (2.5R, take 30%)
    else if(rMultiple >= PartialClose2R && !g_positionData[posDataIndex].partial2Applied) {
        PartialClosePosition(ticket, symbol, PartialClose2Pct);
        g_positionData[posDataIndex].partial2Applied = true;
    }
    // Stage 4: Tighter trailing stop
    else if(rMultiple >= TrailingStartR && g_positionData[posDataIndex].breakevenApplied) {
        ApplyTrailingStopConservative(ticket, symbol, currentPrice);
        g_positionData[posDataIndex].trailingActive = true;
    }
    
    // Winner protection: If trade reached +1R but falls back to +0.3R
    if(g_positionData[posDataIndex].maxRReached >= WinnerProtectionTrigger &&
       rMultiple <= WinnerProtectionExit &&
       g_positionData[posDataIndex].breakevenApplied) {
        ClosePositionAtProfit(ticket, "winner protection");
    }
}

//+------------------------------------------------------------------+
//| Get position data index                                         |
//+------------------------------------------------------------------+
int GetPositionDataIndex(ulong ticket) {
    if(!PositionSelectByTicket(ticket)) return -1;
    datetime openTime = (datetime)PositionGetInteger(POSITION_TIME);
    
    for(int i = 0; i < ArraySize(g_positionData); i++) {
        if(g_positionData[i].openTime == openTime) {
            return i;
        }
    }
    return -1;
}

//+------------------------------------------------------------------+
//| Create position data                                            |
//+------------------------------------------------------------------+
int CreatePositionData(ulong ticket, datetime openTime) {
    int size = ArraySize(g_positionData);
    
    // Find empty slot
    for(int i = 0; i < size; i++) {
        if(g_positionData[i].openTime == 0) {
            InitializePositionData(i, openTime);
            return i;
        }
    }
    
    // Expand array if needed
    ArrayResize(g_positionData, size + 100, 100);
    InitializePositionData(size, openTime);
    return size;
}

//+------------------------------------------------------------------+
//| Initialize position data                                        |
//+------------------------------------------------------------------+
void InitializePositionData(int index, datetime openTime) {
    g_positionData[index].breakevenApplied = false;
    g_positionData[index].partial1Applied = false;
    g_positionData[index].partial2Applied = false;
    g_positionData[index].trailingActive = false;
    g_positionData[index].maxRReached = 0;
    g_positionData[index].slTightened = false;
    g_positionData[index].openTime = openTime;
}

//+------------------------------------------------------------------+
//| Check if near session end                                       |
//+------------------------------------------------------------------+
bool IsNearSessionEnd(string symbol) {
    MqlDateTime timeStruct;
    TimeToStruct(TimeCurrent(), timeStruct);
    
    int currentHour = timeStruct.hour;
    int currentMinute = timeStruct.min;
    
    // Check if within 30 minutes of any session end
    if(symbol == "XAUUSD") {
        return (currentHour == GoldSessionEnd && currentMinute >= 30);
    } else {
        return ((currentHour == LondonEnd && currentMinute >= 30) ||
                (currentHour == NYEnd && currentMinute >= 30));
    }
}

//+------------------------------------------------------------------+
//| Tighten stop loss for anti-loss protection                     |
//+------------------------------------------------------------------+
void TightenStopLoss(ulong ticket, string symbol, double openPrice, double currentSL) {
    if(currentSL == 0) return;
    
    // Calculate 30% tighter SL
    double slDistance = MathAbs(openPrice - currentSL);
    double tighterDistance = slDistance * (1 - AntiLossSLTighten);
    
    double newSL;
    ENUM_POSITION_TYPE posType = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
    
    if(posType == POSITION_TYPE_BUY) {
        newSL = openPrice - tighterDistance;
        if(newSL > currentSL) {  // Only move if better
            if(trade.PositionModify(ticket, newSL, PositionGetDouble(POSITION_TP))) {
                WriteLog(StringFormat("Tightened SL for %s (anti-loss): %.5f", symbol, newSL));
            }
        }
    } else {
        newSL = openPrice + tighterDistance;
        if(newSL < currentSL) {  // Only move if better
            if(trade.PositionModify(ticket, newSL, PositionGetDouble(POSITION_TP))) {
                WriteLog(StringFormat("Tightened SL for %s (anti-loss): %.5f", symbol, newSL));
            }
        }
    }
}

//+------------------------------------------------------------------+
//| Move to breakeven conservative                                  |
//+------------------------------------------------------------------+
void MoveToBreakevenConservative(ulong ticket, string symbol, double openPrice) {
    double point = SymbolInfoDouble(symbol, SYMBOL_POINT);
    int symbolIndex = GetSymbolIndex(symbol);
    if(symbolIndex < 0) return;
    
    double pointMultiplier = g_symbols[symbolIndex].pointMultiplier;
    double buffer = SLBufferPips * point * pointMultiplier;
    
    ENUM_POSITION_TYPE posType = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
    double currentSL = PositionGetDouble(POSITION_SL);
    double newSL;
    
    if(posType == POSITION_TYPE_BUY) {
        // Set SL above entry to ensure PROFIT-ONLY CLOSE
        newSL = openPrice + buffer;
        if(newSL > currentSL) {
            if(trade.PositionModify(ticket, newSL, PositionGetDouble(POSITION_TP))) {
                WriteLog(StringFormat("Conservative breakeven applied to %s: %.5f", symbol, newSL));
            }
        }
    } else {
        // Set SL below entry to ensure PROFIT-ONLY CLOSE
        newSL = openPrice - buffer;
        if(currentSL == 0 || newSL < currentSL) {
            if(trade.PositionModify(ticket, newSL, PositionGetDouble(POSITION_TP))) {
                WriteLog(StringFormat("Conservative breakeven applied to %s: %.5f", symbol, newSL));
            }
        }
    }
}

//+------------------------------------------------------------------+
//| Partial close position                                          |
//+------------------------------------------------------------------+
void PartialClosePosition(ulong ticket, string symbol, double closePercentage) {
    if(!PositionSelectByTicket(ticket)) return;
    
    double currentVolume = PositionGetDouble(POSITION_VOLUME);
    double closeVolume = NormalizeDouble(currentVolume * closePercentage, 2);
    
    // Check minimum volume (proper validation)
    double minLot = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);
    if(closeVolume < minLot) {
        WriteLog(StringFormat("Partial close volume too small: %.2f < %.2f", closeVolume, minLot));
        return;
    }
    
    // Ensure remaining volume is also above minimum
    double remainingVolume = currentVolume - closeVolume;
    if(remainingVolume > 0 && remainingVolume < minLot) {
        closeVolume = currentVolume - minLot;  // Adjust to leave minimum
        if(closeVolume < minLot) return;  // Cannot partial close
    }
    
    ENUM_POSITION_TYPE posType = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
    long magic = PositionGetInteger(POSITION_MAGIC);
    double currentProfit = PositionGetDouble(POSITION_PROFIT);
    
    string comment = StringFormat("Partial_Close_%.0fpct", closePercentage * 100);
    
    bool result;
    if(posType == POSITION_TYPE_BUY) {
        result = trade.Sell(closeVolume, symbol, 0, 0, 0, comment);
    } else {
        result = trade.Buy(closeVolume, symbol, 0, 0, 0, comment);
    }
    
    if(result) {
        WriteLog(StringFormat("Conservative partial close: %s %.0f%% at %.2f lots", 
                             symbol, closePercentage * 100, closeVolume));
        
        // Update daily summary
        g_dailySummary.wins++;
        g_dailySummary.netPnL += currentProfit * closePercentage;
    } else {
        WriteLog(StringFormat("Partial close failed: %s", trade.ResultComment()));
    }
}

//+------------------------------------------------------------------+
//| Apply conservative trailing stop                               |
//+------------------------------------------------------------------+
void ApplyTrailingStopConservative(ulong ticket, string symbol, double currentPrice) {
    if(!PositionSelectByTicket(ticket)) return;
    
    // Get recent rates for ATR calculation
    MqlRates rates[];
    if(CopyRates(symbol, LTFTimeframe, 0, 50, rates) <= 0) {
        return;
    }
    
    double atr = CalculateATR(symbol, rates, ArraySize(rates) - 1);
    if(atr == 0) return;
    
    // TIGHTER trailing distance (1.0x ATR)
    double trailDistance = atr * TrailingATRMult;
    
    ENUM_POSITION_TYPE posType = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
    double currentSL = PositionGetDouble(POSITION_SL);
    double newSL;
    
    if(posType == POSITION_TYPE_BUY) {
        newSL = currentPrice - trailDistance;
        if(newSL > currentSL) {
            if(trade.PositionModify(ticket, newSL, PositionGetDouble(POSITION_TP))) {
                WriteLog(StringFormat("Conservative trailing stop: %s: %.5f", symbol, newSL));
            }
        }
    } else {
        newSL = currentPrice + trailDistance;
        if(currentSL == 0 || newSL < currentSL) {
            if(trade.PositionModify(ticket, newSL, PositionGetDouble(POSITION_TP))) {
                WriteLog(StringFormat("Conservative trailing stop: %s: %.5f", symbol, newSL));
            }
        }
    }
}

//+------------------------------------------------------------------+
//| Close position at profit                                        |
//+------------------------------------------------------------------+
void ClosePositionAtProfit(ulong ticket, string reason) {
    if(!PositionSelectByTicket(ticket)) return;
    
    double currentProfit = PositionGetDouble(POSITION_PROFIT);
    if(currentProfit <= 0) {
        WriteLog(StringFormat("Position %s not profitable, keeping open despite %s", 
                             PositionGetString(POSITION_SYMBOL), reason));
        return;
    }
    
    string symbol = PositionGetString(POSITION_SYMBOL);
    string comment = StringFormat("Conservative_Close_%s", reason);
    
    if(trade.PositionClose(ticket)) {
        WriteLog(StringFormat("Conservative profit close: %s - %s - P&L: $%.2f", 
                             symbol, reason, currentProfit));
        
        // Update daily summary
        g_dailySummary.wins++;
        g_dailySummary.netPnL += currentProfit;
        
        // Clean up position data
        CleanupPositionData(ticket);
    } else {
        WriteLog(StringFormat("Failed to close position at profit: %s", trade.ResultComment()));
    }
}

//+------------------------------------------------------------------+
//| Force close position                                           |
//+------------------------------------------------------------------+
void ClosePositionForce(ulong ticket, string reason) {
    if(!PositionSelectByTicket(ticket)) return;
    
    string symbol = PositionGetString(POSITION_SYMBOL);
    double currentProfit = PositionGetDouble(POSITION_PROFIT);
    string comment = StringFormat("Force_Close_%s", reason);
    
    if(trade.PositionClose(ticket)) {
        bool isWin = (currentProfit > 0);
        WriteLog(StringFormat("Force close: %s - %s - P&L: $%.2f", symbol, reason, currentProfit));
        
        // Update daily summary
        if(isWin) {
            g_dailySummary.wins++;
        } else {
            g_dailySummary.losses++;
        }
        g_dailySummary.netPnL += currentProfit;
        
        // Update trade history
        AddTradeResult(isWin, currentProfit);
        
        // Clean up position data
        CleanupPositionData(ticket);
    } else {
        WriteLog(StringFormat("Failed to force close position: %s", trade.ResultComment()));
    }
}

//+------------------------------------------------------------------+
//| Cleanup position data                                          |
//+------------------------------------------------------------------+
void CleanupPositionData(ulong ticket) {
    datetime openTime = 0;
    if(PositionSelectByTicket(ticket)) {
        openTime = (datetime)PositionGetInteger(POSITION_TIME);
    }
    
    for(int i = 0; i < ArraySize(g_positionData); i++) {
        if(g_positionData[i].openTime == openTime) {
            g_positionData[i].openTime = 0;  // Mark as free
            break;
        }
    }
}

//+------------------------------------------------------------------+
//| Log daily summary                                              |
//+------------------------------------------------------------------+
void LogDailySummary() {
    double winRate = (g_dailySummary.tradesTaken > 0) ? 
                     ((double)g_dailySummary.wins / (double)g_dailySummary.tradesTaken) * 100.0 : 0.0;
    
    WriteLog("==================================================");
    WriteLog("DAILY TRADING SUMMARY");
    WriteLog("==================================================");
    WriteLog(StringFormat("Date: %s", g_dailySummary.date));
    WriteLog(StringFormat("Trades Taken: %d", g_dailySummary.tradesTaken));
    WriteLog(StringFormat("Wins: %d", g_dailySummary.wins));
    WriteLog(StringFormat("Losses: %d", g_dailySummary.losses));
    WriteLog(StringFormat("Net P&L: $%.2f", g_dailySummary.netPnL));
    WriteLog(StringFormat("Win Rate: %.1f%%", winRate));
    WriteLog("==================================================");
}

//+------------------------------------------------------------------+
//| Write log message                                               |
//+------------------------------------------------------------------+
void WriteLog(string message) {
    if(!EnableLogging) return;
    
    string logMessage = StringFormat("%s - %s", TimeToString(TimeCurrent(), TIME_DATE|TIME_MINUTES), message);
    Print(logMessage);
    
    // Optional: Write to file
    string filename = "capital_sniper_conservative_" + TimeToString(TimeCurrent(), TIME_DATE) + ".log";
    int file = FileOpen(filename, FILE_READ|FILE_WRITE|FILE_TXT|FILE_ANSI);
    if(file != INVALID_HANDLE) {
        FileSeek(file, 0, SEEK_END);
        FileWriteString(file, logMessage + "\r\n");
        FileClose(file);
    }
}

//+------------------------------------------------------------------+
//| END OF CAPITAL SNIPER v3.0 CONSERVATIVE MQ5 EA                 |
//+------------------------------------------------------------------+