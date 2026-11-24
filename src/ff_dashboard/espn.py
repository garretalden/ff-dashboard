"""Explicitly invoked ESPN collection, isolated from offline analytics."""
import os
from pathlib import Path


def _owner(team):
    owner = team.owners[0]
    return owner["firstName"] + " " + owner["lastName"]


def collect(year):
    from dotenv import load_dotenv
    from espn_api.football import League

    load_dotenv(Path.home() / "Projects" / ".secrets" / "espn.env", override=False)
    missing = [key for key in ("ESPN_S2", "ESPN_SWID", "ESPN_LEAGUE_ID") if not os.environ.get(key)]
    if missing:
        raise ValueError("Missing required environment variables: " + ", ".join(missing))
    league = League(league_id=int(os.environ["ESPN_LEAGUE_ID"]), year=year,
                    swid=os.environ["ESPN_SWID"], espn_s2=os.environ["ESPN_S2"])
    teams = [{"owner": _owner(t), "wins": t.wins, "losses": t.losses,
              "final_standing": t.final_standing, "standing": t.standing,
              "scores": list(t.scores)} for t in league.teams]
    weeks = []
    for number in range(1, league.current_week + 1):
        starters = []
        matchups = []
        for box in league.box_scores(number):
            for player in box.home_lineup + box.away_lineup:
                starters.append({"player_id": player.playerId, "position": player.position,
                                 "lineup_slot": player.lineupSlot, "points": player.points})
            if box.home_team and box.away_team:  # byes leave one side as 0 or None
                matchups.append({"home_owner": _owner(box.home_team), "away_owner": _owner(box.away_team),
                                 "home_final_standing": box.home_team.final_standing,
                                 "away_final_standing": box.away_team.final_standing,
                                 "home_score": box.home_score, "away_score": box.away_score})
        weeks.append({"week": number, "starters": starters, "matchups": matchups})
    return {"year": year, "current_week": league.current_week,
            "reg_season_count": league.settings.reg_season_count,
            "playoff_team_count": league.settings.playoff_team_count,
            "teams": teams, "drafted_player_ids": [p.playerId for p in league.draft],
            "player_names": {str(k): v for k, v in league.player_map.items() if isinstance(k, int)},
            "weeks": weeks}
