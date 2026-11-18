"""
v15: rerun the v14 ablation on a full year of 1-minute-built bars.

Usage:
  python3 backtest/build_bars.py <1m file>                 # writes data/full/
  python3 backtest/full_year.py [data_dir] [out_dir]        # defaults: data/full, claude/v15_full_year

BUILD = first 8 months of tradable days, TEST = the rest (last ~4 months), run once at the end.
If the data covers under 12 months, the split falls back to 2:1 and every output says PIPELINE TEST.
Shorts and longs are separate accounts and separate ablations.
"""
import json
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vah_rejection as v13  # noqa: E402
import ablation as ab  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
V14_FINAL = dict(levels="real+tested", trend="VWAP", window="03-05", pad=2.0, exit="E2")


def session(t):
    m = t.hour * 60 + t.minute
    return "Asia 18-03" if (m >= 18 * 60 or m < 180) else ("London 03-08" if m < 480 else "NY 08-16")


def ablate(P, side):
    base = ab.Cfg(side=side)
    bm = ab.metrics(ab.backtest(P, base, "build"))
    rows = [dict(Side=side, Switch="BASE (v5 sweep & reclaim)", Group="", **bm, Verdict="control")]
    kept = {}
    for name, grp, kw in ab.SWITCHES:
        s = ab.metrics(ab.backtest(P, replace(base, **kw), "build"))
        vd = ab.verdict(bm, s)
        rows.append(dict(Side=side, Switch=name, Group=grp, **s, Verdict=vd))
        if vd in ("KEEP", "UNSURE"):
            if grp == "Levels":
                kept.setdefault("Levels", []).append((name, kw))
            elif grp not in kept or s["Profit factor"] > kept[grp][2]["Profit factor"]:
                kept[grp] = (name, kw, s)
    combo_kw, names = {}, []
    for name, kw in kept.get("Levels", []):
        if "levels" in kw and "levels" in combo_kw:
            combo_kw["levels"] = "real+tested"
        else:
            combo_kw.update(kw)
        names.append(name)
    for grp, val in kept.items():
        if grp == "Levels":
            continue
        combo_kw.update(val[1])
        names.append(val[0])
    combo = replace(base, **combo_kw)
    cb = ab.metrics(ab.backtest(P, combo, "build"))
    loo, final_kw = [dict(Side=side, Removed="(none: full combo)", **cb, Result="")], dict(combo_kw)
    for name in names:
        kw = dict(ab.SWITCHES[[n for n, _, _ in ab.SWITCHES].index(name)][2])
        undo = {k: getattr(base, k) for k in kw}
        if "levels" in kw and combo.levels == "real+tested":
            undo = {"levels": "base+tested" if name.startswith("S1") else "real"}
        s = ab.metrics(ab.backtest(P, replace(combo, **undo), "build"))
        helps = (s["Profit factor"] or 0) < (cb["Profit factor"] or 0) or abs(s["Max DD $"]) > abs(cb["Max DD $"]) * 1.10
        loo.append(dict(Side=side, Removed=name, **s, Result="still helps" if helps else "not needed: dropped"))
        if not helps:                                   # trim: revert this switch in the final system
            for k, v in undo.items():
                if k == "levels" and final_kw.get("levels") == "real+tested":
                    final_kw["levels"] = v
                else:
                    final_kw.pop(k, None) if getattr(base, k) == v else final_kw.update({k: v})
    final = replace(base, **final_kw)
    return pd.DataFrame(rows), pd.DataFrame(loo), final, names


def months_table(d1, start):
    d = d1[d1["tday"] >= start].copy()
    d["month"] = d["tday"].dt.to_period("M")
    g = d.groupby("month").agg(open=("open", "first"), close=("close", "last"))
    g["change_%"] = (100 * (g["close"] / g["open"] - 1)).round(1)
    g["trend"] = np.where(g["close"] > g["open"], "Rising", "Falling")
    return g.reset_index()


def by_month(t, months):
    if t is None or t.empty:
        return pd.DataFrame()
    t = t.copy()
    t["month"] = pd.to_datetime(t["tday"]).dt.to_period("M")
    rows = []
    for mo, g in t.groupby("month"):
        tr = months.set_index("month").loc[mo, "trend"] if mo in set(months["month"]) else "?"
        rows.append(dict(Month=str(mo), Gold=tr, **ab.metrics(g)))
    return pd.DataFrame(rows)


def splits(t, label):
    if t is None or t.empty:
        return pd.DataFrame()
    t = t.copy()
    t["session"] = pd.to_datetime(t["time_et"]).map(session)
    t["touch"] = t["test"].clip(upper=5).astype(int).astype(str).replace("5", "5+")
    rows = []
    for col, name in [("session", "Session"), ("touch", "Touch"), ("level", "Level")]:
        for (side, val), g in t.groupby(["side", col]):
            rows.append(dict(System=label, Split=name, Side=side, Value=val, **ab.metrics(g)))
    return pd.DataFrame(rows)


def main():
    data_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "data" / "full"
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "claude" / "v15_full_year"
    out.mkdir(parents=True, exist_ok=True)
    v13.DATA_DIR = data_dir
    m15 = v13.load("MGC_15m.csv")
    first, last = m15["tday"].min(), m15["tday"].max()
    ab.START_DAY = first + pd.Timedelta(days=30)               # warm-up: weekly levels + daily EMA20
    span_months = (last - ab.START_DAY).days / 30.44
    full_year = span_months >= 12
    if full_year:
        ab.BUILD_END = ab.START_DAY + pd.DateOffset(months=8) - pd.Timedelta(days=1)
    else:
        ab.BUILD_END = ab.START_DAY + (last - ab.START_DAY) * 2 / 3
    ab.BUILD_END = pd.Timestamp(ab.BUILD_END).normalize()
    info = dict(data_dir=str(data_dir), first_data_day=str(first.date()), first_traded_day=str(ab.START_DAY.date()),
                build_end=str(ab.BUILD_END.date()), last_day=str(last.date()), months_traded=round(span_months, 1),
                mode="FULL YEAR" if full_year else "PIPELINE TEST (under 12 months: 2:1 split)")
    if (data_dir / "data_info.json").exists():
        info.update(json.loads((data_dir / "data_info.json").read_text()))
    print(json.dumps(info, indent=2))
    P = ab.prepare()
    h1 = v13.load("MGC_1h.csv")
    _, _, d1, _ = v13.build_htf(h1)
    months = months_table(d1, ab.START_DAY)

    abl, loos, finals, summary, monthly, split_tabs = [], [], {}, [], [], []
    for side in ["Short", "Long"]:
        A, L, final, kept = ablate(P, side)
        abl.append(A)
        loos.append(L)
        finals[side] = dict(cfg=str(final), kept=kept)
        base = ab.Cfg(side=side)
        v14 = replace(ab.Cfg(), side=side, **V14_FINAL)
        for label, cfg in [("Base v5", base), ("v15 final (chosen on BUILD)", final), ("v14 final as-is", v14)]:
            for per in ["build", "test", "full"]:
                t = ab.backtest(P, cfg, per)
                summary.append(dict(Side=side, System=label, Period=per.upper(), **ab.metrics(t)))
                if per == "full":
                    bm = by_month(t, months)
                    if not bm.empty:
                        bm.insert(0, "System", label)
                        bm.insert(0, "Side", side)
                        monthly.append(bm)
                    split_tabs.append(splits(t, label))
                    t.to_csv(out / f"trades_{side}_{label.split(' (')[0].replace(' ', '_')}.csv", index=False)
    pd.concat(abl).to_csv(out / "ablation_build.csv", index=False)
    pd.concat(loos).to_csv(out / "leave_one_out_build.csv", index=False)
    pd.DataFrame(summary).to_csv(out / "systems.csv", index=False)
    months.assign(month=months["month"].astype(str)).to_csv(out / "months.csv", index=False)
    if monthly:
        pd.concat(monthly).to_csv(out / "by_month.csv", index=False)
    pd.concat(split_tabs).to_csv(out / "splits.csv", index=False)
    (out / "run_info.json").write_text(json.dumps(dict(info, finals=finals), indent=2, default=str))
    pd.set_option("display.width", 250)
    print(pd.DataFrame(summary).to_string(index=False))
    print(json.dumps(finals, indent=2))


if __name__ == "__main__":
    main()
