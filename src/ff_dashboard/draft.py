"""Notebook's playoff score selection; comparison remains intentionally unfinished."""
from collections import defaultdict


def regular_season_scores(season):
    return {t["owner"]: t["scores"][:season["reg_season_count"]] for t in season["teams"]}


def playoff_scores(season):
    reg = season["reg_season_count"]
    scores = defaultdict(list)
    for week in season["weeks"]:
        number = week["week"]
        if not reg + 1 <= number < 18:
            continue
        for match in week.get("matchups", []):
            for side in ("home", "away"):
                if number == reg + 1 or match[f"{side}_final_standing"] <= 2:
                    score = match[f"{side}_score"]
                    if number > reg + 1 and number >= 16:
                        score /= 2
                    scores[match[f"{side}_owner"]].append(score)
    return dict(scores)
