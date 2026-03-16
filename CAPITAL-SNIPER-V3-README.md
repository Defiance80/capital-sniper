# Capital Sniper v3.0 - Python EA for MetaTrader 5

## Overview

Capital Sniper v3.0 is a complete Python rewrite of the Capital Sniper strategy, fixing all known bugs from the previous MQ5 version and integrating advanced SMC/ICT concepts for enhanced profitability. This EA runs as an external Python script that connects to MetaTrader 5 via the official MetaTrader5 Python package.

### Key Features

- **Multi-Symbol Trading**: EURUSD, GBPUSD, USDJPY, USDCAD, AUDUSD, NZDUSD, USDCHF, EURJPY, GBPJPY, XAUUSD
- **Dual Pattern Detection**: Fair Value Gaps (FVG) + Order Block entries
- **SMC/ICT Integration**: HTF bias engine, premium/discount zones, liquidity sweep detection
- **Advanced Trade Management**: Multi-stage profit taking, trailing stops, winner protection
- **Robust Risk Management**: Dynamic position sizing, drawdown limits, consecutive loss protection
- **Enhanced Session Management**: Widened trading windows for more opportunities
- **Production-Ready**: Comprehensive logging, error handling, graceful shutdown

## Installation & Setup

### 1. Install Required Dependencies

```bash
pip install MetaTrader5 pandas numpy
```

### 2. MetaTrader 5 Setup

1. **Install MetaTrader 5** from MetaQuotes website
2. **Enable Algo Trading**: 
   - Tools → Options → Expert Advisors
   - Check "Allow algorithmic trading"
   - Check "Allow DLL imports"
3. **Add Python to PATH** (if not already done)
4. **Verify MT5 Python package**:
   ```python
   import MetaTrader5 as mt5
   print(mt5.__version__)
   ```

### 3. Terminal Configuration

1. **Symbol Setup**: Ensure all traded symbols are available in Market Watch
2. **Account Settings**: Use a demo or live account with sufficient balance
3. **Time Zone**: Ensure MT5 terminal uses your broker's server time
4. **Internet Connection**: Stable connection required for live trading

## How to Run

### Basic Execution
```bash
python capital_sniper_v3.py
```

### Background Execution (Linux/Mac)
```bash
nohup python capital_sniper_v3.py > sniper.log 2>&1 &
```

### Windows Service (Advanced)
Consider using tools like NSSM to run as Windows service for VPS deployment.

## Configuration Parameters

All parameters are configured in the `CONFIG` dictionary at the top of the script. Here's a detailed explanation:

### Risk Management (`CONFIG['RISK']`)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `risk_percent` | 0.75 | Risk per trade as % of equity (0.5-1.0 range) |
| `max_daily_drawdown` | 3.0 | Daily drawdown halt % (prop firm safe) |
| `max_weekly_drawdown` | 6.0 | Weekly drawdown halt % |
| `max_positions_total` | 6 | Maximum total open positions across all symbols |
| `max_positions_per_symbol` | 3 | Maximum positions per symbol |
| `max_sessions_per_symbol` | 3 | Maximum trades per session per symbol |
| `consecutive_loss_limit` | 2 | Pause trading after N consecutive losses |
| `consecutive_loss_pause_hours` | 1 | Hours to pause after consecutive losses |

### Strategy Parameters (`CONFIG['STRATEGY']`)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `fvg_deviation_pips` | 5 | FVG detection threshold (reduced for more opportunities) |
| `exhaustion_threshold_forex` | 20 | Exhaustion filter for forex pairs (pips) |
| `exhaustion_threshold_gold` | 30 | Larger threshold for XAUUSD volatility |
| `wyckoff_confirmation` | False | Optional Wyckoff filter (default OFF for looser entries) |
| `wyckoff_lookback` | 3 | Wyckoff confirmation lookback bars |
| `stack_count` | 2 | Number of stacked orders per signal |
| `stack_offset_points` | 2 | Points offset between stacked orders |
| `sl_buffer_pips` | 2 | Stop loss buffer in pips |
| `min_rr_ratio` | 2.0 | Minimum risk:reward ratio (loosened from 2.5) |
| `displacement_confirmation` | False | Optional displacement filter (default OFF) |
| `displacement_atr_mult` | 1.2 | Candle body >= 1.2x ATR for displacement |
| `market_order_fallback_bars` | 10 | Market order fallback after X bars |

### SMC/ICT Integration (`CONFIG['SMC']`)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `enable_htf_bias` | True | Enable higher timeframe bias engine |
| `htf_timeframe` | H1 | Higher timeframe for bias determination |
| `ltf_timeframe` | M5 | Lower timeframe for execution |
| `enable_premium_discount` | True | Enable premium/discount zone filter |
| `enable_liquidity_sweep` | True | Enable liquidity sweep detection |
| `atr_period` | 14 | ATR period for calculations |
| `structure_lookback` | 20 | Lookback period for swing highs/lows |

### Trading Sessions (`CONFIG['SESSIONS']`)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `london_start` | 7 | London session start (07:00) |
| `london_end` | 16 | London session end (16:00) |
| `ny_start` | 12 | New York session start (12:00) |
| `ny_end` | 21 | New York session end (21:00) |
| `gold_session_start` | 12 | XAUUSD optimal session start |
| `gold_session_end` | 16 | XAUUSD optimal session end |

**Note**: Sessions are widened compared to v2 for more trading opportunities.

### Symbol Settings (`CONFIG['SYMBOLS']`)

Each symbol has specific spread limits and point multipliers:

| Symbol | Max Spread | Point Multiplier | Notes |
|--------|------------|------------------|-------|
| EURUSD | 1.5 pips | 10000 | Major pair |
| GBPUSD | 2.0 pips | 10000 | Major pair |
| USDJPY | 1.5 pips | 100 | JPY pair |
| USDCAD | 2.0 pips | 10000 | Major pair |
| AUDUSD | 2.0 pips | 10000 | Commodity currency |
| NZDUSD | 2.5 pips | 10000 | Commodity currency |
| USDCHF | 2.0 pips | 10000 | Safe haven pair |
| EURJPY | 2.5 pips | 100 | Cross pair |
| GBPJPY | 3.0 pips | 100 | Volatile cross |
| XAUUSD | 0.5 pips | 100 | Gold (special handling) |

### Trade Management (`CONFIG['TRADE_MGMT']`)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `breakeven_trigger_r` | 1.0 | Move to breakeven at +1R |
| `partial_close_1_r` | 2.0 | First partial close at 2R |
| `partial_close_1_pct` | 0.3 | Close 30% at TP1 |
| `partial_close_2_r` | 3.0 | Second partial close at 3R |
| `partial_close_2_pct` | 0.3 | Close 30% at TP2 |
| `trailing_start_r` | 2.0 | Start trailing at 2R |
| `trailing_atr_mult` | 1.5 | ATR multiplier for trailing distance |
| `winner_protection_trigger` | 1.5 | Protect winners if they fall from +1.5R |
| `winner_protection_exit` | 0.5 | Exit level when protecting winners |
| `tp1_target_r` | 2.0 | TP1 target in R multiples |
| `tp2_target_r` | 3.0 | TP2 target in R multiples |
| `tp3_target_r` | 5.0 | TP3 target for runners |

## Strategy Logic Summary

### Entry Conditions

1. **Market Structure Analysis**:
   - HTF bias determination using H1 BOS/CHoCH patterns
   - Premium/discount zone identification
   - Liquidity sweep detection

2. **Pattern Detection**:
   - **FVG (Fair Value Gaps)**: 3-candle inefficiencies on M5
   - **Order Blocks**: Displacement candle origins with volume confirmation

3. **Filter Application**:
   - Optional Wyckoff confirmation (default OFF for looser entries)
   - Exhaustion filter (20 pips forex, 30 pips gold)
   - SMC premium/discount filter (longs in discount, shorts in premium)
   - Optional displacement confirmation (1.2x ATR candle body)
   - Minimum R:R ratio (2.0 minimum)

4. **Order Placement**:
   - Stacked limit orders (2 orders with 2-point offset)
   - Dynamic position sizing based on risk percentage
   - Market order fallback after 10 bars if limits not filled

### Trade Management Stages

1. **Stage 1 - Breakeven** (+1R):
   - Move SL to entry + spread buffer
   - Protects capital once trade shows profit

2. **Stage 2 - First Partial** (+2R):
   - Close 30% of position
   - Locks in initial profits

3. **Stage 3 - Second Partial** (+3R):
   - Close another 30% of position
   - Secures substantial gains

4. **Stage 4 - Trailing** (+2R onwards):
   - ATR-based trailing stop (1.5x ATR behind price)
   - Lets winners run while protecting profits

5. **Winner Protection**:
   - If trade reaches +1.5R but falls back to +0.5R
   - Close at small profit to prevent winners becoming losers

## Risk Management Rules

### Position Sizing
- Dynamic calculation based on risk percentage (default 0.75%)
- Uses actual SL distance and symbol tick value
- Respects broker's minimum/maximum lot sizes

### Drawdown Protection
- **Daily Limit**: 3% drawdown halts all trading until next session
- **Weekly Limit**: 6% drawdown halts all trading until next week
- **Consecutive Losses**: Pause 1 hour after 2 consecutive losses

### Position Limits
- Maximum 6 total positions across all symbols
- Maximum 3 positions per symbol
- Maximum 3 trades per session per symbol

### Session Management
- London: 07:00-16:00 (widened from 08:00-15:59)
- New York: 12:00-21:00 (widened from 13:00-20:59)
- Overlap: 12:00-16:00 (counts for both sessions)
- Gold: Mainly during overlap for reduced volatility

## Logging and Monitoring

### Log Levels
- **INFO**: Normal operations, trades, session resets
- **WARNING**: Risk limit hits, failed orders, spread issues
- **ERROR**: System errors, connection problems, critical failures
- **DEBUG**: Detailed trade management actions

### Log Locations
- **Console Output**: Real-time monitoring
- **File Output**: `logs/capital_sniper_YYYYMMDD.log`
- **Trade History**: All order placement and modifications logged

### Key Metrics to Monitor
- Daily/weekly P&L vs. drawdown limits
- Win rate and average R per trade
- Number of trades per session per symbol
- Spread conditions and order fill rates
- System uptime and connection stability

## Troubleshooting

### Common Issues

1. **"MT5 initialization failed"**:
   - Check MetaTrader 5 is running
   - Verify algorithmic trading is enabled
   - Ensure account is connected and logged in

2. **"Symbol not found" warnings**:
   - Add missing symbols to Market Watch
   - Check symbol names match your broker's naming convention
   - Verify symbol availability in your account type

3. **"Invalid position size" errors**:
   - Check account balance vs. minimum lot sizes
   - Verify broker's margin requirements
   - Ensure risk percentage isn't too low for small accounts

4. **Trades not executing**:
   - Verify spread conditions
   - Check session times vs. broker's server time
   - Confirm risk limits aren't active
   - Check position limits aren't exceeded

5. **Connection issues**:
   - Stable internet connection required
   - Check firewall settings for MT5 and Python
   - Monitor broker's server status

### Performance Optimization

1. **VPS Deployment**:
   - Use Windows VPS near broker's server location
   - Ensure adequate RAM (4GB+ recommended)
   - Set up automatic startup and monitoring

2. **Parameter Tuning**:
   - Start with default settings
   - Adjust risk percentage based on account size
   - Fine-tune session times for your broker
   - Modify spread limits based on market conditions

3. **Monitoring Setup**:
   - Set up log rotation to prevent disk space issues
   - Monitor system resources (CPU, RAM, disk)
   - Implement external monitoring for uptime

## Important Notes

### Risk Warning
- **Trading involves substantial risk of loss**
- **Past performance does not guarantee future results**
- **Only trade with capital you can afford to lose**
- **Test thoroughly on demo accounts before live trading**

### Broker Compatibility
- Designed for ECN/STP brokers with low spreads
- May require adjustments for market maker brokers
- Test order execution quality before live deployment
- Verify commission structures align with strategy assumptions

### Market Conditions
- Strategy performs best in trending markets
- May underperform in extremely low volatility periods
- Adapts to normal market hours; avoid major news events
- Gold trading optimized for London-NY overlap

### Maintenance
- Monitor logs daily for errors or warnings
- Keep MT5 and Python packages updated
- Review and adjust parameters monthly
- Back up configuration and log files regularly

## Support and Updates

### Version History
- **v3.0**: Complete Python rewrite with SMC/ICT integration
- **v2.0**: MQ5 version with bug fixes (deprecated)
- **v1.x**: Original MQ5 versions (deprecated)

### Future Enhancements
- Multi-timeframe confirmation signals
- Machine learning pattern recognition
- Advanced market regime detection
- Portfolio optimization across symbols

### Contact
Built by OpenClaw AI Assistant for Capital Sniper trading strategy.

---

**Disclaimer**: This software is provided for educational and research purposes. The authors are not responsible for any financial losses incurred through the use of this software. Always test thoroughly and trade responsibly.