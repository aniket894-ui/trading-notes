"""Build the markdown tables for the results report from claude/trades/*.csv."""
import sys
from pathlib import Path

import pandas as pd

T = Path(__file__).resolve().parents[1] / "claude" / "trades"
EXITS = ["V1 fixed 2R", "V2 ladder 100/150/200 pips", "V3 level to level", "V4 2R + trail 1 runner"]
SHORT = {"V1 fixed 2R": "V1 2R", "V2 ladder 100/150/200 pips": "V2 ladder",
         "V3 level to level": "V3 level", "V4 2R + trail 1 runner": "V4 trail"}


def money(v):
    if pd.isna(v):
        return "–"
    return ("−" if v < 0 else "+" if v > 0 else "") + f"${abs(v):,.0f}"


def pct(v):
    return "–" if pd.isna(v) else f"{v * 100:.0f}%"


def main_table():
    s = pd.read_csv(T / "summary.csv")
    out = ["| Setup | Exit | Trades | Win % | Net $ | Max drawdown | Shorts | Longs | Total R |",
           "|---|---|--:|--:|--:|--:|--:|--:|--:|"]
    best = s.loc[s.groupby("Test")["Net"].idxmax()].set_index("Test")["Exit"]
    for _, r in s.iterrows():
        first = r.Exit == EXITS[0]
        net = money(r.Net)
        if r.Exit == best[r.Test] and s[s.Test == r.Test]["Net"].nunique() > 1:
            net = f"**{net}**"
        out.append(f"| {r.Test if first else ''} | {SHORT[r.Exit]} | {r.Trades} | {pct(r.Win)} | {net} | "
                   f"{money(r.DD)} | {r['Shorts trades']} · {money(r['Shorts net'])} | "
                   f"{r['Longs trades']} · {money(r['Longs net'])} | {r.R:+.1f} |")
    return "\n".join(out)


def level_table():
    b = pd.read_csv(T / "by_level.csv")
    piv = b.pivot_table(index=["Test", "Level", "Side"], columns="Exit", values="Net", aggfunc="sum")
    base = b[b.Exit == EXITS[0]].set_index(["Test", "Level", "Side"])[["Trades", "Wins"]]
    j = base.join(piv)
    out = ["| Setup | Level | Side | Trades | Wins (2R) | V1 2R | V2 ladder | V3 level | V4 trail |",
           "|---|---|---|--:|--:|--:|--:|--:|--:|"]
    last = None
    for (test, lvl, side), r in j.iterrows():
        name = test.split(" - ")[0] if test != last else ""
        last = test
        out.append(f"| {name} | {lvl} | {side} | {int(r.Trades)} | {int(r.Wins)} | " +
                   " | ".join(money(r.get(e)) for e in EXITS) + " |")
    return "\n".join(out)


def trade_table(test_prefix):
    t = pd.read_csv(T / "all_trades.csv")
    t = t[t.test.str.startswith(test_prefix)]
    key = ["tday", "time_et", "side", "level", "entry", "stop", "lots"]
    base = t[t.exit == EXITS[0]][key].copy()
    for e in EXITS:
        sub = t[t.exit == e][["tday", "time_et", "usd"]].rename(columns={"usd": e})
        base = base.merge(sub, on=["tday", "time_et"], how="left")
    out = ["| Day | Time ET | Side | Level | Entry | Stop | Lots | V1 2R | V2 ladder | V3 level | V4 trail |",
           "|---|---|---|---|--:|--:|--:|--:|--:|--:|--:|"]
    for _, r in base.iterrows():
        cells = [money(r[e]) if not pd.isna(r[e]) else "skipped" for e in EXITS]
        out.append(f"| {r.tday} | {r.time_et} | {r.side} | {r.level} | {r.entry} | {r.stop} | {r.lots} | "
                   + " | ".join(cells) + " |")
    return "\n".join(out)


if __name__ == "__main__":
    what = sys.argv[1]
    print({"main": main_table, "level": level_table}.get(what, lambda: trade_table(what))())
