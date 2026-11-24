"""Collect season snapshots and generate website-ready JSON."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import shutil
import sys

from .analytics import analyze

WEB_DIR = Path(__file__).parent / "web"
SITE_FILES = ("index.html", "app.js", "style.css")


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


def format_value(value):
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def parse_year_range(values):
    """Return years for one year or an inclusive range, or None for 'all'."""
    if values == ["all"]:
        return None
    if len(values) not in (1, 2) or not all(y.isascii() and y.isdigit() and len(y) == 4 for y in values):
        raise ValueError("expected 'all', one four-digit year, or two four-digit years")
    start, end = int(values[0]), int(values[-1])
    if start > end:
        raise ValueError("start year must be no later than end year")
    return list(range(start, end + 1))


def print_table(rows, columns):
    values = [[format_value(row[key]) for key, _ in columns] for row in rows]
    widths = [max(len(label), *(len(row[i]) for row in values)) if values else len(label)
              for i, (_, label) in enumerate(columns)]
    print("  ".join(label.ljust(widths[i]) for i, (_, label) in enumerate(columns)))
    print("  ".join("-" * width for width in widths))
    for row in values:
        print("  ".join(value.ljust(widths[i]) for i, value in enumerate(row)))


def copy_site(output_dir):
    for name in SITE_FILES:
        shutil.copyfile(WEB_DIR / name, output_dir / name)


def serve(directory, port):
    if not (directory / "index.html").is_file():
        raise ValueError(f"No website in {directory}; run 'ff-dashboard generate' first")
    handler = partial(SimpleHTTPRequestHandler, directory=str(directory))
    with ThreadingHTTPServer(("127.0.0.1", port), handler) as server:
        print(f"Serving {directory} at http://127.0.0.1:{port}/ (Ctrl-C to stop)", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nStopped")


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
    p = commands.add_parser("serve", help="Serve a generated website on localhost")
    p.add_argument("--dir", type=Path, default=Path("output"))
    p.add_argument("--port", type=int, default=8000)
    for name in ("standings", "playoffs", "waivers"):
        p = commands.add_parser(name, help=f"View {name} from saved season snapshots")
        p.add_argument("--data-dir", type=Path, default=Path("data"))
        p.add_argument("years", nargs="*" if name != "waivers" else "+", default=["all"], metavar="YEAR|all",
                       help="'all', one year, or an inclusive start and end year"
                            + (" (default: all)" if name != "waivers" else ""))
        if name == "waivers":
            p.add_argument("--limit", type=int, default=10, help="rows to show; 0 shows all (default: 10)")
    args = parser.parse_args(argv)
    if args.command in ("fetch", "generate"):
        if args.start_year > args.end_year:
            parser.error("--start-year must be no later than --end-year")
        years = list(range(args.start_year, args.end_year + 1))
    elif args.command != "serve":
        try:
            years = parse_year_range(args.years)
        except ValueError as exc:
            parser.error(f"{args.command}: {exc}")
        if args.command == "waivers" and args.limit < 0:
            parser.error("--limit must be zero or positive")
    try:
        if args.command == "serve":
            serve(args.dir, args.port)
        elif args.command == "fetch":
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
            copy_site(args.output_dir)
            print(f"Generated analytics for {len(years)} season(s) in {args.output_dir}")
        else:
            if years is None:
                years = available_years(args.data_dir)
            results = analyze(load_seasons(args.data_dir, years))
            print("Seasons: " + ", ".join(str(y) for y in years))
            if args.command == "standings":
                print_table(results["standings"], [("name", "Manager"), ("wins", "Wins"),
                            ("losses", "Losses"), ("win_pct", "Win pct")])
            elif args.command == "playoffs":
                print_table(results["playoff_appearances"], [("name", "Manager"), ("playoff_apps", "Appearances"),
                            ("seasons", "Decided seasons"), ("playoff_pct", "Playoff pct"),
                            ("championships", "Titles")])
            else:
                rows = results["waivers"]["all_seasons"]
                print_table(rows[:args.limit] if args.limit else rows, [("player_name", "Player"), ("position", "Pos"),
                            ("year", "Year"), ("total_points", "Points"), ("weeks", "Starts"), ("vor", "VOR")])
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
