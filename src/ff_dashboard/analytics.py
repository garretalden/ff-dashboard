"""Pure analytics over saved season records; no network access required."""
from collections import defaultdict
from statistics import mean

POSITIONS = ("QB", "RB", "WR", "TE")


def analyze(seasons):
    managers = {}
    all_waivers = []
    standards_by_year = {}
    for season in sorted(seasons, key=lambda s: s["year"]):
        year = season["year"]
        for team in season["teams"]:
            name = team["owner"]
            row = managers.setdefault(name, {"name": name, "wins": 0, "losses": 0, "playoff_apps": 0, "seasons": 0})
            row["wins"] += team["wins"]
            row["losses"] += team["losses"]
            row["seasons"] += 1
            final = team["final_standing"]
            if final:
                row["playoff_apps"] += int(final <= season["playoff_team_count"])
            elif season["current_week"] > season["reg_season_count"]:
                row["playoff_apps"] += int(team["standing"] <= season["playoff_team_count"])

        player_scores = defaultdict(list)
        positions = {}
        weekly_replacements = defaultdict(list)
        for week in season["weeks"]:
            week_scores = defaultdict(list)
            for player in week["starters"]:
                if player["lineup_slot"] in ("BE", "IR"):
                    continue
                pid = player["player_id"]
                player_scores[pid].append(player["points"])
                positions[pid] = player["position"]
                if player["points"] != 0 and player["position"] in POSITIONS:
                    week_scores[player["position"]].append(player["points"])
            for position, scores in week_scores.items():
                weekly_replacements[position].append(mean(sorted(scores)[:3]))
        standards = {p: mean(weekly_replacements[p]) if weekly_replacements[p] else None for p in POSITIONS}
        standards_by_year[str(year)] = standards
        drafted = set(season["drafted_player_ids"])
        names = {int(k): v for k, v in season["player_names"].items()}
        for pid, scores in player_scores.items():
            # The notebook's inner join excludes players absent from player_map.
            if pid in drafted or pid not in names:
                continue
            position = positions[pid]
            standard = standards.get(position)
            total = sum(scores)
            all_waivers.append({"player_id": pid, "player_name": names[pid], "position": position,
                                "total_points": total, "weeks": len(scores), "year": year,
                                "vor": round(total - len(scores) * standard, 2) if standard is not None else None})
    standings = [{"name": r["name"], "wins": r["wins"], "losses": r["losses"],
                  "win_pct": round(r["wins"] / (r["wins"] + r["losses"]), 2) if r["wins"] + r["losses"] else None}
                 for r in managers.values()]
    standings.sort(key=lambda r: (r["win_pct"] is None, -(r["win_pct"] or 0)))
    playoffs = [{"name": r["name"], "playoff_apps": r["playoff_apps"], "seasons": r["seasons"],
                 "playoff_pct": round(r["playoff_apps"] / r["seasons"], 2)} for r in managers.values()]
    playoffs.sort(key=lambda r: (-r["playoff_pct"], -r["seasons"]))
    all_waivers.sort(key=lambda r: (r["vor"] is None, -(r["vor"] or 0)))
    return {"standings": standings, "playoff_appearances": playoffs,
            "waivers": {"all_seasons": all_waivers,
                        "by_season": {str(s["year"]): [r for r in all_waivers if r["year"] == s["year"]]
                                      for s in sorted(seasons, key=lambda s: s["year"])},
                        "replacement_standards": standards_by_year}}
