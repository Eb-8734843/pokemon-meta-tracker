"""Analysis built on the SQLite data: trends, risers/fallers, event impact, teammate network."""

from __future__ import annotations

import sqlite3

import pandas as pd

from . import db


def usage_long(conn: sqlite3.Connection, fmt: str) -> pd.DataFrame:
    """All usage rows for a format: month, pokemon, rank, usage_pct."""
    return pd.read_sql_query(
        """SELECT u.month, p.name AS pokemon, u.rank, u.usage_pct
           FROM usage u JOIN pokemon p ON p.id = u.pokemon_id
           WHERE u.format = ? ORDER BY u.month, u.rank""",
        conn,
        params=(fmt,),
    )


def usage_wide(conn: sqlite3.Connection, fmt: str) -> pd.DataFrame:
    """Months as rows, Pokémon as columns, usage % as values (0 when absent)."""
    long = usage_long(conn, fmt)
    return long.pivot(index="month", columns="pokemon", values="usage_pct").fillna(0.0)


def previous_month(conn: sqlite3.Connection, fmt: str, month: str) -> str | None:
    months = db.loaded_months(conn, fmt)
    i = months.index(month)
    return months[i - 1] if i > 0 else None


def risers_fallers(
    conn: sqlite3.Connection, fmt: str, month: str, compare_to: str | None = None, n: int = 10
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Biggest usage gains and losses between two months (default: the previous month)."""
    compare_to = compare_to or previous_month(conn, fmt, month)
    if compare_to is None:
        raise ValueError(f"No month before {month} to compare against")
    wide = usage_wide(conn, fmt)
    delta = pd.DataFrame({"before": wide.loc[compare_to], "after": wide.loc[month]})
    delta["change"] = delta["after"] - delta["before"]
    delta = delta.rename_axis("pokemon").reset_index()
    risers = delta.nlargest(n, "change").reset_index(drop=True)
    fallers = delta.nsmallest(n, "change").reset_index(drop=True)
    return risers, fallers


def event_impact(
    conn: sqlite3.Connection, fmt: str, event_month: str, window: int = 3, n: int = 10
) -> pd.DataFrame:
    """Average usage in the `window` months before vs after an event.

    The event month itself is excluded because it usually mixes both metas
    (bans and DLC releases rarely land on the 1st).
    """
    wide = usage_wide(conn, fmt)
    before = wide[wide.index < event_month].tail(window)
    after = wide[wide.index > event_month].head(window)
    if before.empty or after.empty:
        raise ValueError(f"Need data on both sides of {event_month} (have {list(wide.index)})")
    out = pd.DataFrame({"before": before.mean(), "after": after.mean()})
    out["change"] = out["after"] - out["before"]
    out = out[(out["before"] >= 1) | (out["after"] >= 1)]
    out = out.reindex(out["change"].abs().sort_values(ascending=False).index).head(n)
    out = out.rename_axis("pokemon").reset_index()
    out.attrs["before_months"] = list(before.index)
    out.attrs["after_months"] = list(after.index)
    return out


def events(conn: sqlite3.Connection, fmt: str) -> pd.DataFrame:
    return pd.read_sql_query(
        "SELECT month, name, kind, notes FROM events WHERE format = ? ORDER BY month",
        conn,
        params=(fmt,),
    )


def teammate_edges(
    conn: sqlite3.Connection, fmt: str, month: str, top_n_pokemon: int = 25, min_pct: float = 25.0
) -> pd.DataFrame:
    """Teammate pairs among the top N Pokémon, kept when they appear together on >= min_pct of teams.

    Each pair is listed once, using the larger of the two directional percentages.
    """
    df = pd.read_sql_query(
        """SELECT a.name AS source, b.name AS target, t.pct
           FROM teammates t
           JOIN pokemon a ON a.id = t.pokemon_id
           JOIN pokemon b ON b.id = t.teammate_id
           JOIN usage ua ON ua.format = t.format AND ua.month = t.month AND ua.pokemon_id = t.pokemon_id
           JOIN usage ub ON ub.format = t.format AND ub.month = t.month AND ub.pokemon_id = t.teammate_id
           WHERE t.format = ? AND t.month = ? AND ua.rank <= ? AND ub.rank <= ?""",
        conn,
        params=(fmt, month, top_n_pokemon, top_n_pokemon),
    )
    if df.empty:
        return df
    key = df.apply(lambda r: tuple(sorted((r.source, r.target))), axis=1)
    df = df.assign(pair=key).sort_values("pct", ascending=False).drop_duplicates("pair")
    return df[df["pct"] >= min_pct].drop(columns="pair").reset_index(drop=True)


def archetypes(edges: pd.DataFrame) -> list[set[str]]:
    """Group Pokémon into clusters with networkx community detection."""
    import networkx as nx
    from networkx.algorithms.community import greedy_modularity_communities

    if edges.empty:
        return []
    g = nx.Graph()
    for r in edges.itertuples():
        g.add_edge(r.source, r.target, weight=r.pct)
    return [set(c) for c in greedy_modularity_communities(g, weight="weight") if len(c) > 1]
