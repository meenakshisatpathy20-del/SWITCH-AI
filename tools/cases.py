"""StrayWatch case ledger.

The single source of truth for every stray-animal case reported in the
StrayWatch room. The Switch agents call this script instead of keeping
state in their heads, so urgency, routing and timings are deterministic
and every agent in the room sees the same cases.

Usage (run from the repo root):
  python tools/cases.py new --animal cow --road "Ratu Road" --area Ratu \
      --road-type main --lane-blocked yes --condition standing --reporter @priya
  python tools/cases.py accept SW-0042 --by @ngo_volunteer
  python tools/cases.py close  SW-0042 --by @ngo_volunteer --proof "photo in chat"
  python tools/cases.py show   SW-0042
  python tools/cases.py list   [--open]
  python tools/cases.py overdue [--minutes 10]
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = Path(os.environ.get("STRAYWATCH_DATA", ROOT / "data"))
LEDGER = DATA / "cases.csv"
RESPONDERS = ROOT / "data" / "responders.json"

FIELDS = [
    "id", "created_at", "reporter", "animal", "condition", "road", "area",
    "landmark", "road_type", "lane_blocked", "urgency", "welfare_check",
    "teams", "status", "accepted_by", "accepted_at", "closed_by", "closed_at",
    "proof", "escalated_at", "notes", "simulated",
]

PEAK_HOURS = [(8, 11), (17, 20)]          # 8-11 AM and 5-8 PM
DUPLICATE_WINDOW_MIN = 60
INJURY_WORDS = ("injured", "lying", "still", "bleeding", "hit", "limping", "not moving", "dead")
AGGRESSIVE_WORDS = ("aggressive", "chasing", "biting", "bit")
TIME_FMT = "%Y-%m-%d %H:%M"


# ---------- storage ----------

def load() -> list[dict]:
    if not LEDGER.exists():
        return []
    with LEDGER.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save(rows: list[dict]) -> None:
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    tmp = LEDGER.with_suffix(".tmp")
    with tmp.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in FIELDS})
    tmp.replace(LEDGER)


def responders() -> dict:
    if RESPONDERS.exists():
        return json.loads(RESPONDERS.read_text(encoding="utf-8"))
    return {}


def now() -> datetime:
    return datetime.now().replace(second=0, microsecond=0)


def parse(ts: str) -> datetime | None:
    return datetime.strptime(ts, TIME_FMT) if ts else None


def find(rows: list[dict], case_id: str) -> dict:
    case_id = case_id.upper().lstrip("#")
    for r in rows:
        if r["id"] == case_id:
            return r
    sys.exit(f"ERROR: no case {case_id}. Run `python tools/cases.py list --open`.")


# ---------- rules (from the StrayWatch urgency policy) ----------

def is_peak(t: datetime) -> bool:
    return any(a <= t.hour < b for a, b in PEAK_HOURS)


def classify(animal: str, condition: str, road_type: str, lane_blocked: bool, t: datetime):
    """Return (urgency, welfare_check, teams, reason)."""
    cond = condition.lower()
    injured = any(w in cond for w in INJURY_WORDS)
    aggressive = any(w in cond for w in AGGRESSIVE_WORDS)
    busy_road = road_type in ("main", "highway")
    peak = is_peak(t)
    is_cattle = animal.lower() in ("cow", "bull", "buffalo", "cattle", "ox", "calf")

    reasons = []
    if lane_blocked and (busy_road or peak):
        urgency = "HIGH"
        reasons.append("lane blocked on " + ("a " + road_type + " road" if busy_road else "a minor road at peak hour"))
    elif injured:
        urgency = "CHECK"
        reasons.append("animal may be injured")
    elif aggressive:
        urgency = "HIGH" if lane_blocked or busy_road else "CHECK"
        reasons.append("aggressive dog near traffic" if urgency == "HIGH" else "aggressive dog reported")
    elif lane_blocked:
        urgency = "CHECK"
        reasons.append("lane blocked on a minor road, off-peak")
    else:
        urgency = "LOW"
        reasons.append("off the lane, no injury reported")
    if peak:
        reasons.append("peak hour")

    welfare = injured
    if injured and urgency == "HIGH":
        reasons.append("also a welfare check")

    teams = []
    if urgency != "LOW":
        if lane_blocked and urgency == "HIGH":
            teams.append("police")
        if aggressive and not is_cattle:
            teams.append("abc")
        elif injured:
            teams.append("ngo")
        elif is_cattle:
            teams.append("municipal")
        else:
            teams.append("ngo")
    return urgency, welfare, teams, "; ".join(reasons)


def is_duplicate(rows, road, animal, t):
    for r in reversed(rows):
        if r["status"] in ("closed",):
            continue
        created = parse(r["created_at"])
        if (r["road"].lower() == road.lower() and r["animal"].lower() == animal.lower()
                and created and t - created <= timedelta(minutes=DUPLICATE_WINDOW_MIN)):
            return r
    return None


def next_id(rows) -> str:
    nums = [int(r["id"].split("-")[1]) for r in rows if r["id"].startswith("SW-")]
    return f"SW-{(max(nums) + 1 if nums else 1):04d}"


# ---------- output ----------

def handles(teams: list[str]) -> str:
    book = responders()
    out = []
    for t in teams:
        entry = book.get(t, {})
        out.append(f"{entry.get('name', t)} {entry.get('telegram', '(no contact set)')}")
    return ", ".join(out) if out else "none (logged for the hotspot map)"


def line(r: dict) -> str:
    age = ""
    created = parse(r["created_at"])
    if created and r["status"] != "closed":
        age = f" · open {int((now() - created).total_seconds() // 60)} min"
    who = f" · by {r['accepted_by']}" if r["accepted_by"] else ""
    return (f"{r['id']} [{r['urgency']}] {r['animal']} · {r['condition']} · "
            f"{r['road']} ({r['area']}) · {r['status'].upper()}{who}{age}")


# ---------- commands ----------

def cmd_new(a):
    rows = load()
    t = now()
    lane = a.lane_blocked.lower() in ("yes", "y", "true", "1")
    dup = is_duplicate(rows, a.road, a.animal, t)
    if dup and not a.force:
        dup["notes"] = (dup["notes"] + f" | also reported by {a.reporter} at {t:%H:%M}").strip(" |")
        save(rows)
        print(json.dumps({
            "duplicate_of": dup["id"],
            "message": f"DUPLICATE of {dup['id']} (same {a.animal} on {a.road}, still {dup['status']}). "
                       f"Added {a.reporter} as a second reporter. Do not dispatch again.",
            "case": line(dup),
        }, indent=2, ensure_ascii=False))
        return
    urgency, welfare, teams, reason = classify(a.animal, a.condition, a.road_type, lane, t)
    row = dict.fromkeys(FIELDS, "")
    row.update({
        "id": next_id(rows), "created_at": t.strftime(TIME_FMT), "reporter": a.reporter,
        "animal": a.animal.lower(), "condition": a.condition, "road": a.road, "area": a.area,
        "landmark": a.landmark, "road_type": a.road_type, "lane_blocked": "yes" if lane else "no",
        "urgency": urgency, "welfare_check": "yes" if welfare else "no", "teams": "+".join(teams),
        "status": "open" if teams else "logged", "notes": a.notes, "simulated": "no",
    })
    rows.append(row)
    save(rows)
    print(json.dumps({
        "id": row["id"], "urgency": urgency, "welfare_check": welfare, "reason": reason,
        "dispatch_to": handles(teams), "teams": teams, "case": line(row),
    }, indent=2, ensure_ascii=False))


def cmd_accept(a):
    rows = load()
    r = find(rows, a.id)
    if r["status"] == "closed":
        sys.exit(f"ERROR: {r['id']} is already closed.")
    if r["accepted_by"] and r["accepted_by"] != a.by:
        print(f"NOTE: {r['id']} was already accepted by {r['accepted_by']}. Adding {a.by} as backup.")
        r["notes"] = (r["notes"] + f" | backup: {a.by}").strip(" |")
    else:
        r["accepted_by"], r["accepted_at"], r["status"] = a.by, now().strftime(TIME_FMT), "accepted"
    save(rows)
    mins = int((parse(r["accepted_at"]) - parse(r["created_at"])).total_seconds() // 60)
    print(f"ACCEPTED {line(r)} · response time {mins} min")


def cmd_close(a):
    rows = load()
    r = find(rows, a.id)
    if not a.proof:
        sys.exit("ERROR: a case closes only with proof. Ask the responder for a photo.")
    r["closed_by"], r["closed_at"], r["proof"], r["status"] = a.by, now().strftime(TIME_FMT), a.proof, "closed"
    if not r["accepted_by"]:
        r["accepted_by"], r["accepted_at"] = a.by, r["closed_at"]
    save(rows)
    mins = int((parse(r["closed_at"]) - parse(r["created_at"])).total_seconds() // 60)
    print(f"CLOSED {r['id']} by {a.by} with proof ({a.proof}). Report to cleared: {mins} min.")


def cmd_show(a):
    print(json.dumps(find(load(), a.id), indent=2, ensure_ascii=False))


def cmd_list(a):
    rows = [r for r in load() if r["simulated"] != "yes"]
    if a.open:
        rows = [r for r in rows if r["status"] in ("open", "accepted", "escalated")]
    order = {"HIGH": 0, "CHECK": 1, "LOW": 2}
    rows.sort(key=lambda r: (order.get(r["urgency"], 3), r["created_at"]))
    print("\n".join(line(r) for r in rows) if rows else "No live cases.")


def cmd_overdue(a):
    rows = load()
    t = now()
    hits = []
    for r in rows:
        if r["status"] != "open" or r["simulated"] == "yes":
            continue
        created = parse(r["created_at"])
        if created and t - created >= timedelta(minutes=a.minutes):
            r["status"], r["escalated_at"] = "escalated", t.strftime(TIME_FMT)
            backup = responders().get("escalation", {})
            hits.append(f"ESCALATE {line(r)} -> {backup.get('name', 'escalation')} {backup.get('telegram', '')}")
    save(rows)
    print("\n".join(hits) if hits else f"Nothing unaccepted for {a.minutes}+ min.")


def main():
    p = argparse.ArgumentParser(description="StrayWatch case ledger")
    sub = p.add_subparsers(dest="cmd", required=True)
    n = sub.add_parser("new")
    n.add_argument("--animal", required=True)
    n.add_argument("--condition", default="standing")
    n.add_argument("--road", required=True)
    n.add_argument("--area", default="")
    n.add_argument("--landmark", default="")
    n.add_argument("--road-type", choices=["highway", "main", "minor"], default="main")
    n.add_argument("--lane-blocked", default="no")
    n.add_argument("--reporter", default="unknown")
    n.add_argument("--notes", default="")
    n.add_argument("--force", action="store_true", help="file even if it looks like a duplicate")
    n.set_defaults(fn=cmd_new)
    for name, fn in (("accept", cmd_accept), ("close", cmd_close), ("show", cmd_show)):
        s = sub.add_parser(name)
        s.add_argument("id")
        if name != "show":
            s.add_argument("--by", required=True)
        if name == "close":
            s.add_argument("--proof", default="")
        s.set_defaults(fn=fn)
    l = sub.add_parser("list")
    l.add_argument("--open", action="store_true")
    l.set_defaults(fn=cmd_list)
    o = sub.add_parser("overdue")
    o.add_argument("--minutes", type=int, default=10)
    o.set_defaults(fn=cmd_overdue)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
