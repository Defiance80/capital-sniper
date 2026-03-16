# OpenClaw Strategy Spec — Liquidity Sweep → Displacement → FVG/OB Entry (Bi-Directional)

> PURPOSE:
Trade ONLY after liquidity is taken (manipulation), THEN confirm displacement (structure shift), THEN enter on retrace into imbalance (FVG) or order block (OB), with HTF + LTF alignment. Bullish and bearish logic are perfect inverses.

---

## 0) GLOBAL SAFETY + EXECUTION RULES (NON-NEGOTIABLE)

- Allowed platforms: MT4/MT5 execution ONLY (no web browsing, no external actions).
- Trade only if spread <= MAX_SPREAD and slippage <= MAX_SLIPPAGE.
- Risk per trade: RISK_PCT = 0.50% to 1.00% of equity.
- Max trades per session: MAX_TRADES_SESSION = 3
- Stop trading conditions:
  - If daily drawdown >= DAILY_DD_MAX (2%–3%) => HALT until next day
  - If weekly drawdown >= WEEKLY_DD_MAX (6%–8%) => HALT until next week
  - If consecutive losses >= 2 => PAUSE until next session
- Minimum reward:risk required: MIN_RR = 2.5
- News filter (if enabled via internal calendar feed):
  - No new entries 10 minutes before/after high-impact news affecting traded symbol.

---

## 1) TIMEFRAME SETUP

- HTF (bias): H1 or H4 (choose one; default H1)
- LTF (execution): M5 or M15 (choose one; default M15)
- Optional micro refinement TF: M1 (only for entry precision if enabled)

---

## 2) DEFINITIONS (MUST APPLY CONSISTENTLY)

### 2.1 Swing Points
- Swing High: a candle high preceded and followed by lower highs (fractals).
- Swing Low: a candle low preceded and followed by higher lows.

### 2.2 Liquidity Pools
- Buy-side liquidity: equal highs / prior swing high / prior session high
- Sell-side liquidity: equal lows / prior swing low / prior session low

### 2.3 Protected High / Protected Low
- Protected High (bearish): last valid swing high that price FAILED to break after a bearish BOS.
- Protected Low (bullish): last valid swing low that price FAILED to break after a bullish BOS.

### 2.4 BOS / CHoCH (Structure Confirmation)
- BOS bullish: candle CLOSE breaks above prior swing high.
- BOS bearish: candle CLOSE breaks below prior swing low.
- CHoCH bullish: prior bearish structure is broken to the upside (first bullish BOS).
- CHoCH bearish: prior bullish structure is broken to the downside (first bearish BOS).

### 2.5 Displacement (Required)
Displacement is valid ONLY if:
- Candle body >= DISP_BODY_ATR_MULT * ATR(14)  (default 1.2x)
- Candle CLOSE is beyond the broken swing level (structure break)
- Creates an imbalance (FVG) or leaves a clear inefficiency

### 2.6 FVG (Fair Value Gap) / Imbalance
- Bullish FVG: candle1 high < candle3 low (3-candle gap up)
- Bearish FVG: candle1 low > candle3 high (3-candle gap down)
- Entry preference: midpoint (50%) of FVG

### 2.7 Premium / Discount (Range Logic)
- Determine most recent HTF swing range: (swing low -> swing high)
- Equilibrium = 50% of range
- Discount (bullish entries): below 50%
- Premium (bearish entries): above 50%

---

## 3) HTF BIAS ENGINE (MUST CHOOSE ONE SIDE)

### 3.1 Determine HTF Bias = BULLISH if:
- Latest confirmed BOS is bullish OR CHoCH bullish occurred
- And structure is making higher highs/higher lows OR bullish displacement is present

### 3.2 Determine HTF Bias = BEARISH if:
- Latest confirmed BOS is bearish OR CHoCH bearish occurred
- And structure is making lower lows/lower highs OR bearish displacement is present

### 3.3 No Trade Condition
- If HTF bias is unclear / ranging / conflicting => NO TRADES.

---

## 4) SETUP SEQUENCE (ACCUMULATION → MANIPULATION → DISTRIBUTION)

Must wait in this exact order:

1) Identify accumulation range (recent consolidation / equal highs-lows)
2) Wait for liquidity to be taken (sweep)
3) Confirm displacement (structure break with momentum)
4) Mark FVG/OB created by displacement
5) Wait for retrace into FVG/OB in correct premium/discount zone
6) Confirm LTF alignment (micro-structure agrees)
7) Execute trade with defined SL/TP and management rules

---

# 5) BULLISH PLAYBOOK (LONGS)

## 5.1 Preconditions (ALL REQUIRED)
- HTF bias = BULLISH
- Price is in DISCOUNT on HTF range (<= 50%) OR returns to discount after sweep
- Liquidity sweep occurred on LTF/HTF:
  - Took sell-side liquidity (equal lows / prior swing low / session low)
- Displacement confirmation:
  - Bullish displacement candle closes above LTF swing high (BOS/CHoCH)
  - Creates bullish FVG or bullish OB

## 5.2 Entry Rules (Choose highest-quality available)
ENTRY_ZONE priority:
1) 50% of bullish FVG (preferred)
2) Bullish order block at origin of displacement
3) 50% retrace of displacement leg

Entry trigger:
- Price returns into ENTRY_ZONE
- LTF forms higher low OR micro CHoCH bullish (if M1 refinement enabled)

## 5.3 Stop Loss (SL)
Place SL at:
- Below the swept low OR
- Below bullish OB low OR
- Below displacement origin
Rule: SL MUST NOT exceed the HTF protected low (avoid invalidation breach).

## 5.4 Take Profit (TP)
Target buy-side liquidity in this order:
TP1 = nearest internal equal highs / recent swing high
TP2 = external liquidity (prior major swing high / prior day high)
TP3 = measured move extension (optional)

Must satisfy MIN_RR >= 2.5 for initial TP target.

## 5.5 Trade Management
- At +1R: move SL to break-even (or -0.1R to cover spread)
- Partial take (optional): 30%–50% at TP1
- Trail stop using structure (preferred):
  - Trail below newly formed higher lows (LTF)
OR ATR trail:
  - Trail = entry + (profit * TRAIL_LOCK_PCT) with ATR buffer
- If using percentage trail:
  - TRAIL_LOCK_PCT = 15%–20% of open profit (lock profits progressively)

---

# 6) BEARISH PLAYBOOK (SHORTS) — PERFECT INVERSE

## 6.1 Preconditions (ALL REQUIRED)
- HTF bias = BEARISH
- Price is in PREMIUM on HTF range (>= 50%) OR returns to premium after sweep
- Liquidity sweep occurred on LTF/HTF:
  - Took buy-side liquidity (equal highs / prior swing high / session high)
- Displacement confirmation:
  - Bearish displacement candle closes below LTF swing low (BOS/CHoCH)
  - Creates bearish FVG or bearish OB

## 6.2 Entry Rules (Choose highest-quality available)
ENTRY_ZONE priority:
1) 50% of bearish FVG (preferred)
2) Bearish order block at origin of displacement
3) 50% retrace of displacement leg

Entry trigger:
- Price returns into ENTRY_ZONE
- LTF forms lower high OR micro CHoCH bearish (if M1 refinement enabled)

## 6.3 Stop Loss (SL)
Place SL at:
- Above the swept high OR
- Above bearish OB high OR
- Above displacement origin
Rule: SL MUST NOT exceed the HTF protected high (avoid invalidation breach).

## 6.4 Take Profit (TP)
Target sell-side liquidity in this order:
TP1 = nearest internal equal lows / recent swing low
TP2 = external liquidity (prior major swing low / prior day low)
TP3 = measured move extension (optional)

Must satisfy MIN_RR >= 2.5 for initial TP target.

## 6.5 Trade Management
- At +1R: move SL to break-even (or -0.1R to cover spread)
- Partial take (optional): 30%–50% at TP1
- Trail stop using structure (preferred):
  - Trail above newly formed lower highs (LTF)
OR ATR trail:
  - Trail = entry - (profit * TRAIL_LOCK_PCT) with ATR buffer
- If using percentage trail:
  - TRAIL_LOCK_PCT = 15%–20% of open profit (lock profits progressively)

---

## 7) QUALITY FILTERS (TO AVOID CHOP + BAD TRADES)

- Volatility filter:
  - ATR(14) must be >= ATR_MA(20)  (avoid dead markets)
- Range filter:
  - If HTF is inside tight range and no sweep/displacement => NO TRADE
- Overtrading filter:
  - If 3 trades executed in session => STOP
- Spread filter:
  - If spread spikes beyond MAX_SPREAD => NO NEW ENTRY

---

## 8) CONFIG DEFAULTS (EDITABLE)

- HTF = H1
- LTF = M15
- ATR_PERIOD = 14
- DISP_BODY_ATR_MULT = 1.2
- MIN_RR = 2.5
- RISK_PCT = 0.75
- DAILY_DD_MAX = 3.0
- WEEKLY_DD_MAX = 8.0
- MAX_TRADES_SESSION = 3
- TRAIL_LOCK_PCT = 0.15 to 0.20
- MAX_SPREAD = (symbol specific)
- MAX_SLIPPAGE = (symbol specific)

---

## 9) EXECUTION CHECKLIST (MUST PASS ALL)

For LONG:
- HTF bias bullish? YES
- Sweep of sell-side liquidity occurred? YES
- Displacement bullish + BOS/CHoCH? YES
- FVG/OB marked? YES
- Retrace into discount entry zone? YES
- LTF alignment confirms higher low? YES
- RR >= 2.5? YES
=> ENTER LONG

For SHORT:
- HTF bias bearish? YES
- Sweep of buy-side liquidity occurred? YES
- Displacement bearish + BOS/CHoCH? YES
- FVG/OB marked? YES
- Retrace into premium entry zone? YES
- LTF alignment confirms lower high? YES
- RR >= 2.5? YES
=> ENTER SHORT

---

## 10) NOTES / INTENT

- This model is a disciplined liquidity framework:
  - Wait for accumulation
  - Let manipulation reveal intent (liquidity sweep)
  - Demand displacement confirmation
  - Enter on retrace to inefficiency
  - Target liquidity pools
  - Protect capital with strict risk limits
- Bullish and bearish are direct inverses; must apply symmetry.

END.
