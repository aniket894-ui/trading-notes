"""
v13 add-on: stop-hunt check on losing trades, and a retest with wider stops.

Input: claude/vah_rejection/signals.csv (v13 signals; run backtest/vah_rejection.py first) and data/MGC_15m.csv.

Stop-hunt check (base stop = trigger wick + 0.5, target = 2R):
  - Losing trade = stopped out. Trades closed at day end with a loss were never stopped, so they're excluded.
  - Did price reach the original 2R target after the stop was hit, (a) within 4 hours, (b) within the same
    trading day (before 17:00 ET)? Checked from the bar AFTER the stop bar (ASSUMPTION: inside the stop bar
    the order of high and low is unknown, so it isn't counted).
  - Points past the stop before reversing = furthest price went beyond the stop, from the stop bar until the
    2R target was touched (if it was, same day) or until the end of the trading day (if not).

Wider-stop retest: same signals, same entries. Stop = wick + 0.5 (base), +1, +2, +3 points. Target = 2R of the new
risk. Lots = floor($300 / (stop pts x $10)), max 5 (ASSUMPTION: Rulebook cap kept), $3 fees per lot. Stop counts
first if a bar touches both. Open trades close at the last bar of the trading day.
Max drawdown: every signal taken, P&L booked in entry-time order (overlapping trades allowed, as in v13).
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "claude" / "vah_rejection"
PAD_BASE = 0.5
PADS = [0.5, 1.0, 2.0, 3.0]
RISK_USD, POINT_USD, MAX_LOTS, FEE = 300.0, 10.0, 5, 3.0
HUNT_HOURS = 4


def load():
    m = pd.read_csv(ROOT / "data" / "MGC_15m.csv")
    m["et"] = pd.to_datetime(m["time_et"])
    m["tday"] = (m["et"] + pd.Timedelta(hours=6)).dt.normalize()
    return m


def simulate(m, i, d, entry, stop):
    """2R target. Returns (result, exit_index)."""
    risk = abs(entry - stop)
    tgt = entry + d * 2 * risk
    tday = m.at[i, "tday"]
    j = i
    for j in range(i + 1, len(m)):
        if m.at[j, "tday"] != tday:
            j -= 1
            break
        hi, lo = m.at[j, "high"], m.at[j, "low"]
        if (hi >= stop) if d == -1 else (lo <= stop):
            return -1.0, j, tgt
        if (lo <= tgt) if d == -1 else (hi >= tgt):
            return 2.0, j, tgt
    return (m.at[j, "close"] - entry) * d / risk, j, tgt      # still open at day end


def hunt(m, j, d, stop, tgt):
    """After stop hit on bar j: target within 4h / same day, and points past the stop before reversing."""
    tday = m.at[j, "tday"]
    t_limit = m.at[j, "et"] + pd.Timedelta(minutes=15) + pd.Timedelta(hours=HUNT_HOURS)
    hit4 = hitday = False
    worst = (m.at[j, "high"] - stop) if d == -1 else (stop - m.at[j, "low"])
    k = j + 1
    while k < len(m):
        hi, lo = m.at[k, "high"], m.at[k, "low"]
        reached = (lo <= tgt) if d == -1 else (hi >= tgt)
        same_day = m.at[k, "tday"] == tday
        if reached:
            if m.at[k, "et"] < t_limit:
                hit4 = True
            if same_day:
                hitday = True
                break
        if not same_day and m.at[k, "et"] >= t_limit:
            break
        if same_day:
            worst = max(worst, (hi - stop) if d == -1 else (stop - lo))
        k += 1
    return hit4, hitday, round(max(worst, 0.0), 1)


def drawdown(usd):
    eq = np.cumsum(usd)
    peak = np.maximum.accumulate(np.concatenate([[0.0], eq]))[1:]
    return float((eq - peak).min()) if len(eq) else 0.0


def main():
    m = load()
    S = pd.read_csv(OUT / "signals.csv")
    pos = {t: k for k, t in enumerate(m["time_et"])}
    S["i"] = S["time_et"].map(pos)
    S["d"] = np.where(S["side"] == "Short", -1, 1)
    S["wick"] = np.where(S["d"] == -1, S["stop"] - PAD_BASE, S["stop"] + PAD_BASE)
    S = S[S["win_Any 18-16"]]            # v13 universe: trigger candle inside 18:00-16:00
    S = S.sort_values("time_et").reset_index(drop=True)

    # ---- wider stops
    res = {}
    for pad in PADS:
        rows = []
        for _, s in S.iterrows():
            stop = round(s.wick + pad, 1) if s.d == -1 else round(s.wick - pad, 1)
            risk = abs(s.entry - stop)
            lots = min(MAX_LOTS, int(RISK_USD // (risk * POINT_USD)))
            r, j, tgt = simulate(m, int(s.i), int(s.d), s.entry, stop)
            usd = r * risk * lots * POINT_USD - FEE * lots if lots else 0.0
            rows.append(dict(R=r, usd=usd, lots=lots, risk=risk, exit_i=j, stop_px=stop, tgt=tgt))
        res[pad] = pd.DataFrame(rows)
        S[f"R_pad{pad}"] = res[pad]["R"].values
        S[f"usd_pad{pad}"] = res[pad]["usd"].values
        S[f"lots_pad{pad}"] = res[pad]["lots"].values

    # ---- stop-hunt on base-stop losers
    base = res[PAD_BASE]
    hunts = []
    for k, s in S.iterrows():
        b = base.iloc[k]
        if b.R != -1.0:
            continue
        h4, hd, past = hunt(m, int(b.exit_i), int(s.d), b.stop_px, b.tgt)
        hunts.append(dict(time_et=s.time_et, side=s.side, level=s.level, test_no=s.test_no,
                          London=s["win_London 03-05"], w0311=s["win_03-11"], entry=s.entry, stop=b.stop_px,
                          target_2R=round(b.tgt, 1), stopped_at=m.at[int(b.exit_i), "time_et"],
                          target_within_4h=h4, target_same_day=hd, pts_past_stop=past))
    H = pd.DataFrame(hunts)
    H.to_csv(OUT / "stop_hunt_losers.csv", index=False)
    S.drop(columns=["i"]).to_csv(OUT / "signals_wider_stops.csv", index=False)

    def hstats(g):
        hd = g[g.target_same_day]
        return dict(Losers=len(g), **{"Hit 2R ≤4h": int(g.target_within_4h.sum()),
                    "% ≤4h": round(100 * g.target_within_4h.mean(), 0),
                    "Hit 2R same day": int(g.target_same_day.sum()),
                    "% same day": round(100 * g.target_same_day.mean(), 0),
                    "Median pts past stop (all)": round(g.pts_past_stop.median(), 1),
                    "Median pts past stop (hunted)": round(hd.pts_past_stop.median(), 1) if len(hd) else np.nan})

    tabs = {}
    rows = []
    for side in ["Short", "Long"]:
        for wname, mask in [("Any 18-16", slice(None)), ("03-11", "w0311"), ("London 03-05", "London")]:
            g = H[H.side == side]
            g = g if mask == slice(None) else g[g[mask]]
            rows.append(dict(Side=side, Window=wname, **hstats(g)))
    tabs["hunt_overview"] = pd.DataFrame(rows)
    rows = []
    for (side, lvl), g in H.groupby(["side", "level"]):
        rows.append(dict(Side=side, Level=lvl, **hstats(g)))
    tabs["hunt_by_level"] = pd.DataFrame(rows)
    H["test_bucket"] = H.test_no.clip(upper=5).astype(int).astype(str).replace("5", "5+")
    rows = []
    for (side, tb), g in H.groupby(["side", "test_bucket"]):
        rows.append(dict(Side=side, Test=tb, **hstats(g)))
    tabs["hunt_by_test"] = pd.DataFrame(rows)
    # how much wider would the stop have needed to be, for hunted trades
    hd = H[H.target_same_day]
    bins = [-0.01, 0.5, 1.5, 2.5, 5, 10, 1e9]
    labels = ["≤0.5", "0.5–1.5", "1.5–2.5", "2.5–5", "5–10", ">10"]
    tabs["hunt_depth"] = (pd.cut(hd.pts_past_stop, bins, labels=labels).value_counts().reindex(labels)
                          .rename_axis("Pts past stop").reset_index(name="Hunted trades"))

    rows = []
    for side in ["Short", "Long"]:
        for wname, col in [("Any 18-16", None), ("03-11", "win_03-11"), ("London 03-05", "win_London 03-05")]:
            for pad in PADS:
                g = S[S.side == side] if col is None else S[(S.side == side) & S[col]]
                r, u = g[f"R_pad{pad}"], g[f"usd_pad{pad}"]
                rows.append(dict(Side=side, Window=wname, Stop=f"wick + {pad:g}", Signals=len(g),
                                 **{"Win %": round(100 * (r >= 2).mean(), 1) if len(g) else np.nan,
                                    "Total R": round(r.sum(), 1), "Net $": round(u.sum(), 0),
                                    "Max DD $": round(drawdown(u.values), 0),
                                    "Avg lots": round(g[f"lots_pad{pad}"].mean(), 2)}))
    tabs["wider_stops"] = pd.DataFrame(rows)
    for k, v in tabs.items():
        v.to_csv(OUT / f"{k}.csv", index=False)
        print(f"\n== {k}\n", v.to_string(index=False))


if __name__ == "__main__":
    main()
