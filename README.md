# Hagerstown fantasy football analytics

A Python pipeline for the analyses in `notebooks/Hagerstown.ipynb`. It saves season snapshots and generates static JSON that a website can fetch. The original notebook remains a historical, exploratory reference; its unfinished playoff-performance comparison is not published as a result.

## Setup

Use Python 3.10 or newer. Runtime dependency versions are pinned in `requirements.txt`.

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -c requirements.txt -e .
```

Set `ESPN_LEAGUE_ID`, `ESPN_S2`, and `ESPN_SWID` in the environment, or place them in the existing `~/Projects/.secrets/espn.env` file. Existing environment variables take precedence. Do not put credentials in this repository. Collection is the only step that accesses ESPN; invoke it only when authorized:

```sh
ff-dashboard fetch --start-year 2021 --end-year 2025 --data-dir data
```

This writes one local snapshot per season, overwriting files for those years. Snapshots include league member names and scores and should be treated as private. The `data/` and `output/` directories are ignored by Git. Choose only seasons available to the league; collection failures should be corrected and the command rerun.

Generate website data from the saved snapshots without network access:

```sh
ff-dashboard generate --start-year 2021 --end-year 2025 --data-dir data --output-dir output
```

Both endpoints of the year range are inclusive. Each requested snapshot must exist and identify the matching year. Generation overwrites its four output files. For a fully offline example, use `--start-year 2025 --end-year 2025 --data-dir tests/fixtures`; sample output is in `examples/` and contains fictional data.

## View rankings in the terminal

These commands calculate and display rankings directly from saved snapshots, without network access or writing output files:

```sh
ff-dashboard standings
ff-dashboard playoffs
ff-dashboard waivers all
ff-dashboard waivers 2025
ff-dashboard waivers 2021 2025
```

Standings, playoffs, and `waivers all` use every four-digit season JSON file in `data/`, even if years are missing. A waiver year range is inclusive and requires a snapshot for every year. Add `--data-dir tests/fixtures` to use the fictional example, or specify another snapshot directory. Percentages are shown as fractions; `-` means a value is unavailable. Waiver rows represent player-seasons rather than combined player totals.

## Website data contract

All files are UTF-8 JSON. `metadata.json` has `schema_version` (currently 1), an ordered `seasons` array, and `source_current_weeks` keyed by season. No generation timestamp is included, so identical snapshots produce identical output.

- `standings.json`: array of manager names, wins, losses, and `win_pct`, sorted by rounded win percentage descending. A manager with no wins or losses has a null percentage.
- `playoff_appearances.json`: array of manager names, playoff appearances, seasons, and `playoff_pct`, sorted by rounded percentage and then seasons descending.
- `waivers.json`: `all_seasons` and `by_season` rankings with player ID, name, position, total starter points, weeks started, year, and `vor`; `replacement_standards` maps each season and position to its standard. A missing standard or VOR is null and sorts last.

As in the notebook, managers are identified by full name; ties are excluded from win percentage. A completed season uses final standing for playoff appearances; after the regular season an ongoing season uses current standing. Waiver rankings exclude every drafted player, count only non-bench/non-IR lineup appearances, and use the season average of each week's bottom three nonzero starter scores at each position as replacement level. Positions outside QB, RB, WR, and TE have no replacement standard. These are notebook definitions, not claims about actual transactions or playoff qualification history.

The draft functions in `ff_dashboard.draft` preserve the notebook's regular-season and playoff score selection, including its fixed week 17 limit and two-week score adjustment. The notebook's comparison function has no implementation; it remains intentionally unfinished. Its score-selection assumptions should be reviewed before completing it.

## Tests

```sh
python -m unittest discover -s tests -v
```

Tests use fictional snapshots and do not contact ESPN. To refresh the sample outputs after changing analytics, run the offline generation command above with `--output-dir examples`.
