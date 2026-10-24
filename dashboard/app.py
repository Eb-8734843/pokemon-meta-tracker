"""Streamlit dashboard: pick a Pokémon, see its trend, teammates, items and moves.

Run locally:  streamlit run dashboard/app.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import plotly.express as px  # noqa: E402
import streamlit as st  # noqa: E402

from meta_tracker import analysis, config, db, queries  # noqa: E402

st.set_page_config(page_title="Pokémon Meta Tracker", page_icon="📈", layout="wide")


@st.cache_resource
def get_conn():
    return db.connect(config.DB_PATH)


conn = get_conn()
formats = [f for (f,) in conn.execute("SELECT DISTINCT format FROM format_months ORDER BY format")]
if not formats:
    st.error("The database is empty. Run `meta-tracker ingest --start 2025-01 --end 2025-12` first.")
    st.stop()

st.title("Pokémon Competitive Meta Tracker")
st.caption("How the Smogon meta changes over time, and why. Data: smogon.com/stats")

with st.sidebar:
    fmt = st.selectbox("Format", formats)
    months = db.loaded_months(conn, fmt)
    month = st.selectbox("Month", months[::-1])
    long = analysis.usage_long(conn, fmt)
    ranked = long[long["month"] == month].sort_values("rank")["pokemon"].tolist()
    pokemon = st.selectbox("Pokémon", ranked)

tab_poke, tab_meta, tab_events = st.tabs(["Pokémon", "Meta overview", "Event impact"])

with tab_poke:
    trend = long[long["pokemon"] == pokemon]
    row = trend[trend["month"] == month].iloc[0]
    c1, c2, c3 = st.columns(3)
    c1.metric("Rank", f"#{row['rank']}")
    c2.metric("Usage", f"{row['usage_pct']:.2f}%")
    prev = analysis.previous_month(conn, fmt, month)
    if prev is not None and (trend["month"] == prev).any():
        prev_pct = trend.loc[trend["month"] == prev, "usage_pct"].iloc[0]
        c3.metric(f"Change vs {prev}", f"{row['usage_pct'] - prev_pct:+.2f} pts")

    st.plotly_chart(
        px.line(trend, x="month", y="usage_pct", markers=True, title=f"{pokemon} usage over time",
                labels={"usage_pct": "Usage %", "month": ""}),
        width="stretch",
    )
    left, right = st.columns(2)
    with left:
        st.subheader("Top teammates")
        st.dataframe(queries.run(conn, "top_teammates", fmt, month=month, pokemon=pokemon, limit=10),
                     hide_index=True, width="stretch")
    with right:
        st.subheader("Items and moves")
        st.dataframe(queries.run(conn, "top_items_and_moves", fmt, month=month, pokemon=pokemon),
                     hide_index=True, width="stretch")

with tab_meta:
    st.subheader(f"Top 20 in {month}")
    st.dataframe(queries.run(conn, "top_usage", fmt, month=month, limit=20),
                 hide_index=True, width="stretch")
    if prev:
        risers, fallers = analysis.risers_fallers(conn, fmt, month, n=8)
        l, r = st.columns(2)
        l.subheader("Risers")
        l.dataframe(risers, hide_index=True, width="stretch")
        r.subheader("Fallers")
        r.dataframe(fallers, hide_index=True, width="stretch")
    clusters = analysis.archetypes(analysis.teammate_edges(conn, fmt, month))
    if clusters:
        st.subheader("Archetypes (teammate clusters)")
        for i, c in enumerate(clusters, 1):
            st.markdown(f"**{i}.** " + ", ".join(sorted(c)))

with tab_events:
    ev = analysis.events(conn, fmt)
    if ev.empty:
        st.info("No events for this format. Add rows to data/events.csv and run `meta-tracker events`.")
    else:
        choice = st.selectbox("Event", ev.itertuples(), format_func=lambda e: f"{e.month}: {e.name}")
        window = st.slider("Months either side", 1, 6, 3)
        try:
            impact = analysis.event_impact(conn, fmt, choice.month, window=window, n=12)
            st.caption(f"Before: {', '.join(impact.attrs['before_months'])} | "
                       f"After: {', '.join(impact.attrs['after_months'])}")
            st.plotly_chart(
                px.bar(impact.melt(id_vars="pokemon", value_vars=["before", "after"]),
                       x="value", y="pokemon", color="variable", barmode="group", orientation="h",
                       labels={"value": "Average usage %", "pokemon": "", "variable": ""}),
                width="stretch",
            )
        except ValueError as e:
            st.warning(str(e))
