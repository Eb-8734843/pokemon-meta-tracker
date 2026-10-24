"""SQLite schema and loaders."""

from __future__ import annotations

import csv
import math
import sqlite3
from pathlib import Path

import pandas as pd

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS pokemon (
    id   INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

-- One row per format + month that has been loaded.
CREATE TABLE IF NOT EXISTS format_months (
    format        TEXT NOT NULL,
    month         TEXT NOT NULL,          -- 'YYYY-MM'
    cutoff        INTEGER NOT NULL,
    total_battles INTEGER NOT NULL,
    PRIMARY KEY (format, month)
);

CREATE TABLE IF NOT EXISTS usage (
    format     TEXT NOT NULL,
    month      TEXT NOT NULL,
    pokemon_id INTEGER NOT NULL REFERENCES pokemon(id),
    rank       INTEGER NOT NULL,
    usage_pct  REAL NOT NULL,             -- weighted usage %
    raw_count  INTEGER NOT NULL,
    raw_pct    REAL NOT NULL,
    real_count INTEGER NOT NULL,
    real_pct   REAL NOT NULL,
    PRIMARY KEY (format, month, pokemon_id)
);

CREATE TABLE IF NOT EXISTS teammates (
    format      TEXT NOT NULL,
    month       TEXT NOT NULL,
    pokemon_id  INTEGER NOT NULL REFERENCES pokemon(id),
    teammate_id INTEGER NOT NULL REFERENCES pokemon(id),
    pct         REAL NOT NULL,            -- % of this Pokémon's teams that include the teammate
    PRIMARY KEY (format, month, pokemon_id, teammate_id)
);

CREATE TABLE IF NOT EXISTS moves (
    format     TEXT NOT NULL,
    month      TEXT NOT NULL,
    pokemon_id INTEGER NOT NULL REFERENCES pokemon(id),
    move       TEXT NOT NULL,
    pct        REAL NOT NULL,
    PRIMARY KEY (format, month, pokemon_id, move)
);

CREATE TABLE IF NOT EXISTS items (
    format     TEXT NOT NULL,
    month      TEXT NOT NULL,
    pokemon_id INTEGER NOT NULL REFERENCES pokemon(id),
    item       TEXT NOT NULL,
    pct        REAL NOT NULL,
    PRIMARY KEY (format, month, pokemon_id, item)
);

-- Bans, DLC releases, suspect tests: used for before/after analysis.
CREATE TABLE IF NOT EXISTS events (
    format TEXT NOT NULL,
    month  TEXT NOT NULL,
    name   TEXT NOT NULL,
    kind   TEXT NOT NULL,                 -- ban | unban | dlc | suspect | other
    notes  TEXT,
    PRIMARY KEY (format, month, name)
);

CREATE INDEX IF NOT EXISTS idx_usage_pokemon ON usage (pokemon_id, format, month);
"""

DETAIL_TABLES = ("usage", "teammates", "moves", "items")


def connect(path: Path | str = config.DB_PATH) -> sqlite3.Connection:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
    # Not every SQLite build ships math functions; register the one our queries use.
    conn.create_function("SQRT", 1, math.sqrt, deterministic=True)
    conn.executescript(SCHEMA)
    return conn


def _pokemon_ids(conn: sqlite3.Connection, names) -> dict[str, int]:
    names = sorted(set(names))
    conn.executemany("INSERT OR IGNORE INTO pokemon (name) VALUES (?)", [(n,) for n in names])
    return dict(conn.execute("SELECT name, id FROM pokemon"))


def load_month(
    conn: sqlite3.Connection,
    fmt: str,
    month: str,
    cutoff: int,
    total_battles: int,
    usage: pd.DataFrame,
    details: dict[str, pd.DataFrame] | None = None,
) -> None:
    """Replace all data for (fmt, month) with the given tables."""
    details = details or {}
    names = list(usage["pokemon"])
    if "teammates" in details:
        names += list(details["teammates"]["pokemon"]) + list(details["teammates"]["teammate"])
    for key in ("moves", "items"):
        if key in details:
            names += list(details[key]["pokemon"])

    with conn:
        for table in DETAIL_TABLES:
            conn.execute(f"DELETE FROM {table} WHERE format = ? AND month = ?", (fmt, month))
        ids = _pokemon_ids(conn, names)
        conn.execute(
            "INSERT OR REPLACE INTO format_months VALUES (?, ?, ?, ?)",
            (fmt, month, cutoff, total_battles),
        )
        conn.executemany(
            "INSERT INTO usage VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (fmt, month, ids[r.pokemon], r.rank, r.usage_pct, r.raw_count, r.raw_pct,
                 r.real_count, r.real_pct)
                for r in usage.itertuples()
            ],
        )
        if "teammates" in details:
            conn.executemany(
                "INSERT OR REPLACE INTO teammates VALUES (?, ?, ?, ?, ?)",
                [(fmt, month, ids[r.pokemon], ids[r.teammate], r.pct)
                 for r in details["teammates"].itertuples()],
            )
        for key in ("moves", "items"):
            if key in details:
                conn.executemany(
                    f"INSERT OR REPLACE INTO {key} VALUES (?, ?, ?, ?, ?)",
                    [(fmt, month, ids[r.pokemon], r[2], r.pct) for r in details[key].itertuples()],
                )


def load_events(conn: sqlite3.Connection, path: Path = config.EVENTS_CSV) -> int:
    """Load events.csv (format,month,name,kind,notes). Lines starting with # are ignored."""
    if not Path(path).exists():
        return 0
    with open(path, encoding="utf-8", newline="") as fh:
        rows = [
            (r["format"], r["month"], r["name"], r["kind"], r.get("notes", ""))
            for r in csv.DictReader(line for line in fh if not line.startswith("#"))
        ]
    with conn:
        conn.execute("DELETE FROM events")
        conn.executemany("INSERT OR REPLACE INTO events VALUES (?, ?, ?, ?, ?)", rows)
    return len(rows)


def loaded_months(conn: sqlite3.Connection, fmt: str) -> list[str]:
    return [m for (m,) in conn.execute(
        "SELECT month FROM format_months WHERE format = ? ORDER BY month", (fmt,)
    )]
