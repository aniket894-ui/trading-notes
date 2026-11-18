"""
v13b: v13 VAH/VAL rejection with Aniket's full rules (stop filter, sizing, costs, exits E1-E5, drawdown protection).

Entries are v13's (see backtest/vah_rejection.py): 15m candle wicks into or past prior day/week VAH (VAL for longs)
or a tested level, closes back inside with a bearish (bullish) close, previous candle was inside. One trade per test.
Assumptions are listed in claude/v13b results.md and marked ASSUMPTION here.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vah_rejection as v13  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "claude" / "v13b"
TICK, PT_USD, FEE, SLIP = 0.1, 10.0, 1.50, 0.1
RISK, HALF_RISK, MIN_LOTS, MAX_LOTS = 300.0, 150.0, 3, 5
MIN_STOP, MAX_STOP = 2.0, 15.0
NEWS_FILE = ROOT / "data" / "news_events.csv"   # column datetime_et 'YYYY-MM-DD HH:MM' (CPI, NFP, FOMC); missing now
EXITS = ["E1", "E2", "E3", "E4", "E5"]
EXIT_NAMES = {"E1": "E1 all out 2R", "E2": "E2 runner BE to next structure, flat 5 PM",
              "E3": "E3 runner BE to opposite value edge, up to 3 days",
              "E4": "E4 like E3, trail 1H lower highs", "E5": "E5 like E3, runner keeps original stop"}


def session(et):
    m = et.hour * 60 + et.minute
    if m >= 18 * 60 or m < 3 * 60:
        return "Asia 18-03"
    return "London 03-08" if m < 8 * 60 else "NY 08-16"


# ------------------------------------------------------------------ candidates (v13 entries + stop/size filter)

def candidates(m15, L, res, sup, h4, d1):
    rows = []
    O, H, Lo, C = (m15[c].values for c in ["open", "high", "low", "close"])
    t = m15["et"]
    bar_end = t + pd.Timedelta(minutes=15)
    used = set()
    starts, ends = L["start"].values, L["end"].clip(upper=pd.Timestamp("2100-01-01")).values
    for i in range(1, len(m15)):
        ti, te = t.iloc[i], bar_end.iloc[i]
        act = np.nonzero((starts <= np.datetime64(ti)) & (ends >= np.datetime64(te)))[0]
        for d in (-1, 1):
            cands = []
            for k in act:
                lv = L.iloc[k]
                p = lv.px
                if d == -1:
                    ok = H[i] >= p and C[i] < p and C[i] < O[i] and C[i - 1] < p
                    tn, edge = res[k].get(i, 0), lv.is_va_edge_short
                else:
                    ok = Lo[i] <= p and C[i] > p and C[i] > O[i] and C[i - 1] > p
                    tn, edge = sup[k].get(i, 0), lv.is_va_edge_long
                if ok and tn >= 1 and (edge or tn >= 2) and (k, d, tn) not in used:
                    cands.append((k, lv, tn, edge))
            if not cands:
                continue
            ext = H[i] if d == -1 else Lo[i]
            entry = C[i] + (SLIP if d == 1 else -SLIP)               # 1 tick worse on entry
            stop = round(ext + 0.5, 1) if d == -1 else round(ext - 0.5, 1)
            risk = abs(entry - stop)
            lots = min(MAX_LOTS, int(RISK // (risk * PT_USD)))
            if risk < MIN_STOP or risk > MAX_STOP or lots < MIN_LOTS:
                continue                                              # skipped signals don't use up the test
            cands.sort(key=lambda c: (not c[3], abs(ext - c[1].px)))
            k, lv, tn, edge = cands[0]
            used.update((c[0], d, c[2]) for c in cands)
            # levels active now, for runner targets
            act_lv = L.iloc[act]
            rows.append(dict(i=i, time_et=ti.strftime("%Y-%m-%d %H:%M"), tday=m15.at[i, "tday"], d=d,
                             side="Short" if d == -1 else "Long", level=lv["name"], level_px=lv.px, test_no=tn,
                             entry=round(entry, 1), stop=stop, risk=round(risk, 2), lots=lots,
                             with_4h=bool((C[i] < v13.last_done(h4, te, "ema20")) if d == -1 else (C[i] > v13.last_done(h4, te, "ema20"))),
                             with_d=bool((C[i] < v13.last_done(d1, te, "ema20")) if d == -1 else (C[i] > v13.last_done(d1, te, "ema20"))),
                             session=session(ti), **{f"win_{w}": v13.in_window(ti, w) for w in v13.WINDOWS},
                             act_names=list(act_lv["name"]), act_px=list(act_lv["px"])))
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ exits

def simulate(P, s, lots, exit_name):
    """Returns dict(pts, free_at, end_at, note). pts = sum over lots of (fill - entry) * direction."""
    m = P["m"]
    i, d, entry, stop = int(s.i), int(s.d), s.entry, s.stop
    risk = abs(entry - stop)
    tgt2 = entry + d * 2 * risk
    tday = s.tday
    if exit_name == "E1":
        core_n, run_n, rtgt = lots, 0, None
    else:
        core_n, run_n = 2, lots - 2
        if exit_name == "E2":
            names = ({"PD VAL", "PW VAL", "PD low", "1H swing low", "4H swing low"} if d == -1
                     else {"PD VAH", "PW VAH", "PD high", "1H swing high", "4H swing high"})
        else:
            names = {"PD VAL", "PW VAL"} if d == -1 else {"PD VAH", "PW VAH"}
        beyond = sorted((p for n, p in zip(s.act_names, s.act_px) if n in names and (p - tgt2) * d > 0),
                        key=lambda p: (p - tgt2) * d)
        rtgt = beyond[0] if beyond else None
    # runner deadline
    days = P["days"]
    if exit_name in ("E3", "E4", "E5"):
        k = days.index(tday)
        last_day = days[min(k + 2, len(days) - 1)]
    else:
        last_day = tday
    core_open, r_stop, free_at, pts, notes = True, stop, None, 0.0, []
    j = i
    for j in range(i + 1, len(m)):
        td, et = m.at[j, "tday"], m.at[j, "et"]
        # deadlines: core flat by 5 PM on entry day; E3-E5 runner flat at the end of day 3 or Friday 4:55 PM
        if core_open and td != tday:
            j -= 1
            break
        if not core_open:
            if td > last_day:
                j -= 1
                break
            if et.weekday() == 4 and et.hour * 60 + et.minute >= 16 * 60 + 45:
                j -= 1                                           # last bar ending before 4:55 PM Friday
                break
        hi, lo, op = m.at[j, "high"], m.at[j, "low"], m.at[j, "open"]
        if core_open:
            if (hi >= stop) if d == -1 else (lo <= stop):
                fill = (max(op, stop) if d == -1 else min(op, stop)) - d * SLIP
                return dict(pts=(fill - entry) * d * lots, free_at=j, end_at=j, note=f"SL x{lots}")
            if (lo <= tgt2) if d == -1 else (hi >= tgt2):
                pts += 2 * risk * core_n
                notes.append(f"2R x{core_n}")
                core_open, free_at = False, j
                if run_n == 0:
                    return dict(pts=pts, free_at=j, end_at=j, note=" ".join(notes))
                if exit_name != "E5":
                    r_stop = entry                               # runner to break-even
                tp_time = m.at[j, "et"] + pd.Timedelta(minutes=15)
            continue
        if exit_name == "E4":                                    # trail behind new 1H lower highs after 2R
            pv = P["piv_h"] if d == -1 else P["piv_l"]
            new = pv[(pv["known"] > tp_time) & (pv["known"] <= et)]
            if len(new):
                c = new["px"].iloc[-1] - d * TICK
                r_stop = min(r_stop, c) if d == -1 else max(r_stop, c)
        if (hi >= r_stop) if d == -1 else (lo <= r_stop):
            fill = (max(op, r_stop) if d == -1 else min(op, r_stop)) - d * SLIP
            pts += (fill - entry) * d * run_n
            return dict(pts=pts, free_at=free_at, end_at=j, note=" ".join(notes + [f"runner stop x{run_n}"]))
        if rtgt is not None and ((lo <= rtgt) if d == -1 else (hi >= rtgt)):
            pts += (rtgt - entry) * d * run_n
            return dict(pts=pts, free_at=free_at, end_at=j, note=" ".join(notes + [f"runner target x{run_n}"]))
        if exit_name == "E2" and (j + 1 >= len(m) or m.at[j + 1, "tday"] != tday):
            break
    px = m.at[j, "close"]                                        # time exit (no slippage: spec says entry and stops)
    left = (lots if core_open else run_n)
    pts += (px - entry) * d * left
    return dict(pts=pts, free_at=free_at if free_at is not None else j, end_at=j,
                note=" ".join(notes + [f"time x{left}"]))


# ------------------------------------------------------------------ account layer

def run(P, C, exit_name, protect):
    """C: candidate rows already filtered to one side / trend / window, in time order."""
    m = P["m"]
    news = P["news"]
    out = []
    day, n, losses, last_res = None, 0, 0, None
    day_pnl, week_pnl = {}, {}
    streak, half = 0, False
    open_until, open_free = -1, -1
    for _, s in C.iterrows():
        td = s.tday
        if protect:
            if td != day:
                if day is not None and n:
                    pnl = day_pnl.get(day, 0.0)
                    streak = streak + 1 if pnl < 0 else 0
                    if pnl > 0:
                        half = False
                    if streak >= 3:
                        half = True
                day, n, losses, last_res = td, 0, 0, None
            if n >= 2 or losses >= 2 or (last_res == "win_then_loss"):
                continue
            wk = td - pd.Timedelta(days=td.weekday())
            if week_pnl.get(wk, 0.0) <= -900:
                continue
            if s.i <= open_free:                                 # never add: wait until flat or risk-free
                continue
            if news is not None:
                t = m.at[int(s.i), "et"]
                if any(abs((t + pd.Timedelta(minutes=15) - e).total_seconds()) <= 30 * 60 or
                       abs((t - e).total_seconds()) <= 30 * 60 for e in news):
                    continue
            risk_usd = HALF_RISK if half else RISK
        else:
            risk_usd = RISK
        lots = min(MAX_LOTS, int(risk_usd // (s.risk * PT_USD)))
        if lots < MIN_LOTS:
            continue
        r = simulate(P, s, lots, exit_name)
        usd = r["pts"] * PT_USD - FEE * lots
        out.append(dict(time_et=s.time_et, tday=str(td.date()), side=s.side, level=s.level, test_no=s.test_no,
                        session=s.session, entry=s.entry, stop=s.stop, risk_pts=round(s.risk, 1), lots=lots,
                        half_risk=bool(protect and half), exit=r["note"], exit_et=m.at[r["end_at"], "time_et"],
                        usd=round(usd, 2)))
        if protect:
            n += 1
            if usd < 0:
                losses += 1
                if n == 2 and out[-2]["usd"] > 0 and out[-2]["tday"] == out[-1]["tday"]:
                    last_res = "win_then_loss"
            day_pnl[td] = day_pnl.get(td, 0.0) + usd
            week_pnl[wk] = week_pnl.get(wk, 0.0) + usd
            open_free = r["free_at"] if exit_name != "E5" else r["end_at"]   # E5 runner keeps risk
    return pd.DataFrame(out)


def metrics(t):
    if t.empty:
        return {"Trades": 0, "Win %": np.nan, "Net $": 0.0, "Profit factor": np.nan, "Max DD $": 0.0,
                "Longest losing streak": 0}
    u = t["usd"].values
    eq = np.cumsum(u)
    dd = float((eq - np.maximum.accumulate(np.concatenate([[0.0], eq]))[1:]).min())
    gp, gl = u[u > 0].sum(), -u[u < 0].sum()
    st = best = 0
    for x in u:
        st = st + 1 if x < 0 else 0
        best = max(best, st)
    return {"Trades": len(u), "Win %": round(100 * (u > 0).mean(), 1), "Net $": round(u.sum(), 0),
            "Profit factor": round(gp / gl, 2) if gl > 0 else np.inf, "Max DD $": round(dd, 0),
            "Longest losing streak": best}


def main():
    m15 = v13.load("MGC_15m.csv").reset_index(drop=True)
    h1 = v13.load("MGC_1h.csv")
    h1, h4, d1, _ = v13.build_htf(h1)
    L = v13.build_levels(m15, h1, h4, d1)
    res, sup = v13.count_tests(m15, L)
    hi, lo = h1["high"].values, h1["low"].values
    piv_h = pd.DataFrame([(h1["et"].iloc[k + 1] + pd.Timedelta(hours=1), hi[k]) for k in range(1, len(h1) - 1)
                          if hi[k] > hi[k - 1] and hi[k] > hi[k + 1] and hi[k] < max(hi[max(0, k - 24):k])],
                         columns=["known", "px"])                 # lower high: below the prior 24h's high
    piv_l = pd.DataFrame([(h1["et"].iloc[k + 1] + pd.Timedelta(hours=1), lo[k]) for k in range(1, len(h1) - 1)
                          if lo[k] < lo[k - 1] and lo[k] < lo[k + 1] and lo[k] > min(lo[max(0, k - 24):k])],
                         columns=["known", "px"])
    news = None
    if NEWS_FILE.exists():
        news = list(pd.to_datetime(pd.read_csv(NEWS_FILE)["datetime_et"]))
    P = dict(m=m15, days=sorted(m15["tday"].unique()), piv_h=piv_h, piv_l=piv_l, news=news)
    C = candidates(m15, L, res, sup, h4, d1)
    OUT.mkdir(parents=True, exist_ok=True)
    C.drop(columns=["act_names", "act_px"]).to_csv(OUT / "candidates.csv", index=False)
    print("candidates:", len(C), C.groupby("side").size().to_dict())

    grid, all_trades = [], []
    for side in ["Short", "Long"]:
        for trend in v13.TRENDS:
            for w in v13.WINDOWS:
                c = C[(C.side == side) & C[f"win_{w}"]]
                if trend == "4H EMA20":
                    c = c[c.with_4h]
                elif trend == "Daily EMA20":
                    c = c[c.with_d]
                for ex in EXITS:
                    for protect in (False, True):
                        t = run(P, c, ex, protect)
                        grid.append(dict(Side=side, Trend=trend, Window=w, Exit=ex,
                                         Protection="ON" if protect else "OFF", **metrics(t)))
                        if len(t):
                            t["trend"], t["window"], t["exit_v"], t["protection"] = trend, w, ex, "ON" if protect else "OFF"
                            all_trades.append(t)
    G = pd.DataFrame(grid)
    T = pd.concat(all_trades, ignore_index=True)
    G.to_csv(OUT / "grid.csv", index=False)
    T.to_csv(OUT / "trades.csv", index=False)
    # splits on the widest universe: no trend filter, any time, every exit, protection OFF and ON
    base = T[(T.trend == "none") & (T.window == "Any 18-16")]
    for key, col in [("by_level", "level"), ("by_touch", "test_no"), ("by_session", "session")]:
        rows = []
        b = base.copy()
        if col == "test_no":
            b["test_no"] = b["test_no"].clip(upper=5).astype(int).astype(str).replace("5", "5+")
        for (side, val, ex, pr), g in b.groupby(["side", col, "exit_v", "protection"]):
            rows.append(dict(Side=side, **{col: val}, Exit=ex, Protection=pr, **metrics(g)))
        pd.DataFrame(rows).to_csv(OUT / f"{key}.csv", index=False)
    pd.set_option("display.width", 250)
    print(G[(G.Trend == "none")].to_string(index=False))


if __name__ == "__main__":
    main()
