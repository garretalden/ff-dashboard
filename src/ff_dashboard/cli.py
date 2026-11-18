"""Collect season snapshots and generate website-ready JSON."""
import argparse
import json
from pathlib import Path
import sys

from .analytics import analyze


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


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
    args = parser.parse_args(argv)
    if args.start_year > args.end_year:
        parser.error("--start-year must be no later than --end-year")
    years = list(range(args.start_year, args.end_year + 1))
    try:
        if args.command == "fetch":
            from .espn import collect
            for year in years:
                write_json(args.data_dir / f"{year}.json", collect(year))
                print(f"Saved season {year}")
        else:
            seasons = []
            for year in years:
                season = json.loads((args.data_dir / f"{year}.json").read_text(encoding="utf-8"))
                if season["year"] != year:
                    raise ValueError(f"Season file {year}.json has a mismatched year")
                seasons.append(season)
            results = analyze(seasons)
            for name, value in results.items():
                write_json(args.output_dir / f"{name}.json", value)
            write_json(args.output_dir / "metadata.json", {"schema_version": 1, "seasons": years,
                       "source_current_weeks": {str(s["year"]): s["current_week"] for s in seasons}})
            print(f"Generated analytics for {len(years)} season(s) in {args.output_dir}")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
