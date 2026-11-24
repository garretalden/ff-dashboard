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
        undecided = analyze([self.season])["playoff_appearances"][0]
        self.assertEqual((undecided["playoff_apps"], undecided["seasons"]), (0, 0))
        self.assertIsNone(undecided["playoff_pct"])

    def test_undecided_season_excluded_from_playoff_pct(self):
        ongoing = json.loads(json.dumps(self.season))
        ongoing.update(year=2026, current_week=1)
        for team in ongoing["teams"]:
            team.update(final_standing=0)
        rows = {r["name"]: r for r in analyze([self.season, ongoing])["playoff_appearances"]}
        self.assertEqual((rows["Alex Example"]["seasons"], rows["Alex Example"]["playoff_pct"]), (1, 1.0))
        self.assertEqual((rows["Blair Example"]["seasons"], rows["Blair Example"]["playoff_pct"]), (1, 0.0))
        standings = {r["name"]: r for r in analyze([self.season, ongoing])["standings"]}
        self.assertEqual(standings["Alex Example"]["wins"], 2)

    def test_championships_and_current_managers(self):
        rows = {r["name"]: r for r in analyze([self.season])["playoff_appearances"]}
        self.assertEqual((rows["Alex Example"]["championships"], rows["Blair Example"]["championships"]), (1, 0))
        ongoing = json.loads(json.dumps(self.season))
        ongoing.update(year=2026, current_week=1)
        for team in ongoing["teams"]:
            team.update(final_standing=0)
        ongoing["teams"][1]["owner"] = "Casey Example"
        result = analyze([ongoing, self.season])
        playoffs = {r["name"]: r for r in result["playoff_appearances"]}
        self.assertEqual(playoffs["Alex Example"]["championships"], 1)
        self.assertEqual(playoffs["Casey Example"]["championships"], 0)
        for table in ("standings", "playoff_appearances"):
            current = {r["name"]: r["current"] for r in result[table]}
            self.assertEqual(current, {"Alex Example": True, "Blair Example": False, "Casey Example": True})

    def test_site_references_contract_files(self):
        web = Path(__file__).parents[1] / "src" / "ff_dashboard" / "web"
        script = (web / "app.js").read_text()
        for name in ("metadata", "standings", "playoff_appearances", "waivers"):
            self.assertIn(f'"{name}"', script)
        html = (web / "index.html").read_text()
        self.assertIn('src="app.js"', html)
        self.assertIn('href="style.css"', html)

    def test_serve_requires_generated_site(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run([sys.executable, "-m", "ff_dashboard.cli", "serve", "--dir", tmp],
                                    capture_output=True, text=True, timeout=30)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("run 'ff-dashboard generate' first", result.stderr)

    def test_rounding_and_tie_breaks(self):
        self.season["weeks"][0]["starters"][1]["points"] = 0.1
        self.season["weeks"][1]["starters"][0]["points"] = 0.2
        waiver = analyze([self.season])["waivers"]["all_seasons"][0]
        self.assertEqual(waiver["total_points"], 0.3)
        for team in self.season["teams"]:
            team.update(wins=1, losses=1, final_standing=1)
        self.season["teams"].reverse()
        result = analyze([self.season])
        self.assertEqual([r["name"] for r in result["standings"]], ["Alex Example", "Blair Example"])
        self.assertEqual([r["name"] for r in result["playoff_appearances"]], ["Alex Example", "Blair Example"])

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
            site = {p.name: p.read_bytes() for p in Path(tmp).iterdir() if p.suffix != ".json"}
            self.assertEqual(set(site), {"index.html", "app.js", "style.css"})
            command[command.index("2025")] = "2024"
            self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)

    def test_view_commands_and_year_selection(self):
        base = [sys.executable, "-m", "ff_dashboard.cli"]
        for command, expected in ((["standings"], "Alex Example"),
                                  (["playoffs"], "Appearances"),
                                  (["waivers", "all"], "Waiver Player"),
                                  (["waivers", "2025"], "Waiver Player"),
                                  (["waivers", "2025", "2025"], "Waiver Player"),
                                  (["standings", "2025"], "Seasons: 2025"),
                                  (["playoffs", "all"], "1.00")):
            result = subprocess.run(base + command + ["--data-dir", str(FIXTURES)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(expected, result.stdout)
        for command in (["waivers", "2024", "2025"], ["waivers", "2025", "2024"], ["waivers", "all", "2025"],
                        ["standings", "2024"], ["waivers", "all", "--limit", "-1"]):
            result = subprocess.run(base + command + ["--data-dir", str(FIXTURES)], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)

    def test_waiver_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            season = json.loads(json.dumps(self.season))
            season["player_names"]["4"] = "Second Waiver"
            season["weeks"][0]["starters"].append({"player_id": 4, "position": "QB", "lineup_slot": "QB", "points": 5})
            (Path(tmp) / "2025.json").write_text(json.dumps(season))
            base = [sys.executable, "-m", "ff_dashboard.cli", "waivers", "all", "--data-dir", tmp]
            limited = subprocess.run(base + ["--limit", "1"], capture_output=True, text=True, check=True).stdout
            self.assertIn("Waiver Player", limited)
            self.assertNotIn("Second Waiver", limited)
            full = subprocess.run(base + ["--limit", "0"], capture_output=True, text=True, check=True).stdout
            self.assertIn("Second Waiver", full)

    def test_view_all_without_snapshots(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run([sys.executable, "-m", "ff_dashboard.cli", "standings", "--data-dir", tmp],
                                    capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("No season snapshots", result.stderr)


if __name__ == "__main__":
    unittest.main()
