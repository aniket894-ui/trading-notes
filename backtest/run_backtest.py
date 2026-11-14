"""
MGC London-session backtest, v12b.

Setups (entries):
  NEW 1  5m engulfing candle at a level, stop past the engulfing candle
  NEW 2  15m rejection wick at a level, stop past the wick
  REF A  15m sweep and reclaim of Asia / prior day high or low (Rulebook Setup A)
  REF B  15m poke outside VAH/VAL and close back inside (Rulebook Setup B)

Exits (each setup runs with all four; entry and stop never change):
  V1  Fixed 1:2R, every lot out at 2R
  V2  Pip ladder, one tranche per target: TP1 100 pips (10 pts), TP2 150 pips (15 pts),
      TP3 200 pips (20 pts). Lots split 1->1, 2->1/1, 3->1/1/1, 4->2/1/1, 5->2/2/1.
      The stop stays where it started.
  V3  Level to level, one target: the nearest level in the trade's direction that is at
      least 1R away. Falls back to 2R when no level is far enough (counted in the output).
  V4  Trail (Rulebook steps 6-7): at 2R close all lots but one. The last lot's stop moves to
      break-even, then trails behind each new confirmed 1-hour swing low (longs) or swing high
      (shorts). It closes only on that stop. A one-lot trade is just the runner.

Rules shared by every test (Aniket's spec):
  - $300 risk, lots = floor(300 / (stop pts * $10)), max 5 lots, skip if under 1 lot
  - Max 2 trades a day, done after 2 losing trades
  - One trade at a time: a new trade can start once the open one is closed or risk-free
    (V4 after its 2R take-profit)
  - The signal candle opens and closes inside London, 3:00 to 5:00 AM ET
  - 1-hour trend filter: longs only if the last closed 1h candle closed above the 1h EMA50,
    shorts only if below
  - Entry at the signal candle's close. If a bar hits the stop and a target, the stop counts.
  - V1-V3: lots still open are closed at the last bar before the 5 PM ET halt
  - Fees: $3 per contract round trip

Levels (from 15m bars, known before London opens):
  Asia high / low (6 PM to 3 AM ET), prior day high / low, prior day VAH / VAL (70% value area)
"""
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = ROOT / "claude" / "trades"

RISK_USD = 300.0
POINT_USD = 10.0          # MGC: $10 per point; 1 pip = 0.1 point
MAX_LOTS = 5
TICK = 0.1
FEE_PER_LOT = 3.0         # round trip
MAX_TRADES = 2
MAX_LOSSES = 2
TOL = 0.5                 # points: how close a wick must come to count as touching a level
EMA_LEN = 50
WIN_START, WIN_END = 3 * 60, 5 * 60   # minutes after midnight ET
LADDER_PTS = [10.0, 15.0, 20.0]       # 100, 150, 200 pips
LADDER_SPLIT = {1: [1], 2: [1, 1], 3: [1, 1, 1], 4: [2, 1, 1], 5: [2, 2, 1]}


# ---------------------------------------------------------------- data

def load(tf):
    df = pd.read_csv(DATA / f"MGC_{tf}.csv")
    df["et"] = pd.to_datetime(df["time_et"])
    df["tday"] = (df["et"] + pd.Timedelta(hours=6)).dt.date   # 6 PM-5 PM session -> one date
    df["mins"] = df["et"].dt.hour * 60 + df["et"].dt.minute
    return df.reset_index(drop=True)


def value_area(bars, bin_size=0.5, pct=0.70):
    lo, hi = bars["low"].min(), bars["high"].max()
    edges = np.arange(math.floor(lo / bin_size) * bin_size, hi + bin_size, bin_size)
    vol = np.zeros(len(edges))
    for l, h, v in zip(bars["low"], bars["high"], bars["volume"]):
        a = int((l - edges[0]) // bin_size)
        b = int((h - edges[0]) // bin_size)
        vol[a:b + 1] += v / (b - a + 1)
    poc = int(vol.argmax())
    lo_i = hi_i = poc
    total, acc = vol.sum(), vol[poc]
    while acc < pct * total and (lo_i > 0 or hi_i < len(vol) - 1):
        up = vol[hi_i + 1] if hi_i < len(vol) - 1 else -1
        dn = vol[lo_i - 1] if lo_i > 0 else -1
        if up >= dn:
            hi_i += 1
            acc += up
        else:
            lo_i -= 1
            acc += dn
    return max(edges[lo_i], lo), min(edges[hi_i] + bin_size, hi)


def build_levels(m15):
    days = sorted(m15["tday"].unique())
    first_full = m15.loc[m15["mins"] == 18 * 60, "tday"].min()
    lv = {}
    for i, d in enumerate(days):
        if d < first_full:
            continue
        today = m15[m15["tday"] == d]
        asia = today[(today["et"].dt.date < d) | (today["mins"] < WIN_START)]
        rec = {}
        if len(asia):
            rec["Asia high"] = asia["high"].max()
            rec["Asia low"] = asia["low"].min()
        if i > 0 and days[i - 1] >= first_full:
            prev = m15[m15["tday"] == days[i - 1]]
            rec["Prior day high"] = prev["high"].max()
            rec["Prior day low"] = prev["low"].min()
            rec["VAL"], rec["VAH"] = value_area(prev)
        lv[d] = rec
    return lv


def trend_series(h1):
    ema = h1["close"].ewm(span=EMA_LEN, adjust=False).mean()
    return pd.DataFrame({"close_time": h1["et"] + pd.Timedelta(hours=1),
                         "up": h1["close"] > ema}).reset_index(drop=True)


def trend_at(tr, t):
    i = tr["close_time"].searchsorted(t, side="right") - 1
    return None if i < 0 else bool(tr["up"].iloc[i])


def swing_series(h1):
    """1h pivot lows/highs (lower/higher than the candle each side), known once the next candle closes."""
    lo, hi = h1["low"].values, h1["high"].values
    rows = []
    for k in range(1, len(h1) - 1):
        known = h1["et"].iloc[k + 1] + pd.Timedelta(hours=1)
        if lo[k] < lo[k - 1] and lo[k] < lo[k + 1]:
            rows.append((known, "low", lo[k]))
        if hi[k] > hi[k - 1] and hi[k] > hi[k + 1]:
            rows.append((known, "high", hi[k]))
    s = pd.DataFrame(rows, columns=["known", "kind", "px"]).sort_values("known")
    return (s[s.kind == "low"].reset_index(drop=True), s[s.kind == "high"].reset_index(drop=True))


def last_swing(sw, t):
    i = sw["known"].searchsorted(t, side="right") - 1
    return None if i < 0 else float(sw["px"].iloc[i])


# ---------------------------------------------------------------- setups
# Each returns a list of (direction, stop, level_name) for bar i.

def touched_long(low, close, level):
    return low <= level + TOL and close > level


def touched_short(high, close, level):
    return high >= level - TOL and close < level


def sig_engulf(df, i, levels):
    if i == 0:
        return []
    p, c = df.iloc[i - 1], df.iloc[i]
    bull = p.close < p.open and c.close > c.open and c.close >= p.open and c.open <= p.close
    bear = p.close > p.open and c.close < c.open and c.close <= p.open and c.open >= p.close
    lo, hi = min(p.low, c.low), max(p.high, c.high)
    out = []
    for name, lvl in levels.items():
        if bull and touched_long(lo, c.close, lvl):
            out.append((1, round(c.low - TICK, 1), name))
        if bear and touched_short(hi, c.close, lvl):
            out.append((-1, round(c.high + TICK, 1), name))
    return out


def sig_wick(df, i, levels):
    c = df.iloc[i]
    rng = c.high - c.low
    if rng <= 0:
        return []
    lower = min(c.open, c.close) - c.low
    upper = c.high - max(c.open, c.close)
    out = []
    for name, lvl in levels.items():
        if lower >= 0.5 * rng and touched_long(c.low, c.close, lvl):
            out.append((1, round(c.low - TICK, 1), name))
        if upper >= 0.5 * rng and touched_short(c.high, c.close, lvl):
            out.append((-1, round(c.high + TICK, 1), name))
    return out


def sig_sweep(df, i, levels):
    c = df.iloc[i]
    out = []
    for name, lvl in levels.items():
        if name.endswith("low") and c.low < lvl and c.close > lvl:
            out.append((1, round(c.low - TICK, 1), name))
        if name.endswith("high") and c.high > lvl and c.close < lvl:
            out.append((-1, round(c.high + TICK, 1), name))
    return out


def sig_va(df, i, levels):
    c = df.iloc[i]
    out = []
    if "VAL" in levels and c.low < levels["VAL"] and c.close > levels["VAL"]:
        out.append((1, round(c.low - TICK, 1), "VAL"))
    if "VAH" in levels and c.high > levels["VAH"] and c.close < levels["VAH"]:
        out.append((-1, round(c.high + TICK, 1), "VAH"))
    return out


# ---------------------------------------------------------------- exits
# Each exit gets the bars after entry and returns a dict:
#   pts_lots: sum over tranches of (exit - entry) * dir * lots
#   free_at:  index where the trade became closed or risk-free
#   end_at:   index where the last lot closed
#   exit_note

def _walk_targets(df, fwd, d, entry, stop, tranches):
    """tranches: list of (target_price, lots). Stop applies to every lot still open."""
    open_tr = list(tranches)
    pts_lots, notes = 0.0, []
    j = fwd[0] if len(fwd) else None
    for j in fwd:
        lo, hi = df.at[j, "low"], df.at[j, "high"]
        if (lo <= stop) if d == 1 else (hi >= stop):
            for _, n in open_tr:
                pts_lots += (stop - entry) * d * n
            if open_tr:
                notes.append(f"SL x{sum(n for _, n in open_tr)}")
            open_tr = []
            break
        still = []
        for tgt, n in open_tr:
            if (hi >= tgt) if d == 1 else (lo <= tgt):
                pts_lots += (tgt - entry) * d * n
                notes.append(f"TP x{n}")
            else:
                still.append((tgt, n))
        open_tr = still
        if not open_tr:
            break
    if open_tr:                                   # end of session
        px = df.at[j, "close"]
        for _, n in open_tr:
            pts_lots += (px - entry) * d * n
        notes.append(f"time x{sum(n for _, n in open_tr)}")
    return dict(pts_lots=pts_lots, free_at=j, end_at=j, exit_note=" ".join(notes),
                exit_et=df.at[j, "et"].strftime("%m-%d %H:%M"))


def exit_fixed_2r(df, fwd_day, fwd_all, d, entry, stop, lots, risk, ctx):
    return _walk_targets(df, fwd_day, d, entry, stop, [(entry + d * 2 * risk, lots)])


def exit_ladder(df, fwd_day, fwd_all, d, entry, stop, lots, risk, ctx):
    split = LADDER_SPLIT[lots]
    tranches = [(entry + d * LADDER_PTS[k], n) for k, n in enumerate(split)]
    return _walk_targets(df, fwd_day, d, entry, stop, tranches)


def exit_level(df, fwd_day, fwd_all, d, entry, stop, lots, risk, ctx):
    ahead = sorted(((p - entry) * d for p in ctx["levels"].values() if (p - entry) * d >= risk))
    if ahead:
        tgt, note = entry + d * ahead[0], "level"
    else:
        tgt, note = entry + d * 2 * risk, "no level, 2R"
    r = _walk_targets(df, fwd_day, d, entry, stop, [(tgt, lots)])
    r["exit_note"] = f"{note} {round((tgt - entry) * d / risk, 1)}R: " + r["exit_note"]
    return r


def exit_trail(df, fwd_day, fwd_all, d, entry, stop, lots, risk, ctx):
    tp1 = entry + d * 2 * risk
    core = lots - 1
    runner_stop = stop
    pts_lots, notes = 0.0, []
    free_at, tp1_hit = None, False
    sw = ctx["swing_lo"] if d == 1 else ctx["swing_hi"]
    j = fwd_all[0]
    for j in fwd_all:
        lo, hi = df.at[j, "low"], df.at[j, "high"]
        if tp1_hit:                               # trail on 1h swings known at this bar's open
            s = last_swing(sw, df.at[j, "et"])
            if s is not None:
                cand = round(s - TICK, 1) if d == 1 else round(s + TICK, 1)
                runner_stop = max(runner_stop, cand) if d == 1 else min(runner_stop, cand)
        if (lo <= runner_stop) if d == 1 else (hi >= runner_stop):
            n = 1 + (0 if tp1_hit else core)
            op = df.at[j, "open"]                 # price already past the stop: fill at the open
            fill = min(op, runner_stop) if d == 1 else max(op, runner_stop)
            pts_lots += (fill - entry) * d * n
            notes.append(("trail" if tp1_hit else "SL") + f" x{n}")
            if free_at is None:
                free_at = j
            break
        if not tp1_hit and ((hi >= tp1) if d == 1 else (lo <= tp1)):
            tp1_hit = True
            if core:
                pts_lots += 2 * risk * core
                notes.append(f"TP1 x{core}")
            runner_stop = entry                   # runner is now a free trade
            free_at = j
    else:                                         # data ended with the runner still open
        n = 1 + (0 if tp1_hit else core)
        pts_lots += (df.at[j, "close"] - entry) * d * n
        notes.append(f"open at data end x{n}")
        free_at = free_at or j
    return dict(pts_lots=pts_lots, free_at=free_at, end_at=j, exit_note=" ".join(notes),
                exit_et=df.at[j, "et"].strftime("%m-%d %H:%M"))


EXITS = [("V1 fixed 2R", exit_fixed_2r), ("V2 ladder 100/150/200 pips", exit_ladder),
         ("V3 level to level", exit_level), ("V4 2R + trail 1 runner", exit_trail)]


# ---------------------------------------------------------------- engine

def run(test, df, tf_min, signal_fn, exit_name, exit_fn, levels, trend, swings, start_day):
    trades = []
    bar_close = df["et"] + pd.Timedelta(minutes=tf_min)
    all_idx = df.index
    for d, day in df[df["tday"] >= start_day].groupby("tday"):
        if d not in levels or not levels[d] or d.weekday() >= 5:
            continue
        lv = levels[d]
        n_tr = n_loss = 0
        busy_until = -1
        idx = day.index
        for i in idx:
            m = df.at[i, "mins"]
            if m < WIN_START or m + tf_min > WIN_END or df.at[i, "et"].date() != d:
                continue
            if i <= busy_until or n_tr >= MAX_TRADES or n_loss >= MAX_LOSSES:
                continue
            sigs = signal_fn(df, i, lv)
            if not sigs:
                continue
            up = trend_at(trend, bar_close[i])
            if up is None:
                continue
            sigs = [s for s in sigs if (s[0] == 1) == up]
            if not sigs:
                continue
            entry = df.at[i, "close"]
            direction, stop, lvl_name = min(sigs, key=lambda s: abs(entry - lv[s[2]]))
            risk = (entry - stop) * direction
            if risk <= 0:
                continue
            lots = min(MAX_LOTS, int(RISK_USD // (risk * POINT_USD)))
            if lots < 1:
                continue
            ctx = dict(levels=lv, swing_lo=swings[0], swing_hi=swings[1])
            r = exit_fn(df, idx[idx > i], all_idx[all_idx > i], direction, entry, stop, lots, risk, ctx)
            usd = r["pts_lots"] * POINT_USD - FEE_PER_LOT * lots
            trades.append(dict(test=test, exit=exit_name, tday=str(d),
                               time_et=df.at[i, "et"].strftime("%H:%M"),
                               side="Long" if direction == 1 else "Short", level=lvl_name,
                               level_px=round(lv[lvl_name], 1), entry=entry, stop=stop,
                               risk_pts=round(risk, 1), lots=lots, exit_note=r["exit_note"],
                               exit_et=r["exit_et"],
                               R=round(r["pts_lots"] / (risk * lots), 2), usd=round(usd, 2)))
            n_tr += 1
            if usd < 0:
                n_loss += 1
            busy_until = r["free_at"]
    return pd.DataFrame(trades)


def summarize(t):
    if t.empty:
        return dict(Trades=0, Wins=0, Win=np.nan, R=0.0, Net=0.0, DD=0.0)
    eq = t["usd"].cumsum()
    return dict(Trades=len(t), Wins=int((t["usd"] > 0).sum()), Win=(t["usd"] > 0).mean(),
                R=t["R"].sum(), Net=t["usd"].sum(), DD=(eq - eq.cummax().clip(lower=0)).min())


def main():
    m5, m15, h1 = load("5m"), load("15m"), load("1h")
    levels = build_levels(m15)
    trend = trend_series(h1)
    swings = swing_series(h1)
    lv_days = sorted(d for d, v in levels.items() if "VAH" in v)
    start_15 = lv_days[0]
    start_5 = min(d for d in lv_days if d > m5["tday"].min())

    tests = [
        ("NEW 1 - 5m engulfing at level", m5, 5, sig_engulf, start_5),
        ("NEW 2 - 15m rejection wick at level", m15, 15, sig_wick, start_15),
        ("REF A - 15m sweep & reclaim (Rulebook)", m15, 15, sig_sweep, start_15),
        ("REF B - 15m VAH/VAL close back inside (Rulebook)", m15, 15, sig_va, start_15),
    ]
    OUT.mkdir(parents=True, exist_ok=True)
    rows, lvl_rows, all_trades = [], [], []
    for test, df, tf, fn, start in tests:
        for exit_name, exit_fn in EXITS:
            t = run(test, df, tf, fn, exit_name, exit_fn, levels, trend, swings, start)
            all_trades.append(t)
            row = dict(Test=test, Exit=exit_name, From=str(start), To=str(df["tday"].max()))
            row.update(summarize(t))
            for side in ["Short", "Long"]:
                s = summarize(t[t["side"] == side] if not t.empty else t)
                row[f"{side}s trades"], row[f"{side}s win"] = s["Trades"], s["Win"]
                row[f"{side}s R"], row[f"{side}s net"] = s["R"], s["Net"]
            rows.append(row)
            if not t.empty:
                for (lvl, side), g in t.groupby(["level", "side"]):
                    lvl_rows.append(dict(Test=test, Exit=exit_name, Level=lvl, Side=side,
                                         **summarize(g)))
    res = pd.DataFrame(rows)
    trades = pd.concat(all_trades, ignore_index=True)
    trades.to_csv(OUT / "all_trades.csv", index=False)
    res.to_csv(OUT / "summary.csv", index=False)
    pd.DataFrame(lvl_rows).to_csv(OUT / "by_level.csv", index=False)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 30)
    print(res.drop(columns=["From", "To"]).to_string(index=False, float_format=lambda x: f"{x:,.1f}"))


if __name__ == "__main__":
    sys.exit(main())
