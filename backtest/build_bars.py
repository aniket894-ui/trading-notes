"""
Turn a 1-minute gold file into the 5m / 15m / 1H bar files the backtests read (4H and daily are built from 1H).

Usage:  python3 backtest/build_bars.py <1m file or folder of 1m CSVs> [out_dir]      (out_dir default: data/full)

Accepted inputs (detected from the header):
  - Dukascopy "Historical Data Export" CSV: Gmt time,Open,High,Low,Close,Volume  (e.g. 14.10.2025 00:00:00.000, GMT)
    Volume is TICK volume (spot gold has no exchange volume).
  - Databento ohlcv-1m CSV: ts_event,...,open,high,low,close,volume[,symbol]  (UTC; real contract volume)
  - Generic: time_utc,open,high,low,close,volume  (UTC)
Writes MGC-style CSVs: time_utc,time_et,open,high,low,close,volume, one file per timeframe, plus data_info.json.
"""
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def read_1m(path):
    path = Path(path)
    if path.is_dir():                              # several export files: read and stack them all
        df = pd.concat([pd.read_csv(f) for f in sorted(path.glob("*.csv"))], ignore_index=True)
    else:
        df = pd.read_csv(path)
    cols = {c.lower().strip(): c for c in df.columns}
    if "gmt time" in cols:
        t = pd.to_datetime(df[cols["gmt time"]], format="%d.%m.%Y %H:%M:%S.%f", utc=True)
        src = "Dukascopy export (tick volume)"
    elif "ts_event" in cols:
        t = pd.to_datetime(df[cols["ts_event"]], utc=True)
        src = "Databento ohlcv-1m (exchange volume)"
        if "symbol" in cols:                      # keep the most-traded contract each day (front month)
            df["_d"] = t.dt.date
            vol = df.groupby(["_d", cols["symbol"]])[cols["volume"]].transform("sum")
            top = vol == df.assign(_v=vol).groupby("_d")["_v"].transform("max")
            df, t = df[top], t[top]
    elif "time_utc" in cols:
        t = pd.to_datetime(df[cols["time_utc"]], utc=True)
        src = "generic 1m CSV"
    else:
        raise SystemExit(f"Unknown 1m format, columns: {list(df.columns)}")
    out = pd.DataFrame({"t": t.values, "open": df[cols["open"]].values, "high": df[cols["high"]].values,
                        "low": df[cols["low"]].values, "close": df[cols["close"]].values,
                        "volume": df[cols["volume"]].values})
    out["t"] = pd.to_datetime(out["t"], utc=True)
    out = out[out["volume"] > 0].drop_duplicates("t").sort_values("t")   # Dukascopy pads closed hours with 0 volume
    return out.reset_index(drop=True), src


def resample(m1, rule):
    g = m1.set_index("t").resample(rule, label="left", closed="left")
    b = g.agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}).dropna()
    return b.reset_index()


def write(b, path):
    et = b["t"].dt.tz_convert("America/New_York")
    out = pd.DataFrame({"time_utc": b["t"].dt.strftime("%Y-%m-%d %H:%M"), "time_et": et.dt.strftime("%Y-%m-%d %H:%M"),
                        "open": b["open"].round(2), "high": b["high"].round(2), "low": b["low"].round(2),
                        "close": b["close"].round(2), "volume": b["volume"]})
    out.to_csv(path, index=False)


def main():
    src_path = Path(sys.argv[1])
    out_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "data" / "full"
    out_dir.mkdir(parents=True, exist_ok=True)
    m1, src = read_1m(src_path)
    write(m1, out_dir / "MGC_1m.csv")
    for rule, name in [("5min", "5m"), ("15min", "15m"), ("1h", "1h")]:
        write(resample(m1, rule), out_dir / f"MGC_{name}.csv")
    et = m1["t"].dt.tz_convert("America/New_York")
    info = dict(source=src, input=str(src_path), first_bar_et=str(et.iloc[0]), last_bar_et=str(et.iloc[-1]),
                bars_1m=len(m1))
    (out_dir / "data_info.json").write_text(json.dumps(info, indent=2))
    print(json.dumps(info, indent=2))


if __name__ == "__main__":
    main()
