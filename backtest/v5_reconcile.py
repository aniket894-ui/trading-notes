"""
v5 reconcile: TradingView "Gold v5 core - sweep and reclaim" vs Claude Code "base v5" (backtest/ablation.py).

One engine, one switch per rule that differs. All switches set to "tv" = the TradingView rules as read from
its trade list (claude/v5_reconcile/tv_v5_trades.csv). All set to "base" = ablation.py Cfg() exactly.
Data: data/MGC_15m.csv + data/MGC_1h.csv (15m ends Nov 13, 2026).
Run:  python backtest/v5_reconcile.py
"""
import sys
from dataclasses import dataclass, replace, asdict
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ablation as ab  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "claude" / "v5_reconcile"
TV_FILE = OUT / "tv_v5_trades.csv"
START, END = pd.Timestamp("2026-09-01"), pd.Timestamp("2026-11-17")
TICK, PT_USD = 0.1, 10.0


@dataclass(frozen=True)
class Rules:
    window: str = "tv"        # tv: signal bar 03:00-10:30, flat at the 11:15 open | base: signal bar 03:00-10:45
    trend: str = "tv"         # tv: longs need close > 1H EMA20, shorts free | 4H: both sides vs 4H EMA20 | none
    levels: str = "hh20"      # hh20: 20-bar high/low, red/green close | base: PD/PW/Asia/1H swing, touch 1-3
    fill: str = "tv"          # tv: next bar open, no slippage, target 2R off signal close
                              # base: signal close +/- 1 tick, target 2R off entry
    cap15: bool = True        # tv: skip if stop is more than 15 pts from the signal close | base: no cap
    sizing: str = "fixed3"    # fixed3 | risk300 (floor($300 / risk), 3-5 lots, skip under 3)
    fee: float = 1.0          # $ per contract round trip (TV list: $3 per 3-lot trade)
    exits: str = "tv"         # tv: TV bar path, exit fills at price, close at 11:15 open, can re-enter on exit bar
                              # base: stop first, 1 tick slip on stops/time exits, close 16:45, no re-entry on exit bar
    day: str = "tv"           # tv: daily limits by CME trade date (holiday early-close session counts as the next day)
                              # base: daily limits by 18:00-to-17:00 trading day


TV = Rules()
BASE = Rules(window="base", trend="4H", levels="base", fill="base", cap15=False, sizing="risk300", fee=1.5,
             exits="base", day="base")


def prepare():
    P = ab.prepare()
    m = P["m"]
    m["hh20"] = m["high"].shift(1).rolling(20).max()
    m["ll20"] = m["low"].shift(1).rolling(20).min()
    # last COMPLETED 1H bar: its close and its EMA20 (what request.security("60", ...) sees without lookahead)
    h1 = ab.v13.load("MGC_1h.csv")
    h1["end"] = h1["et"] + pd.Timedelta(hours=1)
    h1["ema20"] = h1["close"].ewm(span=20, adjust=False).mean()
    k = h1["end"].searchsorted(m["et"] + pd.Timedelta(minutes=15), side="right") - 1
    m["h1_close"] = np.where(k >= 0, h1["close"].values[k.clip(0)], np.nan)
    m["h1_ema"] = np.where(k >= 0, h1["ema20"].values[k.clip(0)], np.nan)
    P["cand_by_i"] = {i: g for i, g in P["cand"].groupby("i")}
    # CME trade date: a weekday session that halts before 15:00 ET (e.g. Labor Day, Sep 7) belongs to the next day
    last_bar = m.groupby("tday")["mins"].apply(lambda s: s[s < 18 * 60].max())
    days = sorted(m["tday"].unique())
    nxt = {d: days[k + 1] for k, d in enumerate(days[:-1])}
    roll = {d: nxt[d] for d in days[:-1] if d.weekday() < 5 and last_bar.get(d, 999) < 15 * 60}
    m["cme_day"] = m["tday"].map(lambda d: roll.get(d, d))
    P["holiday_roll"] = roll
    return P


def in_window(mins, w):
    if w == "tv":
        return 180 <= mins <= 630           # signal bar 03:00-10:30 -> entries 03:15-10:45
    return mins >= 180 and mins + 15 <= 660  # ablation 03-11: bar opens >= 03:00 and closes <= 11:00


def signals(P, R, i, used):
    """[(d, level_name, extreme, cand_rows)] for bar i."""
    m = P["m"]
    o, h, l, c = (m.at[i, k] for k in ("open", "high", "low", "close"))
    out = []
    if R.levels == "hh20":
        hh, ll = m.at[i, "hh20"], m.at[i, "ll20"]
        if not np.isnan(hh) and h > hh and c < hh and c < o:
            out.append((-1, "20-bar high", h, None))
        if not np.isnan(ll) and l < ll and c > ll and c > o:
            out.append((1, "20-bar low", l, None))
        return out
    g = P["cand_by_i"].get(i)
    if g is None:
        return out
    for d in (-1, 1):
        cg = g[g.d == d]
        ok = [r for _, r in cg.iterrows()
              if (r.k, d, r.test) not in used and 1 <= r.test <= 3 and r["name"] in ab.BASE_LEVELS]
        if ok:
            ext = h if d == -1 else l
            r = min(ok, key=lambda r: abs(ext - r.px))
            out.append((d, r["name"], ext, cg))
    return out


def trend_ok(m, R, i, d):
    c = m.at[i, "close"]
    if R.trend == "none":
        return True
    if R.trend in ("tv", "tv_both"):                     # last done 1H close vs 1H EMA20
        hc, he = m.at[i, "h1_close"], m.at[i, "h1_ema"]
        if d == -1:
            return R.trend == "tv" or hc < he
        return hc > he
    e = m.at[i, "ema4h"]
    return not np.isnan(e) and (c < e if d == -1 else c > e)


def run_exit(m, R, i, d, entry, stop, tgt):
    """Walk bars from i+1. Returns (exit_px, exit_bar, how)."""
    tday = m.at[i, "tday"]
    slip = TICK if R.exits == "base" else 0.0
    n = len(m)
    for j in range(i + 1, n):
        if m.at[j, "tday"] != tday:
            return m.at[j - 1, "close"] - d * slip, j - 1, "time"
        op, hi, lo = m.at[j, "open"], m.at[j, "high"], m.at[j, "low"]
        if R.exits == "tv":
            if m.at[j, "mins"] >= 675 and j > i + 1:                  # 11:15 bar: flat at its open
                return op, j, "end session"
            if (op >= stop) if d == -1 else (op <= stop):
                return op, j, "stop"
            if (op <= tgt) if d == -1 else (op >= tgt):
                return op, j, "target"
            hit_s = (hi >= stop) if d == -1 else (lo <= stop)
            hit_t = (lo <= tgt) if d == -1 else (hi >= tgt)
            if hit_s and hit_t:
                high_first = abs(hi - op) < abs(op - lo)              # TV broker emulator bar path
                stop_first = high_first if d == -1 else not high_first
                return (stop, j, "stop") if stop_first else (tgt, j, "target")
            if hit_s:
                return stop, j, "stop"
            if hit_t:
                return tgt, j, "target"
        else:
            if (hi >= stop) if d == -1 else (lo <= stop):
                fill = (max(op, stop) if d == -1 else min(op, stop)) - d * slip
                return fill, j, "stop"
            if (lo <= tgt) if d == -1 else (hi >= tgt):
                return tgt, j, "target"
    return m.at[n - 1, "close"] - d * slip, n - 1, "data end"


def backtest(P, R, start=START, end=END):
    m = P["m"]
    trades, used = [], set()
    state = dict(tday=None, n=0, loss=0)
    busy_until = -1
    for i in range(21, len(m) - 1):
        td = m.at[i, "tday"]
        if not (start <= td <= end) or td.weekday() >= 5 or not in_window(m.at[i, "mins"], R.window):
            continue
        dkey = m.at[i, "cme_day"] if R.day == "tv" else td
        if dkey != state["tday"]:
            state = dict(tday=dkey, n=0, loss=0)
        free = i >= busy_until if R.exits == "tv" else i > busy_until
        if not free or state["n"] >= 2 or state["loss"] >= 2:
            continue
        for d, lvl, ext, cg in signals(P, R, i, used):
            if not trend_ok(m, R, i, d):
                continue
            c = m.at[i, "close"]
            stop = round(ext + 0.5, 1) if d == -1 else round(ext - 0.5, 1)
            if R.cap15 and abs(stop - c) > 15.0 + 1e-9:
                continue
            if R.fill == "tv":
                entry = m.at[i + 1, "open"]
                risk_ref = c
            else:
                entry = c + (TICK if d == 1 else -TICK)
                risk_ref = entry
            risk = abs(stop - risk_ref)
            tgt = risk_ref + d * 2 * risk
            if R.sizing == "fixed3":
                lots = 3
            else:
                lots = min(5, int(300 // (abs(entry - stop) * PT_USD)))
                if lots < 3:
                    continue
            if cg is not None:
                for _, rr in cg.iterrows():
                    used.add((rr.k, d, rr.test))
            px, j, how = run_exit(m, R, i, d, entry, stop, tgt)
            usd = (px - entry) * d * PT_USD * lots - R.fee * lots
            entry_et = m.at[i + 1, "et"] if R.fill == "tv" else m.at[i, "et"] + pd.Timedelta(minutes=15)
            trades.append(dict(signal_et=m.at[i, "et"], entry_et=entry_et, side="short" if d == -1 else "long",
                               level=lvl, entry=round(entry, 1), stop=stop, target=round(tgt, 1), lots=lots,
                               exit=how, exit_et=m.at[j, "et"], exit_px=round(px, 1), usd=round(usd, 2)))
            state["n"] += 1
            state["loss"] += usd < 0
            busy_until = j
            break
    return pd.DataFrame(trades)


def load_tv():
    df = pd.read_csv(TV_FILE)
    e = df[df["Type"].str.startswith("Entry")]
    x = df[df["Type"].str.startswith("Exit")]
    t = e.merge(x, on="Trade number", suffixes=("_e", "_x"))
    return pd.DataFrame(dict(entry_et=pd.to_datetime(t["Date and time_e"]), side=t["Type_e"].str.split().str[1],
                             entry=t["Price USD_e"], exit_et=pd.to_datetime(t["Date and time_x"]),
                             exit_px=t["Price USD_x"], exit=t["Signal_x"], usd=t["Net PnL USD_e"]))


def stats(t):
    if t.empty:
        return dict(trades=0, win_pct=0.0, net=0.0)
    return dict(trades=len(t), win_pct=round(100 * (t.usd > 0).mean(), 1), net=round(t.usd.sum(), 0))


def compare(py, tv):
    k = ["entry_et", "side"]
    a = py.merge(tv, on=k, how="outer", suffixes=("_py", "_tv"), indicator=True)
    a["where"] = a["_merge"].map({"both": "both", "left_only": "python only", "right_only": "TV only"})
    a["same_result"] = (a["where"] == "both") & ((a["usd_py"] - a["usd_tv"]).abs() < 1.0)
    return a.drop(columns="_merge").sort_values("entry_et")


def main():
    P = prepare()
    data_end = P["m"]["tday"].max()
    tv = load_tv()
    tv_in = tv[(tv.entry_et >= START) & (tv.entry_et < END + pd.Timedelta(days=1))]
    tv_data = tv_in[tv_in.entry_et < data_end + pd.Timedelta(days=1)]

    for name, R in [("TV, longs-only 1H filter", TV), ("TV, 1H filter both sides", replace(TV, trend="tv_both")),
                    ("TV, no trend filter", replace(TV, trend="none"))]:
        c = compare(backtest(P, R), tv_data)
        print(f"{name}: {stats(backtest(P, R))} match={int(c['same_result'].sum())}",
              c["where"].value_counts().to_dict())
    py = backtest(P, TV)
    py.to_csv(OUT / "python_tv_rules_trades.csv", index=False)
    cmp_ = compare(py, tv_data)
    cmp_.to_csv(OUT / "trade_by_trade.csv", index=False)

    # check base mode reproduces ablation.py exactly (Sep 1 - Nov 13)
    base_mine = backtest(P, BASE)
    base_ab = ab.backtest(P, ab.Cfg(), "all")

    # one difference at a time, TV -> base
    steps = [("TradingView rules (Python)", TV)]
    order = [("+ base window 03:00-11:00", dict(window="base")),
             ("+ base trend filter (4H EMA20, both sides)", dict(trend="4H")),
             ("+ base levels (PD/PW/Asia/1H swing, touch 1-3, any candle color)", dict(levels="base")),
             ("+ base fills (close +1 tick, 2R off entry)", dict(fill="base")),
             ("+ no 15-pt stop cap", dict(cap15=False)),
             ("+ base sizing ($300 risk, 3-5 lots)", dict(sizing="risk300")),
             ("+ base fees ($1.50/contract)", dict(fee=1.5)),
             ("+ base exits (stop first, slippage, hold to 16:45)", dict(exits="base")),
             ("+ base day count (holiday session not rolled)", dict(day="base"))]
    R = TV
    for name, kw in order:
        R = replace(R, **kw)
        steps.append((name, R))
    rows = []
    for name, R in steps:
        s = stats(backtest(P, R))
        rows.append(dict(step=name, **s))
    S = pd.DataFrame(rows)
    S["change"] = S["net"].diff()
    S.to_csv(OUT / "one_change_at_a_time.csv", index=False)

    # each of the three named differences alone, from TV
    solo = [dict(step=n, **stats(backtest(P, replace(TV, **kw)))) for n, kw in order[:3]]
    pd.DataFrame(solo).to_csv(OUT / "each_change_alone.csv", index=False)

    pd.set_option("display.width", 250); pd.set_option("display.max_rows", 200); pd.set_option("display.max_columns", 30)
    print("data ends", data_end.date(), "| holiday roll:", {str(k.date()): str(v.date()) for k, v in P["holiday_roll"].items()})
    print("TV Sep1-Nov17:", stats(tv_in), "| TV inside data:", stats(tv_data), "| Python TV rules:", stats(py))
    print("base mine:", stats(base_mine), "| ablation.py base:", ab.metrics(base_ab))
    print(cmp_["where"].value_counts().to_dict(), "same result:", int(cmp_["same_result"].sum()))
    print(cmp_[["entry_et", "side", "where", "entry_py", "entry_tv", "exit_py", "exit_tv", "usd_py", "usd_tv"]].to_string(index=False))
    print(S.to_string(index=False))
    print(pd.DataFrame(solo).to_string(index=False))


if __name__ == "__main__":
    main()
