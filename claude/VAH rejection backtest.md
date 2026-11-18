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
