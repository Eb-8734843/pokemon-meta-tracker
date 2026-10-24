import pytest

from meta_tracker import fetch, parse

from .conftest import MONTHS, chaos, usage_text


def test_parse_usage_text():
    u = parse.parse_usage_text(usage_text(4321, MONTHS["2024-01"]))
    assert u.total_battles == 4321
    assert list(u.table["pokemon"]) == ["Great Tusk", "Kingambit", "Gholdengo", "Dragonite"]
    assert u.table.loc[0, "usage_pct"] == pytest.approx(30.0)
    assert list(u.table["rank"]) == [1, 2, 3, 4]


def test_parse_usage_rejects_garbage():
    with pytest.raises(ValueError):
        parse.parse_usage_text("<html>not found</html>")


def test_parse_chaos_percentages():
    tables = parse.parse_chaos(chaos(MONTHS["2024-01"]), min_usage_pct=0)
    items = tables["items"]
    leftovers = items[(items.pokemon == "Great Tusk") & (items.item == "Leftovers")]
    assert leftovers.pct.iloc[0] == pytest.approx(50.0)  # 50 / (75 + 25)
    assert "" not in set(tables["moves"]["move"])  # empty move slot is dropped
    mates = tables["teammates"]
    assert mates[(mates.pokemon == "Great Tusk") & (mates.teammate == "Kingambit")].pct.iloc[0] == 80


def test_parse_chaos_usage_threshold():
    tables = parse.parse_chaos(chaos(MONTHS["2024-02"]), min_usage_pct=10)
    assert "Dragonite" not in set(tables["moves"]["pokemon"])  # 5% < 10%


def test_month_range_crosses_year():
    assert fetch.month_range("2024-11", "2025-02") == ["2024-11", "2024-12", "2025-01", "2025-02"]
