"""sw-watch: StrayWatch's escalation watcher, a custom Switch agent.

Switch has no scheduler, so this small agent keeps the clock. Every minute it
checks the case ledger for cases nobody has accepted in time, and posts an
escalation into the StrayWatch room through the Switch agent protocol.
It needs only the Python standard library.

One-time setup:
  1. In the Switch Gateway, open API Keys and create a key of type
     "registration". Then run:
       python tools/watcher.py register --server http://localhost:PORT --registration-key <key>
     This registers the agent `sw-watch` and saves its own API key to
     .switch-agent.json (git-ignored; never commit it).
  2. In the Telegram group, invite it:   !invite-agent @sw-watch
  3. Find the room:   python tools/watcher.py rooms

Run it (leave the window open during the demo):
  python tools/watcher.py run --room "StrayWatch Ranchi" --minutes 10 --every 60
Test it once without posting:
  python tools/watcher.py run --room "StrayWatch Ranchi" --once --dry-run
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CREDS = ROOT / ".switch-agent.json"
CASES = [sys.executable, str(ROOT / "tools" / "cases.py")]

INSTRUCTIONS = (
    "I am sw-watch, StrayWatch's escalation clock. Every minute I check the case "
    "ledger and post when a case has had no responder for too long. I don't take "
    "instructions; talk to @sw-dispatch or @sw-triage."
)


def http(method: str, url: str, token: str, body: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            raw = r.read().decode() or "{}"
            return json.loads(raw)
    except urllib.error.HTTPError as e:
        sys.exit(f"Switch said {e.code} for {method} {url}: {e.read().decode()[:400]}")
    except urllib.error.URLError as e:
        sys.exit(f"Cannot reach Switch at {url}: {e.reason}. Is the server (and Docker) running?")


def creds() -> dict:
    if not CREDS.exists():
        sys.exit("Not registered yet. Run: python tools/watcher.py register --server ... --registration-key ...")
    return json.loads(CREDS.read_text(encoding="utf-8"))


def cmd_register(a):
    server = a.server.rstrip("/")
    res = http("POST", f"{server}/agents", a.registration_key, {
        "name": "sw-watch",
        "display_name": "StrayWatch Watch",
        "description": INSTRUCTIONS,
        "connector_type": "straywatch-watcher",
        "integration_profile": {
            "connection_model": "session_passive",
            "message_exchange": True,
            "pre_invocation_mediation": [],
            "post_invocation_mediation": [],
            "event_reporting": [],
        },
        "overwrite": a.overwrite,
    })
    CREDS.write_text(json.dumps({"server": server, "agent_id": res["id"], "api_key": res["api_key"]}, indent=2),
                     encoding="utf-8")
    print(f"Registered sw-watch (id {res['id']}). Key saved to {CREDS.name}.")
    print("Next: in the Telegram group send   !invite-agent @sw-watch")


def ops(c: dict, op: str, args: dict | None = None):
    return http("POST", f"{c['server']}/agents/{c['agent_id']}/ops/{op}", c["api_key"], args or {}).get("result")


def all_rooms(c: dict) -> list[dict]:
    res = ops(c, "list_rooms")
    if isinstance(res, dict):
        res = res.get("rooms") or next((v for v in res.values() if isinstance(v, list)), [])
    return [r for r in (res or []) if isinstance(r, dict)]


def cmd_rooms(a):
    rooms = all_rooms(creds())
    if not rooms:
        print("sw-watch is in no rooms yet. In the Telegram group send:  !invite-agent @sw-watch")
    for r in rooms:
        print(f"{r.get('id') or r.get('room_id')}\t{r.get('name')}")


def resolve_room(c: dict, room: str) -> str:
    for r in all_rooms(c):
        rid = r.get("id") or r.get("room_id")
        if room in (rid, r.get("name")) or room.lower() == str(r.get("name", "")).lower():
            return rid
    sys.exit(f"sw-watch is not in a room called {room!r}. Run `python tools/watcher.py rooms`.")


def post(c: dict, room_id: str, text: str) -> None:
    http("POST", f"{c['server']}/agents/{c['agent_id']}/message", c["api_key"], {"room_id": room_id, "content": text})


def check(minutes: int, dry: bool) -> list[str]:
    cmd = CASES + ["overdue", "--minutes", str(minutes)]
    if dry:
        cmd = CASES + ["list", "--open"]
    out = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8").stdout
    if dry:
        return [f"(dry run) open cases:\n{out.strip()}"]
    return [line for line in out.splitlines() if line.startswith("ESCALATE")]


def cmd_run(a):
    c = creds()
    room_id = resolve_room(c, a.room)
    print(f"sw-watch watching room {room_id}: escalate after {a.minutes} min, check every {a.every}s. Ctrl+C to stop.")
    while True:
        for line in check(a.minutes, a.dry_run):
            body = line.removeprefix("ESCALATE ")
            case_id, _, rest = body.partition(" ")
            details, _, who = rest.partition(" -> ")
            text = (f"⏰ {case_id} has had no responder for {a.minutes}+ min.\n"
                    f"{details}\n"
                    f"Escalating to {who.strip()}. Anyone nearby, reply \"@sw-dispatch accept {case_id}\".")
            if a.dry_run:
                print(line)
            else:
                post(c, room_id, text)
                print(f"[{datetime.now():%H:%M}] posted escalation for {case_id}")
        if a.once:
            break
        time.sleep(a.every)


def main():
    p = argparse.ArgumentParser(description="StrayWatch escalation watcher (Switch custom agent)")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("register")
    r.add_argument("--server", required=True, help="Switch server address, e.g. http://localhost:8000")
    r.add_argument("--registration-key", required=True)
    r.add_argument("--overwrite", action="store_true")
    r.set_defaults(fn=cmd_register)
    sub.add_parser("rooms").set_defaults(fn=cmd_rooms)
    run = sub.add_parser("run")
    run.add_argument("--room", required=True, help="room name or id")
    run.add_argument("--minutes", type=int, default=10)
    run.add_argument("--every", type=int, default=60, help="seconds between checks")
    run.add_argument("--once", action="store_true")
    run.add_argument("--dry-run", action="store_true")
    run.set_defaults(fn=cmd_run)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
