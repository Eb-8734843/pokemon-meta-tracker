"""Fetch -> parse -> load, for one or many months."""

from __future__ import annotations

import logging
import sqlite3

import requests

from . import config, db, fetch, parse

log = logging.getLogger(__name__)


def ingest_month(
    conn: sqlite3.Connection,
    month: str,
    fmt: str = config.DEFAULT_FORMAT,
    cutoff: int = config.DEFAULT_CUTOFF,
    include_details: bool = True,
) -> None:
    usage_path, chaos_path = fetch.fetch_month(month, fmt, cutoff, include_chaos=include_details)
    usage = parse.parse_usage_file(usage_path)
    details = parse.parse_chaos(parse.load_chaos(chaos_path)) if chaos_path else None
    db.load_month(conn, fmt, month, cutoff, usage.total_battles, usage.table, details)
    log.info("%s %s: %d Pokémon, %d battles", fmt, month, len(usage.table), usage.total_battles)


def ingest(
    conn: sqlite3.Connection,
    months: list[str],
    fmt: str = config.DEFAULT_FORMAT,
    cutoff: int = config.DEFAULT_CUTOFF,
    include_details: bool = True,
) -> list[str]:
    """Ingest each month, skipping (and logging) months Smogon doesn't have. Returns loaded months."""
    done = []
    for month in months:
        try:
            ingest_month(conn, month, fmt, cutoff, include_details)
            done.append(month)
        except requests.HTTPError as e:
            log.warning("Skipping %s %s: %s", fmt, month, e)
    db.load_events(conn)
    return done


def update(
    conn: sqlite3.Connection,
    fmt: str = config.DEFAULT_FORMAT,
    cutoff: int = config.DEFAULT_CUTOFF,
    since: str | None = None,
) -> list[str]:
    """Ingest any months Smogon has published that aren't in the DB yet."""
    have = set(db.loaded_months(conn, fmt))
    since = since or (min(have) if have else None)
    todo = [m for m in fetch.available_months() if m not in have and (since is None or m >= since)]
    return ingest(conn, todo, fmt, cutoff)
