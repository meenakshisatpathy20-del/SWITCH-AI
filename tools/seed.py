"""Generate simulated case history for the hotspot demo.

Writes data/cases.csv with ~45 SIMULATED past cases on real Ranchi roads,
dated over the last 7 days relative to now, so the hotspot report always
has something to show. Every row is marked simulated=yes.

Usage:  python tools/seed.py          (overwrites data/cases.csv)
"""
from __future__ import annotations

import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cases import FIELDS, TIME_FMT, classify, save  # noqa: E402

# (road, area, road_type, weight, typical hours, animals)
SPOTS = [
    ("Ratu Road", "Ratu", "main", 9, [18, 18, 19, 8], ["cow", "cow", "bull", "dog"]),
    ("Main Road", "Firayalal Chowk", "main", 7, [9, 18, 19], ["cow", "dog", "cow"]),
    ("Ring Road", "Kanke", "highway", 6, [19, 20, 6], ["cow", "buffalo", "dog"]),
    ("Kanke Road", "Kanke", "main", 5, [8, 9, 17], ["dog", "dog", "cow"]),
    ("Harmu Road", "Harmu", "main", 4, [18, 19], ["cow", "dog"]),
    ("NH-33", "Namkum", "highway", 4, [21, 22, 6], ["cow", "bull"]),
    ("Lalpur Chowk", "Lalpur", "main", 3, [10, 17], ["dog"]),
    ("Bariatu Road", "Bariatu", "minor", 2, [7, 15], ["dog", "cow"]),
    ("Circular Road", "Lalpur", "minor", 2, [13, 18], ["dog"]),
    ("Kokar Chowk", "Kokar", "main", 2, [9, 19], ["cow", "dog"]),
]
CONDITIONS = ["standing in lane", "sitting in lane", "crossing repeatedly", "lying still", "limping",
              "chasing bikes", "on roadside"]
PEOPLE = ["@ngo_team", "@municipal_team", "@traffic_police", "@volunteer_aman", "@volunteer_riya"]


def main():
    rng = random.Random(7)
    now = datetime.now().replace(second=0, microsecond=0)
    weighted = [s for s in SPOTS for _ in range(s[3])]
    rows = []
    for i in range(45):
        road, area, rtype, _, hours, animals = rng.choice(weighted)
        day = now - timedelta(days=rng.randint(1, 7))
        t = day.replace(hour=rng.choice(hours), minute=rng.randint(0, 59))
        animal = rng.choice(animals)
        cond = rng.choice(CONDITIONS if animal != "cow" else CONDITIONS[:5] + ["on roadside"])
        lane = cond in ("standing in lane", "sitting in lane", "crossing repeatedly", "lying still")
        urgency, welfare, teams, _ = classify(animal, cond, rtype, lane, t)
        accepted = t + timedelta(minutes=rng.randint(4, 35)) if teams else None
        closed = accepted + timedelta(minutes=rng.randint(10, 50)) if accepted and rng.random() < 0.9 else None
        who = rng.choice(PEOPLE) if accepted else ""
        rows.append({
            "id": "", "created_at": t.strftime(TIME_FMT), "reporter": "@citizen", "animal": animal,
            "condition": cond, "road": road, "area": area, "landmark": "", "road_type": rtype,
            "lane_blocked": "yes" if lane else "no", "urgency": urgency,
            "welfare_check": "yes" if welfare else "no", "teams": "+".join(teams),
            "status": "closed" if closed else ("logged" if not teams else "accepted"),
            "accepted_by": who, "accepted_at": accepted.strftime(TIME_FMT) if accepted else "",
            "closed_by": who if closed else "", "closed_at": closed.strftime(TIME_FMT) if closed else "",
            "proof": "photo" if closed else "", "escalated_at": "", "notes": "", "simulated": "yes",
        })
    rows.sort(key=lambda r: r["created_at"])
    for n, r in enumerate(rows, 1):
        r["id"] = f"SW-{n:04d}"
        if r["status"] == "accepted":      # old cases are not left hanging
            r["status"], r["closed_by"], r["closed_at"], r["proof"] = "closed", r["accepted_by"], r["accepted_at"], "photo"
    assert set(rows[0]) == set(FIELDS)
    save(rows)
    print(f"Wrote {len(rows)} simulated cases to data/cases.csv")


if __name__ == "__main__":
    main()
