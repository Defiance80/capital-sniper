# Koala Capital Sniper v2.0

## Overview

**Koala Capital Sniper v2.0** is a completely rewritten automated trading Expert Advisor (EA) that implements a sophisticated Fair Value Gap (FVG) and Wyckoff-based scalping strategy. This version addresses all 10 critical bugs found in the original implementation and introduces significant production-level enhancements.

The strategy operates on **10 major forex and commodity symbols** during **London and New York trading sessions**, utilizing M5 timeframe analysis to identify price inefficiencies (FVG patterns) confirmed by Wyckoff accumulation/distribution signals. The EA features advanced risk management, dynamic position sizing, comprehensive trade management, and robust error handling.

### Key Features

- **Multi-Symbol Trading**: Trades 10 major symbols (EURUSD, GBPUSD, USDJPY, USDCAD, AUDUSD, NZDUSD, USDCHF, EURJPY, GBPJPY, XAUUSD)
- **Session-Based Operation**: Active during London (08:00-15:59) and New York (13:00-20:59) sessions
- **Advanced Entry Logic**: FVG pattern detection with Wyckoff confirmation and exhaustion filter
- **Sophisticated Trade Management**: Break-even, partial closes, and trailing stops with proper stage gating
- **Dynamic Risk Management**: Percentage-based position sizing with daily and peak drawdown protection
- **Production-Ready**: Comprehensive logging, error handling, retry mechanisms, and spread filtering

---

## Original Bugs Found & Fixed

The original MQL5 implementation contained 10 significant bugs that have been completely resolved in v2.0:

| Bug # | Severity | Description | Root Cause | Fix Applied |
|-------|----------|-------------|------------|-------------|
| **1** | **Critical** | Division by zero crash on EA startup | `sessionEquityStart = 0` when EA starts outside session hours, causing `/0` in drawdown calculation | Proper initialization in `OnInit()` with current equity, added zero-check validation |
| **2** | **Critical** | Session reset firing every tick during hours 8 & 13 | Missing static flags in `OnStartOrNewDay()` function | Implemented proper daily reset flags and date checking to ensure once-per-day execution |
| **3** | **Critical** | Incorrect calculations for non-chart symbols | `_Point` variable belongs to attached chart, not traded symbol | Per-symbol point/digits retrieval using `SymbolInfoDouble()` and `SymbolInfoInteger()` |
| **4** | **High** | Unreliable position counting | `CountOpenTrades()` reads stale `POSITION_SYMBOL` without proper selection | Proper position selection with `PositionGetTicket()` before accessing properties |
| **5** | **High** | Partial close failing at minimum lot sizes | `0.01 × 0.25 = 0.0025` rounds to 0.00, causing OrderSend failure | Volume validation against `SYMBOL_VOLUME_MIN` before attempting partial close |
| **6** | **High** | Array buffer overrun in Wyckoff filter | Hardcoded array size 3, but `WyckoffLookback` input can exceed this | Dynamic array sizing using `ArrayResize()` based on user input |
| **7** | **Medium** | Incorrect session trade counting | `RegisterTrade()` increments by 1 regardless of `StackCount` | Fixed to increment by actual number of orders placed (`StackCount`) |
| **8** | **Medium** | Session overlap miscounting | Hours 13-15 only count for London session, NY counter never increments | Fixed overlap logic to increment both session counters during 13-15 hours |
| **9** | **Medium** | Simultaneous trade management triggers | All three management stages (BE, partial, trailing) fire on same tick | Implemented proper `else-if` gating to ensure only one action per tick |
| **10** | **Low** | Dead code and unused variables | `BaseRiskPercent`, `floatingPeak`, unused functions cluttering codebase | Complete code cleanup, implemented dynamic position sizing, functional peak tracking |

---

## Enhancements Added

### Dynamic Position Sizing (`BaseRiskPercent`)
- **What**: Position sizes are now calculated based on a percentage of account equity
- **How**: `lot_size = (equity × risk_percent) ÷ (SL_distance × tick_value)`
- **Benefit**: Consistent risk exposure regardless of account size or SL distance
- **Default**: 0.75% of equity per trade

### Per-Symbol Point/Digits Handling
- **What**: Each symbol uses its own point size and decimal precision
- **How**: `SymbolInfoDouble(symbol, SYMBOL_POINT)` and `SymbolInfoInteger(symbol, SYMBOL_DIGITS)`
- **Benefit**: Accurate calculations for JPY pairs (2/3 digits) vs major pairs (4/5 digits)
- **Impact**: Fixes all SL/TP/pip calculations across different symbol types

### Trailing Drawdown from Equity Peak
- **What**: Tracks highest equity reached and halts trading if drawdown from peak exceeds threshold
- **How**: `floatingPeak` updated every tick, halt triggered if `(peak - current) / peak > threshold`
- **Benefit**: Protects against giving back large unrealized gains
- **Default**: 20% drawdown from peak triggers halt

### Unique Magic Numbers per Symbol
- **What**: Each symbol gets its own magic number to prevent order conflicts
- **How**: `magic = MagicBase + symbol_index` (e.g., 987654 + 0 for EURUSD, 987654 + 1 for GBPUSD)
- **Benefit**: Clean separation of positions, accurate position counting per symbol
- **Range**: 987654-987663 for the 10 traded symbols

### Complete Trade Logging to File
- **What**: All trade actions, errors, and decisions logged to daily files
- **How**: Timestamped entries to `KoalaSniper_YYYY-MM-DD.log` with rotation
- **Benefit**: Full audit trail for analysis, debugging, and compliance
- **Content**: Entry signals, order results, management actions, errors, drawdown events

### Max Spread Filter
- **What**: Prevents entries when spread exceeds configurable threshold
- **How**: Calculates spread in pips per symbol, skips entry if `spread > MaxSpreadPips`
- **Benefit**: Avoids trading during high-cost periods (news, illiquid sessions)
- **Default**: 3.0 pips maximum spread

### OrderSend Retry Logic
- **What**: Automatically retries failed order placements with exponential backoff
- **How**: Up to 3 retry attempts with 500ms delays between attempts
- **Benefit**: Improved order fill rates during network latency or broker delays
- **Logging**: Each retry attempt and final result logged for analysis

### Descriptive Order Comments
- **What**: Each order gets a unique, descriptive comment for identification
- **How**: Format: `KoalaSniper_v2_{SYMBOL}_{DIRECTION}_Stack{N}` (e.g., `KoalaSniper_v2_EURUSD_BUY_Stack1`)
- **Benefit**: Easy identification in trade history, position management, and analysis
- **Usage**: Helps distinguish between multiple strategies and stack levels

### Proper Trade Management Stage Gating
- **What**: Only one management action executes per position per tick
- **How**: `if-elif-elif` structure instead of independent `if` statements
- **Benefit**: Prevents conflicting actions (e.g., partial close + break-even on same tick)
- **Logic**: Trailing stop (25+ pips) → Partial close (30+ pips) → Break-even (15+ pips)

---

## Strategy Logic

### Symbols Traded
| Symbol | Type | Pip Value | Typical Spread | Session Preference |
|--------|------|-----------|----------------|-------------------|
| EURUSD | Major | $10 | 0.1-0.3 | London/NY Overlap |
| GBPUSD | Major | $10 | 0.2-0.5 | London/NY Overlap |
| USDJPY | Major | $9.09 | 0.1-0.3 | NY Session |
| USDCAD | Major | $7.46 | 0.5-1.0 | NY Session |
| AUDUSD | Commodity | $10 | 0.3-0.7 | London Session |
| NZDUSD | Commodity | $10 | 0.4-0.8 | London Session |
| USDCHF | Major | $10.24 | 0.3-0.6 | London Session |
| EURJPY | Cross | $9.09 | 0.3-0.8 | London/NY Overlap |
| GBPJPY | Cross | $9.09 | 0.5-1.2 | London Session |
| XAUUSD | Commodity | $10 | 0.2-0.5 | NY Session |

### Session Logic
| Session | Server Time | Market Overlap | Volatility | Primary Pairs |
|---------|-------------|----------------|------------|---------------|
| **London** | 08:00-15:59 | European open | High | EUR*, GBP*, commodities |
| **NY** | 13:00-20:59 | US open | High | USD*, JPY crosses |
| **Overlap** | 13:00-15:59 | London + NY | Highest | All majors |

- **Session Reset**: Counters reset at 08:00 (London) and 13:00 (NY)
- **Overlap Handling**: Hours 13-15 count for both sessions (fixed bug #8)
- **Max Setups**: 3 setups per symbol per session (independently tracked)

### Entry Conditions

#### 1. Fair Value Gap (FVG) Detection
**Timeframe**: M5 (5-minute bars)  
**Lookback**: 5 closed bars  
**Calculation**: Uses symbol-specific point sizes

**Bearish FVG (SELL Setup)**:
```
Condition: bar[3].high > bar[4].high + FVGDeviationPips
Entry: bar[3].high - FVGDeviationPips (Sell Limit)
Logic: Price left unfilled gap above → expect reversion down
```

**Bullish FVG (BUY Setup)**:
```
Condition: bar[3].low < bar[4].low - FVGDeviationPips  
Entry: bar[3].low + FVGDeviationPips (Buy Limit)
Logic: Price left unfilled gap below → expect reversion up
```

#### 2. Wyckoff Confirmation Filter
**Requirement**: Must confirm BEFORE order placement  
**Lookback**: Configurable (default: 3 bars)

| Signal Type | Condition | Market Psychology |
|-------------|-----------|-------------------|
| **BUY** | `bar[0].low < bar[1].low` | Lower lows = Accumulation/Spring |
| **SELL** | `bar[0].high > bar[1].high` | Higher highs = Distribution/Upthrust |

#### 3. Exhaustion Filter (Rejection)
**Purpose**: Avoid entering after large moves  
**Condition**: Skip setup if most recent bar range >= ExhaustionPips  
**Default**: 20 pips  
**Logic**: Large recent candle indicates momentum exhaustion

### Order Stacking
When valid setup is confirmed:
1. **Primary Order**: Placed at calculated entry price
2. **Secondary Order**: Placed 2 points away from primary
3. **Volume**: Same lot size for both orders (calculated dynamically)
4. **SL/TP**: Identical for both orders

### SL/TP Calculation

| Order Type | Stop Loss | Take Profit |
|------------|-----------|-------------|
| **Buy** | `bar[4].low - SLBufferPips` | `entry + BreakEvenPoints × 2` |
| **Sell** | `bar[4].high + SLBufferPips` | `entry - BreakEvenPoints × 2` |

**Default Values**:
- SLBufferPips: 2 pips
- BreakEvenPoints: 15 points (TP = 30 points)

### Trade Management Stages

#### Stage 1: Break-Even (15+ pips profit)
- **Trigger**: Floating profit >= BreakEvenPoints
- **Action**: Move SL to entry + SLBufferPips
- **Purpose**: Lock in small profit, eliminate risk

#### Stage 2: Partial Close (30+ pips profit)  
- **Trigger**: Floating profit >= BreakEvenPoints × 2
- **Action**: Close 25% of position volume
- **Purpose**: Secure partial profits while letting remainder run

#### Stage 3: Trailing Stop (25+ pips profit)
- **Trigger**: Floating profit >= TrailingStartPips  
- **Action**: Trail SL by TrailingStepPips behind price
- **Purpose**: Protect profits while allowing for further upside

**Important**: Stages use proper else-if gating (fixed bug #9)

---

## Parameters

| Parameter | Default | Range | Description |
|-----------|---------|-------|-------------|
| **RISK MANAGEMENT** |
| `BaseRiskPercent` | 0.75 | 0.1-5.0 | Risk per trade as % of equity |
| `MaxDailyLossPercent` | 30.0 | 5.0-50.0 | Daily drawdown halt threshold |
| `MaxDrawdownFromPeak` | 20.0 | 5.0-50.0 | Trailing drawdown halt threshold |
| `MaxSetupsPerSession` | 3 | 1-10 | Max entries per symbol per session |
| `MaxTradesPerSymbol` | 3 | 1-5 | Max open positions per symbol |
| `MaxSpreadPips` | 3.0 | 0.5-10.0 | Skip entry if spread exceeds this |
| **STRATEGY** |
| `SLBufferPips` | 2 | 1-10 | Stop loss buffer in pips |
| `BreakEvenPoints` | 15 | 5-50 | Break-even trigger in points |
| `PartialClosePct` | 0.25 | 0.1-0.5 | Partial close percentage |
| `TrailingStartPips` | 25 | 10-100 | Trailing stop activation |
| `TrailingStepPips` | 15 | 5-50 | Trailing stop distance |
| `StackCount` | 2 | 1-5 | Number of stacked orders |
| `FVGDeviationPips` | 10 | 5-20 | FVG detection sensitivity |
| `WyckoffLookback` | 3 | 2-10 | Wyckoff confirmation bars |
| `ExhaustionPips` | 20 | 10-50 | Exhaustion filter threshold |
| **SYSTEM** |
| `MagicBase` | 987654 | 100000+ | Base magic number |
| `EnableLogging` | true | true/false | Enable trade logging |
| `OrderRetries` | 3 | 1-10 | Max order retry attempts |

---

## Installation

### MQL5 Version

#### Prerequisites
- MetaTrader 5 terminal (build 3280+)
- Trading account with your broker
- Symbols EURUSD, GBPUSD, USDJPY, USDCAD, AUDUSD, NZDUSD, USDCHF, EURJPY, GBPJPY, XAUUSD available

#### Installation Steps
1. **Download Files**: Obtain `KoalaCapital_Sniper_v2.mq5`
2. **Copy to MT5**: Place in `MetaTrader 5\MQL5\Experts\` folder
3. **Compile**: Open in MetaEditor and compile (F7)
4. **Attach to Chart**: Drag EA to any chart (calculations are symbol-independent)
5. **Configure**: Set input parameters as desired
6. **Enable Auto Trading**: Click "Auto Trading" button in MT5 terminal
7. **Monitor**: Check logs and Experts tab for activity

#### Configuration Tips
- Attach to a major pair chart (e.g., EURUSD) for stability
- Start with conservative risk settings (0.5% BaseRiskPercent)
- Monitor during overlap hours (13-15 GMT) for highest activity
- Check spread conditions during your broker's active hours

### Python Version

#### Prerequisites
- **Python 3.8+** (recommended: Python 3.9 or higher)
- **MetaTrader 5 terminal** installed and running
- **Trading account** connected in MT5
- **pip** package manager

#### Installation Steps

1. **Clone/Download Repository**:
   ```bash
   git clone <repository-url>
   cd capital-sniper
   ```

2. **Install Python Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Ensure MT5 Terminal is Running**:
   - Open MetaTrader 5 terminal
   - Login to your trading account
   - Enable "Tools → Options → Expert Advisors → Allow automated trading"
   - Ensure the traded symbols are available in Market Watch

4. **Configure Parameters** (optional):
   Edit the configuration in `KoalaCapital_Sniper_v2.py`:
   ```python
   config = TradeConfig()
   config.base_risk_percent = 1.0  # 1% risk per trade
   config.max_daily_loss_percent = 25.0  # 25% daily halt
   config.scan_interval_seconds = 5  # Check every 5 seconds
   ```

5. **Run the Bot**:
   ```bash
   python KoalaCapital_Sniper_v2.py
   ```

#### System Requirements
- **Operating System**: Windows 10/11 (required for MT5 integration)
- **RAM**: Minimum 4GB, recommended 8GB+
- **CPU**: Dual-core processor, 2.5GHz+
- **Internet**: Stable connection for real-time trading
- **Storage**: 100MB for logs and data

#### Troubleshooting
- **ImportError**: Ensure MetaTrader5 package is installed: `pip install MetaTrader5`
- **Connection Failed**: Verify MT5 terminal is running and logged in
- **Symbol Error**: Check that all 10 symbols are available in Market Watch
- **Permission Error**: Run terminal as Administrator if file access issues occur

---

## Files

### Core Files
| File | Type | Description |
|------|------|-------------|
| `KoalaCapital_Sniper_v2.mq5` | MQL5 Expert Advisor | Original MetaTrader 5 implementation |
| `KoalaCapital_Sniper_v2.py` | Python Script | Equivalent Python implementation |
| `requirements.txt` | Python Dependencies | Required packages for Python version |
| `README.md` | Documentation | This comprehensive guide |

### Generated Files
| File | Location | Description |
|------|----------|-------------|
| `KoalaSniper_YYYY-MM-DD.log` | `logs/` (Python) or MT5 Files folder | Daily trading logs with timestamped events |
| Position reports | Trade history | Automated trade summaries and statistics |

### Log File Content
The trading logs contain:
- EA initialization and shutdown events
- Session resets and equity baseline updates  
- Entry signal detection and validation results
- Order placement attempts and results (with retry details)
- Trade management actions (break-even, partial close, trailing)
- Drawdown warnings and emergency halt triggers
- Error messages and recovery actions

---

## Changelog

### v2.0 vs v1.0 Changes

#### 🔧 **Critical Bug Fixes**
- **Fixed Division by Zero**: Proper equity initialization prevents crashes
- **Fixed Session Reset Loop**: One-time daily resets instead of every-tick triggers
- **Fixed Symbol Calculations**: Per-symbol point/digit handling for accurate math
- **Fixed Position Counting**: Reliable open trade counts using proper selection

#### 🚀 **Major Enhancements**
- **Dynamic Position Sizing**: Risk-based lot calculation using BaseRiskPercent
- **Advanced Risk Management**: Daily + trailing drawdown protection with proper peak tracking
- **Professional Logging**: Comprehensive file logging with trade audit trails
- **Error Resilience**: Order retry mechanisms and spread filtering

#### 🎯 **Strategy Improvements**  
- **Proper Stage Gating**: Eliminated simultaneous management action conflicts
- **Enhanced Session Logic**: Fixed overlap period handling for both London/NY
- **Volume Validation**: Prevents partial close failures at minimum lot sizes
- **Magic Number System**: Per-symbol magic numbers eliminate position conflicts

#### 🏗️ **Code Quality**
- **Dead Code Removal**: Eliminated unused variables and functions
- **Array Safety**: Dynamic sizing prevents buffer overruns
- **Input Validation**: Parameter range checking and error handling
- **Documentation**: Comprehensive inline comments and docstrings

#### 📊 **Operational Features**
- **Spread Monitoring**: Real-time spread filtering to avoid high-cost entries
- **Trade Identification**: Descriptive order comments for easy tracking
- **Session Analytics**: Detailed setup counting and session performance tracking
- **Platform Portability**: Python version provides cross-platform compatibility

### Breaking Changes from v1.0
- Parameter names updated for clarity (e.g., `Risk_Percent` → `BaseRiskPercent`)
- Magic number range changed to accommodate per-symbol numbering
- Log file format enhanced with more detailed event tracking
- Session reset timing made more strict (once-per-day vs every-tick)

---

## License

Copyright 2025, Koala Capital Sniper AI. All rights reserved.

This software is provided for educational and research purposes. Use in live trading is at your own risk. Past performance does not guarantee future results.

---

## Support & Contact

For technical support, bug reports, or enhancement requests:
- **Documentation**: This README covers most common scenarios
- **Logs**: Check daily log files for detailed error information  
- **Community**: Share experiences and solutions with other users
- **Development**: Contributions and improvements are welcome

---

## Disclaimer

**RISK WARNING**: Trading forex and commodities carries a high level of risk and may not be suitable for all investors. Leverage can work against you as well as for you. Before deciding to trade, carefully consider your investment objectives, experience level, and risk appetite. You could lose some or all of your initial investment; do not invest money you cannot afford to lose.

This Expert Advisor is a tool to assist in trading decisions but does not guarantee profits. Market conditions, broker execution, slippage, and other factors can significantly impact results. Always test thoroughly on demo accounts before live trading.

The developers and distributors of this software accept no responsibility for any losses incurred through its use.