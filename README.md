# Koala Capital – Sniper Strategy Reference

> Compiled for external AI review. Describes the intended trading logic as implemented in `KoalaCapital_Sniper.mq5`. Known bugs are noted inline where relevant.

---

## Overview

A multi-symbol intraday scalping/sniper EA for MT5. It trades 10 forex/commodity symbols during London and New York sessions, entering on Fair Value Gap (FVG) price inefficiencies confirmed by a Wyckoff exhaustion filter, with stacked limit orders, break-even management, partial closes, and a trailing stop.

---

## Symbols Traded

| # | Symbol |
|---|--------|
| 1 | EURUSD |
| 2 | GBPUSD |
| 3 | USDJPY |
| 4 | USDCAD |
| 5 | AUDUSD |
| 6 | NZDUSD |
| 7 | USDCHF |
| 8 | EURJPY |
| 9 | GBPJPY |
| 10 | XAUUSD |

---

## Session Logic

| Session | Hours (Server Time) | Label |
|---------|---------------------|-------|
| London | 08:00 – 15:59 | Session 1 |
| New York | 13:00 – 20:59 | Session 2 |
| Off-hours | All other hours | No trading |

- Session counters reset at the **start** of each session (08:00 and 13:00).
- Each symbol is independently tracked per session.
- Maximum setups per symbol per session: `MaxSetupsPerSession` (default: 3).

> **Known Bug:** The session reset fires every tick during hours 8 and 13, not just once. This bypasses the daily loss halt and trade counters during those hours.

> **Known Bug:** Hours 13–15 are detected as London (Session 1) only. NY session counter never fills during the overlap window.

---

## Entry Conditions

### 1. Fair Value Gap (FVG) Detection
Evaluated on the **M5 timeframe**, looking back 5 closed bars.

**Bearish FVG (SELL setup):**
- `bar[3].high > bar[4].high + FVGDeviationPips`
- Signals price left an unfilled gap above — expect reversion down
- Entry placed as a **Sell Limit** at `bar[3].high - FVGDeviationPips`

**Bullish FVG (BUY setup):**
- `bar[3].low < bar[4].low - FVGDeviationPips`
- Signals price left an unfilled gap below — expect reversion up
- Entry placed as a **Buy Limit** at `bar[3].low + FVGDeviationPips`

`FVGDeviationPips` default: **10 pips**

---

### 2. Wyckoff Confirmation Filter
Evaluated on the **M5 timeframe**, looking back `WyckoffLookback` (default: 3) bars from bar 2.

| Setup | Condition | Interpretation |
|-------|-----------|----------------|
| BUY | `bar[0].low < bar[1].low` | Lower lows confirm accumulation / spring |
| SELL | `bar[0].high > bar[1].high` | Higher highs confirm distribution / upthrust |

Both conditions must be true **before** an order is placed.

> **Known Bug:** Array is hardcoded to size 3. If `WyckoffLookback` is increased beyond 3 via input, a buffer overrun occurs.

---

### 3. Exhaustion Filter (Rejection)
Evaluated on the **M5 timeframe**, most recent 2 closed bars.

- If the most recent bar's range (`high - low`) is **>= ExhaustionPips** (default: 20 pips), the setup is **skipped**.
- Purpose: avoid entering after a candle that has already moved too far — momentum likely spent.

---

### 4. Order Stacking
When a valid setup is found, `StackCount` (default: 2) limit orders are placed at slightly offset entry prices.

| Order # | Offset |
|---------|--------|
| 1st | Entry price (base) |
| 2nd | Entry ± 2 points |

- Each stacked order uses the **same SL and TP**.
- All orders placed as limit orders (pending), not market orders.

> **Known Bug:** `RegisterTrade()` only increments the session counter by 1 per signal regardless of `StackCount`. Actual orders placed = `2 × MaxSetupsPerSession` maximum.

---

## Stop Loss & Take Profit

| Parameter | Calculation |
|-----------|-------------|
| **SL (Sell)** | `bar[4].high + SLBufferPips * _Point` |
| **SL (Buy)** | `bar[4].low - SLBufferPips * _Point` |
| **TP (Sell)** | `entry - BreakEvenPoints × 2 × _Point` |
| **TP (Buy)** | `entry + BreakEvenPoints × 2 × _Point` |

`SLBufferPips` default: **2 pips**
`BreakEvenPoints` default: **15 points** (TP distance = 30 points)

> **Known Bug:** `_Point` used in all calculations is the point size of the chart the EA is attached to, not the individual symbol being traded. Calculations for USDJPY, GBPJPY, XAUUSD etc. will be incorrect unless the EA is attached to those charts individually.

---

## Trade Management (Per Open Position)

All management logic runs every tick via `ManageTrades()`.

### Stage 1 — Break-Even
- **Trigger:** Floating profit in pips >= `BreakEvenPoints` (15)
- **Action:** Move SL to entry + `SLBufferPips` (locks in a small buffer above entry)
- **Condition:** Position must be net profitable (after spread, swap, commission)

### Stage 2 — Partial Close
- **Trigger:** Floating profit in pips >= `BreakEvenPoints × 2` (30)
- **Action:** Close `PartialClosePct` (25%) of current volume
- **Condition:** Position must be net profitable

> **Known Bug:** With minimum lot 0.01 × 0.25 = 0.0025 → rounds to 0.00. Partial close will always fail at minimum lot size.

### Stage 3 — Trailing Stop
- **Trigger:** Floating profit in pips >= `TrailingStartPips` (25)
- **Movement:** Trail by `TrailingStepPips` (15 pips) behind current price
- **Condition:** New SL must be better than existing SL. Position must be net profitable.

> **Note:** All three stages are independent `if` checks. When pips >= 30, all three fire on the same tick. There is no `else if` gating between them.

---

## Net Profitability Check

Before any SL modification or close, the EA checks:

```
net = profit + swap - commission - spreadCost
```

Where `spreadCost = spread_points × _Point × volume`.

Only acts if `net > 0`. This prevents modifying or closing positions that are technically losing once costs are factored in.

---

## Risk & Session Safety

### Per-Symbol Trade Limit
- Max open positions per symbol: `MaxTradesPerSymbol` (default: 3)
- Checked via `CountOpenTrades()` before each new entry

> **Known Bug:** `CountOpenTrades()` reads `POSITION_SYMBOL` without selecting the position first, so it reads stale data from the previously selected position.

### Daily Drawdown Halt
- Baseline equity captured at session open (08:00 / 13:00)
- Drawdown % = `(sessionEquityStart - currentEquity) / sessionEquityStart × 100`
- If drawdown >= `MaxDailyLossPercent` (30%): set `stopAllTrading = true`, close all net-profitable positions

> **Known Bug:** `sessionEquityStart = 0` at EA start. If EA starts outside session open hours, the drawdown formula divides by zero every tick.

> **Known Bug:** `stopAllTrading` flag is reset to `false` on every tick during hours 8 and 13, making the halt ineffective during those hours.

### `floatingPeak` / Trailing Drawdown
- Variable is set at session open and assigned current equity.
- **Never read again.** Trailing drawdown-from-peak protection is not functional.

---

## Position Sizing

- All orders hardcoded to **0.01 lots**.
- `BaseRiskPercent` input (default: 0.75%) is **never used** in any calculation.
- Dynamic risk-based position sizing is not implemented.

---

## Parameters Summary

| Input | Default | Used? |
|-------|---------|-------|
| `BaseRiskPercent` | 0.75% | ❌ Never used |
| `MaxDailyLossPercent` | 30% | ✅ |
| `MaxSetupsPerSession` | 3 | ✅ (bugged) |
| `SLBufferPips` | 2 | ✅ |
| `BreakEvenPoints` | 15 | ✅ |
| `PartialClosePct` | 0.25 | ✅ (bugged) |
| `MaxTradesPerSymbol` | 3 | ✅ (bugged) |
| `TrailingStartPips` | 25 | ✅ |
| `TrailingStepPips` | 15 | ✅ |
| `StackCount` | 2 | ✅ |
| `FVGDeviationPips` | 10 | ✅ |
| `WyckoffLookback` | 3 | ✅ (bugged) |
| `ExhaustionPips` | 20 | ✅ |

---

## Known Bugs Summary (for Reviewer)

| # | Severity | Description |
|---|----------|-------------|
| 1 | Critical | Division by zero on `sessionEquityStart = 0` at EA start |
| 2 | Critical | `OnStartOrNewDay()` fires every tick during reset hours, bypassing daily halt and counters |
| 3 | Critical | `_Point` belongs to attached chart symbol, not the traded symbol |
| 4 | High | `CountOpenTrades()` reads stale `POSITION_SYMBOL` — count is unreliable |
| 5 | High | Partial close volume rounds to 0.00 at minimum lot size |
| 6 | High | `WyckoffLookback` input can exceed hardcoded array size 3 — buffer overrun |
| 7 | Medium | `RegisterTrade()` only counts 1 trade per signal regardless of `StackCount` |
| 8 | Medium | Session overlap hours 13–15 are always London; NY counter is never incremented |
| 9 | Medium | All three management stages fire independently on the same tick |
| 10 | Low | `BaseRiskPercent`, `floatingPeak`, `IsOppositePositionOpen()` are unused dead code |
