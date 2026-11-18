# v14 ablation study: MGC sweep and reclaim

Run Nov 18, 2026 on branch `claude/mgc-vah-rejection-backtest`. Code: `backtest/ablation.py`. CSVs: `claude/v14_ablation/`.

## Voice summary

I took my sweep-and-reclaim setup and tested each rule change one at a time against the same starting version. Then I combined the ones that helped. The starting version lost money: minus 1,706 dollars on 44 trades in the first seven weeks.

Five changes made it better and still helped when they were combined. Only trade the London hour, 3 to 5 in the morning. Use VWAP for direction: shorts below it, longs above it. Stick to real levels, meaning yesterday's and last week's value area edges, yesterday's high and low, and the Asia high and low, plus any level that has already rejected price twice. And put the stop 2 points past the wick instead of half a point.

Then came the honest test. On the last three and a half weeks, which I never looked at while choosing, the final system made plus 1,372 dollars on 9 trades. It won 5 of the 9, and the biggest drawdown was 290 dollars. The starting version made plus 520 dollars on 21 trades over the same weeks.

Nine trades is far too few to trust. Every number here is unproven until it holds up on more data. The test only covers about two and a half months of a falling gold market, and news days couldn't be tested because I didn't have verified dates. Not financial advice.

## What couldn't be done as asked

- **No 12 months of data.** TradingView keeps about 5,000 bars per timeframe on your plan, and today's daily call limit was used up. So this uses the same real candles as v13: 15m from Aug 31 to Nov 13, 2026, and 1H from Jan 12. **The walk-forward uses the same 2:1 ratio as the 8 + 4 months you asked for:** BUILD = trading days Sep 1 to Oct 19, TEST = Oct 20 to Nov 13. Every switch, the combination and the trimming were decided on BUILD only. TEST was run once at the end.
- **S12 (skip news days) was not run.** There are no verified CPI, NFP and FOMC dates in this session (TradingView's calendar was blocked by the daily limit), and I won't guess them. Add `data/news_days.csv` with a `date` column, rerun, and S12 runs.
- **S16 has no effect by design.** With 2 trades a day max, "stop after a win then a loss" never blocks a trade that wasn't already blocked.

## Assumptions

1. **Base levels ("recent highs/lows"):** prior day high/low, prior week high/low, Asia high/low (19:00 to 02:00), and 1H fractal swing highs/lows (3 bars each side, retired at the first 1H close beyond them). These are the v13 levels.
2. **Sweep and reclaim:** a 15m candle trades beyond the level, closes back inside, and the candle before it closed inside too. No bearish/bullish close is required. One trade per test of a level.
3. **Touch number** is counted as in v13: a wick within 1.0 point with a close back on the starting side, and a new touch only after price leaves the 1-point zone. The base allows touches 1 to 3, and S4 allows 4th and later.
4. **S1 real levels** = PD VAH/VAL, PW VAH/VAL, PDH/PDL, Asia H/L. **S2 tested** = any level type (POC, VAH/VAL, highs/lows, swings) on its 3rd touch or later, i.e. 2 earlier rejections. S1 and S2 can stack.
5. **Trend:** the trigger candle's close vs the 20 EMA of the last completed 4H (base), 1H (S5) or daily (S6) bar. S7 uses session VWAP from 18:00 (typical price × volume, 15m bars). Shorts need the close below, longs above.
6. **Windows:** the trigger candle opens and closes inside 03:00–11:00 (base), 03:00–05:00 (S9) or 19:00–11:00 (S10). Thursdays are judged by trading day.
7. **Size:** lots = floor($300 ÷ (stop pts × $10)), at least 3 and at most 5, skip if under 3. The stop is the wick + 0.5 (base), + 1, + 2 or + 3 (S13). Risk stays $300 as lots are recalculated.
8. **Costs:** $1.50 per contract round trip. 1 tick slippage on entries, stops and market exits, none on limit targets. If a candle hits the stop and a target, the stop counts.
9. **Exits:** E2 (all out at 2R) is the base. On E1/E2, lots still open close at the 16:45 bar close. For E3 to E7, "2 lots at 2R" means 2 lots close at 2R and the rest (1 to 3 lots) run.
   - **E3/E4:** the runner targets the next level beyond 2R and closes at 5 PM.
   - **E5/E6/E7:** the runner targets the nearest prior day/week VAL (shorts) or VAH (longs) beyond 2R, for up to 3 trading days.
   - **Runner stop:** break-even in E3/E5/E7, the original stop in E4/E6. E7 then trails behind 1H 1-bar pivot highs (lows for longs).
10. **Daily rules:** max 2 trades a day, done after 2 losses, one trade at a time. A new trade can start once the open trade is closed or its 2R part is filled.
11. **Brakes:**
   - **S14:** half risk ($150) after 3 losing days in a row, until a green day. The 3-lot minimum still applies, so only tight stops qualify.
   - **S15:** no new trades for the rest of the week once the week is down $900.
   - P&L counts on the day of entry.
12. **Keep rule:** KEEP if the profit factor rises and max drawdown gets no more than 10% worse, with 30 or more trades. **UNSURE** if it passes with under 30 trades. Both are stacked, but UNSURE is flagged. Otherwise DROP.
   - **Groups where only one can win:** trend (S5–S8), time (S9/S10), stop width (S13) and exit (E1–E7). The highest profit factor among the passing switches in each group goes in.
   - **Trimming:** a switch whose removal changes nothing is "not needed in combo" and is dropped from the final system.
13. **Max drawdown** = worst fall in cumulative closed-trade P&L, in entry order, starting from $0.

## Results: every switch alone vs base (BUILD period, Sep 1 – Oct 19)

Anything under 30 trades is unproven.

| Switch | Trades | Win % | Net $ | Profit factor | Max drawdown | Longest losing streak | Verdict |
|---|--:|--:|--:|--:|--:|--:|---|
| BASE (v5 sweep & reclaim) | 44 | 32% | −$1,706 | 0.77 | −$3,504 | 9 | **control** |
| S1 only real levels | 51 | 31% | −$1,136 | 0.86 | −$3,090 | 9 | **KEEP** |
| S2 add tested levels (2+ rejections) | 52 | 36% | +$426 | 1.05 | −$2,418 | 10 | **KEEP** |
| S3 drop Asia high shorts | 37 | 35% | −$887 | 0.85 | −$2,445 | 8 | **KEEP** |
| S4 allow 4th+ touch re-entries | 46 | 30% | −$2,216 | 0.72 | −$4,014 | 9 | **DROP** |
| S5 1H trend | 36 | 31% | −$919 | 0.84 | −$2,312 | 8 | **KEEP** |
| S6 daily trend | 46 | 33% | −$1,218 | 0.84 | −$3,016 | 6 | **KEEP** |
| S7 VWAP side as trend | 34 | 35% | +$285 | 1.06 | −$1,880 | 8 | **KEEP** |
| S8 no trend filter | 61 | 28% | −$2,781 | 0.73 | −$4,051 | 9 | **DROP** |
| S9 London only 3-5 AM | 16 ⚠ under 30 | 44% | +$952 | 1.42 | −$1,220 | 5 | **UNSURE** |
| S10 Asia+London+NY 7 PM-11 AM | 53 | 36% | −$309 | 0.96 | −$2,920 | 7 | **KEEP** |
| S11 skip Thursdays | 38 | 29% | −$2,452 | 0.62 | −$3,680 | 9 | **DROP** |
| S12 skip news days | – | – | – | – | – | – | **NOT RUN** (no verified news dates) |
| S13a stop wick +1 | 42 | 29% | −$2,282 | 0.70 | −$4,443 | 9 | **DROP** |
| S13b stop wick +2 | 39 | 36% | +$44 | 1.01 | −$2,828 | 8 | **KEEP** |
| S13c stop wick +3 | 36 | 25% | −$2,888 | 0.62 | −$3,862 | 6 | **DROP** |
| E1 all out 1.5R | 44 | 32% | −$3,148 | 0.57 | −$4,284 | 9 | **DROP** |
| E3 2 at 2R, runner BE to next structure, out 5 PM | 44 | 32% | −$1,652 | 0.78 | −$3,568 | 9 | **KEEP** |
| E4 2 at 2R, runner original stop to next structure | 44 | 32% | −$2,382 | 0.68 | −$3,820 | 9 | **DROP** |
| E5 2 at 2R, runner BE to opposite value edge, 3 days | 44 | 32% | −$3,016 | 0.59 | −$3,428 | 9 | **DROP** |
| E6 like E5, runner keeps original stop | 44 | 32% | −$4,294 | 0.42 | −$4,334 | 9 | **DROP** |
| E7 like E5, trail 1H lower highs | 44 | 32% | +$396 | 1.05 | −$3,910 | 9 | **DROP** |
| S14 half risk after 3 losing days | 44 | 34% | −$1,047 | 0.85 | −$2,845 | 6 | **KEEP** |
| S15 weekly loss cap $900 | 40 | 32% | −$1,232 | 0.81 | −$3,030 | 10 | **KEEP** |
| S16 stop after win then loss | 44 | 32% | −$1,706 | 0.77 | −$3,504 | 9 | **DROP** |


### Combined system, removing one switch at a time (BUILD period)

| Removed from combo | Trades | Win % | Net $ | Profit factor | Max drawdown | Result |
|---|--:|--:|--:|--:|--:|---|
| (none: full combo) | 18 | 78% | +$5,309 | 6.14 | −$292 |  |
| S1 only real levels | 15 | 73% | +$4,334 | 5.36 | −$452 | still helps |
| S2 add tested levels (2+ rejections) | 16 | 75% | +$4,209 | 5.08 | −$292 | still helps |
| S3 drop Asia high shorts | 18 | 78% | +$5,309 | 6.14 | −$292 | not needed in combo |
| S7 VWAP side as trend | 16 | 69% | +$4,300 | 4.17 | −$531 | still helps |
| S9 London only 3-5 AM | 33 | 39% | +$833 | 1.18 | −$2,146 | still helps |
| S13b stop wick +2 | 21 | 52% | +$3,240 | 2.76 | −$438 | still helps |
| E3 2 at 2R, runner BE to next structure, out 5 PM | 18 | 78% | +$5,305 | 6.14 | −$292 | not needed in combo |
| S14 half risk after 3 losing days | 18 | 78% | +$5,309 | 6.14 | −$292 | not needed in combo |
| S15 weekly loss cap $900 | 18 | 78% | +$5,309 | 6.14 | −$292 | not needed in combo |


### Walk-forward: BUILD vs the untouched TEST period

| System | Period | Trades | Win % | Net $ | Profit factor | Max drawdown | Longest losing streak |
|---|---|--:|--:|--:|--:|--:|--:|
| Base | BUILD Sep 1 – Oct 19 | 44 | 32% | −$1,706 | 0.77 | −$3,504 | 9 |
| Final system | BUILD Sep 1 – Oct 19 | 18 | 78% | +$5,305 | 6.14 | −$292 | 1 |
| Base | **TEST Oct 20 – Nov 13 (untouched)** | 21 | 38% | +$520 | 1.18 | −$1,027 | 4 |
| Final system | **TEST Oct 20 – Nov 13 (untouched)** | 9 | 56% | +$1,372 | 2.39 | −$290 | 1 |
| Base | Whole period | 65 | 34% | −$1,186 | 0.88 | −$3,926 | 9 |
| Final system | Whole period | 27 | 70% | +$6,678 | 4.30 | −$292 | 1 |
| Full combo, before trimming | **TEST Oct 20 – Nov 13 (untouched)** | 9 | 56% | +$738 | 1.75 | −$386 | 1 |


### Every trade of the final system on the TEST period

| Time ET | Side | Level | Touch | Entry | Stop | Lots | Result | Net $ |
|---|---|---|--:|--:|--:|--:|---|--:|
| 2026-10-21 04:15 | Long | PD VAL | 3 | 4140.5 | 4133.5 | 4 | stop | −$290 |
| 2026-10-23 04:45 | Long | PD low | 1 | 4037.2 | 4033.3 | 5 | 2R target | +$382 |
| 2026-10-27 04:00 | Short | PD VAL | 1 | 4009.1 | 4016.9 | 3 | stop | −$242 |
| 2026-10-29 03:00 | Short | PD VAL | 2 | 4045.1 | 4051.5 | 4 | 2R target | +$506 |
| 2026-10-30 03:15 | Short | Asia low | 2 | 3994.0 | 3999.5 | 5 | 2R target | +$542 |
| 2026-10-30 04:15 | Short | Asia low | 3 | 3995.0 | 4002.0 | 4 | stop | −$290 |
| 2026-11-04 03:15 | Long | Asia high | 1 | 4038.7 | 4034.7 | 5 | 2R target | +$392 |
| 2026-11-06 03:00 | Short | PD low | 2 | 4066.2 | 4069.3 | 5 | stop | −$168 |
| 2026-11-10 03:15 | Short | PD POC | 3 | 4125.5 | 4132.3 | 4 | 2R target | +$538 |


## The final system, as simple rules

**Trade only 3:00 to 5:00 AM ET.**

1. **Mark your levels before 3 AM:**
   - Yesterday's value area high and low
   - Last week's value area high and low
   - Yesterday's high and low
   - The Asia high and low (7 PM to 2 AM)
   - Any other level, such as a POC or swing high/low, that has already rejected price twice
2. **Wait for a sweep:** a 15-minute candle pushes past one of those levels and closes back on the other side.
3. **Trade with VWAP:** short only if that candle closes below VWAP, long only if it closes above.
4. **Skip it** if the level has already been touched 3 times (this is the 4th or later).
5. **Enter** at the candle close.
6. **Stop:** 2 points past the candle's wick.
7. **Size:** $300 ÷ (stop in points × $10), rounded down. If that's under 3 lots, skip. Max 5 lots.
8. **Exit:** everything at 2R. No runner.
9. **Daily limits:** max 2 trades a day, and stop after 2 losses.

**Dropped after testing:**
- **Thursday skip:** it hurt here.
- **4th+ touches.**
- **No trend filter.**
- **Every runner exit except E3,** and E3 added nothing in the combo.
- **The two loss brakes:** they changed nothing in the combo.
- **The 1.5R exit.**

**News days:** not tested yet.

## Validation

- Hand-checked the final system's **Nov 10, 3:15 AM short**:
  - **Trigger:** the high (4130.3) swept the prior day POC at 4129.9 (its 3rd touch), and the candle closed back below at 4125.6.
  - **VWAP filter:** the close was under VWAP (4132.8).
  - **Entry, stop and size:** entry 4125.5 after 1 tick of slippage, stop 4132.3 (wick + 2), 4 lots.
  - **Exit:** the 2R target (4111.9) was hit at 4:00. Net +$538 after fees.
- Every base trade used 3 to 5 lots, as the rules require.

## Read this before trusting it

- **The build result is overfit.** The final system's 78% win rate and profit factor 6.1 on BUILD come from stacking filters onto 44 trades. Only the TEST number counts.
- **The TEST result is 9 trades.** It's encouraging (+$1,372, profit factor 2.4, against the base's +$520), but a couple of trades either way changes the picture. The full combo, before trimming, made +$738 on the same weeks. **That's unproven.**
- **London-only (S9) was UNSURE alone** with 16 trades, and it's the switch the combo leans on most. Removing it drops the profit factor from 6.1 to 1.2.
- **One market:** gold mostly fell in Sep to Nov 2026.
- **To confirm it:** 12+ months of 15m data and verified news dates, then rerun `python3 backtest/ablation.py`. It takes about 10 seconds.

Not financial advice.
