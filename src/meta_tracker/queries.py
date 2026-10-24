"""Load the named queries from queries.sql and run them into DataFrames."""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import pandas as pd

SQL_FILE = Path(__file__).with_name("queries.sql")


@dataclass(frozen=True)
class Query:
    name: str
    question: str
    sql: str


@lru_cache
def load_queries() -> dict[str, Query]:
    text = SQL_FILE.read_text(encoding="utf-8")
    queries = {}
    for block in re.split(r"^-- name: ", text, flags=re.M)[1:]:
        name, _, body = block.partition("\n")
        q = re.search(r"^-- question: (.+)$", body, flags=re.M)
        sql = "\n".join(l for l in body.splitlines() if not l.startswith("--")).strip()
        queries[name.strip()] = Query(name.strip(), q.group(1) if q else "", sql)
    return queries


def run(
    conn: sqlite3.Connection,
    name: str,
    format: str,
    month: str | None = None,
    pokemon: str | None = None,
    limit: int = 15,
) -> pd.DataFrame:
    query = load_queries()[name]
    params = {"format": format, "month": month, "pokemon": pokemon, "limit": limit}
    return pd.read_sql_query(query.sql, conn, params=params)
