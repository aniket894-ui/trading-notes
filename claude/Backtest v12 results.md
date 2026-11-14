# Backtest v12 results: MGC London, 4 setups × 4 exits

Run Nov 14, 2026. Data: COMEX MGC1! (micro gold, front month) from TradingView.

## Read this first

1. **The v11 tests are not rerun.** `claude/Backtest v11 results.md` is in your Trading Master Claude Project, and a Claude Code cloud session can't read Project files. Paste its text in the chat and I'll add those tests to these tables.
2. **This is not a full year.** TradingView keeps about 5,000 bars per timeframe on your plan, and other data sites are blocked from this session:

| Timeframe | From | To | Bars | File |
|---|---|---|--:|---|
| 5 minute | Oct 20, 2026 | Nov 13, 2026 | 5,000 | `data/MGC_5m.csv` |
| 15 minute | Aug 31, 2026 | Nov 13, 2026 | 5,000 | `data/MGC_15m.csv` |
| 1 hour | Jan 12, 2026 | Nov 13, 2026 | 4,999 | `data/MGC_1h.csv` |

The 5m test covers **18 London sessions** and the 15m tests cover **53**. That's 2 to 12 trades per setup, **far too few to prove anything.** Read every number below as "worth watching", not "proven".

## Rules (every setup, every exit)

- **Window:** the signal candle opens and closes inside London, 3:00 to 5:00 AM ET.
- **Risk:** $300 a trade. Lots = $300 ÷ (stop in points × $10), rounded down, **max 5**, skip if under 1.
- **Stop:** 1 tick past the signal candle.
- **2 trades a day, 2 losses and done.** One trade at a time; a new one can start once the open trade is closed or risk-free.
- **1H trend filter:** longs only when the last closed 1-hour candle closed above the 1-hour 50 EMA, shorts only when below.
- **Levels:** Asia high and low (6 PM to 3 AM ET), prior day high and low, prior day VAH and VAL. A wick within 0.5 points counts as a touch, and the candle must close on the trade's side of the level.
- Entry is at the signal candle's close. If a candle hits the stop and a target, the stop counts. Fees are $3 per contract round trip.

## The four exits

Entry and stop are identical in all four, so only the exit changes.

| | Exit | How it works |
|---|---|---|
| **V1** | Fixed 1:2R | Every lot out at 2R. |
| **V2** | Pip ladder | TP1 **100 pips** (10 pts), TP2 **150 pips** (15 pts), TP3 **200 pips** (20 pts), one tranche each. 5 lots split 2/2/1, 4 split 2/1/1, 3 split 1/1/1. The stop stays where it started. |
| **V3** | Level to level | One stop, one target: the next level in the trade's direction at least 1R away. If there's none, 2R (this happened 2 times out of 22). |
| **V4** | 2R + trail | Your Rulebook steps 6–7. At 2R, close all lots but one. The last lot's stop goes to break-even, then trails behind each new 1-hour swing low (longs) or swing high (shorts), with no time limit. |

## Results: every setup, every exit

Shorts and longs are shown as *trades · net $*. Bold marks the best exit for each setup.

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


**Why Total R and Net $ disagree:** net $ includes fees ($15 on a 5-lot trade), and some trades risk under $300 because of lot rounding or the 5-lot cap. Net $ is what hits your account, so go by that.

## Results by level

The trade count and wins are for V1. The other columns show each exit's net $ for that level.

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


**Levels that never traded:** prior day high, prior day low and VAH never gave a signal in London that passed the trend filter.

## Every trade, all four exits side by side

**NEW 2: 15m rejection wick**

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


"skipped" means V2 was still holding the earlier Oct 29 trade when this signal came.

**NEW 1: 5m engulfing**

| Day | Time ET | Side | Level | Entry | Stop | Lots | V1 2R | V2 ladder | V3 level | V4 trail |
|---|---|---|---|--:|--:|--:|--:|--:|--:|--:|
| 2026-10-26 | 04:55 | Short | Asia high | 4030.6 | 4035.8 | 5 | −$275 | −$275 | −$275 | −$275 |
| 2026-10-27 | 04:05 | Short | VAL | 4009.6 | 4015.0 | 5 | −$285 | −$285 | −$285 | −$285 |
| 2026-10-29 | 03:10 | Short | VAL | 4045.2 | 4049.6 | 5 | +$425 | +$441 | +$380 | +$337 |
| 2026-11-04 | 03:30 | Long | Asia high | 4043.6 | 4037.0 | 4 | +$516 | +$538 | +$516 | +$384 |


## My opinions

**On the exits**

- **V1, fixed 2R. Keep it as your default.** It's simple and it was solid on both new setups, never the worst exit on either. Your 5-month playbook test said the same thing: 2R beat everything.
- **V2, pip ladder (100/150/200). Drop it, or tie the targets to R.** It won the 5m test by only $38, and it was the worst exit on the 15m wick (−$281 versus 2R). Your typical stop here was 5–6 points, so 100 pips was under 2R. You banked less on winners while losers still cost the full $300. Pip targets ignore the size of your stop, which is exactly what your Rulebook warns about ("never a pip number").
- **V3, level to level. Highest win rate, smaller wins.** It won 50% on the 15m wick, but the next level was often only 1.1–1.8R away, so it made less than plain 2R. The next level makes a good *check* on a trade, but a weak *target*. One surprise: the trades with under 2R of room to the next level did *better* at 2R (4 wins of 7, +$964) than the ones with 2R+ room (3 of 9, −$150). Gold was falling, so price ran straight through levels. That's too few trades to change your 2R-room rule.
- **V4, 2R + trail. Best on the 15m wick (+$595), worst on the 5m engulfing (+$161).** Two runners caught big moves: Sep 23 ran into the evening, and Oct 14 went to 3.3R overall. On the 5m it gave back what 2R would have banked. It's the closest to how your Rulebook says to manage, so it's the one to keep paper-logging. It needs 30+ trades before it beats 2R for sure.

**On the levels**

- **VAL shorts were the standout.** Price came up into the prior day's VAL from below and rejected: 4 wins of 5 on the 15m wick, +$1,484 at 2R. That's the setup to watch.
- **Asia high shorts lost every time.** 0 of 3 on the new setups and 0 of 4 on sweep and reclaim: 7 losses from 7 trades. In this falling market, a London push up to the Asia high kept breaking through.
- **Longs barely got a chance.** The trend filter allowed just 3 longs across the two new setups, and 1 won. Don't judge longs from this; they need a rising market to test.

**On the setups**

- **15m rejection wick is the best of the four,** finishing green under every exit, but it's 12 trades.
- **5m engulfing is too small to call** with 4 trades.
- **The two Rulebook stand-ins (sweep and reclaim, VAH/VAL close inside) lost under every exit,** but each had only 2 to 4 trades, too few to judge.

**Bottom line:** nothing here is strong enough to change your rules. Keep **2R** as the main exit, paper-log the **V4 runner** next to it, keep an eye on **VAL shorts**, and drop the **pip ladder**. Then rerun this once there's more data (see below).

## Next steps

1. **Send the v11 file** (paste the text) and I'll add those tests to these tables.
2. **More data.** Export longer 5m/15m history from TradingView on your computer and add it to `data/`, or get a plan with Deep Backtesting, or use a data provider such as Databento (you'd add the API key in the environment's settings).
3. **Paper-log 20 London sessions** of the 15m wick with both 2R and the V4 runner.

## How to rerun

```
python3 backtest/run_backtest.py      # runs every setup × exit, writes claude/trades/*.csv
python3 backtest/make_tables.py main  # prints the main table
```

All rules sit at the top of `backtest/run_backtest.py`. Trade lists: `claude/trades/all_trades.csv`. By level: `claude/trades/by_level.csv`.

Not financial advice. Results from 2 to 12 trades say almost nothing about the future.
