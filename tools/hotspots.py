"""StrayWatch hotspot report.

Reads the case ledger (data/cases.csv) and prints where and when stray
animals keep causing trouble, so the city can act before the rush.

Usage:
  python tools/hotspots.py            # last 7 days
  python tools/hotspots.py --days 14
"""
from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

import os
LEDGER = Path(os.environ.get("STRAYWATCH_DATA", Path(__file__).resolve().parent.parent / "data")) / "cases.csv"
FMT = "%Y-%m-%d %H:%M"


def window(hour: int) -> str:
    return f"{hour % 12 or 12}{'AM' if hour < 12 else 'PM'}-{(hour + 1) % 12 or 12}{'AM' if hour + 1 < 12 or hour + 1 == 24 else 'PM'}"


def minutes(a: str, b: str) -> float | None:
    if not a or not b:
        return None
    return (datetime.strptime(b, FMT) - datetime.strptime(a, FMT)).total_seconds() / 60


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--days", type=int, default=7)
    p.add_argument("--top", type=int, default=5)
    args = p.parse_args()

    since = datetime.now() - timedelta(days=args.days)
    with LEDGER.open(newline="", encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if datetime.strptime(r["created_at"], FMT) >= since]
    if not rows:
        print(f"No cases in the last {args.days} days.")
        return

    spots = defaultdict(list)
    for r in rows:
        spots[(r["road"], int(r["created_at"][11:13]))].append(r)
    ranked = sorted(spots.items(), key=lambda kv: (-len(kv[1]), kv[0]))[: args.top]

    print(f"STRAYWATCH HOTSPOTS · last {args.days} days · {len(rows)} cases")
    print(f"(simulated history: {sum(r['simulated'] == 'yes' for r in rows)}, live: {sum(r['simulated'] != 'yes' for r in rows)})")
    print()
    for i, ((road, hour), cases) in enumerate(ranked, 1):
        animals = Counter(r["animal"] for r in cases).most_common(2)
        high = sum(r["urgency"] == "HIGH" for r in cases)
        mix = ", ".join(f"{n} {a}" for a, n in animals)
        print(f"{i}. {road}, {window(hour)}: {len(cases)} cases ({mix}), {high} HIGH")

    print()
    clear = [m for r in rows if (m := minutes(r["created_at"], r["closed_at"])) is not None]
    accept = [m for r in rows if (m := minutes(r["created_at"], r["accepted_at"])) is not None]
    welfare = [r for r in rows if r["welfare_check"] == "yes"]
    if accept:
        print(f"Avg time to a responder accepting: {sum(accept) / len(accept):.0f} min")
    if clear:
        print(f"Avg time from report to cleared:   {sum(clear) / len(clear):.0f} min")
    print(f"Welfare checks (possibly injured): {len(welfare)}, closed with proof: {sum(r['status'] == 'closed' for r in welfare)}")
    print(f"Still open: {sum(r['status'] in ('open', 'accepted', 'escalated') for r in rows)}, escalated: {sum(bool(r['escalated_at']) for r in rows)}")

    print()
    print("RECOMMENDED ACTIONS")
    for (road, hour), cases in ranked[:3]:
        top_animal = Counter(r["animal"] for r in cases).most_common(1)[0][0]
        team = "municipal cattle team" if top_animal in ("cow", "bull", "buffalo", "calf") else "NGO / ABC team"
        print(f"- {road}: schedule the {team} at {window(hour - 1 if hour else 23).split('-')[0]}, before the {window(hour)} rush.")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
