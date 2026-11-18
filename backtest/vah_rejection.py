"""
MGC volume-profile level rejection backtest (shorts at VAH / tested resistance, longs mirrored).

Every assumption is listed in claude/VAH rejection backtest.md and marked ASSUMPTION below.

Data
  data/MGC_15m.csv  TradingView native 15m (verified identical to 15m built from 5m on 1,666 overlap bars)
  data/MGC_1h.csv   TradingView native 1H, used to build 4H, daily and weekly bars
Times are America/New_York. Trading day = 18:00 ET to 17:00 ET (labelled by the date it ends).
Week = Sunday 18:00 ET to Friday 17:00 ET.
"""
import math
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "claude" / "vah_rejection"
DATA_DIR = ROOT / "data"     # full-year runs point this at data/full

BIN = 0.1            # volume-at-price bin
VA_PCT = 0.70
TEST_TOL = 1.0       # wick within 1.0 point counts as a test
STOP_PAD = 0.5       # stop 0.5 point past the trigger candle
FRACTAL_N = 3        # swing = fractal with 3 bars each side
EMA_LEN = 20
POINT_USD = 10.0
RISK_USD = 300.0     # ASSUMPTION (spec cut off): your Rulebook risk
MAX_LOTS = 5         # ASSUMPTION (spec cut off): your Rulebook cap
FEE_PER_LOT = 3.0    # ASSUMPTION: same fee as earlier backtests
TARGETS = [1.0, 2.0, 3.0]   # ASSUMPTION (spec cut off): exits reported at 1R, 2R and 3R

WINDOWS = {"London 03-05": (3 * 60, 5 * 60), "03-11": (3 * 60, 11 * 60), "Any 18-16": None}
TRENDS = ["none", "4H EMA20", "Daily EMA20"]


# ------------------------------------------------------------------ bars

def load(name):
    df = pd.read_csv(DATA_DIR / name)
    df["et"] = pd.to_datetime(df["time_et"])
    df["tday"] = (df["et"] + pd.Timedelta(hours=6)).dt.normalize()
    return df


def build_htf(h1):
    """4H, daily, weekly from 1H. 4H buckets start at 18:00: 18-22, 22-02, 02-06, 06-10, 10-14, 14-17."""
    h1 = h1.copy()
    h1["end"] = h1["et"] + pd.Timedelta(hours=1)
    h1["b4"] = ((h1["et"].dt.hour - 18) % 24) // 4
    agg = dict(et=("et", "first"), end=("end", "last"), open=("open", "first"), high=("high", "max"),
               low=("low", "min"), close=("close", "last"), volume=("volume", "sum"))
    h4 = h1.groupby(["tday", "b4"]).agg(**agg).reset_index()
    d1 = h1.groupby("tday").agg(**agg).reset_index()
    d1["week"] = d1["tday"] - pd.to_timedelta(d1["tday"].dt.weekday, unit="D")   # Monday of that week
    w1 = d1.groupby("week").agg(et=("et", "first"), end=("end", "last"), open=("open", "first"),
                                high=("high", "max"), low=("low", "min"), close=("close", "last")).reset_index()
    for df in (h4, d1):
        df["ema20"] = df["close"].ewm(span=EMA_LEN, adjust=False).mean()
    h1 = h1.rename(columns={})
    return h1, h4, d1, w1


def last_done(df, t, col):
    """Value of col on the last bar that closed at or before t."""
    i = df["end"].searchsorted(t, side="right") - 1
    return np.nan if i < 0 else df[col].iloc[i]


# ------------------------------------------------------------------ volume profile

def profile(bars):
    """POC / VAH / VAL from 15m bars. Each bar's volume is spread evenly over 0.1 bins from low to high
    (ASSUMPTION: no tick or volume-at-price data is available). Value area grows from the POC, adding the
    larger of the next bin above or below until 70% of volume is covered."""
    lo = math.floor(bars["low"].min() / BIN + 1e-9)
    hi = math.floor(bars["high"].max() / BIN + 1e-9)
    vol = np.zeros(hi - lo + 1)
    for l, h, v in zip(bars["low"].values, bars["high"].values, bars["volume"].values):
        a = math.floor(l / BIN + 1e-9) - lo
        b = math.floor(h / BIN + 1e-9) - lo
        vol[a:b + 1] += v / (b - a + 1)
    poc = int(vol.argmax())
    a = b = poc
    acc, total = vol[poc], vol.sum()
    while acc < VA_PCT * total and (a > 0 or b < len(vol) - 1):
        up = vol[b + 1] if b < len(vol) - 1 else -1
        dn = vol[a - 1] if a > 0 else -1
        if up >= dn:
            b += 1
            acc += up
        else:
            a -= 1
            acc += dn
    px = lambda k: round((lo + k) * BIN, 1)
    return px(poc), px(b), px(a)       # POC, VAH, VAL (bin price = bin's lower edge)


# ------------------------------------------------------------------ levels

def fractals(df, kind_prefix):
    """Fractal highs/lows: strictly higher (lower) than the 3 bars on each side. Known at the close of the
    3rd bar after. Retired at the first 1H close beyond the level (ASSUMPTION)."""
    out = []
    hi, lo = df["high"].values, df["low"].values
    for k in range(FRACTAL_N, len(df) - FRACTAL_N):
        known = df["end"].iloc[k + FRACTAL_N]
        if hi[k] > hi[k - FRACTAL_N:k].max() and hi[k] > hi[k + 1:k + 1 + FRACTAL_N].max():
            out.append(dict(name=f"{kind_prefix} swing high", px=round(hi[k], 1), start=known, side="high"))
        if lo[k] < lo[k - FRACTAL_N:k].min() and lo[k] < lo[k + 1:k + 1 + FRACTAL_N].min():
            out.append(dict(name=f"{kind_prefix} swing low", px=round(lo[k], 1), start=known, side="low"))
    return out


def build_levels(m15, h1, h4, d1, pbars=None):
    """pbars: optional 1m bars (with tday) used for the volume profiles instead of 15m."""
    pday = {d: g for d, g in pbars.groupby("tday")} if pbars is not None else None
    lv = []
    days = sorted(m15["tday"].unique())
    # a trading day is complete in the 15m file if it has its 18:00 bar
    full = set(m15.loc[(m15["et"].dt.hour == 18) & (m15["et"].dt.minute == 0), "tday"])
    by_day = {d: g for d, g in m15.groupby("tday")}
    for i, d in enumerate(days):
        d_end = d + pd.Timedelta(hours=17)
        d_start = d - pd.Timedelta(hours=6)
        if i > 0 and days[i - 1] in full:
            prev = by_day[days[i - 1]]
            poc, vah, val = profile(pday.get(days[i - 1], prev) if pday is not None else prev)
            for n, p in [("PD POC", poc), ("PD VAH", vah), ("PD VAL", val),
                         ("PD high", prev["high"].max()), ("PD low", prev["low"].min())]:
                lv.append(dict(name=n, px=round(p, 1), start=d_start, end=d_end))
        if d in full:
            g = by_day[d]
            asia = g[(g["et"] >= d - pd.Timedelta(hours=5)) & (g["et"] < d + pd.Timedelta(hours=2))]
            if len(asia) == 28:          # 19:00-02:00 = 28 bars of 15m
                t0 = d + pd.Timedelta(hours=2)
                lv.append(dict(name="Asia high", px=asia["high"].max(), start=t0, end=d_end))
                lv.append(dict(name="Asia low", px=asia["low"].min(), start=t0, end=d_end))
    # weekly
    m15w = m15.copy()
    m15w["week"] = m15w["tday"] - pd.to_timedelta(m15w["tday"].dt.weekday, unit="D")
    weeks = sorted(m15w["week"].unique())
    for i in range(1, len(weeks)):
        pw = m15w[m15w["week"] == weeks[i - 1]]
        if not set(pd.date_range(weeks[i - 1], periods=5)).issubset(full):
            continue                      # prior week must be complete in the 15m file
        w_start = weeks[i] - pd.Timedelta(hours=6)
        w_end = weeks[i] + pd.Timedelta(days=4, hours=17)
        if pbars is not None:
            wk_days = set(pw["tday"].unique())
            pwp = pbars[pbars["tday"].isin(wk_days)]
            poc, vah, val = profile(pwp if len(pwp) else pw)
        else:
            poc, vah, val = profile(pw)
        for n, p in [("PW POC", poc), ("PW VAH", vah), ("PW VAL", val),
                     ("PW high", pw["high"].max()), ("PW low", pw["low"].min())]:
            lv.append(dict(name=n, px=round(p, 1), start=w_start, end=w_end))
    # swings, retired at the first 1H close beyond
    h1c = h1[["end", "close"]].reset_index(drop=True)
    for df, pref in [(h1, "1H"), (h4, "4H"), (d1, "Daily")]:
        for s in fractals(df, pref):
            after = h1c[h1c["end"] > s["start"]]
            beyond = after[after["close"] > s["px"]] if s["side"] == "high" else after[after["close"] < s["px"]]
            end = beyond["end"].iloc[0] if len(beyond) else pd.Timestamp.max
            if end <= m15["et"].iloc[0]:
                continue                  # gone before the 15m data starts
            lv.append(dict(name=s["name"], px=s["px"], start=s["start"], end=end,
                           pre_data=s["start"] < m15["et"].iloc[0]))
    L = pd.DataFrame(lv)
    L["pre_data"] = L.get("pre_data", False)
    L["pre_data"] = L["pre_data"].fillna(False).astype(bool)
    L["is_va_edge_short"] = L["name"].isin(["PD VAH", "PW VAH"])
    L["is_va_edge_long"] = L["name"].isin(["PD VAL", "PW VAL"])
    return L.reset_index(drop=True)


# ------------------------------------------------------------------ test counting

def count_tests(m15, L):
    """For each level and each 15m bar, the resistance / support test number the bar belongs to (0 = not a touch).
    Resistance touch: high >= L - 1.0 and close < L.  Support touch: low <= L + 1.0 and close > L.
    A new test starts only after price has left the 1.0-point zone (a bar whose high < L - 1.0, resp.
    low > L + 1.0) since the last touch (ASSUMPTION: how 'then a close away' is read)."""
    t = m15["et"].values
    end = (m15["et"] + pd.Timedelta(minutes=15)).values
    H, Lo, C = m15["high"].values, m15["low"].values, m15["close"].values
    res, sup = {}, {}
    for k, lv in L.iterrows():
        mask = (t >= np.datetime64(lv.start)) & (end <= np.datetime64(min(lv.end, pd.Timestamp("2100-01-01"))))
        idx = np.nonzero(mask)[0]
        p = lv.px
        rn = sn = 0
        r_away = s_away = True
        rmap, smap = {}, {}
        for i in idx:
            if H[i] >= p - TEST_TOL and C[i] < p:
                if r_away:
                    rn += 1
                    r_away = False
                rmap[i] = rn
            if H[i] < p - TEST_TOL:
                r_away = True
            if Lo[i] <= p + TEST_TOL and C[i] > p:
                if s_away:
                    sn += 1
                    s_away = False
                smap[i] = sn
            if Lo[i] > p + TEST_TOL:
                s_away = True
        res[k], sup[k] = rmap, smap
    return res, sup


# ------------------------------------------------------------------ signals and outcomes

def in_window(et, name):
    w = WINDOWS[name]
    m = et.hour * 60 + et.minute
    if w is None:                         # 18:00 to 16:00: candle opens >= 18:00 or closes by 16:00
        return m >= 18 * 60 or m + 15 <= 16 * 60
    return m >= w[0] and m + 15 <= w[1]


def outcome(m15, i, d, entry, stop):
    """Walk 15m bars after the signal to the end of the trading day. If one bar touches the stop and a target,
    the stop counts. Returns R result per target and the max favourable excursion (R) before the stop."""
    risk = abs(entry - stop)
    tday = m15.at[i, "tday"]
    res = {}
    mfe, stopped_at = 0.0, None
    j = i
    for j in range(i + 1, len(m15)):
        if m15.at[j, "tday"] != tday:
            j -= 1
            break
        hi, lo = m15.at[j, "high"], m15.at[j, "low"]
        if (hi >= stop) if d == -1 else (lo <= stop):
            stopped_at = j
            break
        fav = (entry - lo) if d == -1 else (hi - entry)
        mfe = max(mfe, fav / risk)
    last_close = m15.at[j, "close"]
    for tr in TARGETS:
        if mfe >= tr:
            res[tr] = tr
        elif stopped_at is not None:
            res[tr] = -1.0
        else:                              # still open at 16:45 bar close
            res[tr] = round((entry - last_close) * (1 if d == -1 else -1) / risk, 3)
    return res, round(mfe, 2), ("stop" if stopped_at is not None else "day end")


def find_signals(m15, L, res, sup, h4, d1):
    rows = []
    O, H, Lo, C = (m15[c].values for c in ["open", "high", "low", "close"])
    t = m15["et"]
    bar_end = t + pd.Timedelta(minutes=15)
    act = [(k, lv) for k, lv in L.iterrows()]
    used = set()                          # (level, side, test number) already traded: one trade per test
    for i in range(1, len(m15)):
        ti, te = t.iloc[i], bar_end.iloc[i]
        for d in (-1, 1):
            cands = []
            for k, lv in act:
                if not (lv.start <= ti and te <= lv.end):
                    continue
                p = lv.px
                if d == -1:
                    ok = H[i] >= p and C[i] < p and C[i] < O[i] and C[i - 1] < p
                    tn = res[k].get(i, 0)
                    edge = lv.is_va_edge_short
                else:
                    ok = Lo[i] <= p and C[i] > p and C[i] > O[i] and C[i - 1] > p
                    tn = sup[k].get(i, 0)
                    edge = lv.is_va_edge_long
                if ok and tn >= 1 and (edge or tn >= 2) and (k, d, tn) not in used:
                    cands.append((k, lv, tn, edge))
            if not cands:
                continue
            # primary level: a VA edge if there is one, else the level nearest the wick extreme
            ext = H[i] if d == -1 else Lo[i]
            cands.sort(key=lambda c: (not c[3], abs(ext - c[1].px)))
            k, lv, tn, edge = cands[0]
            used.update((c[0], d, c[2]) for c in cands)
            entry = C[i]
            stop = round(H[i] + STOP_PAD, 1) if d == -1 else round(Lo[i] - STOP_PAD, 1)
            risk = abs(entry - stop)
            r, mfe, how = outcome(m15, i, d, entry, stop)
            e4, ed = last_done(h4, te, "ema20"), last_done(d1, te, "ema20")
            lots = min(MAX_LOTS, int(RISK_USD // (risk * POINT_USD)))
            rows.append(dict(
                time_et=ti.strftime("%Y-%m-%d %H:%M"), tday=m15.at[i, "tday"].date().isoformat(),
                side="Short" if d == -1 else "Long", level=lv["name"], level_px=lv.px, test_no=tn,
                level_pre_data=bool(lv.pre_data), all_levels="; ".join(f"{c[1]['name']} {c[1].px} (test {c[2]})" for c in cands),
                entry=entry, stop=stop, risk_pts=round(risk, 1), lots=lots,
                ema4h=round(e4, 1), ema_d=round(ed, 1),
                with_4h=bool((entry < e4) if d == -1 else (entry > e4)),
                with_d=bool((entry < ed) if d == -1 else (entry > ed)),
                **{f"win_{w}": in_window(ti, w) for w in WINDOWS},
                R1=r[1.0], R2=r[2.0], R3=r[3.0], mfe_R=mfe, exit=how,
                usd_2R=round(r[2.0] * risk * lots * POINT_USD - FEE_PER_LOT * lots, 2) if lots else 0.0))
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ reporting

def pick(T, side, trend, window):
    s = T[(T.side == side) & T[f"win_{window}"]]
    if trend == "4H EMA20":
        s = s[s.with_4h]
    elif trend == "Daily EMA20":
        s = s[s.with_d]
    return s


def stats(s):
    n = len(s)
    if not n:
        return dict(Signals=0)
    out = dict(Signals=n)
    for tr, col in zip(TARGETS, ["R1", "R2", "R3"]):
        out[f"Win% {int(tr)}R"] = round(100 * (s[col] >= tr).mean(), 1)
        out[f"Total R {int(tr)}R"] = round(s[col].sum(), 1)
    out["Net $ 2R"] = round(s["usd_2R"].sum(), 0)
    out["Avg risk pts"] = round(s["risk_pts"].mean(), 1)
    return out


def main():
    m15 = load("MGC_15m.csv").reset_index(drop=True)
    h1 = load("MGC_1h.csv")
    h1, h4, d1, w1 = build_htf(h1)
    L = build_levels(m15, h1, h4, d1)
    res, sup = count_tests(m15, L)
    T = find_signals(m15, L, res, sup, h4, d1)
    OUT.mkdir(parents=True, exist_ok=True)
    T.to_csv(OUT / "signals.csv", index=False)
    L.to_csv(OUT / "levels.csv", index=False)
    grid, by_test, by_level = [], [], []
    for side in ["Short", "Long"]:
        for trend in TRENDS:
            for w in WINDOWS:
                s = pick(T, side, trend, w)
                grid.append(dict(Side=side, Trend=trend, Window=w, **stats(s)))
                for tn in [1, 2, 3, 4]:
                    by_test.append(dict(Side=side, Trend=trend, Window=w, Test=str(tn), **stats(s[s.test_no == tn])))
                by_test.append(dict(Side=side, Trend=trend, Window=w, Test="5+", **stats(s[s.test_no >= 5])))
                for lvl, g in s.groupby("level"):
                    by_level.append(dict(Side=side, Trend=trend, Window=w, Level=lvl, **stats(g)))
    pd.DataFrame(grid).to_csv(OUT / "grid.csv", index=False)
    pd.DataFrame(by_test).to_csv(OUT / "by_test.csv", index=False)
    pd.DataFrame(by_level).to_csv(OUT / "by_level.csv", index=False)
    print(pd.DataFrame(grid).to_string(index=False))
    print("signals:", len(T), "levels:", len(L), "first signal day:", T.tday.min() if len(T) else None)


if __name__ == "__main__":
    main()
