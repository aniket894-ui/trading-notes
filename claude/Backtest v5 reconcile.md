# Backtest v5 reconcile: TradingView vs Claude Code

Run Nov 18, 2026. Code: `backtest/v5_reconcile.py`. Files: `claude/v5_reconcile/`.
TradingView trade list: `claude/v5_reconcile/tv_v5_trades.csv` (export of "Gold v5 core - sweep and reclaim", MGC1!, 15m).

## Short answer

- **Both numbers are calculated correctly.** Python with the TradingView rules matches all 49 TradingView trades I have data for, to the dollar. Python with the base rules gives exactly −$1,186, the same as `ablation.py`.
- **The gap is rules, not bugs.** Nearly all of it comes from one rule: the trend filter.
- **TradingView v5 makes its money on shorts against the 1H trend:** 31 trades, +$5,688. Its shorts that went with the 1H trend lost −$942. That breaks your own rule (shorts only when momentum is bearish), and it only worked because gold fell all autumn.
- **Neither version is proven.** TradingView's filter was chosen after seeing that shorts won in these same 11 weeks.

## Results

| Version | Dates | Trades | Win % | Net $ |
|---|---|--:|--:|--:|
| TradingView v5 (its list) | Sep 1 – Nov 17 | 50 | 52% | **+$5,574** |
| TradingView v5 (its list), dates I have data for | Sep 1 – Nov 13 | 49 | 51% | +$4,911 |
| **Python, TradingView rules** | Sep 1 – Nov 13 | 49 | 51% | **+$4,911** |
| Python, base rules (= `ablation.py` base v5) | Sep 1 – Nov 13 | 65 | 34% | **−$1,186** |

My 15m data ends Nov 13, so the TradingView trade on Nov 16 (+$663) can't be rerun. I couldn't fetch Nov 14–17: the TradingView tool hit its daily limit.

## 1. The rules side by side

| Rule | TradingView v5 | Claude Code base v5 |
|---|---|---|
| Levels | Highest high / lowest low of the last 20 bars (5 hours) | PD high/low, PW high/low, Asia high/low, 1H swing highs/lows |
| Sweep | Wick past the level, close back inside, **red close for shorts, green for longs** | Wick past the level, close back inside, prior candle also inside, any colour. Touches 1–3 only |
| Trend filter | **Longs only if the last finished 1H candle closes above its 20 EMA. Shorts: no filter** | Shorts only if the 15m close is under the 4H 20 EMA, longs only if above |
| Time window | Signal candle 03:00–10:30. Anything open is closed at the 11:15 open | Signal candle 03:00–10:45 (closes by 11:00). Hold until 16:45 |
| Entry | Next candle's open | Signal close, 1 tick worse |
| Stop | Wick + 0.5. Skip if more than 15 pts from the signal close | Wick + 0.5. No cap |
| Target | 2R, measured from the signal close | 2R, measured from the entry |
| Sizing | Always 3 lots | $300 ÷ risk, 3–5 lots, skip if under 3 |
| Fees | $3 per trade ($1 per contract) | $1.50 per contract |
| Slippage | None | 1 tick on entries, stops, time exits |
| Stop and target in the same candle | TradingView's guess from the candle shape | Stop counts |
| Trade limits | 1 at a time, 2 a day, done after 2 losses. Can re-enter on the candle that closed the last trade. A day = CME trade date | Same limits. No re-entry on the exit candle. A day = 18:00 to 17:00 |
| Dates | Sep 1 – Nov 17 (list runs Jun 4 – Nov 16) | Sep 1 – Nov 13 |

## 2. TradingView rules I can't confirm

I couldn't open the Pine code: the TradingView tool is at its daily limit. These rules come from the trade list and the chat log, and the 49/49 exact match backs them, but **please confirm each one:**

1. **Long trend filter = last finished 1H close above the 1H 20 EMA.** The chat log only says "no longs unless the 1H is bullish". This reading matches all 8 longs. Using the 15m close instead loses 2 of them.
2. **Long entry is the mirror of the short** (sweep of the 20-bar low, green close). The chat log cuts off before the long rule.
3. **Labor Day counts as Sep 8.** On Sep 8 TradingView skipped a short that Python took (+$321). That's explained if Sep 7's holiday session counts toward Sep 8, which then already had 2 trades. That's how CME dates it, but I can't see the code.
4. **Window end.** No signal ever came at 10:45, so 10:30 vs 10:45 changes nothing here.
5. **Commission setting.** $3 per 3-lot trade. It could be $1 per contract or $1.50 per order. Same result either way.

## 3. Trade by trade (Sep 1 – Nov 13)

| | Trades |
|---|--:|
| In both, same entry, exit and $ | **49** |
| TradingView only | 1: Nov 16 short, +$663, after my data ends |
| Python only | 0 |

Full list: `claude/v5_reconcile/trade_by_trade.csv`.

On the first run, 3 trades didn't match. Each one was fixed by reading the rule more carefully, not by tuning:
- **Sep 25 and Oct 2 longs (TradingView only):** I first tested the 15m close against the 1H EMA. TradingView uses the 1H candle's own close.
- **Sep 8, 09:15 short (Python only):** the Labor Day trade-date rule above.

## 4. One change at a time, from TradingView to base

| Step | Trades | Win % | Net $ | Change |
|---|--:|--:|--:|--:|
| TradingView rules (Python) | 49 | 51% | +$4,911 | |
| + base window | 49 | 51% | +$4,911 | $0 |
| + base trend filter (4H EMA, both sides) | 29 | 28% | −$1,368 | **−$6,279** |
| + base levels | 71 | 32% | −$1,887 | −$519 |
| + base entry and target | 71 | 32% | −$1,947 | −$60 |
| + no 15-pt stop cap | 74 | 35% | +$615 | +$2,562 |
| + $300 risk sizing, 3–5 lots | 67 | 33% | −$1,736 | −$2,351 |
| + $1.50 fees | 67 | 33% | −$1,882 | −$146 |
| + base exits (stop first, slippage, hold to 16:45) | 65 | 34% | **−$1,186** | +$696 |
| + base day count | 65 | 34% | −$1,186 | $0 |

Each of the three named changes alone, starting from the TradingView rules: window $0 (+$4,911), trend −$6,279 (−$1,368), levels −$3,699 (+$1,212).

## Causes of the gap (+$5,574 vs −$1,186 = $6,760)

1. **Trend filter: −$6,279.** TradingView takes every short. Base skips shorts above the 4H EMA, and those were TradingView's best trades: 23 shorts above the 4H EMA made +$5,226.
2. **Dates: −$663.** TradingView includes Nov 16. Base stops at Nov 13.
3. **Levels: −$519.** Different levels, a red/green close required, no touch limit.
4. **Stop cap and sizing roughly cancel: +$211.** With no cap, a few wide-stop winners at 3 lots add +$2,562. $300 sizing then skips those same wide stops (−$2,351).
5. **Exits, fees, fills: +$490.** Holding to 16:45 helped a bit. Fees and slippage cost a little.
6. **Window: $0.**

## Which version is right

- **Both are calculated right.** Each one is rebuilt to the dollar.
- **Base is closer to how you trade:** $300 risk, 3–5 lots, real slippage, and a trend filter on both sides, like your rulebook.
- **TradingView v5's profit is a bet on a falling market.** It fades rallies, and 31 of its 41 shorts were taken while the 1H was bullish. If gold turns up, that bet flips.
- **To test it fairly:** rerun the TradingView rules on a rising stretch of gold, or on 12 months of data. Only 11 weeks of a falling market are tested here.

Not financial advice.
