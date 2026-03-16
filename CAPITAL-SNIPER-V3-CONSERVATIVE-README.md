# Capital Sniper v3.0 CONSERVATIVE - README

## Overview

This is the **conservative hardened version** of Capital Sniper v3.0, specifically designed around Robert's risk management mandate:

> "Leave out anything that would put my strategy at risk. Close out only in profit. Limit entries that put you in risk. Keep very limited drawdowns."

The conservative version is based on Robert's proven 2023 trading style: **small lots (0.06-0.09), diversified across pairs, both directions, $4-38 individual wins, no martingale, no grid.**

---

## 🔒 **KEY CONSERVATIVE PRINCIPLES**

1. **Profit-Only Exits** - Positions can only close in profit after breakeven is set
2. **Single Position Per Pair** - Maximum 1 position per symbol (like 2023 style)
3. **Ultra-Tight Risk Limits** - 0.50% risk per trade, 2% daily drawdown limit
4. **High Confidence Only** - Minimum 70% confidence threshold for entries
5. **Time-Based Protection** - Automatic position closure to avoid overnight/weekend risk
6. **Anti-Loss Logic** - Prevents new trades when floating P&L is negative

---

## 📊 **CONSERVATIVE PARAMETER CHANGES**

### 1. **TIGHTER RISK CONFIGURATION**

| Parameter | Original | Conservative | Change |
|-----------|----------|--------------|--------|
| `risk_percent` | 0.75% | **0.50%** | ⬇️ 33% reduction |
| `max_daily_drawdown` | 3.0% | **2.0%** | ⬇️ 33% reduction |
| `max_weekly_drawdown` | 6.0% | **4.0%** | ⬇️ 33% reduction |
| `max_positions_total` | 6 | **4** | ⬇️ 33% reduction |
| `max_positions_per_symbol` | 3 | **1** | ⬇️ 67% reduction |
| `max_sessions_per_symbol` | 3 | **2** | ⬇️ 33% reduction |
| `consecutive_loss_pause_hours` | 1 | **2** | ⬆️ 100% increase |

### 2. **STACKING REMOVAL**

| Parameter | Original | Conservative | Change |
|-----------|----------|--------------|--------|
| `stack_count` | 2 | **1** | 🚫 No stacking |
| `stack_offset_points` | 2 | **0** | 🚫 Disabled |

**Result**: Single clean entries only, like Robert's 2023 style.

### 3. **ENTRY FILTERS - TIGHTER NOT LOOSER**

| Parameter | Original | Conservative | Change |
|-----------|----------|--------------|--------|
| `wyckoff_confirmation` | False | **True** | ✅ Enabled |
| `displacement_confirmation` | False | **True** | ✅ Enabled |
| `min_rr_ratio` | 2.0 | **3.0** | ⬆️ 50% increase |
| `fvg_deviation_pips` | 5 | **3** | ⬇️ 40% tighter |
| `min_confidence_threshold` | N/A | **0.7** | 🆕 New filter |

**Result**: Only high-confidence, high-reward setups are taken.

### 4. **PROFIT-ONLY EXIT LOGIC** ⭐ **CRITICAL**

| Parameter | Original | Conservative | Change |
|-----------|----------|--------------|--------|
| `breakeven_trigger_r` | 1.0R | **0.75R** | ⬆️ 25% faster |
| `winner_protection_trigger` | 1.5R | **1.0R** | ⬆️ 50% earlier |
| `winner_protection_exit` | 0.5R | **0.3R** | ⬆️ 40% sooner |
| `partial_close_1_r` | 2.0R | **1.5R** | ⬆️ 25% earlier |
| `partial_close_1_pct` | 30% | **40%** | ⬆️ 33% more profit locked |
| `partial_close_2_r` | 3.0R | **2.5R** | ⬆️ 17% earlier |
| `trailing_atr_mult` | 1.5x | **1.0x** | ⬇️ 33% tighter |

**Key Feature**: After breakeven is set, positions can **ONLY** close in profit. Stop loss is moved above/below entry price + buffer to guarantee profitable exits.

### 5. **TIME-BASED EXIT PROTECTION** 🆕

| Rule | Description |
|------|-------------|
| **4-Hour Profit Rule** | If position is profitable after 4 hours, close it |
| **6-Hour Time Limit** | Close ALL positions after 6 hours regardless |
| **Session End Protection** | Close ALL positions 30min before session end |

**Purpose**: Avoid overnight/weekend risk and lock in profits.

### 6. **ANTI-LOSS LOGIC** 🆕

| Feature | Description |
|---------|-------------|
| **Floating P&L Check** | Block new trades if total floating P&L < 0 |
| **Stop Loss Tightening** | If position drops below -0.5R, tighten SL by 30% |
| **Win Rate Monitor** | Pause trading if win rate drops below 50% (last 10 trades) |

### 7. **TIGHTER SPREAD FILTERS**

| Symbol | Original | Conservative | Change |
|--------|----------|--------------|--------|
| EURUSD | 1.5 pips | **1.0 pips** | ⬇️ 33% tighter |
| GBPUSD | 2.0 pips | **1.0 pips** | ⬇️ 50% tighter |
| USDJPY | 1.5 pips | **1.0 pips** | ⬇️ 33% tighter |
| Crosses | 2.0-3.0 pips | **1.5 pips** | ⬇️ ~40% tighter |
| XAUUSD | 0.5 pips | **3.0 pips** | ⬆️ Realistic for gold |

**Result**: Only trade during optimal spread conditions.

### 8. **CONSERVATIVE SESSION TIMING**

| Session | Original | Conservative | Change |
|---------|----------|--------------|--------|
| London | 07:00-16:00 | **08:00-15:00** | ⬇️ Trimmed edges |
| NY | 12:00-21:00 | **13:00-20:00** | ⬇️ Trimmed edges |
| Gold | 12:00-16:00 | **13:00-16:00** | ⬇️ Overlap only |
| **Warmup Period** | None | **15 minutes** | 🆕 No trading first 15min |
| **Cooldown Period** | None | **30 minutes** | 🆕 No trading last 30min |

**Result**: Avoid early volatility and session transition risks.

### 9. **CLEANUP CHANGES** 🧹

| Removed Feature | Reason |
|-----------------|--------|
| **Market Order Fallback** | Conservative approach: limit orders only |
| **Order Block Detection** | Simplified to FVG only (fewer bad entries) |
| **Stacking Logic** | Single entries only |

**Result**: Simpler, cleaner strategy with fewer risk points.

### 10. **DAILY SUMMARY LOGGING** 🆕

At end of each session, automatically logs:
- Trades taken
- Wins vs losses
- Net P&L
- Max drawdown hit
- Current win rate

---

## 🎯 **EXPECTED TRADING STYLE**

The conservative version should produce trading similar to Robert's 2023 reference:

- **Position Sizes**: 0.05-0.08 lots (based on 0.50% risk)
- **Trade Frequency**: 2-4 trades per session maximum
- **Win Sizes**: $4-$38 per trade (conservative R:R targets)
- **Diversification**: Maximum 1 position per pair
- **Risk Profile**: Ultra-low drawdown, steady profits

---

## ⚡ **PERFORMANCE EXPECTATIONS**

### Conservative Targets:
- **Daily Drawdown**: < 1% (well below 2% limit)
- **Weekly Growth**: 1-3% steady gains
- **Win Rate**: 60-70% (quality over quantity)
- **Max Simultaneous Risk**: 2.0% (4 positions × 0.5% each)

### Risk Protection:
- **Floating P&L Protection**: New trades blocked if underwater
- **Time-Based Exits**: No overnight/weekend exposure
- **Profit-Only Closes**: Guaranteed profitable exits after breakeven
- **Dynamic Stop Tightening**: Reduced losses on failing trades

---

## 🚀 **GETTING STARTED**

### 1. **Account Requirements**
- Minimum balance: $1,000 (for 0.05+ lot sizes)
- Spread-optimized broker (tight spreads essential)
- MetaTrader 5 platform

### 2. **Recommended Settings**
- Start with paper trading to validate conservative approach
- Monitor first week closely for parameter fine-tuning
- Ensure spreads meet the tighter requirements

### 3. **Key Monitoring Points**
- Daily drawdown (should stay well below 2%)
- Win rate (target 60%+)
- Average trade duration (should be < 4 hours mostly)
- Spread conditions during entry attempts

---

## 🔧 **CUSTOMIZATION NOTES**

### Safe to Adjust:
- `risk_percent`: Can go as low as 0.25% for ultra-conservative
- `min_confidence_threshold`: Can increase to 0.8 for even higher quality
- Session timing: Can narrow further if needed

### **DO NOT CHANGE**:
- Profit-only exit logic
- Anti-loss features  
- Time-based protections
- Single position per pair limit

---

## 📋 **CONSERVATIVE CHECKLIST**

Before going live:

- [ ] ✅ Verify broker spreads meet tighter requirements
- [ ] ✅ Confirm account size supports minimum lot sizes
- [ ] ✅ Test on paper trading first
- [ ] ✅ Monitor daily drawdown limits closely
- [ ] ✅ Ensure MT5 connection is stable
- [ ] ✅ Set up proper logging directory
- [ ] ✅ Verify session timing matches your timezone

---

## ⚠️ **CRITICAL SUCCESS FACTORS**

1. **Discipline**: Let the conservative logic work - don't override
2. **Patience**: Fewer trades, higher quality
3. **Monitoring**: Watch daily summaries for performance trends
4. **Spreads**: Ensure broker provides competitive spreads
5. **Risk Management**: The 2% daily limit is HARD - respect it

---

## 📞 **SUPPORT & MODIFICATIONS**

This conservative version is designed to be **stable and low-risk**. Any modifications should maintain the core conservative principles:

- **Profit-focused exits**
- **Minimal drawdown**  
- **High-confidence entries only**
- **Time-based risk protection**

**Remember**: The goal is consistent, low-risk profits - not maximum returns.

---

*Conservative version created by OpenClaw AI Assistant based on Robert's 2023 trading mandates and risk management requirements.*