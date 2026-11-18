import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from ff_dashboard.analytics import analyze
from ff_dashboard.draft import playoff_scores, regular_season_scores

FIXTURES = Path(__file__).parent / "fixtures"


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.season = json.loads((FIXTURES / "2025.json").read_text())

    def test_notebook_analytics(self):
        result = analyze([self.season])
        self.assertEqual(result["standings"][0]["win_pct"], 1.0)
        self.assertEqual(result["playoff_appearances"][0]["playoff_apps"], 1)
        self.assertEqual(result["waivers"]["replacement_standards"]["2025"]["QB"], 15)
        waiver = result["waivers"]["all_seasons"]
        self.assertEqual(len(waiver), 1)
        self.assertEqual((waiver[0]["weeks"], waiver[0]["total_points"], waiver[0]["vor"]), (2, 20, -10))
        self.assertIsNone(result["waivers"]["replacement_standards"]["2025"]["RB"])

    def test_ongoing_and_zero_games(self):
        for team in self.season["teams"]:
            team.update(final_standing=0, wins=0, losses=0)
        result = analyze([self.season])
        self.assertIsNone(result["standings"][0]["win_pct"])
        self.assertEqual(result["playoff_appearances"][0]["playoff_apps"], 1)
        self.season["current_week"] = 1
        self.assertEqual(analyze([self.season])["playoff_appearances"][0]["playoff_apps"], 0)

    def test_replacement_uses_bottom_three_starter_scores(self):
        self.season["weeks"] = [{"week": 1, "starters": [
            {"player_id": 1, "position": "QB", "lineup_slot": "QB", "points": 10},
            {"player_id": 2, "position": "QB", "lineup_slot": "QB", "points": 20},
            {"player_id": 4, "position": "QB", "lineup_slot": "QB", "points": 30},
            {"player_id": 5, "position": "QB", "lineup_slot": "QB", "points": 40},
        ]}]
        result = analyze([self.season])["waivers"]
        self.assertEqual(result["replacement_standards"]["2025"]["QB"], 20)
        self.assertEqual(result["all_seasons"][0]["vor"], 0)

    def test_draft_score_selection(self):
        self.assertEqual(regular_season_scores(self.season)["Alex Example"], [100])
        self.assertEqual(playoff_scores(self.season)["Blair Example"], [95])

    def test_cli_reproducible_and_missing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            command = [sys.executable, "-m", "ff_dashboard.cli", "generate", "--start-year", "2025", "--end-year", "2025", "--data-dir", str(FIXTURES), "--output-dir", tmp]
            subprocess.run(command, check=True, capture_output=True)
            first = {p.name: p.read_bytes() for p in Path(tmp).glob("*.json")}
            subprocess.run(command, check=True, capture_output=True)
            self.assertEqual(first, {p.name: p.read_bytes() for p in Path(tmp).glob("*.json")})
            self.assertEqual(json.loads(first["metadata.json"])["seasons"], [2025])
            command[command.index("2025")] = "2024"
            self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)

    def test_view_commands_and_year_selection(self):
        base = [sys.executable, "-m", "ff_dashboard.cli"]
        for command, expected in ((["standings"], "Alex Example"),
                                  (["playoffs"], "Appearances"),
                                  (["waivers", "all"], "Waiver Player"),
                                  (["waivers", "2025"], "Waiver Player"),
                                  (["waivers", "2025", "2025"], "Waiver Player")):
            result = subprocess.run(base + command + ["--data-dir", str(FIXTURES)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(expected, result.stdout)
        for command in (["waivers", "2024", "2025"], ["waivers", "2025", "2024"], ["waivers", "all", "2025"]):
            result = subprocess.run(base + command + ["--data-dir", str(FIXTURES)], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)

    def test_view_all_without_snapshots(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run([sys.executable, "-m", "ff_dashboard.cli", "standings", "--data-dir", tmp],
                                    capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("No season snapshots", result.stderr)


if __name__ == "__main__":
    unittest.main()
