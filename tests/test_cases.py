"""Tests for the StrayWatch ledger. Run: python -m unittest discover tests"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from cases import classify  # noqa: E402

OFF_PEAK = datetime(2026, 11, 6, 14, 0)
PEAK = datetime(2026, 11, 6, 18, 30)


class Rules(unittest.TestCase):
    def test_lane_blocked_main_road_is_high_with_police(self):
        u, welfare, teams, _ = classify("cow", "standing in lane", "main", True, OFF_PEAK)
        self.assertEqual(u, "HIGH")
        self.assertEqual(teams, ["police", "municipal"])
        self.assertFalse(welfare)

    def test_injured_in_lane_is_high_and_welfare(self):
        u, welfare, teams, _ = classify("cow", "lying still", "main", True, OFF_PEAK)
        self.assertEqual((u, welfare), ("HIGH", True))
        self.assertIn("ngo", teams)

    def test_injured_off_lane_is_check_to_ngo(self):
        u, welfare, teams, _ = classify("dog", "limping", "minor", False, OFF_PEAK)
        self.assertEqual((u, welfare, teams), ("CHECK", True, ["ngo"]))

    def test_aggressive_dog_goes_to_abc_never_removal(self):
        u, _, teams, _ = classify("dog", "chasing bikes", "main", False, OFF_PEAK)
        self.assertEqual((u, teams), ("HIGH", ["abc"]))

    def test_minor_road_lane_blocked_peak_is_high(self):
        self.assertEqual(classify("cow", "sitting", "minor", True, PEAK)[0], "HIGH")
        self.assertEqual(classify("cow", "sitting", "minor", True, OFF_PEAK)[0], "CHECK")

    def test_roadside_is_low_and_not_dispatched(self):
        u, _, teams, _ = classify("dog", "on footpath", "main", False, OFF_PEAK)
        self.assertEqual((u, teams), ("LOW", []))


class Ledger(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = {**os.environ, "STRAYWATCH_DATA": self.tmp.name, "PYTHONIOENCODING": "utf-8"}

    def tearDown(self):
        self.tmp.cleanup()

    def run_cli(self, *args, ok=True):
        p = subprocess.run([sys.executable, str(ROOT / "tools" / "cases.py"), *args],
                           capture_output=True, text=True, encoding="utf-8", env=self.env)
        if ok:
            self.assertEqual(p.returncode, 0, p.stderr)
        return p

    def new(self, reporter="@a"):
        out = self.run_cli("new", "--animal", "cow", "--condition", "lying still", "--road", "Ratu Road",
                           "--area", "Ratu", "--road-type", "main", "--lane-blocked", "yes",
                           "--reporter", reporter).stdout
        return json.loads(out)

    def test_full_case_lifecycle(self):
        case = self.new()
        self.assertEqual(case["id"], "SW-0001")
        dup = self.new("@b")
        self.assertEqual(dup["duplicate_of"], "SW-0001")
        self.assertIn("ACCEPTED", self.run_cli("accept", "SW-0001", "--by", "@ngo").stdout)
        refused = self.run_cli("close", "SW-0001", "--by", "@ngo", ok=False)
        self.assertNotEqual(refused.returncode, 0)
        self.assertIn("proof", refused.stderr)
        self.assertIn("CLOSED", self.run_cli("close", "SW-0001", "--by", "@ngo", "--proof", "cow on verge").stdout)
        self.assertEqual(self.run_cli("list", "--open").stdout.strip(), "No live cases.")

    def test_unaccepted_case_escalates(self):
        self.new()
        out = self.run_cli("overdue", "--minutes", "0").stdout
        self.assertIn("ESCALATE SW-0001", out)
        self.assertIn("Nothing unaccepted", self.run_cli("overdue", "--minutes", "0").stdout)


if __name__ == "__main__":
    unittest.main()
