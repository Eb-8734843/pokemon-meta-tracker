"""Command line entry point: `meta-tracker <command>` (or `python -m meta_tracker`)."""

from __future__ import annotations

import argparse
import logging
import sys

import pandas as pd

from . import charts, config, db, export, fetch, names, pipeline, queries, report


def _months(args) -> list[str]:
    if args.months:
        return args.months
    return fetch.month_range(args.start, args.end or args.start)


def cmd_ingest(args, conn):
    done = pipeline.ingest(conn, _months(args), args.format, args.cutoff, not args.no_details)
    print(f"Loaded {len(done)} month(s): {', '.join(done) or 'none'}")


def cmd_update(args, conn):
    done = pipeline.update(conn, args.format, args.cutoff, args.since)
    print(f"Loaded {len(done)} new month(s): {', '.join(done) or 'already up to date'}")


def cmd_events(args, conn):
    print(f"Loaded {db.load_events(conn)} event(s) from {config.EVENTS_CSV}")


def cmd_status(args, conn):
    rows = conn.execute(
        "SELECT format, COUNT(*), MIN(month), MAX(month), SUM(total_battles) "
        "FROM format_months GROUP BY format"
    ).fetchall()
    if not rows:
        print("Database is empty. Try: meta-tracker ingest --start 2025-01 --end 2025-12")
    for fmt, n, lo, hi, battles in rows:
        print(f"{fmt}: {n} months ({lo} to {hi}), {battles:,} battles")


def cmd_query(args, conn):
    if args.name is None:
        for q in queries.load_queries().values():
            print(f"{q.name:22} {q.question}")
        return
    month = args.month or db.loaded_months(conn, args.format)[-1]
    df = queries.run(conn, args.name, args.format, month=month, pokemon=args.pokemon, limit=args.limit)
    print(f"{queries.load_queries()[args.name].question}  [{args.format} {month}]\n")
    with pd.option_context("display.max_rows", None, "display.width", 120):
        print(df.to_string(index=False))


def cmd_report(args, conn):
    print(f"Wrote {report.write_report(conn, args.format, args.month)}")


def cmd_charts(args, conn):
    for p in charts.make_all(conn, args.format, args.month):
        print(f"Wrote {p}")


def cmd_export(args, conn):
    print(f"Wrote {export.write_export(conn, args.format, args.month)}")


def cmd_names(args, conn):
    print(f"Wrote {names.download()}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="meta-tracker", description=__doc__)
    p.add_argument("--db", default=config.DB_PATH, help="SQLite database path")
    p.add_argument("--format", default=config.DEFAULT_FORMAT, help="e.g. gen9ou, gen9uu")
    p.add_argument("--cutoff", type=int, default=config.DEFAULT_CUTOFF)
    p.add_argument("-v", "--verbose", action="store_true")
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("ingest", help="download and load specific months")
    s.add_argument("--start", help="first month, YYYY-MM")
    s.add_argument("--end", help="last month, YYYY-MM (default: --start)")
    s.add_argument("--months", nargs="+", help="explicit list of months instead of a range")
    s.add_argument("--no-details", action="store_true", help="skip teammates/moves/items (faster)")
    s.set_defaults(func=cmd_ingest)

    s = sub.add_parser("update", help="load any newly published months")
    s.add_argument("--since", help="ignore months before this (default: earliest month in DB)")
    s.set_defaults(func=cmd_update)

    sub.add_parser("events", help="reload data/events.csv").set_defaults(func=cmd_events)
    sub.add_parser("status", help="show what is in the database").set_defaults(func=cmd_status)

    s = sub.add_parser("query", help="run one of the named SQL queries (no name = list them)")
    s.add_argument("name", nargs="?", choices=list(queries.load_queries()))
    s.add_argument("--month")
    s.add_argument("--pokemon", default="Great Tusk")
    s.add_argument("--limit", type=int, default=15)
    s.set_defaults(func=cmd_query)

    s = sub.add_parser("report", help="write the monthly Markdown insight report")
    s.add_argument("--month", help="default: latest loaded month")
    s.set_defaults(func=cmd_report)

    s = sub.add_parser("charts", help="render PNG charts to reports/figures")
    s.add_argument("--month", help="default: latest loaded month")
    s.set_defaults(func=cmd_charts)

    s = sub.add_parser("export", help="write exports/meta-<format>.json for the Team Builder")
    s.add_argument("--month", help="default: latest loaded month")
    s.set_defaults(func=cmd_export)

    sub.add_parser("names", help="refresh item and move names from Showdown").set_defaults(func=cmd_names)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING,
                        format="%(levelname)s %(message)s")
    if args.command == "ingest" and not (args.start or args.months):
        print("ingest needs --start (and optionally --end) or --months", file=sys.stderr)
        return 2
    conn = db.connect(args.db)
    try:
        args.func(args, conn)
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
