# MGC volume-profile rejection backtest (VAH shorts, VAL longs mirrored)

Run Nov 18, 2026 on branch `claude/mgc-vah-rejection-backtest`. Code: `backtest/vah_rejection.py`. Every signal: `claude/vah_rejection/signals.csv`.

## Status: what's missing

1. **Your message was cut off at "Skip if".** No skip rules are applied. Exit, target, risk and daily-limit rules weren't in the message either, so I report results at **1R, 2R and 3R targets** side by side. Dollar figures use your Rulebook sizing as a placeholder (assumptions 14–16). Send the rest and I'll rerun.
2. **No 12 months of data.** TradingView keeps about 5,000 bars per timeframe on your plan, and today its **daily call limit was already used up**, so nothing new could be downloaded. This test uses the candles saved on Nov 14 (real TradingView data, nothing invented):

| File | Covers | Used for |
|---|---|---|
| `data/MGC_15m.csv` | Aug 31 – Nov 13, 2026 (5,000 bars) | Triggers, trade management, volume profiles, Asia range, test counts |
| `data/MGC_1h.csv` | Jan 12 – Nov 13, 2026 (4,999 bars) | Built into 4H, daily and weekly bars; EMAs; swing levels |
| `data/MGC_5m.csv` | Oct 20 – Nov 13, 2026 (5,000 bars) | Checks only (see Validation) |

No 1-minute data was available. **Test period: Sep 1 – Nov 13, 2026, 52 trading days with signals.** That's about 2.5 months, not 12. Gold fell from about 4,500 to 3,900 over this stretch, which favours shorts.

## Assumptions (every one)

**Bars and time**
1. All times America/New_York. Trading day = 18:00 to 17:00, named by the date it ends. Week = Sunday 18:00 to Friday 17:00.
2. 15m bars are TradingView's own. On the 1,666 bars where 5m data overlaps, 15m built from 5m matched them exactly (open, high, low, close and volume).
3. 4H, daily and weekly are built from 1H. 4H blocks start at 18:00: 18–22, 22–02, 02–06, 06–10, 10–14, 14–17 (the last block is 3 hours).

**Levels**
4. **Volume profile is approximate.** There's no tick or volume-at-price data, so each 15m bar's volume is spread evenly across 0.1-point bins from its low to its high. POC = busiest bin. The value area grows from the POC, adding whichever neighbouring bin has more volume, until it holds 70% of volume. Prices are each bin's lower edge.
5. Prior day POC/VAH/VAL/high/low are active for the whole next trading day, but only if the prior day is complete in the data. Prior week levels are active for the whole next week, but only if all 5 days of the prior week are complete, so weekly levels start Sep 14.
6. Asia high/low = 19:00 to 02:00 (28 bars of 15m). It's usable from 02:00 to the end of that trading day.
7. Swing highs/lows = fractals on 1H, 4H and daily: strictly higher (lower) than the 3 bars on each side. A swing becomes usable when the 3rd bar after it closes, and is **retired at the first 1H close beyond it**. Swings formed before Aug 31 are included, but their tests could only be counted from Aug 31 on, so their test numbers may be too low. 13 signals use such levels.

**Tests**
8. **Resistance test:** a 15m bar whose high gets within 1.0 point of the level and closes below it. **Support test:** a low within 1.0 point and a close above. A new test only starts after price has left the 1-point zone, i.e. a bar's high stays more than 1.0 below the level (more than 1.0 above for support). This is how I read "then a close away".
9. Each signal records the test number it belongs to. The trigger candle counts as part of that test.

**Entries (shorts; longs are the mirror image)**
10. The trigger is a 15m candle with **high ≥ level** (wicks into or above it), **close < level**, a **bearish close** (close < open), and **the previous candle closed below the level**, so price traded *up into* it.
11. The level must be the prior day VAH or prior week VAH (any test), or any other level type on its **2nd test or later** ("tested resistance"). Longs: prior day VAL or prior week VAL (any test), or any other level on its 2nd test or later.
12. If one candle triggers on several levels, it's one trade. The level shown is a VAH/VAL if there is one, otherwise the level nearest the wick. All of them are listed in `all_levels`.
13. **One trade per test of a level.** After a trade, that level's same test can't trigger again. Signals are evaluated independently, and overlapping trades are allowed (no daily cap), because the spec says to take every test.

**Exits and money (placeholders, since the spec was cut off)**
14. Entry at the trigger candle's close. Stop 0.5 point above the trigger candle's high (below its low for longs).
15. Results at fixed 1R, 2R and 3R targets. If one bar touches the stop and a target, the stop counts. A trade still open at the end of the trading day (16:45 bar close) closes there.
16. $ at 2R uses $300 risk, lots = floor($300 ÷ (stop pts × $10)), max 5, plus $3 fees per contract round trip. 4 signals had stops over 30 points (under 1 lot): they're in the R totals but count $0.

**Filters and windows**
17. Trend filters compare the trigger candle's close with the 20 EMA of the **last completed** 4H or daily bar. Shorts need the close below it, longs above.
18. Windows: the trigger candle must open and close inside it. London 03:00–05:00; 03:00–11:00; any time 18:00–16:00.

## Results

Win % is the share of signals that reached the target. Total R is the sum of R across signals.


#### Shorts

| Trend filter | Window | Signals | Win % 1R | Total R at 1R | Win % 2R | Total R at 2R | Win % 3R | Total R at 3R | Net $ at 2R | Avg stop pts |
|---|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| none | London 03-05 | 18 | 78% | +10.0 | 61% | +15.0 | 39% | +10.0 | +$3,491 | 6.3 |
| none | 03-11 | 65 | 49% | +0.3 | 38% | +13.9 | 25% | +5.9 | +$3,289 | 8.0 |
| none | Any 18-16 | 181 | 48% | −3.1 | 31% | +6.8 | 20% | −3.4 | +$373 | 7.6 |
| 4H EMA20 | London 03-05 | 12 | 83% | +8.0 | 58% | +9.0 | 42% | +8.0 | +$2,322 | 7.1 |
| 4H EMA20 | 03-11 | 51 | 45% | −3.7 | 33% | +3.9 | 20% | −4.1 | +$1,156 | 8.6 |
| 4H EMA20 | Any 18-16 | 133 | 48% | −0.7 | 29% | −0.8 | 17% | −15.1 | −$1,035 | 8.2 |
| Daily EMA20 | London 03-05 | 17 | 76% | +9.0 | 59% | +13.0 | 35% | +7.0 | +$2,986 | 6.4 |
| Daily EMA20 | 03-11 | 63 | 48% | −1.7 | 36% | +9.9 | 22% | −0.1 | +$2,325 | 8.1 |
| Daily EMA20 | Any 18-16 | 172 | 48% | −3.7 | 30% | +2.2 | 19% | −12.0 | −$815 | 7.7 |

#### Longs

| Trend filter | Window | Signals | Win % 1R | Total R at 1R | Win % 2R | Total R at 2R | Win % 3R | Total R at 3R | Net $ at 2R | Avg stop pts |
|---|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| none | London 03-05 | 17 | 47% | −1.0 | 35% | +1.0 | 24% | −1.0 | −$822 | 5.5 |
| none | 03-11 | 78 | 32% | −27.1 | 23% | −23.1 | 12% | −38.4 | −$7,332 | 7.9 |
| none | Any 18-16 | 196 | 38% | −43.5 | 23% | −44.5 | 14% | −55.6 | −$14,472 | 7.9 |
| 4H EMA20 | London 03-05 | 2 | 50% | +0.0 | 50% | +1.0 | 0% | −2.0 | +$100 | 3.6 |
| 4H EMA20 | 03-11 | 23 | 22% | −13.0 | 17% | −11.0 | 13% | −11.0 | −$3,282 | 7.6 |
| 4H EMA20 | Any 18-16 | 56 | 32% | −18.2 | 16% | −24.9 | 11% | −25.7 | −$7,250 | 8.3 |
| Daily EMA20 | London 03-05 | 1 | 0% | −1.0 | 0% | −1.0 | 0% | −1.0 | −$215 | 4.0 |
| Daily EMA20 | 03-11 | 5 | 40% | −1.0 | 40% | +1.0 | 40% | +3.0 | −$85 | 3.6 |
| Daily EMA20 | Any 18-16 | 13 | 31% | −4.6 | 23% | −3.6 | 15% | −4.6 | −$1,066 | 6.4 |

### By test number (no trend filter)


#### Shorts

| Window | Test | Signals | Win % 2R | Total R at 1R | Total R at 2R | Total R at 3R | Net $ at 2R |
|---|---|--:|--:|--:|--:|--:|--:|
| London 03-05 | 1 | 0 | – | – | – | – | – |
| London 03-05 | 2 | 9 | 78% | +7.0 | +12.0 | +7.0 | +$2,584 |
| London 03-05 | 3 | 4 | 75% | +4.0 | +5.0 | +8.0 | +$1,313 |
| London 03-05 | 4 | 1 | 0% | −1.0 | −1.0 | −1.0 | −$235 |
| London 03-05 | 5+ | 4 | 25% | +0.0 | −1.0 | −4.0 | −$171 |
| 03-11 | 1 | 1 | 0% | −1.0 | −1.0 | −1.0 | −$243 |
| 03-11 | 2 | 26 | 50% | +6.0 | +15.6 | +8.6 | +$3,162 |
| 03-11 | 3 | 13 | 46% | +2.3 | +6.3 | +9.4 | +$1,723 |
| 03-11 | 4 | 8 | 25% | −4.0 | −2.0 | −4.0 | −$394 |
| 03-11 | 5+ | 17 | 24% | −3.0 | −5.0 | −7.1 | −$959 |
| Any 18-16 | 1 | 16 | 19% | −5.3 | −6.3 | −7.3 | −$1,701 |
| Any 18-16 | 2 | 64 | 36% | +4.0 | +9.4 | +2.3 | +$969 |
| Any 18-16 | 3 | 40 | 35% | +0.9 | +7.9 | +9.1 | +$2,148 |
| Any 18-16 | 4 | 22 | 18% | −6.5 | −8.5 | −14.4 | −$2,051 |
| Any 18-16 | 5+ | 39 | 31% | +3.8 | +4.3 | +6.9 | +$1,008 |

#### Longs

| Window | Test | Signals | Win % 2R | Total R at 1R | Total R at 2R | Total R at 3R | Net $ at 2R |
|---|---|--:|--:|--:|--:|--:|--:|
| London 03-05 | 1 | 2 | 0% | +0.0 | −2.0 | −2.0 | −$604 |
| London 03-05 | 2 | 6 | 33% | +0.0 | +0.0 | −2.0 | −$115 |
| London 03-05 | 3 | 5 | 40% | −1.0 | +1.0 | −1.0 | −$165 |
| London 03-05 | 4 | 1 | 0% | −1.0 | −1.0 | −1.0 | −$300 |
| London 03-05 | 5+ | 3 | 67% | +1.0 | +3.0 | +5.0 | +$362 |
| 03-11 | 1 | 7 | 14% | −3.0 | −4.0 | −3.0 | −$1,146 |
| 03-11 | 2 | 27 | 30% | −7.0 | −3.0 | −11.0 | −$1,232 |
| 03-11 | 3 | 21 | 24% | −7.0 | −6.0 | −12.0 | −$1,802 |
| 03-11 | 4 | 10 | 10% | −3.1 | −6.1 | −7.4 | −$1,715 |
| 03-11 | 5+ | 13 | 23% | −7.0 | −4.0 | −5.0 | −$1,437 |
| Any 18-16 | 1 | 21 | 19% | −9.0 | −9.0 | −9.0 | −$2,466 |
| Any 18-16 | 2 | 70 | 27% | −13.6 | −7.6 | −18.6 | −$2,724 |
| Any 18-16 | 3 | 44 | 18% | −9.0 | −16.3 | −19.4 | −$4,790 |
| Any 18-16 | 4 | 30 | 20% | −3.7 | −8.1 | −6.2 | −$2,702 |
| Any 18-16 | 5+ | 31 | 26% | −8.3 | −3.5 | −2.3 | −$1,790 |

### By level type (any time 18-16, no trend filter)

| Side | Level | Signals | Win % 2R | Total R at 2R | Net $ at 2R |
|---|---|--:|--:|--:|--:|
| Short | 1H swing high | 14 | 21% | −5.0 | −$1,415 |
| Short | 1H swing low | 1 | 0% | −1.0 | −$264 |
| Short | Asia high | 8 | 25% | −2.0 | −$847 |
| Short | Asia low | 12 | 58% | +10.4 | +$2,042 |
| Short | PD POC | 25 | 40% | +5.0 | +$1,269 |
| Short | PD VAH | 28 | 25% | −4.6 | −$1,031 |
| Short | PD VAL | 19 | 26% | −1.1 | −$184 |
| Short | PD high | 6 | 50% | +3.0 | +$784 |
| Short | PD low | 17 | 35% | +3.9 | +$813 |
| Short | PW POC | 4 | 25% | +0.5 | +$211 |
| Short | PW VAH | 20 | 30% | +0.4 | −$32 |
| Short | PW VAL | 17 | 18% | −4.3 | −$1,448 |
| Short | PW low | 10 | 30% | +1.6 | +$475 |
| Long | 1H swing low | 26 | 23% | −3.4 | −$536 |
| Long | Asia high | 13 | 15% | −7.0 | −$1,587 |
| Long | Asia low | 12 | 33% | +0.0 | −$34 |
| Long | PD POC | 23 | 22% | −3.7 | −$1,643 |
| Long | PD VAH | 21 | 24% | −6.0 | −$2,494 |
| Long | PD VAL | 40 | 12% | −21.1 | −$5,336 |
| Long | PD high | 3 | 33% | +0.0 | −$287 |
| Long | PD low | 19 | 42% | +5.0 | +$1,010 |
| Long | PW POC | 4 | 25% | −1.0 | −$410 |
| Long | PW VAH | 9 | 11% | −5.4 | −$1,453 |
| Long | PW VAL | 15 | 20% | −2.9 | −$1,124 |
| Long | PW high | 1 | 0% | −1.0 | −$240 |
| Long | PW low | 10 | 40% | +2.0 | −$338 |


## Validation

- **15m bars:** built from 5m, they match TradingView's 15m exactly on the overlap.
- **Volume profile error:** on the 17 complete days with 5m data, levels from 5m bars vs 15m bars differed by a median of **0.7 (POC), 0.5 (VAH) and 0.7 (VAL) points**. A few days were far off, though: max **110 (POC), 38 (VAH) and 32 (VAL) points**, on days with two similar volume peaks. Proper volume-at-price data would remove this error.
- **One-trade-per-test fix:** the first run took repeat trades inside the same test (e.g. two shorts on Sep 3 at the PD VAH 4524.0, at 18:30 and 19:00, without price leaving the zone). Now it's one per test: 384 signals instead of 478.
- **Exits:** 301 signals ended at the stop and 83 at the end of the day.

## What it says

- **Shorts in London were the strongest slice,** +15.0R on 18 signals at 2R (61% reached 2R) and +$3,491. They were positive in both halves of the period (+10.0R on 11, then +5.0R on 7), but 18 trades is small.
- **Shorts at any time of day were roughly flat,** +6.8R on 181 signals at 2R. They were −13.3R in the first half and +20.0R in the second, so they aren't stable.
- **The VAH levels themselves weren't the edge.** Prior day VAH shorts were −4.6R on 28 trades and prior week VAH +0.4R on 20 (any time, no filter). The gains came from *tested* levels: Asia low retested from below (+10.4R on 12), PD POC (+5.0R on 25) and PD low (+3.9R on 17).
- **2nd and 3rd tests were best, 1st and 4th tests worst.** Shorts at any time: 1st test −6.3R on 16, 2nd +9.4R on 64, 3rd +7.9R on 40, 4th −8.5R on 22, 5th+ +4.3R on 39. The London pattern looks the same (2nd test +12.0R on 9), but with very few trades.
- **Trend filters didn't help shorts.** Neither the 4H nor the daily EMA filter improved any window.
- **Longs lost in almost every combination,** e.g. −44.5R on 196 at 2R any time, with PD VAL longs at −21.1R on 40. In a falling market that's expected, so this doesn't prove long rejections fail.
- **2R beat 1R and 3R** for shorts in every window.

Not financial advice. This is 2.5 months of one falling market, with an approximate volume profile.

## What I need from you

1. **The rest of your message** (after "Skip if"), plus your exit, target, risk and daily-limit rules. Then I'll rerun with exactly those.
2. **Longer data** for the 12+ months you asked for. Options: wait for TradingView's daily limit to reset (it still caps out at about 5,000 bars), export history from TradingView on your computer, or use a data provider with volume-at-price (e.g. Databento, which needs an API key) for a true volume profile.

## Files

- `claude/vah_rejection/signals.csv`: every signal with level, test number, entry, stop, filters, windows, R at 1/2/3R, MFE, $ at 2R
- `claude/vah_rejection/grid.csv`, `by_test.csv`, `by_level.csv`: the tables above, for every trend × window combination
- `claude/vah_rejection/levels.csv`: every level with its active period
- Rerun: `python3 backtest/vah_rejection.py` (about 1 minute)


---

# v13 add-on: stop-hunt check and wider stops (Nov 18, 2026)

"v13" = this VAH rejection backtest. Code: `backtest/stop_hunt.py` (run after `backtest/vah_rejection.py`). Same data, period (Sep 1 – Nov 13, 2026) and signals as above. Base case = stop at wick + 0.5, target 2R.

## How it's measured (assumptions)

1. **Losing trade = stopped out at the base stop.** Trades that closed at the end of the day with a loss were never stopped, so they aren't included.
2. **"Reached the original 2R target"** is checked from the bar *after* the stop bar. Inside the stop bar there's no way to know whether the high or the low came first.
   - **Within 4 hours:** bars that open before the stop bar's close + 4 hours. This can run past 17:00 into the next session.
   - **Same day:** bars up to the 17:00 ET close of that trading day.
3. **"Points past the stop before reversing"** = the furthest price went beyond the stop, from the stop bar until the 2R target was touched (if it was, the same day) or until the end of the trading day (if not). For trades that later hit 2R, this is the extra room the stop would have needed.
4. **Wider stops:** same entries. Stop = wick + 0.5 (base), + 1, + 2, + 3 points. **The target moves to 2R of the new, wider risk.** Lots = floor($300 ÷ (stop pts × $10)), still capped at 5, so a few tight trades risk under $300. $3 fees per contract.
5. **Max drawdown:** every signal is taken and P&L is booked in entry-time order. Overlapping trades are allowed, as in v13.
6. **The universe is v13's:** trigger candle inside 18:00–16:00. The wick + 0.5 rows reproduce v13 exactly (shorts any time: 181 signals, +6.8R, +$373).

## Results

### Stop-hunt overview

| Side | Window  Losers | Hit 2R within 4h | Hit 2R same day | Median pts past stop (all losers) | Median pts past stop (hunted only) |
|---|---|--:|--:|--:|--:|--:|
| Short | Any 18-16 | 110 | 39 (35%) | 50 (45%) | 11.2 | 6.5 |
| Short | 03-11 | 38 | 16 (42%) | 20 (53%) | 14.9 | 5.8 |
| Short | London 03-05 | 7 | 3 (43%) | 4 (57%) | 18.5 | 5.2 |
| Long | Any 18-16 | 138 | 46 (33%) | 63 (46%) | 14.3 | 6.7 |
| Long | 03-11 | 59 | 21 (36%) | 27 (46%) | 18.5 | 7.2 |
| Long | London 03-05 | 11 | 3 (27%) | 5 (45%) | 30.3 | 8.0 |

### Stop hunts by level type (any time 18–16)

| Side | Level  Losers | Hit 2R within 4h | Hit 2R same day | Median pts past stop (all losers) | Median pts past stop (hunted only) |
|---|---|--:|--:|--:|--:|--:|
| Short | 1H swing high | 11 | 5 (45%) | 7 (64%) | 21.1 | 8.6 |
| Short | 1H swing low | 1 | 1 (100%) | 1 (100%) | 1.2 | 1.2 |
| Short | Asia high | 6 | 1 (17%) | 1 (17%) | 26.2 | 33.4 |
| Short | Asia low | 4 | 1 (25%) | 1 (25%) | 4.9 | 4.2 |
| Short | PD POC | 15 | 6 (40%) | 9 (60%) | 8.6 | 6.0 |
| Short | PD VAH | 18 | 7 (39%) | 9 (50%) | 19.2 | 7.5 |
| Short | PD VAL | 11 | 2 (18%) | 2 (18%) | 27.5 | 1.0 |
| Short | PD high | 3 | 1 (33%) | 1 (33%) | 21.6 | 7.4 |
| Short | PD low | 9 | 4 (44%) | 4 (44%) | 8.0 | 2.6 |
| Short | PW POC | 2 | 2 (100%) | 2 (100%) | 5.6 | 5.6 |
| Short | PW VAH | 12 | 2 (17%) | 3 (25%) | 5.0 | 6.2 |
| Short | PW VAL | 12 | 5 (42%) | 7 (58%) | 7.4 | 7.4 |
| Short | PW low | 6 | 2 (33%) | 3 (50%) | 9.2 | 2.2 |
| Long | 1H swing low | 17 | 9 (53%) | 10 (59%) | 14.3 | 7.0 |
| Long | Asia high | 11 | 4 (36%) | 5 (45%) | 5.8 | 5.8 |
| Long | Asia low | 8 | 5 (62%) | 5 (62%) | 5.8 | 4.7 |
| Long | PD POC | 14 | 6 (43%) | 8 (57%) | 15.2 | 4.0 |
| Long | PD VAH | 16 | 3 (19%) | 6 (38%) | 5.7 | 5.5 |
| Long | PD VAL | 32 | 11 (34%) | 16 (50%) | 22.8 | 10.2 |
| Long | PD high | 2 | 1 (50%) | 1 (50%) | 18.8 | 20.2 |
| Long | PD low | 11 | 1 (9%) | 3 (27%) | 40.2 | 7.2 |
| Long | PW POC | 3 | 0 (0%) | 1 (33%) | 43.5 | 4.2 |
| Long | PW VAH | 7 | 1 (14%) | 1 (14%) | 18.5 | 0.6 |
| Long | PW VAL | 10 | 4 (40%) | 5 (50%) | 20.6 | 20.3 |
| Long | PW high | 1 | 0 (0%) | 0 (0%) | 62.2 | – |
| Long | PW low | 6 | 1 (17%) | 2 (33%) | 10.8 | 4.4 |

### Stop hunts by touch number (any time 18–16)

| Side | Test  Losers | Hit 2R within 4h | Hit 2R same day | Median pts past stop (all losers) | Median pts past stop (hunted only) |
|---|---|--:|--:|--:|--:|--:|
| Short | 1 | 12 | 5 (42%) | 7 (58%) | 17.2 | 8.8 |
| Short | 2 | 39 | 13 (33%) | 18 (46%) | 11.7 | 5.8 |
| Short | 3 | 21 | 5 (24%) | 5 (24%) | 12.1 | 6.0 |
| Short | 4 | 16 | 7 (44%) | 9 (56%) | 8.8 | 6.2 |
| Short | 5+ | 22 | 9 (41%) | 11 (50%) | 10.0 | 7.4 |
| Long | 1 | 17 | 7 (41%) | 10 (59%) | 14.3 | 10.2 |
| Long | 2 | 47 | 18 (38%) | 25 (53%) | 17.9 | 5.8 |
| Long | 3 | 33 | 12 (36%) | 15 (45%) | 10.1 | 5.6 |
| Long | 4 | 21 | 4 (19%) | 5 (24%) | 13.3 | 10.3 |
| Long | 5+ | 20 | 5 (25%) | 8 (40%) | 18.1 | 4.3 |

### How far past the stop the hunted trades went (both sides, hit 2R same day)

| Points past stop | Trades |
|---|--:|
| ≤0.5 | 5 |
| 0.5–1.5 | 19 |
| 1.5–2.5 | 9 |
| 2.5–5 | 14 |
| 5–10 | 27 |
| >10 | 39 |

### Wider stops, $300 risk (lots recalculated), target 2R of the new risk

| Side | Window | Stop | Signals | Win % | Total R | Net $ | Max drawdown | Avg lots |
|---|---|---|--:|--:|--:|--:|--:|--:|
| Short | Any 18-16 | wick + 0.5 | 181 | 31% | +6.8 | +$373 | −$5,872 | 3.86 |
|  |  | wick + 1 | 181 | 30% | +7.6 | +$687 | −$5,833 | 3.71 |
|  |  | wick + 2 | 181 | 29% | +6.8 | −$252 | −$5,737 | 3.38 |
|  |  | wick + 3 | 181 | 29% | +12.3 | +$2,378 | −$5,716 | 2.99 |
| Short | 03-11 | wick + 0.5 | 65 | 38% | +13.9 | +$3,289 | −$1,542 | 3.57 |
|  |  | wick + 1 | 65 | 37% | +11.8 | +$2,939 | −$1,455 | 3.43 |
|  |  | wick + 2 | 65 | 38% | +15.9 | +$3,558 | −$1,598 | 3.12 |
|  |  | wick + 3 | 65 | 35% | +9.9 | +$2,130 | −$1,799 | 2.82 |
| Short | London 03-05 | wick + 0.5 | 18 | 61% | +15.0 | +$3,491 | −$795 | 4.22 |
|  |  | wick + 1 | 18 | 56% | +12.0 | +$2,708 | −$1,127 | 4.06 |
|  |  | wick + 2 | 18 | 67% | +18.0 | +$4,496 | −$781 | 3.72 |
|  |  | wick + 3 | 18 | 50% | +9.0 | +$2,252 | −$809 | 3.22 |
| Long | Any 18-16 | wick + 0.5 | 196 | 23% | -44.5 | −$14,472 | −$14,472 | 3.76 |
|  |  | wick + 1 | 196 | 24% | -36.8 | −$13,307 | −$13,477 | 3.61 |
|  |  | wick + 2 | 196 | 24% | -33.3 | −$11,092 | −$11,092 | 3.30 |
|  |  | wick + 3 | 196 | 20% | -42.2 | −$11,695 | −$11,875 | 2.93 |
| Long | 03-11 | wick + 0.5 | 78 | 23% | -23.1 | −$7,332 | −$8,621 | 3.86 |
|  |  | wick + 1 | 78 | 24% | -18.1 | −$6,113 | −$8,001 | 3.72 |
|  |  | wick + 2 | 78 | 20% | -25.6 | −$7,808 | −$9,355 | 3.40 |
|  |  | wick + 3 | 78 | 18% | -30.6 | −$8,216 | −$9,377 | 3.01 |
| Long | London 03-05 | wick + 0.5 | 17 | 35% | +1.0 | −$822 | −$1,610 | 4.35 |
|  |  | wick + 1 | 17 | 35% | +1.0 | −$584 | −$1,452 | 4.24 |
|  |  | wick + 2 | 17 | 24% | -5.0 | −$1,473 | −$2,016 | 3.88 |
|  |  | wick + 3 | 17 | 24% | -5.0 | −$1,686 | −$2,088 | 3.59 |


## Validation

- The base rows match v13 exactly for every side and window.
- Hand-checked one hunted trade: **short Sep 6 21:45** at a 1H swing low on its 2nd test. Entry 4455.7, stop 4464.2, 2R target 4438.7. The stop was hit at 22:30 (high 4465.0), and price went 1.2 points past it (22:45 high 4465.4). Price then hit the 2R target at 02:00 (low 4430.6), inside the 4-hour window that ends at 02:45. A wick + 2 stop (4465.7) would have survived, and its target (4435.7) was also hit.
- I caught and fixed two bugs in my first run: the short target was placed above entry, and signals outside 18:00–16:00 were included. The numbers above are after the fix.

## What it says

- **Many stops look like hunts on paper.** 45% of stopped shorts (50 of 110) and 46% of stopped longs (63 of 138) still reached the original 2R target the same day. 35% and 33% did it within 4 hours.
- **But most of them went too far past the stop for a small widening to save them.** Hunted trades went a median 6.5 points past the stop for shorts and 6.7 for longs. Only 33 of 113 hunted trades went 2.5 points or less past it, which is the extra room a wick + 3 stop gives over the base wick + 0.5.
- **Wider stops didn't consistently help.** For shorts at any time, net $ went +$373 → +$687 → −$252 → +$2,378 for + 0.5 / + 1 / + 2 / + 3. That isn't a trend, it's noise: each wider stop also pushes the 2R target further away, and drawdown stayed around −$5,700 to −$5,900. London shorts were best at wick + 2 (+$4,496, 67% win, −$781 drawdown), but that's 18 trades, where a single extra winner makes the difference. Longs lost at every width.
- **By level (shorts):** stops at PD POC (9 of 15), 1H swing highs (7 of 11) and PW VAL (7 of 12) were often hunts, meaning the idea was right but the stop was too tight. Stops at Asia high (1 of 6) and PD VAL (2 of 11) were rarely hunts, meaning those trades were simply wrong.
- **By touch (shorts):** 3rd-touch losers were hunted least (5 of 21, 24%). When a 3rd test failed, it usually kept going. 1st- and 4th-touch losers were hunted more than half the time.
- **Bottom line:** most of these losers weren't hunts that a slightly wider stop would have saved. A fixed 1–3 point widening isn't a fix. If you want to act on this, the level split is the lead to follow: tight stops at POCs and swing highs got hunted, while Asia high and PD VAL losses were real. That's 2.5 months of data, so treat it as a lead to test, not a rule.

## Files

- `claude/vah_rejection/stop_hunt_losers.csv`: every stopped trade with stop time, 2R target, hit within 4h / same day, points past the stop
- `claude/vah_rejection/hunt_overview.csv`, `hunt_by_level.csv`, `hunt_by_test.csv`, `hunt_depth.csv`
- `claude/vah_rejection/wider_stops.csv`, and `signals_wider_stops.csv` (each signal's R, $ and lots at every stop width)

The spec is still cut off at "Skip if", so exits and sizing remain the placeholders listed at the top.
