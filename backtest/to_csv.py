"""Convert TradingView OHLCV JSON (columns format) to CSV with UTC and New York timestamps."""
import json, sys, csv
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
NY = ZoneInfo("America/New_York")
src, dst = sys.argv[1], sys.argv[2]
d = json.load(open(src))
b = d["bars"]
n = len(b["t"])
with open(dst, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["time_utc", "time_et", "open", "high", "low", "close", "volume"])
    for i in range(n):
        t = datetime.fromtimestamp(b["t"][i], tz=timezone.utc)
        w.writerow([t.strftime("%Y-%m-%d %H:%M"), t.astimezone(NY).strftime("%Y-%m-%d %H:%M"),
                    b["o"][i], b["h"][i], b["l"][i], b["c"][i], b["v"][i]])
print(d.get("symbol"), d.get("interval"), n, "bars")
