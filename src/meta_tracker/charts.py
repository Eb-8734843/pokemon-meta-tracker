"""Static matplotlib charts for the README and reports."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import networkx as nx  # noqa: E402
import pandas as pd  # noqa: E402

from . import analysis, config, db, queries  # noqa: E402


def _save(fig, name: str, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{name}.png"
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def usage_trends(conn, fmt, month, out_dir, n=6) -> Path:
    wide = analysis.usage_wide(conn, fmt)
    top = wide.loc[month].nlargest(n).index
    fig, ax = plt.subplots(figsize=(10, 5))
    for name in top:
        ax.plot(wide.index, wide[name], marker="o", label=name)
    ax.set(title=f"{fmt}: usage of the current top {n}", ylabel="Usage %", xlabel="")
    ax.tick_params(axis="x", rotation=45)
    ax.legend(frameon=False, ncol=2)
    ax.grid(alpha=0.3)
    return _save(fig, f"{fmt}-trends", out_dir)


def risers_fallers(conn, fmt, month, out_dir, n=8) -> Path:
    risers, fallers = analysis.risers_fallers(conn, fmt, month, n=n)
    df = pd.concat([risers, fallers]).drop_duplicates("pokemon").sort_values("change")
    colors = ["#c0392b" if c < 0 else "#27ae60" for c in df["change"]]
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.barh(df["pokemon"], df["change"], color=colors)
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set(title=f"{fmt}: biggest movers in {month}", xlabel="Change in usage (percentage points)")
    return _save(fig, f"{fmt}-{month}-movers", out_dir)


def event_impact(conn, fmt, event_month, event_name, out_dir, window=3) -> Path:
    df = analysis.event_impact(conn, fmt, event_month, window=window, n=10).iloc[::-1]
    fig, ax = plt.subplots(figsize=(8, 6))
    y = range(len(df))
    ax.barh([i + 0.2 for i in y], df["before"], height=0.4, label="before", color="#95a5a6")
    ax.barh([i - 0.2 for i in y], df["after"], height=0.4, label="after", color="#2980b9")
    ax.set_yticks(list(y), df["pokemon"])
    ax.set(title=f"{fmt}: impact of {event_name} ({event_month})",
           xlabel=f"Average usage % ({window} months either side)")
    ax.legend(frameon=False)
    safe = "".join(ch if ch.isalnum() else "-" for ch in event_name.lower())
    return _save(fig, f"{fmt}-event-{event_month}-{safe}", out_dir)


def teammate_network(conn, fmt, month, out_dir) -> Path:
    edges = analysis.teammate_edges(conn, fmt, month)
    g = nx.Graph()
    for r in edges.itertuples():
        g.add_edge(r.source, r.target, weight=r.pct)
    clusters = analysis.archetypes(edges)
    colour_of = {n: i for i, c in enumerate(clusters) for n in c}
    fig, ax = plt.subplots(figsize=(10, 8))
    if g.number_of_nodes():
        pos = nx.spring_layout(g, weight="weight", seed=42, k=0.8)
        widths = [g[u][v]["weight"] / 15 for u, v in g.edges]
        nx.draw_networkx_edges(g, pos, width=widths, alpha=0.4, ax=ax)
        nx.draw_networkx_nodes(
            g, pos, node_color=[colour_of.get(n, -1) for n in g.nodes],
            cmap="tab10", node_size=600, ax=ax,
        )
        nx.draw_networkx_labels(g, pos, font_size=8, ax=ax)
    ax.set_title(f"{fmt} {month}: teammate network of the top 25 (colour = archetype)")
    ax.axis("off")
    return _save(fig, f"{fmt}-{month}-network", out_dir)


def top_heatmap(conn, fmt, out_dir, n=15) -> Path:
    wide = analysis.usage_wide(conn, fmt)
    top = wide.mean().nlargest(n).index
    data = wide[top].T
    fig, ax = plt.subplots(figsize=(max(8, len(wide) * 0.6), 7))
    im = ax.imshow(data.values, aspect="auto", cmap="viridis")
    ax.set_xticks(range(len(data.columns)), data.columns, rotation=45, ha="right")
    ax.set_yticks(range(len(data.index)), data.index)
    fig.colorbar(im, ax=ax, label="Usage %")
    ax.set_title(f"{fmt}: usage heatmap of the {n} most used Pokémon")
    return _save(fig, f"{fmt}-heatmap", out_dir)


def activity(conn, fmt, out_dir) -> Path:
    df = queries.run(conn, "activity", fmt)
    fig, ax1 = plt.subplots(figsize=(10, 4.5))
    ax1.bar(df["month"], df["total_battles"], color="#bdc3c7")
    ax1.set_ylabel("Battles")
    ax1.tick_params(axis="x", rotation=45)
    ax2 = ax1.twinx()
    ax2.plot(df["month"], df["top10_share_of_team_slots"], color="#8e44ad", marker="o")
    ax2.set_ylabel("Top 10 share of team slots (%)", color="#8e44ad")
    ax1.set_title(f"{fmt}: battles per month and meta concentration")
    return _save(fig, f"{fmt}-activity", out_dir)


def make_all(conn: sqlite3.Connection, fmt: str, month: str | None = None,
             out_dir: Path = config.FIGURES_DIR) -> list[Path]:
    months = db.loaded_months(conn, fmt)
    month = month or months[-1]
    paths = [usage_trends(conn, fmt, month, out_dir), top_heatmap(conn, fmt, out_dir),
             activity(conn, fmt, out_dir), teammate_network(conn, fmt, month, out_dir)]
    if months.index(month) > 0:
        paths.append(risers_fallers(conn, fmt, month, out_dir))
    for e in analysis.events(conn, fmt).itertuples():
        try:
            paths.append(event_impact(conn, fmt, e.month, e.name, out_dir))
        except ValueError:
            pass  # not enough data on both sides of this event
    return paths
