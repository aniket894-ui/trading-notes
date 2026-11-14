# Backtest v12 results: MGC London, 5m engulfing and 15m rejection wick

Run Nov 14, 2026. Data: COMEX MGC1! (micro gold, front month) from TradingView.

## Read this first: two things I could not do

1. **I could not open `claude/Backtest v11 results.md`.** It lives in the Trading Master Claude Project. A Claude Code cloud session can't read Project files, and it wasn't in Google Drive or this repo. So **the v11 tests are not rerun here.** Paste that file's text into the chat, or add it to this repo, and I'll run those tests on the same candles and add them to this table.
2. **A full year of 5m and 15m candles doesn't exist on this feed.** TradingView keeps about 5,000 bars per timeframe on your plan, and Deep Backtesting (longer history) isn't included in it. Other data sites are blocked from this session. What I could get:

| Timeframe | From | To | Bars | File |
|---|---|---|--:|---|
| 5 minute | Oct 20, 2026 | Nov 13, 2026 | 5,000 | `data/MGC_5m.csv` |
| 15 minute | Aug 31, 2026 | Nov 13, 2026 | 5,000 | `data/MGC_15m.csv` |
| 1 hour | Jan 12, 2026 | Nov 13, 2026 | 4,999 | `data/MGC_1h.csv` |

So the 5m test covers **18 London sessions** and the 15m test covers **53 London sessions**, not a year.

## Rules used (same for every row)

- **Window:** the signal candle opens and closes inside London, 3:00 to 5:00 AM ET. The trade then runs until its stop or target, whichever comes first.
- **Risk:** $300 a trade. Lots = $300 ÷ (stop in points × $10), rounded down, **max 5**. Skip if under 1 lot.
- **Target:** 2R. **Stop:** 1 tick past the signal candle.
- **2 trades a day, 2 losses and done,** one trade open at a time.
- **1H trend filter:** longs only when the last closed 1-hour candle closed above the 1-hour 50 EMA. Shorts only when below.
- **The level:** Asia high and low (6 PM to 3 AM ET), prior day high and low, and prior day VAH and VAL (70% value area). A candle "touches" a level if its wick gets within 0.5 points of it, and it must close on the trade's side of the level.
- Entry is at the signal candle's close. If one candle hits both stop and target, I count the stop. Fees are $3 per contract round trip.

**The two new tests**

- **NEW 1, 5m engulfing:** a red candle followed by a green candle whose body covers the red body (mirror image for shorts). One of the two candles touches the level, and the green candle closes beyond it. Stop goes past the engulfing candle.
- **NEW 2, 15m rejection wick:** the wick touching the level is at least half the candle's full range, and the candle closes back on the trade's side of the level. Stop goes past the wick.

**Stand-in rows (not v11).** Since v11 couldn't be opened, I ran your Rulebook Setup A (sweep and reclaim) and Setup B (VAH/VAL close back inside) on the same rules, so the new tests have something to compare against. Replace these rows with the v11 tests once I have the file.

## Results

| Test | Side | Trades | Wins | Losses | Win % | Total R | Net $ | Max drawdown |
|---|---|--:|--:|--:|--:|--:|--:|--:|
| NEW 1 - 5m engulfing at level | **All** | 4 | 2 | 2 | 50% | +2.0 | $381 | -$560 |
|  | Shorts | 3 | 1 | 2 | 33% | +0.0 | -$135 | -$560 |
|  | Longs | 1 | 1 | 0 | 100% | +2.0 | $516 | $0 |
| NEW 2 - 15m rejection wick at level | **All** | 12 | 5 | 7 | 42% | +3.0 | $433 | -$885 |
|  | Shorts | 10 | 5 | 5 | 50% | +5.0 | $808 | -$620 |
|  | Longs | 2 | 0 | 2 | 0% | -2.0 | -$375 | -$375 |
| REF A - 15m sweep & reclaim (Rulebook) | **All** | 4 | 0 | 4 | 0% | -4.0 | -$991 | -$991 |
|  | Shorts | 4 | 0 | 4 | 0% | -4.0 | -$991 | -$991 |
|  | Longs | 0 | 0 | 0 | – | +0.0 | $0 | $0 |
| REF B - 15m VAH/VAL close back inside (Rulebook) | **All** | 2 | 0 | 2 | 0% | -2.0 | -$395 | -$395 |
|  | Shorts | 0 | 0 | 0 | – | +0.0 | $0 | $0 |
|  | Longs | 2 | 0 | 2 | 0% | -2.0 | -$395 | -$395 |
| NEW 2 - 15m wick, 5m window only | **All** | 4 | 2 | 2 | 50% | +2.0 | $205 | -$605 |
|  | Shorts | 4 | 2 | 2 | 50% | +2.0 | $205 | -$605 |
|  | Longs | 0 | 0 | 0 | – | +0.0 | $0 | $0 |

The last row runs the 15m wick test over only the 5m test's dates (Oct 21 to Nov 13), so NEW 1 and NEW 2 can be compared side by side.

## What it says

- **Far too few trades to judge anything.** 4 trades for the 5m engulfing and 12 for the 15m wick. One trade either way flips the result, so both are "small sample, unproven", like most of v9.
- **Shorts carried it again.** For the 15m wick, shorts went +5R on 10 trades and longs went −2R on 2. Gold fell from about 4,500 to 3,880 over this stretch, so the 1H filter allowed very few longs. v9 also said "shorts carry it".
- **The 1H filter cut most signals.** In the London window: the 5m engulfing fired 12 times and 6 passed the filter; the 15m wick fired 35 times and 15 passed; the sweep and reclaim fired 58 times and 5 passed. The sweep is a reversal setup, so a trend filter mostly blocks it.
- **Both new tests finished green, and the Rulebook stand-ins finished red,** on the same rules and dates. That's worth tracking, not acting on.
- **Every trade hit its stop or its 2R target.** None ran to the end of the session.

## Trades (new tests)

| Test | Day | Time ET | Side | Level | Entry | Stop | Lots | Result | R | $ |
|---|---|---|---|---|--:|--:|--:|---|--:|--:|
| 5m engulf | 2026-10-26 | 04:55 | Short | Asia high 4032.9 | 4030.6 | 4035.8 | 5 | loss | -1 | -$275 |
| 5m engulf | 2026-10-27 | 04:05 | Short | VAL 4011.5 | 4009.6 | 4015.0 | 5 | loss | -1 | -$285 |
| 5m engulf | 2026-10-29 | 03:10 | Short | VAL 4046.0 | 4045.2 | 4049.6 | 5 | win | +2 | $425 |
| 5m engulf | 2026-11-04 | 03:30 | Long | Asia high 4039.2 | 4043.6 | 4037.0 | 4 | win | +2 | $516 |
| 15m wick | 2026-09-08 | 04:30 | Short | VAL 4439.5 | 4437.1 | 4443.0 | 5 | loss | -1 | -$310 |
| 15m wick | 2026-09-09 | 03:15 | Long | Asia high 4450.0 | 4451.4 | 4446.4 | 5 | loss | -1 | -$265 |
| 15m wick | 2026-09-21 | 03:45 | Short | Asia low 4383.5 | 4381.5 | 4387.4 | 5 | loss | -1 | -$310 |
| 15m wick | 2026-09-23 | 03:15 | Short | Asia low 4363.0 | 4360.5 | 4365.6 | 5 | win | +2 | $495 |
| 15m wick | 2026-09-24 | 04:00 | Short | VAL 4312.5 | 4311.6 | 4320.5 | 3 | win | +2 | $525 |
| 15m wick | 2026-10-05 | 03:45 | Short | Asia high 4191.2 | 4189.0 | 4195.1 | 4 | loss | -1 | -$256 |
| 15m wick | 2026-10-12 | 04:15 | Long | VAL 4200.5 | 4200.7 | 4198.8 | 5 | loss | -1 | -$110 |
| 15m wick | 2026-10-14 | 04:15 | Short | VAL 4176.0 | 4173.3 | 4181.1 | 3 | win | +2 | $459 |
| 15m wick | 2026-10-26 | 04:45 | Short | Asia high 4032.9 | 4030.6 | 4036.3 | 5 | loss | -1 | -$300 |
| 15m wick | 2026-10-27 | 04:00 | Short | Asia low 4009.5 | 4009.2 | 4015.0 | 5 | loss | -1 | -$305 |
| 15m wick | 2026-10-29 | 03:00 | Short | VAL 4046.0 | 4045.2 | 4049.6 | 5 | win | +2 | $425 |
| 15m wick | 2026-10-29 | 04:15 | Short | VAL 4046.0 | 4042.5 | 4046.5 | 5 | win | +2 | $385 |

Full trade list for every row: `claude/trades/all_trades.csv`. Summary numbers: `claude/trades/summary.csv`.

## Next steps

1. **Send the v11 file** (paste the text in chat). I'll add those tests to this table on the same candles.
2. **For a real year of data,** pick one:
   - Export the candles from TradingView on your computer and add the CSVs to `data/`. This needs a plan that allows exports with more history.
   - Upgrade TradingView to a plan with Deep Backtesting.
   - Use a paid data provider such as Databento. You'd add the API key in this environment's settings.
3. **Paper-log both new setups in London** for the next 20 sessions, alongside your v5 trades.

## How to rerun

```
python3 backtest/run_backtest.py
```

Rules are at the top of `backtest/run_backtest.py`. `backtest/to_csv.py` converts a TradingView candle download into these CSVs.

Not financial advice. Past results on 4 to 12 trades say almost nothing about future results.
