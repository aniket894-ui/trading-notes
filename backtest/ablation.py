"""
v14 ablation study: v5 sweep and reclaim, every switch ON vs OFF against the same base, then combine the winners.

Data: data/MGC_15m.csv (Aug 31 - Nov 13, 2026) and data/MGC_1h.csv (Jan 12 - Nov 13, 2026), same as v13.
Walk-forward: switches are chosen on BUILD (trading days Sep 1 - Oct 19), the final system is then run once on
TEST (Oct 20 - Nov 13), which plays no part in any choice. Same 2:1 split as the requested 8 + 4 months.
Every assumption is listed in claude/v14 ablation.md and marked ASSUMPTION here.
"""
import sys
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vah_rejection as v13  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "claude" / "v14_ablation"
BUILD_END = pd.Timestamp("2026-10-19")          # last trading day of BUILD (full-year runs override)
START_DAY = pd.Timestamp("2026-09-01")          # first trading day traded (full-year runs override)
TICK, PT_USD, FEE = 0.1, 10.0, 1.50             # $1.50 per contract round trip
SLIP = 1 * TICK                                 # 1 tick on entries, stops and market exits; none on limit targets
NEWS_FILE = ROOT / "data" / "news_days.csv"      # one column 'date' (YYYY-MM-DD); not available yet

BASE_LEVELS = {"PD high", "PD low", "PW high", "PW low", "Asia high", "Asia low",
               "1H swing high", "1H swing low"}                       # ASSUMPTION: "recent high/low"
REAL_LEVELS = {"PD VAH", "PD VAL", "PW VAH", "PW VAL", "PD high", "PD low", "Asia high", "Asia low"}


@dataclass(frozen=True)
class Cfg:
    levels: str = "base"         # base | real | base+tested | real+tested
    no_asia_high_shorts: bool = False
    max_touch: int = 3           # base blocks 4th+ touches
    trend: str = "4H"            # 4H | 1H | D | VWAP | none
    window: str = "03-11"        # 03-11 | 03-05 | 19-11
    skip_thu: bool = False
    skip_news: bool = False
    pad: float = 0.5
    exit: str = "E2"
    half_after_3_losing_days: bool = False
    weekly_cap: bool = False
    stop_after_win_loss: bool = False
    risk: float = 300.0
    min_lots: int = 3
    max_lots: int = 5
    max_trades: int = 2
    max_losses: int = 2
    side: str = "both"           # both | Short | Long (Short/Long = separate account)


# ------------------------------------------------------------------ prepare data once

def prepare():
    m = v13.load("MGC_15m.csv").reset_index(drop=True)
    h1 = v13.load("MGC_1h.csv")
    h1, h4, d1, _ = v13.build_htf(h1)
    h1["ema20"] = h1["close"].ewm(span=20, adjust=False).mean()
    m1_path = v13.DATA_DIR / "MGC_1m.csv"
    pbars = v13.load("MGC_1m.csv") if m1_path.exists() else None   # 1m volume profile when available
    L = v13.build_levels(m, h1, h4, d1, pbars=pbars)
    res, sup = v13.count_tests(m, L)
    end = m["et"] + pd.Timedelta(minutes=15)
    m["ema1h"] = [v13.last_done(h1, t, "ema20") for t in end]
    m["ema4h"] = [v13.last_done(h4, t, "ema20") for t in end]
    m["emad"] = [v13.last_done(d1, t, "ema20") for t in end]
    tp = (m["high"] + m["low"] + m["close"]) / 3                     # session VWAP from 18:00
    m["vwap"] = (tp * m["volume"]).groupby(m["tday"]).cumsum() / m["volume"].groupby(m["tday"]).cumsum()
    m["mins"] = m["et"].dt.hour * 60 + m["et"].dt.minute
    # 1H 1-bar pivots for the E7 trail, known when the next 1H bar closes
    hi, lo = h1["high"].values, h1["low"].values
    piv_h = [(h1["et"].iloc[k + 1] + pd.Timedelta(hours=1), hi[k]) for k in range(1, len(h1) - 1)
             if hi[k] > hi[k - 1] and hi[k] > hi[k + 1]]
    piv_l = [(h1["et"].iloc[k + 1] + pd.Timedelta(hours=1), lo[k]) for k in range(1, len(h1) - 1)
             if lo[k] < lo[k - 1] and lo[k] < lo[k + 1]]
    piv_h, piv_l = pd.DataFrame(piv_h, columns=["t", "px"]), pd.DataFrame(piv_l, columns=["t", "px"])

    # every sweep-and-reclaim candidate: (bar, side, level) with the test number
    t0, t1 = m["et"].values, end.values
    O, H, Lo, C = (m[c].values for c in ["open", "high", "low", "close"])
    cand = []
    for k, lv in L.iterrows():
        a = np.searchsorted(t0, np.datetime64(lv.start), "left")
        b = np.searchsorted(t1, np.datetime64(min(lv.end, pd.Timestamp("2100-01-01"))), "right")
        for i in range(max(a, 1), b):
            p = lv.px
            if H[i] > p and C[i] < p and C[i - 1] < p:                  # swept above, closed back below
                cand.append((i, -1, k, lv["name"], p, res[k].get(i, 0)))
            if Lo[i] < p and C[i] > p and C[i - 1] > p:                 # swept below, closed back above
                cand.append((i, 1, k, lv["name"], p, sup[k].get(i, 0)))
    cand = pd.DataFrame(cand, columns=["i", "d", "k", "name", "px", "test"]).sort_values(["i", "d"])
    news = set(pd.read_csv(NEWS_FILE)["date"]) if NEWS_FILE.exists() else None
    return dict(m=m, L=L, cand=cand, piv_h=piv_h, piv_l=piv_l, news=news, days=sorted(m["tday"].unique()))


# ------------------------------------------------------------------ exits

def run_exit(P, cfg, i, d, entry, stop, lots, risk, pool):
    """Returns (points x lots before fees, free_index, end_index, note). entry already includes slippage.
    Core lots (all lots for E1/E2, 2 lots otherwise) close at the target, the stop, or the 16:45 bar close.
    Runner (E3-E7): E3/E4 close at 5 PM; E5-E7 hold up to 3 trading days (entry day + 2)."""
    m = P["m"]
    tday = m.at[i, "tday"]
    ex = cfg.exit
    tgt2 = entry + d * 2 * risk
    if ex in ("E1", "E2"):
        core_tgt, core_n, run_n, rtgt = entry + d * (1.5 if ex == "E1" else 2.0) * risk, lots, 0, None
    else:
        core_tgt, core_n = tgt2, min(2, lots)
        run_n = lots - core_n
        prices = pool if ex in ("E3", "E4") else [p for n, p in pool.items()
                                                   if n in (("PD VAL", "PW VAL") if d == -1 else ("PD VAH", "PW VAH"))]
        beyond = sorted((p for p in prices if (p - tgt2) * d > 0), key=lambda p: (p - tgt2) * d)
        rtgt = beyond[0] if beyond else None
    last_day = tday
    if ex in ("E5", "E6", "E7"):
        dl = P["days"]
        last_day = dl[min(dl.index(tday) + 2, len(dl) - 1)]
    core_open, r_stop, free_at, pts, notes = True, stop, None, 0.0, []
    j = i
    for j in range(i + 1, len(m)):
        td = m.at[j, "tday"]
        if td > last_day or (core_open and td != tday):
            j -= 1
            break
        hi, lo, op = m.at[j, "high"], m.at[j, "low"], m.at[j, "open"]
        if core_open:
            if (hi >= stop) if d == -1 else (lo <= stop):
                fill = (max(op, stop) if d == -1 else min(op, stop)) - d * SLIP
                pts += (fill - entry) * d * (core_n + run_n)
                return pts, j, j, f"SL x{core_n + run_n}"
            if (lo <= core_tgt) if d == -1 else (hi >= core_tgt):
                pts += (core_tgt - entry) * d * core_n
                notes.append(f"TP x{core_n}")
                core_open, free_at = False, j
                if run_n == 0:
                    return pts, j, j, " ".join(notes)
                if ex in ("E3", "E5", "E7"):
                    r_stop = entry                                  # runner to break-even
            continue
        if ex == "E7":                                              # trail behind 1H pivots
            pv = P["piv_h"] if d == -1 else P["piv_l"]
            q = pv["t"].searchsorted(m.at[j, "et"], side="right") - 1
            if q >= 0:
                c = pv["px"].iloc[q] - d * TICK
                r_stop = min(r_stop, c) if d == -1 else max(r_stop, c)
        if (hi >= r_stop) if d == -1 else (lo <= r_stop):
            fill = (max(op, r_stop) if d == -1 else min(op, r_stop)) - d * SLIP
            pts += (fill - entry) * d * run_n
            return pts, free_at, j, " ".join(notes + [f"runner stop x{run_n}"])
        if rtgt is not None and ((lo <= rtgt) if d == -1 else (hi >= rtgt)):
            pts += (rtgt - entry) * d * run_n
            return pts, free_at, j, " ".join(notes + [f"runner target x{run_n}"])
    px = m.at[j, "close"] - d * SLIP                                # time exit, 1 tick worse
    n_left = (core_n if core_open else 0) + run_n
    pts += (px - entry) * d * n_left
    return pts, free_at if free_at is not None else j, j, " ".join(notes + [f"time x{n_left}"])


# ------------------------------------------------------------------ one backtest

def in_window(mins, w):
    if w == "03-11":
        return mins >= 180 and mins + 15 <= 660
    if w == "03-05":
        return mins >= 180 and mins + 15 <= 300
    return mins >= 19 * 60 or mins + 15 <= 660                 # 19:00 to 11:00


def backtest(P, cfg, period):
    m, L, cand = P["m"], P["L"], P["cand"]
    if cfg.skip_news and P["news"] is None:
        return None                                            # no verified news dates: not run
    days = m["tday"]
    lo_day = START_DAY
    if period == "build":
        rng = (lo_day, BUILD_END)
    elif period == "test":
        rng = (BUILD_END + pd.Timedelta(days=1), pd.Timestamp("2100-01-01"))
    else:
        rng = (lo_day, pd.Timestamp("2100-01-01"))
    allowed = {"base": BASE_LEVELS, "real": REAL_LEVELS}[cfg.levels.split("+")[0]]
    tested = cfg.levels.endswith("+tested")
    trades = []
    state = dict(tday=None, n=0, loss=0, win_then_loss=False)
    busy_until, used = -1, set()
    day_pnl, week_pnl = {}, {}
    losing_streak, half = 0, False
    last_day = None
    for i, g in cand.groupby("i", sort=True):
        td = days.iat[i]
        if not (rng[0] <= td <= rng[1]) or td.weekday() >= 5:
            continue
        if not in_window(m.at[i, "mins"], cfg.window):
            continue
        if cfg.skip_thu and td.weekday() == 3:
            continue
        if cfg.skip_news and td.strftime("%Y-%m-%d") in P["news"]:
            continue
        if td != state["tday"]:
            if state["tday"] is not None:                       # close out the previous day for the brakes
                pnl = day_pnl.get(state["tday"], 0.0)
                if state["n"]:
                    losing_streak = losing_streak + 1 if pnl < 0 else 0
                    if pnl > 0:
                        half = False
                    if cfg.half_after_3_losing_days and losing_streak >= 3:
                        half = True
            state = dict(tday=td, n=0, loss=0, win_then_loss=False)
        if i <= busy_until or state["n"] >= cfg.max_trades or state["loss"] >= cfg.max_losses:
            continue
        if cfg.stop_after_win_loss and state["win_then_loss"]:
            continue
        wk = td - pd.Timedelta(days=td.weekday())
        if cfg.weekly_cap and week_pnl.get(wk, 0.0) <= -900:
            continue
        entry_c = m.at[i, "close"]
        for d in (-1, 1):
            if cfg.side != "both" and (d == -1) != (cfg.side == "Short"):
                continue
            if state["n"] >= cfg.max_trades or i <= busy_until:
                break
            ref = {"4H": "ema4h", "1H": "ema1h", "D": "emad", "VWAP": "vwap"}.get(cfg.trend)
            if ref is not None:
                e = m.at[i, ref]
                if np.isnan(e) or ((entry_c >= e) if d == -1 else (entry_c <= e)):
                    continue
            c = g[g.d == d]
            ok = []
            for _, r in c.iterrows():
                if (r.k, d, r.test) in used or r.test < 1:
                    continue
                in_set = r["name"] in allowed
                if tested and r.test >= 3:                     # 2+ earlier rejections
                    in_set = True
                if not in_set or r.test > cfg.max_touch:
                    continue
                if cfg.no_asia_high_shorts and d == -1 and r["name"] == "Asia high":
                    continue
                ok.append(r)
            if not ok:
                continue
            ext = m.at[i, "high"] if d == -1 else m.at[i, "low"]
            r = min(ok, key=lambda r: abs(ext - r.px))
            entry = entry_c + (SLIP if d == 1 else -SLIP)             # pay 1 tick on entry
            stop = round(ext + cfg.pad, 1) if d == -1 else round(ext - cfg.pad, 1)
            risk = abs(entry - stop)
            risk_usd = cfg.risk / 2 if half else cfg.risk
            lots = min(cfg.max_lots, int(risk_usd // (risk * PT_USD)))
            if lots < cfg.min_lots:
                continue
            for _, rr in c.iterrows():
                used.add((rr.k, d, rr.test))
            active = L[(L.start <= m.at[i, "et"]) & (L.end >= m.at[i, "et"] + pd.Timedelta(minutes=15))]
            lvl_px = dict(zip(active["name"] + "|" + active.index.astype(str), active["px"]))
            lvl_px_named = {}
            for key, p in lvl_px.items():
                nm = key.split("|")[0]
                if nm in ("PD VAL", "PW VAL", "PD VAH", "PW VAH"):
                    lvl_px_named[nm] = p
            pool = list(lvl_px.values()) if cfg.exit in ("E3", "E4") else lvl_px_named
            pts, free_at, end_at, note = run_exit(P, cfg, i, d, entry, stop, lots, risk, pool)
            usd = pts * PT_USD - FEE * lots
            trades.append(dict(time_et=m.at[i, "time_et"], tday=td.date().isoformat(), side="Short" if d == -1 else "Long",
                               level=r["name"], test=int(r.test), entry=round(entry, 1), stop=stop, risk_pts=round(risk, 1),
                               lots=lots, half_risk=half, exit=note, exit_et=m.at[end_at, "time_et"], usd=round(usd, 2)))
            state["n"] += 1
            if usd < 0:
                state["loss"] += 1
                if state["n"] == 2 and trades[-2]["usd"] > 0 and trades[-2]["tday"] == trades[-1]["tday"]:
                    state["win_then_loss"] = True
            day_pnl[td] = day_pnl.get(td, 0.0) + usd
            week_pnl[wk] = week_pnl.get(wk, 0.0) + usd
            busy_until = free_at
    return pd.DataFrame(trades)


def metrics(t):
    if t is None:
        return dict(Trades=None)
    if t.empty:
        return dict(Trades=0, **{"Win %": np.nan, "Net $": 0.0, "Profit factor": np.nan, "Max DD $": 0.0, "Longest losing streak": 0})
    u = t["usd"].values
    eq = np.cumsum(u)
    dd = float((eq - np.maximum.accumulate(np.concatenate([[0.0], eq]))[1:]).min())
    gp, gl = u[u > 0].sum(), -u[u < 0].sum()
    streak = best = 0
    for x in u:
        streak = streak + 1 if x < 0 else 0
        best = max(best, streak)
    return {"Trades": len(u), "Win %": round(100 * (u > 0).mean(), 1), "Net $": round(u.sum(), 0),
            "Profit factor": round(gp / gl, 2) if gl > 0 else np.inf, "Max DD $": round(dd, 0),
            "Longest losing streak": best}


SWITCHES = [
    ("S1 only real levels", "Levels", dict(levels="real")),
    ("S2 add tested levels (2+ rejections)", "Levels", dict(levels="base+tested")),
    ("S3 drop Asia high shorts", "Levels", dict(no_asia_high_shorts=True)),
    ("S4 allow 4th+ touch re-entries", "Levels", dict(max_touch=99)),
    ("S5 1H trend", "Trend", dict(trend="1H")),
    ("S6 daily trend", "Trend", dict(trend="D")),
    ("S7 VWAP side as trend", "Trend", dict(trend="VWAP")),
    ("S8 no trend filter", "Trend", dict(trend="none")),
    ("S9 London only 3-5 AM", "Time", dict(window="03-05")),
    ("S10 Asia+London+NY 7 PM-11 AM", "Time", dict(window="19-11")),
    ("S11 skip Thursdays", "Thu", dict(skip_thu=True)),
    ("S12 skip news days", "News", dict(skip_news=True)),
    ("S13a stop wick +1", "Stop", dict(pad=1.0)),
    ("S13b stop wick +2", "Stop", dict(pad=2.0)),
    ("S13c stop wick +3", "Stop", dict(pad=3.0)),
    ("E1 all out 1.5R", "Exit", dict(exit="E1")),
    ("E3 2 at 2R, runner BE to next structure, out 5 PM", "Exit", dict(exit="E3")),
    ("E4 2 at 2R, runner original stop to next structure", "Exit", dict(exit="E4")),
    ("E5 2 at 2R, runner BE to opposite value edge, 3 days", "Exit", dict(exit="E5")),
    ("E6 like E5, runner keeps original stop", "Exit", dict(exit="E6")),
    ("E7 like E5, trail 1H lower highs", "Exit", dict(exit="E7")),
    ("S14 half risk after 3 losing days", "Brake14", dict(half_after_3_losing_days=True)),
    ("S15 weekly loss cap $900", "Brake15", dict(weekly_cap=True)),
    ("S16 stop after win then loss", "Brake16", dict(stop_after_win_loss=True)),
]


def verdict(b, s):
    if s["Trades"] is None:
        return "NOT RUN"
    if not s["Trades"]:
        return "DROP"
    pf_up = (s["Profit factor"] or 0) > (b["Profit factor"] or 0)
    dd_ok = abs(s["Max DD $"]) <= 1.10 * abs(b["Max DD $"]) + 1e-9
    if pf_up and dd_ok:
        return "KEEP" if s["Trades"] >= 30 else "UNSURE"
    return "DROP"


def main():
    P = prepare()
    OUT.mkdir(parents=True, exist_ok=True)
    base = Cfg()
    rows, kept = [], {}
    bt = backtest(P, base, "build")
    bm = metrics(bt)
    rows.append(dict(Switch="BASE (v5 sweep & reclaim)", Group="", **bm, Verdict="control"))
    for name, grp, kw in SWITCHES:
        s = metrics(backtest(P, replace(base, **kw), "build"))
        vd = verdict(bm, s)
        rows.append(dict(Switch=name, Group=grp, **s, Verdict=vd))
        if vd in ("KEEP", "UNSURE"):
            if grp not in kept or s["Profit factor"] > kept[grp][2]["Profit factor"]:
                kept[grp] = (name, kw, s)          # mutually exclusive groups keep their best
    A = pd.DataFrame(rows)
    A.to_csv(OUT / "ablation_build.csv", index=False)
    # Levels group: S1 and S2 can stack (real + tested); S3 and S4 stand alone
    combo_kw = {}
    level_names = [r for r in rows if r["Group"] == "Levels" and r["Verdict"] in ("KEEP", "UNSURE")]
    names_kept = []
    for r in level_names:
        kw = dict(SWITCHES[[n for n, _, _ in SWITCHES].index(r["Switch"])][2])
        if "levels" in kw and "levels" in combo_kw:
            combo_kw["levels"] = "real+tested"
        else:
            combo_kw.update(kw)
        names_kept.append(r["Switch"])
    for grp, (name, kw, s) in kept.items():
        if grp == "Levels":
            continue
        combo_kw.update(kw)
        names_kept.append(name)
    combo = replace(base, **combo_kw)
    cb = metrics(backtest(P, combo, "build"))
    loo = [dict(Removed="(none: full combo)", **cb, Verdict="")]
    for name in names_kept:
        kw = dict(SWITCHES[[n for n, _, _ in SWITCHES].index(name)][2])
        undo = {k: getattr(base, k) for k in kw}
        if "levels" in kw and combo.levels == "real+tested":
            undo = {"levels": "base+tested" if name.startswith("S1") else "real"}
        s = metrics(backtest(P, replace(combo, **undo), "build"))
        helps = (s["Profit factor"] or 0) < (cb["Profit factor"] or 0) or abs(s["Max DD $"]) > abs(cb["Max DD $"]) * 1.10
        loo.append(dict(Removed=name, **s, Verdict="still helps" if helps else "not needed in combo"))
    LOO = pd.DataFrame(loo)
    LOO.to_csv(OUT / "combo_leave_one_out_build.csv", index=False)
    # walk-forward: one run on TEST, nothing re-chosen
    tt = backtest(P, combo, "test")
    tb = backtest(P, base, "test")
    W = pd.DataFrame([dict(System="BASE", Period="TEST Oct 20 - Nov 13", **metrics(tb)),
                      dict(System="COMBINED", Period="TEST Oct 20 - Nov 13", **metrics(tt)),
                      dict(System="BASE", Period="BUILD Sep 1 - Oct 19", **bm),
                      dict(System="COMBINED", Period="BUILD Sep 1 - Oct 19", **cb)])
    W.to_csv(OUT / "walk_forward.csv", index=False)
    backtest(P, combo, "build").to_csv(OUT / "combined_trades_build.csv", index=False)
    tt.to_csv(OUT / "combined_trades_test.csv", index=False)
    tb.to_csv(OUT / "base_trades_test.csv", index=False)
    bt.to_csv(OUT / "base_trades_build.csv", index=False)
    pd.Series({"combo": str(combo), "kept": names_kept}).to_json(OUT / "combo.json")
    pd.set_option("display.width", 250)
    print(A.to_string(index=False))
    print("\nKEPT:", names_kept, "\nCOMBO:", combo)
    print(LOO.to_string(index=False))
    print(W.to_string(index=False))


if __name__ == "__main__":
    main()
