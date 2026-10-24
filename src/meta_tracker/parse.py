"""Turn raw Smogon stats files into pandas DataFrames."""

from __future__ import annotations

import gzip
import json
import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from . import config

# | 1    | Great Tusk         | 35.12345% | 123456 | 30.123% | 98765  | 29.123% |
ROW_RE = re.compile(
    r"^\s*\|\s*(\d+)\s*\|\s*(.+?)\s*\|\s*([\d.]+)%\s*\|\s*(\d+)\s*\|\s*([\d.]+)%\s*\|"
    r"\s*(\d+)\s*\|\s*([\d.]+)%\s*\|"
)
TOTAL_RE = re.compile(r"Total battles:\s*(\d+)")

USAGE_COLUMNS = ["rank", "pokemon", "usage_pct", "raw_count", "raw_pct", "real_count", "real_pct"]


@dataclass
class UsageFile:
    total_battles: int
    table: pd.DataFrame


def parse_usage_text(text: str) -> UsageFile:
    """Parse the usage .txt table into a DataFrame (one row per Pokémon)."""
    total = TOTAL_RE.search(text)
    rows = []
    for line in text.splitlines():
        m = ROW_RE.match(line)
        if m:
            rank, name, usage, raw, raw_pct, real, real_pct = m.groups()
            rows.append(
                (int(rank), name, float(usage), int(raw), float(raw_pct), int(real), float(real_pct))
            )
    if not rows:
        raise ValueError("No usage rows found - is this a Smogon usage .txt file?")
    return UsageFile(
        total_battles=int(total.group(1)) if total else 0,
        table=pd.DataFrame(rows, columns=USAGE_COLUMNS),
    )


def parse_usage_file(path: Path) -> UsageFile:
    return parse_usage_text(Path(path).read_text(encoding="utf-8"))


def load_chaos(path: Path) -> dict:
    path = Path(path)
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as fh:
        return json.load(fh)


def _top(d: dict, n: int) -> list[tuple[str, float]]:
    return sorted(d.items(), key=lambda kv: kv[1], reverse=True)[:n]


def parse_chaos(
    chaos: dict,
    min_usage_pct: float = config.DETAIL_MIN_USAGE_PCT,
    top_teammates: int = config.TOP_TEAMMATES,
    top_moves: int = config.TOP_MOVES,
    top_items: int = config.TOP_ITEMS,
) -> dict[str, pd.DataFrame]:
    """Extract teammates, moves and items tables from a chaos JSON blob.

    Chaos values are weighted counts. We convert them to a percentage of the
    Pokémon's own weighted count (the sum of its Abilities), which is how
    Smogon's moveset pages present them.
    """
    teammates, moves, items = [], [], []
    for name, d in chaos["data"].items():
        if d.get("usage", 0) * 100 < min_usage_pct:
            continue
        total = sum(d.get("Abilities", {}).values()) or d.get("Raw count") or 1
        for mate, v in _top(d.get("Teammates", {}), top_teammates):
            teammates.append((name, mate, v / total * 100))
        for move, v in _top({k: v for k, v in d.get("Moves", {}).items() if k}, top_moves):
            moves.append((name, move, v / total * 100))
        for item, v in _top(d.get("Items", {}), top_items):
            items.append((name, item, v / total * 100))
    return {
        "teammates": pd.DataFrame(teammates, columns=["pokemon", "teammate", "pct"]),
        "moves": pd.DataFrame(moves, columns=["pokemon", "move", "pct"]),
        "items": pd.DataFrame(items, columns=["pokemon", "item", "pct"]),
    }
