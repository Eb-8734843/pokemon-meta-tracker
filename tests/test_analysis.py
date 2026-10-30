import pytest

from meta_tracker import analysis, charts, db, export, names, parse, queries, report

from .conftest import MONTHS, usage_text


def test_loaded_months(conn):
    assert db.loaded_months(conn, "gen9ou") == ["2024-01", "2024-02", "2024-03"]


def test_reload_month_is_idempotent(conn):
    u = parse.parse_usage_text(usage_text(1000, MONTHS["2024-03"]))
    db.load_month(conn, "gen9ou", "2024-03", 1695, 1000, u.table)
    n = conn.execute("SELECT COUNT(*) FROM usage WHERE month='2024-03'").fetchone()[0]
    assert n == 4


@pytest.mark.parametrize("name", list(queries.load_queries()))
def test_every_query_runs(conn, name):
    df = queries.run(conn, name, "gen9ou", month="2024-03", pokemon="Great Tusk", limit=5)
    assert not df.empty, name


def test_at_least_ten_queries_with_questions():
    qs = queries.load_queries()
    assert len(qs) >= 10
    assert all(q.question for q in qs.values())


def test_risers_and_fallers(conn):
    risers, fallers = analysis.risers_fallers(conn, "gen9ou", "2024-03")
    assert risers.iloc[0].pokemon == "Gholdengo"
    assert risers.iloc[0].change == pytest.approx(9.0)
    # Dragonite dropped out of the data entirely, which must count as a fall to 0.
    assert fallers.iloc[0].pokemon == "Dragonite"
    assert fallers.iloc[0].after == 0


def test_sql_risers_match_pandas(conn):
    sql = queries.run(conn, "biggest_risers", "gen9ou", month="2024-03", limit=1)
    assert sql.iloc[0]["name"] == "Gholdengo"


def test_event_impact_excludes_event_month(conn):
    impact = analysis.event_impact(conn, "gen9ou", "2024-02", window=1)
    assert impact.attrs["before_months"] == ["2024-01"]
    assert impact.attrs["after_months"] == ["2024-03"]
    gholdengo = impact.set_index("pokemon").loc["Gholdengo"]
    assert gholdengo.change == pytest.approx(15.0)


def test_teammate_network_finds_strong_pair(conn):
    edges = analysis.teammate_edges(conn, "gen9ou", "2024-03", min_pct=50)
    pairs = {tuple(sorted(p)) for p in zip(edges.source, edges.target)}
    assert pairs == {("Great Tusk", "Kingambit")}


def test_report_mentions_top_riser(conn):
    text = report.monthly_report(conn, "gen9ou", "2024-03")
    assert "biggest riser was **Gholdengo**" in text


def test_charts_render(conn, tmp_path):
    paths = charts.make_all(conn, "gen9ou", out_dir=tmp_path)
    assert len(paths) == 6
    assert all(p.exists() and p.stat().st_size > 0 for p in paths)


def test_export_shape(conn):
    data = export.build_export(conn, "gen9ou")
    assert data["month"] == "2024-03"
    first = data["pokemon"][0]
    assert first["name"] == "Gholdengo" and first["slug"] == "gholdengo"
    assert len(first["history"]) == 3
    assert first["teammates"] and first["items"] and first["moves"]


@pytest.mark.parametrize("name,expected", [
    ("Slowking-Galar", "slowking-galar"), ("Mr. Mime", "mr-mime"),
    ("Nidoran-F", "nidoran-f"), ("Farfetch’d", "farfetchd"), ("Flabébé", "flabebe"),
])
def test_slug(name, expected):
    assert export.slug(name) == expected


def test_names_use_lookup_then_fall_back():
    assert names.item_name("heavydutyboots") == "Heavy-Duty Boots"
    assert names.move_name("uturn") == "U-turn"
    assert names.item_name("nothing") == "No item"
    assert names.move_name("notarealmove") == "Notarealmove"


def test_export_has_readable_names_for_known_ids(conn):
    conn.execute("UPDATE moves SET move = 'uturn' WHERE move = 'Protect'")
    conn.execute("UPDATE items SET item = 'heavydutyboots' WHERE item = 'Leftovers'")
    first = export.build_export(conn, "gen9ou")["pokemon"][0]
    assert "U-turn" in [m for m, _ in first["moves"]]
    assert "Heavy-Duty Boots" in [i for i, _ in first["items"]]
