"""
MGC London-session backtest: 5m engulfing at level, 15m rejection wick at level,
plus Rulebook Setups A and B as reference rows.

Rules shared by every test (from Aniket's spec):
  - $300 risk per trade, lots = floor(300 / (stop_pts * $10)), max 5 lots, skip if < 1 lot
  - Target 2R, stop 1 tick past the signal candle
  - Max 2 trades a day, done after 2 losses, one position at a time
  - Signal candle must open and close inside London 3:00-5:00 AM ET
  - 1-hour trend filter: longs only when the last closed 1h candle closed above the 1h EMA50,
    shorts only when below
  - Entry at the signal candle's close. If a bar hits both stop and target, the stop counts.
  - Open trades are closed at the last bar before the 5 PM ET daily halt.
  - Fees: $3 per contract round trip.

Levels (computed from 15m bars, available before the London open):
  - Asia high / low: 6 PM ET (prior evening) to 3 AM ET
  - Prior day high / low: full prior session, 6 PM to 5 PM ET
  - Prior day VAH / VAL: 70% value area from the prior session's volume profile
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
POINT_USD = 10.0          # MGC: $10 per point
MAX_LOTS = 5
TICK = 0.1
FEE_PER_LOT = 3.0         # round trip
TARGET_R = 2.0
MAX_TRADES = 2
MAX_LOSSES = 2
TOL = 0.5                 # points: how close a wick must come to count as touching a level
EMA_LEN = 50
WIN_START, WIN_END = 3 * 60, 5 * 60   # minutes after midnight ET


def load(tf):
    df = pd.read_csv(DATA / f"MGC_{tf}.csv")
    df["et"] = pd.to_datetime(df["time_et"])
    # Trading day runs 6 PM ET to 5 PM ET; shift 6h so it maps to one calendar date
    df["tday"] = (df["et"] + pd.Timedelta(hours=6)).dt.date
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
    val = max(edges[lo_i], lo)                  # keep VA inside the day's range
    vah = min(edges[hi_i] + bin_size, hi)
    return val, vah, edges[poc] + bin_size / 2


def build_levels(m15):
    days = sorted(m15["tday"].unique())
    first_full = m15.loc[m15["mins"] == 18 * 60, "tday"].min()   # first day that starts at 6 PM
    lv = {}
    for i, d in enumerate(days):
        if d < first_full:
            continue
        today = m15[m15["tday"] == d]
        asia = today[(today["et"].dt.date < pd.Timestamp(d).date()) |
                     (today["mins"] < WIN_START)]
        rec = {}
        if len(asia):
            rec["Asia high"] = asia["high"].max()
            rec["Asia low"] = asia["low"].min()
        if i > 0 and days[i - 1] >= first_full:
            prev = m15[m15["tday"] == days[i - 1]]
            rec["Prior day high"] = prev["high"].max()
            rec["Prior day low"] = prev["low"].min()
            val, vah, _ = value_area(prev)
            rec["VAH"] = vah
            rec["VAL"] = val
        lv[d] = rec
    return lv


def trend_series(h1):
    ema = h1["close"].ewm(span=EMA_LEN, adjust=False).mean()
    close_time = h1["et"] + pd.Timedelta(hours=1)
    return pd.DataFrame({"close_time": close_time, "up": h1["close"] > ema}).reset_index(drop=True)


def trend_at(tr, t):
    i = tr["close_time"].searchsorted(t, side="right") - 1
    return None if i < 0 else bool(tr["up"].iloc[i])


# ---------- signal definitions ----------
# Each returns a list of (direction, stop, level_name) for bar i, or [].

def touched_long(low, close, level):
    return low <= level + TOL and close > level


def touched_short(high, close, level):
    return high >= level - TOL and close < level


def sig_engulf(df, i, levels):
    if i == 0:
        return []
    p, c = df.iloc[i - 1], df.iloc[i]
    out = []
    bull = p.close < p.open and c.close > c.open and c.close >= p.open and c.open <= p.close
    bear = p.close > p.open and c.close < c.open and c.close <= p.open and c.open >= p.close
    lo, hi = min(p.low, c.low), max(p.high, c.high)
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
    """Setup A: runs past Asia / prior day high or low, closes back inside."""
    c = df.iloc[i]
    out = []
    for name, lvl in levels.items():
        if name.endswith("low") and c.low < lvl and c.close > lvl:
            out.append((1, round(c.low - TICK, 1), name))
        if name.endswith("high") and c.high > lvl and c.close < lvl:
            out.append((-1, round(c.high + TICK, 1), name))
    return out


def sig_va(df, i, levels):
    """Setup B: 15m pokes outside value (VAH/VAL) and closes back inside."""
    c = df.iloc[i]
    out = []
    if "VAL" in levels and c.low < levels["VAL"] and c.close > levels["VAL"]:
        out.append((1, round(c.low - TICK, 1), "VAL"))
    if "VAH" in levels and c.high > levels["VAH"] and c.close < levels["VAH"]:
        out.append((-1, round(c.high + TICK, 1), "VAH"))
    return out


# ---------- engine ----------

def run(name, df, tf_min, signal_fn, levels, trend, start_day):
    trades = []
    bar_close = df["et"] + pd.Timedelta(minutes=tf_min)
    for d, day in df[df["tday"] >= start_day].groupby("tday"):
        if d not in levels or d.weekday() >= 5:
            continue
        lv = levels[d]
        if not lv:
            continue
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
            # nearest level wins if several qualify
            direction, stop, lvl_name = min(sigs, key=lambda s: abs(entry - lv[s[2]]))
            risk = (entry - stop) * direction
            if risk <= 0:
                continue
            lots = min(MAX_LOTS, int(RISK_USD // (risk * POINT_USD)))
            if lots < 1:
                continue
            target = entry + direction * TARGET_R * risk
            # walk forward
            result, exit_px, j = None, None, i
            for j in idx[idx > i]:
                lo, hi = df.at[j, "low"], df.at[j, "high"]
                hit_stop = lo <= stop if direction == 1 else hi >= stop
                hit_tgt = hi >= target if direction == 1 else lo <= target
                if hit_stop:
                    result, exit_px = "loss", stop
                    break
                if hit_tgt:
                    result, exit_px = "win", target
                    break
            if result is None:                     # session ended
                exit_px = df.at[j, "close"]
                result = "time"
            r_mult = (exit_px - entry) * direction / risk
            usd = (exit_px - entry) * direction * lots * POINT_USD - FEE_PER_LOT * lots
            trades.append(dict(test=name, tday=str(d), time_et=df.at[i, "et"].strftime("%H:%M"),
                               side="Long" if direction == 1 else "Short", level=lvl_name,
                               level_px=round(lv[lvl_name], 1), entry=entry, stop=stop,
                               target=round(target, 1), risk_pts=round(risk, 1), lots=lots,
                               result=result, exit=round(exit_px, 1),
                               exit_et=df.at[j, "et"].strftime("%m-%d %H:%M"),
                               R=round(r_mult, 2), usd=round(usd, 2)))
            n_tr += 1
            if usd < 0:
                n_loss += 1
            busy_until = j
    return pd.DataFrame(trades)


def summarize(t):
    if t.empty:
        return dict(Trades=0, Wins=0, Losses=0, Win=np.nan, R=0.0, Net=0.0, DD=0.0, AvgLots=np.nan)
    eq = t["usd"].cumsum()
    dd = (eq - eq.cummax().clip(lower=0)).min()
    return dict(Trades=len(t), Wins=int((t["R"] > 0).sum()), Losses=int((t["R"] <= 0).sum()),
                Win=(t["R"] > 0).mean(), R=t["R"].sum(), Net=t["usd"].sum(), DD=dd,
                AvgLots=t["lots"].mean())


def main():
    m5, m15, h1 = load("5m"), load("15m"), load("1h")
    levels = build_levels(m15)
    trend = trend_series(h1)

    # first trading day with a complete prior day of levels in each dataset
    lv_days = sorted(d for d, v in levels.items() if "VAH" in v)
    start_15 = lv_days[0]
    start_5 = min(d for d in lv_days if d > m5["tday"].min())

    tests = [
        ("NEW 1 - 5m engulfing at level", m5, 5, sig_engulf, start_5),
        ("NEW 2 - 15m rejection wick at level", m15, 15, sig_wick, start_15),
        ("REF A - 15m sweep & reclaim (Rulebook)", m15, 15, sig_sweep, start_15),
        ("REF B - 15m VAH/VAL close back inside (Rulebook)", m15, 15, sig_va, start_15),
        # Same 15m tests clipped to the 5m window so they line up with NEW 1
        ("NEW 2 - 15m wick, 5m window only", m15, 15, sig_wick, start_5),
    ]
    OUT.mkdir(parents=True, exist_ok=True)
    rows, all_trades = [], []
    for name, df, tf, fn, start in tests:
        t = run(name, df, tf, fn, levels, trend, start)
        all_trades.append(t)
        last = df["tday"].max()
        for side in ["All", "Shorts", "Longs"]:
            sub = t if side == "All" or t.empty else t[t["side"] == side[:-1]]
            s = summarize(sub)
            rows.append(dict(Test=name, Side=side, From=str(start), To=str(last), **s))
    res = pd.DataFrame(rows)
    trades = pd.concat(all_trades, ignore_index=True)
    trades.to_csv(OUT / "all_trades.csv", index=False)
    res.to_csv(OUT / "summary.csv", index=False)
    pd.set_option("display.width", 220)
    pd.set_option("display.max_columns", 20)
    print(res.to_string(index=False, float_format=lambda x: f"{x:,.2f}"))
    print("\nlevels sample:", list(levels.items())[-1])


if __name__ == "__main__":
    sys.exit(main())
