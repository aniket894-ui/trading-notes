# v13b: VAH/VAL rejection with your full rules

Run Nov 18, 2026 on branch `claude/mgc-vah-rejection-backtest`. Code: `backtest/v13b.py`. CSVs: `claude/v13b/`.

## Voice summary

This is version 13 rerun with the rest of your rules. Stops between 2 and 15 points, 300 dollars risk, at least 3 lots and at most 5, real costs, five exit styles, and each one with and without the loss protection.

The best result was shorts between 3 and 11 in the morning. Taking everything off at 2R with the protection on made plus 4,845 dollars on 39 trades. It won about half of them, and the worst drawdown was 1,050 dollars. Trailing the last lot behind the 1-hour lower highs made a bit more, plus 5,086 dollars on 33 trades, with a 1,306 dollar drawdown.

London only, 3 to 5 in the morning, had the best win rate at 62 percent, but only 14 to 16 trades, so it's unproven.

Shorts at any time of day barely made money. Longs lost almost everywhere. Gold was falling the whole time, so that doesn't prove longs fail.

The protection cut the drawdowns roughly in half when trading all day. In the morning window it also helped profit, but over the whole day it cut profit too.

The third touch of a level was the best for shorts: plus 3,454 dollars on 32 trades. First and fourth touches lost.

This is only about two and a half months of data, and the news-time block couldn't be applied because I don't have verified news times. Anything under 30 trades is unproven. Not financial advice.

## What's applied and what isn't

| Rule | Status |
|---|---|
| Skip if stop under 2 or over 15 points | Applied. With a 3-lot minimum at $300 risk, stops over 10 points are already skipped, so in practice stops ran 2.2 to 9.9 points. |
| $300 risk, lots = floor(300 ÷ (stop × $10)), max 5, skip under 3 | Applied |
| $1.50 per contract round trip, 1 tick slippage on entry and stops | Applied. No slippage on targets or time exits, since your spec names entry and stops only. |
| E1–E5 exits | Applied (details below) |
| Max 2 trades/day, stop after 2 losses or win-then-loss | Applied with protection ON. Win-then-loss can never block an extra trade under a 2-trade cap. |
| $150 risk after 3 losing days until a winning day | Applied with protection ON. The 3-lot minimum still holds, so at $150 only stops of 5 points or less qualify. |
| Weekly loss cap $900 | Applied with protection ON |
| **No entries 30 min around CPI, NFP, FOMC** | **NOT applied.** I have no verified event times (TradingView's calendar was blocked by today's call limit). Add `data/news_events.csv` with a `datetime_et` column, rerun, and it applies. |
| Never add to a losing trade | Applied with protection ON: one trade at a time. A new trade only once the open one is closed or risk-free. For E5, whose runner keeps its original stop, that means fully closed. |

**Data:** the same real candles as v13. 15m covers Aug 31 to Nov 13, 2026, with signals from Sep 1, so about 2.5 months, not 12. 1H covers Jan 12 to Nov 13 and is used for the 4H/daily trend and the swings. Gold mostly fell over this stretch.

## Assumptions

1. **Entries are v13's, unchanged.**
   - **Trigger:** a 15m candle wicks into or past the level, closes back inside with a bearish close (bullish for longs), and the candle before it was inside.
   - **Levels:** prior day/week VAH (VAL for longs) on any test, or any other level type on its 2nd test or later.
   - **One trade per test.** A signal skipped by the stop or size rules doesn't use up its test, so a later candle in the same test can still trigger.
2. **Entry and stop:** entry = trigger close minus 1 tick (plus 1 tick for longs). Stop = wick + 0.5 point. Stop size is measured from the entry fill.
3. **Exits:** 2 lots at 2R, and the rest (1–3 lots) is the runner. If the 2R target isn't hit by 5 PM, everything closes at the 16:45 bar close on entry day.
   - **E2:** the runner targets the nearest of PD VAL, PW VAL, PD low, 1H swing low or 4H swing low beyond 2R (the VAH/high side for longs). If there's none, it closes at 5 PM.
   - **E3:** the runner targets the nearest PD/PW VAL beyond 2R (VAH for longs). It holds up to the end of the 3rd trading day (entry day + 2), but is flat at the last bar ending before 4:55 PM on Friday.
   - **E4:** as E3, but once past 2R the stop trails 1 tick beyond each new 1H lower high (higher low for longs). A lower high here is a 1-bar pivot high that's below the prior 24 hours' high, usable once the next 1H bar closes.
   - **E5:** as E3, but the runner keeps the original stop.
   - **Runner stop:** goes to break-even after 2R in E2, E3 and E4, then trails in E4. If a bar hits a stop and a target, the stop counts.
4. **Protection OFF:** every signal is taken and trades can overlap, as in v13. **Protection ON:** the five rules above, with P&L counted on the entry day. **Shorts and longs are separate accounts.**
5. **Sessions** by trigger candle time: Asia 18:00–03:00, London 03:00–08:00, NY 08:00–16:00. Windows and trend filters are as in v13.
6. **Win %** = trades with net $ above 0, after fees. **Max drawdown** = worst fall in cumulative closed P&L, in entry order. ⚠ = under 30 trades, unproven.

## Results

### 1. Every exit, with and without drawdown protection (no trend filter)


#### Shorts

| Window | Exit | Protection | Trades | Win % | Net $ | Profit factor | Max drawdown | Longest losing streak |
|---|---|---|--:|--:|--:|--:|--:|--:|
| London 03-05 | E1 | OFF | 16 ⚠ | 62% | +$3,373 | 3.23 | −$801 | 3 |
|  | E1 | ON | 14 ⚠ | 64% | +$2,942 | 3.26 | −$1,020 | 3 |
|  | E2 | OFF | 16 ⚠ | 62% | +$1,635 | 2.08 | −$974 | 3 |
|  | E2 | ON | 14 ⚠ | 64% | +$1,628 | 2.25 | −$1,166 | 3 |
|  | E3 | OFF | 16 ⚠ | 62% | +$1,689 | 2.12 | −$974 | 3 |
|  | E3 | ON | 14 ⚠ | 64% | +$1,682 | 2.29 | −$1,166 | 3 |
|  | E4 | OFF | 16 ⚠ | 62% | +$1,689 | 2.12 | −$974 | 3 |
|  | E4 | ON | 14 ⚠ | 64% | +$1,682 | 2.29 | −$1,166 | 3 |
|  | E5 | OFF | 16 ⚠ | 62% | +$1,139 | 1.75 | −$1,402 | 3 |
|  | E5 | ON | 14 ⚠ | 64% | +$1,342 | 2.03 | −$1,238 | 3 |
| 03-11 | E1 | OFF | 50 | 46% | +$4,696 | 1.69 | −$1,298 | 3 |
|  | E1 | ON | 39 | 51% | +$4,845 | 2.00 | −$1,050 | 3 |
|  | E2 | OFF | 50 | 46% | +$3,163 | 1.46 | −$1,819 | 3 |
|  | E2 | ON | 33 | 52% | +$3,324 | 1.89 | −$1,306 | 3 |
|  | E3 | OFF | 50 | 46% | +$3,818 | 1.56 | −$2,047 | 3 |
|  | E3 | ON | 33 | 52% | +$3,480 | 1.93 | −$1,306 | 3 |
|  | E4 | OFF | 50 | 46% | +$5,433 | 1.79 | −$2,037 | 3 |
|  | E4 | ON | 33 | 52% | +$5,086 | 2.37 | −$1,306 | 3 |
|  | E5 | OFF | 50 | 46% | +$3,597 | 1.53 | −$1,996 | 3 |
|  | E5 | ON | 33 | 52% | +$2,272 | 1.60 | −$1,744 | 3 |
| Any 18-16 | E1 | OFF | 149 | 36% | +$2,288 | 1.10 | −$5,095 | 10 |
|  | E1 | ON | 69 | 36% | +$526 | 1.05 | −$2,228 | 8 |
|  | E2 | OFF | 149 | 36% | −$554 | 0.98 | −$6,040 | 10 |
|  | E2 | ON | 61 | 33% | −$1,976 | 0.81 | −$2,316 | 8 |
|  | E3 | OFF | 149 | 36% | +$475 | 1.02 | −$7,804 | 10 |
|  | E3 | ON | 61 | 33% | −$1,068 | 0.89 | −$2,503 | 8 |
|  | E4 | OFF | 149 | 36% | +$2,054 | 1.09 | −$6,268 | 10 |
|  | E4 | ON | 61 | 33% | −$1,462 | 0.86 | −$2,419 | 8 |
|  | E5 | OFF | 149 | 36% | +$1,628 | 1.07 | −$8,684 | 10 |
|  | E5 | ON | 58 | 29% | −$2,008 | 0.79 | −$2,474 | 8 |

#### Longs

| Window | Exit | Protection | Trades | Win % | Net $ | Profit factor | Max drawdown | Longest losing streak |
|---|---|---|--:|--:|--:|--:|--:|--:|
| London 03-05 | E1 | OFF | 16 ⚠ | 38% | −$446 | 0.83 | −$1,262 | 4 |
|  | E1 | ON | 15 ⚠ | 33% | −$804 | 0.68 | −$1,620 | 4 |
|  | E2 | OFF | 16 ⚠ | 38% | −$890 | 0.65 | −$1,330 | 4 |
|  | E2 | ON | 14 ⚠ | 29% | −$1,676 | 0.34 | −$1,810 | 4 |
|  | E3 | OFF | 16 ⚠ | 38% | −$792 | 0.69 | −$1,232 | 4 |
|  | E3 | ON | 14 ⚠ | 29% | −$1,577 | 0.38 | −$1,710 | 4 |
|  | E4 | OFF | 16 ⚠ | 38% | −$702 | 0.73 | −$1,232 | 4 |
|  | E4 | ON | 14 ⚠ | 29% | −$1,577 | 0.38 | −$1,710 | 4 |
|  | E5 | OFF | 16 ⚠ | 38% | −$384 | 0.85 | −$884 | 4 |
|  | E5 | ON | 14 ⚠ | 36% | −$541 | 0.76 | −$1,113 | 4 |
| 03-11 | E1 | OFF | 60 | 27% | −$4,218 | 0.62 | −$5,771 | 7 |
|  | E1 | ON | 38 | 26% | −$2,360 | 0.61 | −$3,914 | 10 |
|  | E2 | OFF | 60 | 27% | −$6,095 | 0.45 | −$7,164 | 7 |
|  | E2 | ON | 37 | 27% | −$2,694 | 0.54 | −$3,762 | 10 |
|  | E3 | OFF | 60 | 27% | −$6,284 | 0.43 | −$7,065 | 7 |
|  | E3 | ON | 37 | 27% | −$2,882 | 0.50 | −$3,664 | 10 |
|  | E4 | OFF | 60 | 27% | −$5,764 | 0.48 | −$7,024 | 7 |
|  | E4 | ON | 37 | 27% | −$2,404 | 0.59 | −$3,664 | 10 |
|  | E5 | OFF | 60 | 27% | −$6,885 | 0.38 | −$7,264 | 7 |
|  | E5 | ON | 34 | 24% | −$3,888 | 0.27 | −$3,914 | 10 |
| Any 18-16 | E1 | OFF | 154 | 23% | −$14,324 | 0.52 | −$14,324 | 12 |
|  | E1 | ON | 59 | 15% | −$7,474 | 0.28 | −$7,474 | 11 |
|  | E2 | OFF | 154 | 23% | −$15,843 | 0.46 | −$15,843 | 12 |
|  | E2 | ON | 58 | 16% | −$7,177 | 0.27 | −$7,177 | 10 |
|  | E3 | OFF | 154 | 23% | −$15,109 | 0.49 | −$15,109 | 12 |
|  | E3 | ON | 58 | 16% | −$7,742 | 0.22 | −$7,742 | 10 |
|  | E4 | OFF | 154 | 23% | −$15,429 | 0.48 | −$15,429 | 12 |
|  | E4 | ON | 58 | 16% | −$7,616 | 0.23 | −$7,616 | 10 |
|  | E5 | OFF | 154 | 23% | −$15,585 | 0.47 | −$15,585 | 12 |
|  | E5 | ON | 58 | 17% | −$8,166 | 0.16 | −$8,166 | 10 |


### 2. Trend filters (E1 all out at 2R)

| Side | Trend | Window | Trades (off) | Win % (off) | Net $ (off) | PF (off) | Max DD (off) | Trades (on) | Net $ (on) | PF (on) | Max DD (on) |
|---|---|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| Short | none | London 03-05 | 16 ⚠ | 62% | +$3,373 | 3.23 | −$801 | 14 ⚠ | +$2,942 | 3.26 | −$1,020 |
| Short | none | 03-11 | 50 | 46% | +$4,696 | 1.69 | −$1,298 | 39 | +$4,845 | 2.00 | −$1,050 |
| Short | none | Any 18-16 | 149 | 36% | +$2,288 | 1.10 | −$5,095 | 69 | +$526 | 1.05 | −$2,228 |
| Short | 4H EMA20 | London 03-05 | 10 ⚠ | 60% | +$2,138 | 3.10 | −$564 | 9 ⚠ | +$2,351 | 3.92 | −$564 |
| Short | 4H EMA20 | 03-11 | 37 | 40% | +$2,212 | 1.39 | −$1,521 | 26 ⚠ | +$2,016 | 1.57 | −$1,700 |
| Short | 4H EMA20 | Any 18-16 | 105 | 35% | +$756 | 1.05 | −$4,411 | 56 | +$256 | 1.03 | −$4,314 |
| Short | Daily EMA20 | London 03-05 | 15 ⚠ | 60% | +$2,850 | 2.88 | −$801 | 13 ⚠ | +$2,420 | 2.86 | −$1,020 |
| Short | Daily EMA20 | 03-11 | 48 | 44% | +$3,704 | 1.54 | −$1,298 | 37 | +$3,853 | 1.79 | −$1,050 |
| Short | Daily EMA20 | Any 18-16 | 141 | 36% | +$978 | 1.04 | −$5,095 | 65 | −$436 | 0.96 | −$3,134 |
| Long | none | London 03-05 | 16 ⚠ | 38% | −$446 | 0.83 | −$1,262 | 15 ⚠ | −$804 | 0.68 | −$1,620 |
| Long | none | 03-11 | 60 | 27% | −$4,218 | 0.62 | −$5,771 | 38 | −$2,360 | 0.61 | −$3,914 |
| Long | none | Any 18-16 | 154 | 23% | −$14,324 | 0.52 | −$14,324 | 59 | −$7,474 | 0.28 | −$7,474 |
| Long | 4H EMA20 | London 03-05 | 2 ⚠ | 50% | +$115 | 1.53 | −$218 | 2 ⚠ | +$115 | 1.53 | −$218 |
| Long | 4H EMA20 | 03-11 | 17 ⚠ | 24% | −$1,606 | 0.48 | −$2,286 | 14 ⚠ | −$782 | 0.65 | −$1,462 |
| Long | 4H EMA20 | Any 18-16 | 44 | 18% | −$5,490 | 0.37 | −$5,493 | 24 ⚠ | −$2,473 | 0.39 | −$2,762 |
| Long | Daily EMA20 | London 03-05 | 1 ⚠ | 0% | −$218 | 0.00 | −$218 | 1 ⚠ | −$218 | 0.00 | −$218 |
| Long | Daily EMA20 | 03-11 | 5 ⚠ | 40% | −$58 | 0.91 | −$445 | 4 ⚠ | +$135 | 1.29 | −$252 |
| Long | Daily EMA20 | Any 18-16 | 11 ⚠ | 18% | −$1,352 | 0.31 | −$1,354 | 7 ⚠ | −$1,129 | 0.21 | −$1,132 |


### 3. By level (no trend filter, any time 18–16, protection OFF)

| Side | Level | Trades | Win % (E1) | PF (E1) | Net $ E1 | Net $ E2 | Net $ E3 | Net $ E4 | Net $ E5 |
|---|---|--:|--:|--:|--:|--:|--:|--:|--:|
| Long | 1H swing low | 21 ⚠ | 29% | 0.86 | −$532 | −$190 | +$1,762 | +$698 | +$1,882 |
| Long | Asia high | 12 ⚠ | 17% | 0.41 | −$1,296 | −$1,178 | −$1,178 | −$1,178 | −$1,278 |
| Long | Asia low | 11 ⚠ | 27% | 0.68 | −$616 | −$1,221 | −$1,273 | −$1,273 | −$1,445 |
| Long | PD POC | 17 ⚠ | 18% | 0.29 | −$2,478 | −$2,334 | −$2,235 | −$2,235 | −$2,235 |
| Long | PD VAH | 18 ⚠ | 22% | 0.35 | −$2,394 | −$2,529 | −$3,198 | −$3,198 | −$3,594 |
| Long | PD VAL | 28 ⚠ | 11% | 0.23 | −$4,763 | −$5,500 | −$5,500 | −$5,500 | −$5,865 |
| Long | PD high | 2 ⚠ | 50% | 1.24 | +$57 | −$126 | −$126 | $0 | −$216 |
| Long | PD low | 14 ⚠ | 43% | 1.42 | +$833 | +$420 | +$111 | +$377 | +$299 |
| Long | PW POC | 3 ⚠ | 33% | 0.65 | −$188 | −$406 | −$406 | −$406 | −$514 |
| Long | PW VAH | 8 ⚠ | 12% | 0.35 | −$1,110 | −$729 | −$729 | −$729 | −$729 |
| Long | PW VAL | 12 ⚠ | 25% | 0.58 | −$948 | −$1,188 | −$1,476 | −$1,122 | −$1,736 |
| Long | PW high | 1 ⚠ | 0% | 0.00 | −$242 | −$242 | −$242 | −$242 | −$242 |
| Long | PW low | 7 ⚠ | 29% | 0.54 | −$648 | −$620 | −$620 | −$620 | +$88 |
| Short | 1H swing high | 12 ⚠ | 25% | 0.61 | −$870 | −$1,530 | −$1,668 | −$1,596 | −$1,474 |
| Short | 1H swing low | 1 ⚠ | 0% | 0.00 | −$266 | −$266 | −$266 | −$266 | −$266 |
| Short | Asia high | 7 ⚠ | 29% | 0.56 | −$590 | −$812 | −$812 | −$812 | −$896 |
| Short | Asia low | 10 ⚠ | 60% | 2.25 | +$1,300 | +$1,422 | +$2,178 | +$3,390 | +$1,680 |
| Short | PD POC | 20 ⚠ | 45% | 1.73 | +$1,996 | +$1,727 | +$3,507 | +$2,940 | +$5,594 |
| Short | PD VAH | 24 ⚠ | 29% | 0.93 | −$280 | −$641 | −$1,076 | −$809 | −$1,038 |
| Short | PD VAL | 14 ⚠ | 43% | 1.60 | +$1,124 | −$178 | −$508 | −$508 | −$1,318 |
| Short | PD high | 5 ⚠ | 60% | 2.74 | +$902 | +$456 | +$558 | +$558 | +$519 |
| Short | PD low | 14 ⚠ | 43% | 1.39 | +$740 | +$42 | −$176 | −$50 | −$598 |
| Short | PW POC | 3 ⚠ | 33% | 1.33 | +$128 | +$322 | +$322 | +$322 | +$322 |
| Short | PW VAH | 17 ⚠ | 35% | 0.98 | −$52 | +$796 | +$288 | +$382 | +$1,288 |
| Short | PW VAL | 13 ⚠ | 15% | 0.26 | −$1,997 | −$1,730 | −$2,435 | −$2,060 | −$2,651 |
| Short | PW low | 9 ⚠ | 33% | 1.10 | +$153 | −$165 | +$562 | +$562 | +$465 |


### 4. By touch number (no trend filter, any time 18–16, protection OFF)

| Side | Touch number | Trades | Win % (E1) | PF (E1) | Net $ E1 | Net $ E2 | Net $ E3 | Net $ E4 | Net $ E5 |
|---|---|--:|--:|--:|--:|--:|--:|--:|--:|
| Long | 1 | 14 ⚠ | 14% | 0.29 | −$2,069 | −$2,151 | −$2,439 | −$2,176 | −$2,622 |
| Long | 2 | 57 | 26% | 0.69 | −$3,228 | −$4,273 | −$3,380 | −$3,874 | −$4,466 |
| Long | 3 | 38 | 18% | 0.34 | −$5,021 | −$5,693 | −$4,943 | −$5,298 | −$5,394 |
| Long | 4 | 23 ⚠ | 22% | 0.46 | −$2,524 | −$2,032 | −$2,653 | −$2,428 | −$2,620 |
| Long | 5+ | 22 ⚠ | 27% | 0.64 | −$1,482 | −$1,694 | −$1,694 | −$1,653 | −$483 |
| Short | 1 | 14 ⚠ | 21% | 0.51 | −$1,331 | −$1,446 | −$1,446 | −$1,446 | −$1,005 |
| Short | 2 | 54 | 39% | 1.18 | +$1,482 | −$834 | +$617 | +$1,261 | +$918 |
| Short | 3 | 32 | 47% | 1.89 | +$3,454 | +$3,802 | +$4,614 | +$5,008 | +$4,112 |
| Short | 4 | 17 ⚠ | 18% | 0.52 | −$1,529 | −$1,994 | −$2,132 | −$2,060 | −$1,846 |
| Short | 5+ | 32 | 38% | 1.04 | +$212 | −$82 | −$1,178 | −$710 | −$552 |


### 5. By session (no trend filter, any time 18–16, protection OFF)

| Side | Session | Trades | Win % (E1) | PF (E1) | Net $ E1 | Net $ E2 | Net $ E3 | Net $ E4 | Net $ E5 |
|---|---|--:|--:|--:|--:|--:|--:|--:|--:|
| Long | Asia 18-03 | 48 | 15% | 0.33 | −$6,810 | −$6,203 | −$6,872 | −$6,872 | −$7,334 |
| Long | London 03-08 | 39 | 33% | 0.81 | −$1,188 | −$3,168 | −$3,070 | −$2,812 | −$3,422 |
| Long | NY 08-16 | 67 | 22% | 0.51 | −$6,326 | −$6,472 | −$5,168 | −$5,744 | −$4,830 |
| Short | Asia 18-03 | 52 | 35% | 1.05 | +$458 | +$232 | +$1,448 | +$966 | +$2,892 |
| Short | London 03-08 | 34 | 50% | 2.00 | +$4,124 | +$2,716 | +$4,254 | +$5,466 | +$3,268 |
| Short | NY 08-16 | 63 | 30% | 0.78 | −$2,294 | −$3,502 | −$5,227 | −$4,377 | −$4,531 |


## What it says

- **Shorts 3–11 AM is the one solid slice,** above 30 trades with or without protection:
  - **E1:** +$4,845, profit factor 2.00, max drawdown −$1,050 (39 trades, protection ON).
  - **E4:** +$5,086, profit factor 2.37, max drawdown −$1,306 (33 trades, protection ON).
  - E4 wins mostly through a few long runners, e.g. the Sep 10 short made +$1,480 under E4 vs +$268 under E3.
- **London shorts (3–5 AM) had the best win rate and profit factor** (62%, 3.2 on E1), but on 14–16 trades. That's unproven, and there E1 beat every runner exit.
- **Shorts all day were barely positive** without protection (+$2,288, profit factor 1.10, drawdown −$5,095). With protection the drawdown fell to −$2,228, but profit fell to +$526, and every runner exit went negative.
- **Protection mostly helps the drawdown.** In the morning windows it also raised the profit factor. Over the whole day it cut profit.
- **E1 vs runners:** E1 was best in London. E4 was best in 3–11. E2, E3 and E5 were usually worse than E1, and E5 (runner keeps the original stop) had the worst drawdowns.
- **Trend filters didn't help shorts.** No filter beat both the 4H and daily EMA filters in the 3–11 window.
- **By touch (shorts):** the 3rd touch was best (+$3,454, profit factor 1.89, 32 trades), then the 2nd (+$1,482, 54 trades). 1st and 4th touches lost.
- **By session (shorts):** London made +$4,124 (profit factor 2.00, 34 trades), Asia was about flat (+$458), and NY lost (−$2,294).
- **By level (shorts):**
  - **Best:** PD POC +$1,996 and Asia low +$1,300.
  - **Worst:** PW VAL −$1,997.
  - **The VAH levels the setup was built around were about flat:** PD VAH −$280, PW VAH −$52.
  - Every level has under 30 trades, so none of these are proven.
- **Longs lost in nearly every slice.** Gold fell through this period, so that alone doesn't prove long rejections fail.

Not financial advice. 2.5 months of one falling market, with an approximate volume profile (see the v13 report), and no news filter.
