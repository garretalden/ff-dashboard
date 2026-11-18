"""Collect season snapshots and generate website-ready JSON."""
import argparse
import json
from pathlib import Path
import sys

from .analytics import analyze


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def available_years(data_dir):
    years = sorted(int(p.stem) for p in data_dir.glob("[0-9][0-9][0-9][0-9].json"))
    if not years:
        raise ValueError(f"No season snapshots found in {data_dir}")
    return years


def load_seasons(data_dir, years):
    seasons = []
    for year in years:
        season = json.loads((data_dir / f"{year}.json").read_text(encoding="utf-8"))
        if season["year"] != year:
            raise ValueError(f"Season file {year}.json has a mismatched year")
        seasons.append(season)
    return seasons


def print_table(rows, columns):
    values = [["-" if row[key] is None else str(row[key]) for key, _ in columns] for row in rows]
    widths = [max(len(label), *(len(row[i]) for row in values)) if values else len(label)
              for i, (_, label) in enumerate(columns)]
    print("  ".join(label.ljust(widths[i]) for i, (_, label) in enumerate(columns)))
    print("  ".join("-" * width for width in widths))
    for row in values:
        print("  ".join(value.ljust(widths[i]) for i, value in enumerate(row)))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("fetch", "generate"):
        p = commands.add_parser(name)
        p.add_argument("--start-year", type=int, required=True)
        p.add_argument("--end-year", type=int, required=True)
        p.add_argument("--data-dir", type=Path, default=Path("data"))
        if name == "generate":
            p.add_argument("--output-dir", type=Path, default=Path("output"))
    for name in ("standings", "playoffs", "waivers"):
        p = commands.add_parser(name, help=f"View {name} from saved season snapshots")
        p.add_argument("--data-dir", type=Path, default=Path("data"))
        if name == "waivers":
            p.add_argument("years", nargs="+", metavar="YEAR|all",
                           help="'all', one year, or an inclusive start and end year")
    args = parser.parse_args(argv)
    if args.command in ("fetch", "generate"):
        if args.start_year > args.end_year:
            parser.error("--start-year must be no later than --end-year")
        years = list(range(args.start_year, args.end_year + 1))
    elif args.command == "waivers" and args.years != ["all"]:
        if len(args.years) not in (1, 2) or not all(y.isascii() and y.isdigit() and len(y) == 4 for y in args.years):
            parser.error("waivers requires 'all', one four-digit year, or two four-digit years")
        start, end = int(args.years[0]), int(args.years[-1])
        if start > end:
            parser.error("start year must be no later than end year")
        years = list(range(start, end + 1))
    try:
        if args.command == "fetch":
            from .espn import collect
            for year in years:
                write_json(args.data_dir / f"{year}.json", collect(year))
                print(f"Saved season {year}")
        elif args.command == "generate":
            seasons = load_seasons(args.data_dir, years)
            results = analyze(seasons)
            for name, value in results.items():
                write_json(args.output_dir / f"{name}.json", value)
            write_json(args.output_dir / "metadata.json", {"schema_version": 1, "seasons": years,
                       "source_current_weeks": {str(s["year"]): s["current_week"] for s in seasons}})
            print(f"Generated analytics for {len(years)} season(s) in {args.output_dir}")
        else:
            if args.command != "waivers" or args.years == ["all"]:
                years = available_years(args.data_dir)
            results = analyze(load_seasons(args.data_dir, years))
            if args.command == "standings":
                print_table(results["standings"], [("name", "Manager"), ("wins", "Wins"),
                            ("losses", "Losses"), ("win_pct", "Win pct")])
            elif args.command == "playoffs":
                print_table(results["playoff_appearances"], [("name", "Manager"), ("playoff_apps", "Appearances"),
                            ("seasons", "Seasons"), ("playoff_pct", "Playoff pct")])
            else:
                print_table(results["waivers"]["all_seasons"], [("player_name", "Player"), ("position", "Pos"),
                            ("year", "Year"), ("total_points", "Points"), ("weeks", "Starts"), ("vor", "VOR")])
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
