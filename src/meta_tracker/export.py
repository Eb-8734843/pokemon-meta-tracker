"""Export the latest month's meta as JSON for the JavaScript Team Builder."""

from __future__ import annotations

import json
import re
import sqlite3
import unicodedata
from pathlib import Path

import pandas as pd

from . import config, db, names

EXPORT_DIR = config.PROJECT_ROOT / "exports"


def slug(name: str) -> str:
    """Smogon name -> PokéAPI-style id, e.g. 'Slowking-Galar' -> 'slowking-galar', 'Mr. Mime' -> 'mr-mime'.

    PokéAPI ids differ for a few forms (e.g. Ogerpon masks), so treat this as a best guess.
    """
    s = name.replace("♀", "-f").replace("♂", "-m")
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[.':%]", "", s)
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def _grouped(df: pd.DataFrame, key: str, cols: list[str], limit: int) -> dict[str, list]:
    return {
        name: [[r[c] for c in cols] for r in g.head(limit).to_dict("records")]
        for name, g in df.sort_values("pct", ascending=False).groupby(key, sort=False)
    }


def build_export(
    conn: sqlite3.Connection, fmt: str, month: str | None = None, top_n: int = 100
) -> dict:
    months = db.loaded_months(conn, fmt)
    if not months:
        raise ValueError(f"No data for {fmt}")
    month = month or months[-1]
    params = (fmt, month)

    usage = pd.read_sql_query(
        """SELECT p.name, u.rank, u.usage_pct FROM usage u JOIN pokemon p ON p.id = u.pokemon_id
           WHERE u.format = ? AND u.month = ? ORDER BY u.rank""",
        conn, params=params,
    ).head(top_n)
    mates = pd.read_sql_query(
        """SELECT a.name, b.name AS teammate, t.pct FROM teammates t
           JOIN pokemon a ON a.id = t.pokemon_id JOIN pokemon b ON b.id = t.teammate_id
           WHERE t.format = ? AND t.month = ?""",
        conn, params=params,
    )
    items = pd.read_sql_query(
        """SELECT p.name, i.item, i.pct FROM items i JOIN pokemon p ON p.id = i.pokemon_id
           WHERE i.format = ? AND i.month = ?""",
        conn, params=params,
    )
    moves = pd.read_sql_query(
        """SELECT p.name, m.move, m.pct FROM moves m JOIN pokemon p ON p.id = m.pokemon_id
           WHERE m.format = ? AND m.month = ?""",
        conn, params=params,
    )
    mates_by, items_by, moves_by = (
        _grouped(mates, "name", ["teammate", "pct"], 15),
        _grouped(items.assign(item=items["item"].map(names.item_name)), "name", ["item", "pct"], 5),
        _grouped(moves.assign(move=moves["move"].map(names.move_name)), "name", ["move", "pct"], 8),
    )

    # Usage history for the trend sparkline in the Team Builder.
    history = pd.read_sql_query(
        """SELECT p.name, u.month, u.usage_pct FROM usage u JOIN pokemon p ON p.id = u.pokemon_id
           WHERE u.format = ?""",
        conn, params=(fmt,),
    )
    history = history[history["name"].isin(usage["name"])]
    hist_by = {n: dict(zip(g["month"], g["usage_pct"].round(2))) for n, g in history.groupby("name")}

    rnd = lambda pairs: [[a, round(b, 1)] for a, b in pairs]  # noqa: E731
    return {
        "format": fmt,
        "month": month,
        "months": months,
        "pokemon": [
            {
                "name": r.name,
                "slug": slug(r.name),
                "rank": int(r.rank),
                "usage": round(r.usage_pct, 2),
                "history": [hist_by.get(r.name, {}).get(m) for m in months],
                "teammates": rnd(mates_by.get(r.name, [])),
                "items": rnd(items_by.get(r.name, [])),
                "moves": rnd(moves_by.get(r.name, [])),
            }
            for r in usage.itertuples()
        ],
    }


def write_export(conn: sqlite3.Connection, fmt: str, month: str | None = None,
                 out_dir: Path = EXPORT_DIR) -> Path:
    data = build_export(conn, fmt, month)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"meta-{fmt}.json"
    path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return path
