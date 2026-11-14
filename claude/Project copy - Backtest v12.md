# Backtest v12 results (MGC London, Nov 14, 2026)

Source: Claude Code session, GitHub repo aniket894-ui/trading-notes, branch claude/mgc-backtest-new-strategies-kniij3.

## Voice version (read this out loud when asked for a summary)

This is backtest version 12, in plain words. I tested micro gold in the London session, 3 to 5 in the morning Eastern time, with my rules: 300 dollars risk, max 5 lots, 2 trades a day, done after 2 losses, and only trading with the 1-hour trend.

The data only goes back to the end of August for 15-minute candles and to October 20 for 5-minute candles. That means between 2 and 12 trades per setup, so nothing here is proven. The v11 tests aren't in this yet.

The best new setup was the 15-minute rejection wick at a level. It made money with every exit: 433 dollars on 12 trades with a fixed 2R target, and 595 dollars with 2R plus a trailing runner. The 5-minute engulfing candle made between 161 and 419 dollars, but on only 4 trades.

The two Rulebook setups I used as stand-ins lost. Sweep and reclaim lost 991 dollars on 4 trades. Value area high and low close back inside lost 395 dollars on 2 trades.

Exits. Fixed 2R is the best default. The pip ladder at 100, 150 and 200 pips was the worst exit on the 15-minute setup, because my stops were 5 to 6 points, so 100 pips came in under 2R. Drop it. Taking profit at the next level wins more often but makes less. 2R plus a trailing runner was best on the 15-minute setup and worst on the 5-minute one, so keep paper-logging it.

Levels. Shorting into the prior day's value area low, with price coming up into it from below, won 4 out of 5 for plus 1,484 dollars. Shorting the Asia high lost all 7 times. Only 3 longs were taken, because gold was falling and the trend filter blocked them.

Bottom line: keep 2R as the main exit, paper-log the trailing runner beside it, watch value area low shorts, be careful with Asia high shorts, and drop the pip ladder. Then retest when there's more data.

## What was tested

- **Market:** COMEX MGC1! (micro gold front month), TradingView data.
- **Data:** 5m Oct 20 to Nov 13, 2026 (18 London sessions); 15m Aug 31 to Nov 13, 2026 (53 London sessions); 1h Jan 12 to Nov 13, 2026 (for the trend filter). A full year wasn't available: about 5,000 bars per timeframe on the TradingView plan.
- **Not included:** the v11 tests (that file couldn't be opened from the Claude Code session).

## Rules (every setup, every exit)

- Signal candle opens and closes inside London, 3:00 to 5:00 AM ET.
- $300 risk. Lots = $300 ÷ (stop points × $10), rounded down, max 5, skip if under 1.
- Stop 1 tick past the signal candle. Entry at the signal candle's close.
- 2 trades a day, done after 2 losses, one trade at a time.
- 1H trend filter: longs only when the last 1-hour close is above the 1-hour 50 EMA, shorts only below.
- Levels: Asia high/low (6 PM to 3 AM ET), prior day high/low, prior day VAH/VAL (70% value area). A wick within 0.5 points counts as a touch, and the candle must close on the trade's side.
- If one candle hits the stop and a target, the stop counts. Fees $3 per contract round trip.

## Setups

- **NEW 1, 5m engulfing:** a red candle then a green candle whose body covers the red body (mirror for shorts), touching the level. Stop past the engulfing candle.
- **NEW 2, 15m rejection wick:** the wick touching the level is at least half the candle's range, and the candle closes back on the trade's side. Stop past the wick.
- **REF A, 15m sweep and reclaim (Rulebook Setup A):** runs past an Asia or prior day high/low and closes back inside. Stand-in, not v11.
- **REF B, 15m VAH/VAL close back inside (Rulebook Setup B).** Stand-in, not v11.

## Exits

- **V1 fixed 2R:** every lot out at 2R.
- **V2 pip ladder:** TP1 100 pips (10 pts), TP2 150 pips (15 pts), TP3 200 pips (20 pts). 5 lots split 2/2/1, 4 split 2/1/1, 3 split 1/1/1. The stop stays where it started.
- **V3 level to level:** one target, the next level at least 1R away (2R if there's none).
- **V4 2R + trail:** at 2R close all lots but one. The last lot goes to break-even, then trails behind 1-hour swing highs or lows.

## Results: every setup, every exit (net $ after fees)

Shorts and longs shown as trades · net $.

| Setup | Exit | Trades | Win % | Net $ | Max drawdown | Shorts | Longs | Total R |
|---|---|--:|--:|--:|--:|--:|--:|--:|
| NEW 1 - 5m engulfing at level | V1 2R | 4 | 50% | +$381 | −$560 | 3 · −$135 | 1 · +$516 | +2.0 |
|  | V2 ladder | 4 | 50% | **+$419** | −$560 | 3 · −$119 | 1 · +$538 | +2.1 |
|  | V3 level | 4 | 50% | +$336 | −$560 | 3 · −$180 | 1 · +$516 | +1.8 |
|  | V4 trail | 4 | 50% | +$161 | −$560 | 3 · −$223 | 1 · +$384 | +1.1 |
| NEW 2 - 15m rejection wick at level | V1 2R | 12 | 42% | +$433 | −$885 | 10 · +$808 | 2 · −$375 | +3.0 |
|  | V2 ladder | 11 | 36% | +$152 | −$885 | 9 · +$527 | 2 · −$375 | +1.4 |
|  | V3 level | 12 | 50% | +$249 | −$885 | 10 · +$394 | 2 · −$145 | +3.5 |
|  | V4 trail | 12 | 42% | **+$595** | −$885 | 10 · +$970 | 2 · −$375 | +3.6 |
| REF A - 15m sweep & reclaim (Rulebook) | V1 2R | 4 | 0% | −$991 | −$991 | 4 · −$991 | 0 · $0 | -4.0 |
|  | V2 ladder | 4 | 0% | −$991 | −$991 | 4 · −$991 | 0 · $0 | -4.0 |
|  | V3 level | 4 | 0% | −$991 | −$991 | 4 · −$991 | 0 · $0 | -4.0 |
|  | V4 trail | 4 | 0% | −$991 | −$991 | 4 · −$991 | 0 · $0 | -4.0 |
| REF B - 15m VAH/VAL close back inside (Rulebook) | V1 2R | 2 | 0% | −$395 | −$395 | 0 · $0 | 2 · −$395 | -2.0 |
|  | V2 ladder | 2 | 0% | −$395 | −$395 | 0 · $0 | 2 · −$395 | -2.0 |
|  | V3 level | 2 | 50% | **−$165** | −$285 | 0 · $0 | 2 · −$165 | +0.4 |
|  | V4 trail | 2 | 0% | −$395 | −$395 | 0 · $0 | 2 · −$395 | -2.0 |


## Results by level (trades and wins at V1; net $ for each exit)

| Setup | Level | Side | Trades | Wins (2R) | V1 2R | V2 ladder | V3 level | V4 trail |
|---|---|---|--:|--:|--:|--:|--:|--:|
| NEW 1 | Asia high | Long | 1 | 1 | +$516 | +$538 | +$516 | +$384 |
|  | Asia high | Short | 1 | 0 | −$275 | −$275 | −$275 | −$275 |
|  | VAL | Short | 2 | 1 | +$140 | +$156 | +$95 | +$52 |
| NEW 2 | Asia high | Long | 1 | 0 | −$265 | −$265 | −$265 | −$265 |
|  | Asia high | Short | 2 | 0 | −$556 | −$556 | −$556 | −$556 |
|  | Asia low | Short | 3 | 1 | −$120 | +$70 | −$130 | +$91 |
|  | VAL | Long | 1 | 0 | −$110 | −$110 | +$120 | −$110 |
|  | VAL | Short | 5 | 4 | +$1,484 | +$1,013 | +$1,080 | +$1,435 |
| REF A | Asia high | Short | 4 | 0 | −$991 | −$991 | −$991 | −$991 |
| REF B | VAL | Long | 2 | 0 | −$395 | −$395 | −$165 | −$395 |


Prior day high, prior day low and VAH never triggered a trade.

## Every trade: 15m rejection wick

| Day | Time ET | Side | Level | Entry | Stop | Lots | V1 2R | V2 ladder | V3 level | V4 trail |
|---|---|---|---|--:|--:|--:|--:|--:|--:|--:|
| 2026-09-08 | 04:30 | Short | VAL | 4437.1 | 4443.0 | 5 | −$310 | −$310 | −$310 | −$310 |
| 2026-09-09 | 03:15 | Long | Asia high | 4451.4 | 4446.4 | 5 | −$265 | −$265 | −$265 | −$265 |
| 2026-09-21 | 03:45 | Short | Asia low | 4381.5 | 4387.4 | 5 | −$310 | −$310 | −$310 | −$310 |
| 2026-09-23 | 03:15 | Short | Asia low | 4360.5 | 4365.6 | 5 | +$495 | +$685 | +$485 | +$706 |
| 2026-09-24 | 04:00 | Short | VAL | 4311.6 | 4320.5 | 3 | +$525 | +$441 | +$525 | +$347 |
| 2026-10-05 | 03:45 | Short | Asia high | 4189.0 | 4195.1 | 4 | −$256 | −$256 | −$256 | −$256 |
| 2026-10-12 | 04:15 | Long | VAL | 4200.7 | 4198.8 | 5 | −$110 | −$110 | +$120 | −$110 |
| 2026-10-14 | 04:15 | Short | VAL | 4173.3 | 4181.1 | 3 | +$459 | +$441 | +$240 | +$756 |
| 2026-10-26 | 04:45 | Short | Asia high | 4030.6 | 4036.3 | 5 | −$300 | −$300 | −$300 | −$300 |
| 2026-10-27 | 04:00 | Short | Asia low | 4009.2 | 4015.0 | 5 | −$305 | −$305 | −$305 | −$305 |
| 2026-10-29 | 03:00 | Short | VAL | 4045.2 | 4049.6 | 5 | +$425 | +$441 | +$380 | +$337 |
| 2026-10-29 | 04:15 | Short | VAL | 4042.5 | 4046.5 | 5 | +$385 | skipped | +$245 | +$305 |


## Every trade: 5m engulfing

| Day | Time ET | Side | Level | Entry | Stop | Lots | V1 2R | V2 ladder | V3 level | V4 trail |
|---|---|---|---|--:|--:|--:|--:|--:|--:|--:|
| 2026-10-26 | 04:55 | Short | Asia high | 4030.6 | 4035.8 | 5 | −$275 | −$275 | −$275 | −$275 |
| 2026-10-27 | 04:05 | Short | VAL | 4009.6 | 4015.0 | 5 | −$285 | −$285 | −$285 | −$285 |
| 2026-10-29 | 03:10 | Short | VAL | 4045.2 | 4049.6 | 5 | +$425 | +$441 | +$380 | +$337 |
| 2026-11-04 | 03:30 | Long | Asia high | 4043.6 | 4037.0 | 4 | +$516 | +$538 | +$516 | +$384 |


## Opinions

- **V1 fixed 2R:** keep it as the default. It was solid on both new setups.
- **V2 pip ladder:** drop it. Stops of 5–6 points made 100 pips smaller than 2R, so winners paid less while losers cost the full $300. Worst exit on the 15m wick.
- **V3 level to level:** best win rate (50%) but smaller wins. Use the next level as a check, not as the target.
- **V4 2R + trail:** best on the 15m wick (+$595), worst on the 5m engulfing (+$161). Closest to the Rulebook. Keep paper-logging it.
- **VAL shorts:** 4 wins of 5, +$1,484. The one to watch.
- **Asia high shorts:** 0 wins of 7 across all setups.
- **Longs:** only 3 taken, because the trend filter blocked them while gold fell. Untested.
- **Surprise:** at 2R, trades with under 2R of room to the next level did better (4 of 7, +$964) than trades with 2R+ room (3 of 9, −$150). Too few trades to change the 2R-room rule.

## Next steps

1. Add the v11 tests to these tables.
2. Get more data (a TradingView export with longer history, Deep Backtesting, or a data provider).
3. Paper-log 20 London sessions of the 15m wick with both 2R and the trailing runner.

Not financial advice. 2 to 12 trades per setup say almost nothing about the future.
