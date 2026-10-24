"""Shared fixtures: a small fake meta across three months, built in the real Smogon formats."""

import pytest

from meta_tracker import db, parse

HEADER = """ Total battles: {battles}
 Avg. weight/team: 0.05
 + ---- + ------------------ + --------- + ------ + ------- + ------ + ------- +
 | Rank | Pokemon            | Usage %   | Raw    | %       | Real   | %       |
 + ---- + ------------------ + --------- + ------ + ------- + ------ + ------- +
"""


def usage_text(battles: int, rows: list[tuple[str, float]]) -> str:
    lines = [HEADER.format(battles=battles)]
    for i, (name, pct) in enumerate(rows, 1):
        raw = int(pct * 100)
        lines.append(
            f" | {i:<4} | {name:<18} | {pct:8.5f}% | {raw:<6} | {pct:6.3f}% | {raw:<6} | {pct:6.3f}% | "
        )
    lines.append(" + ---- + ------------------ + --------- + ------ + ------- + ------ + ------- + ")
    return "\n".join(lines)


def chaos(rows: list[tuple[str, float]]) -> dict:
    names = [n for n, _ in rows]
    data = {}
    for name, pct in rows:
        mates = {m: (80.0 if {name, m} == {"Great Tusk", "Kingambit"} else 30.0)
                 for m in names if m != name}
        data[name] = {
            "Raw count": int(pct * 100),
            "usage": pct / 100,
            "Abilities": {"Ability A": 75.0, "Ability B": 25.0},
            "Items": {"Leftovers": 50.0, "Choice Scarf": 30.0},
            "Moves": {"Protect": 90.0, "Earthquake": 60.0, "": 5.0},
            "Teammates": mates,
        }
    return {"info": {"metagame": "gen9ou", "cutoff": 1695}, "data": data}


MONTHS = {
    "2024-01": [("Great Tusk", 30.0), ("Kingambit", 25.0), ("Gholdengo", 20.0), ("Dragonite", 10.0)],
    "2024-02": [("Great Tusk", 32.0), ("Gholdengo", 26.0), ("Kingambit", 22.0), ("Dragonite", 5.0)],
    "2024-03": [("Gholdengo", 35.0), ("Great Tusk", 31.0), ("Kingambit", 20.0), ("Iron Valiant", 8.0)],
}


@pytest.fixture
def conn(tmp_path):
    c = db.connect(tmp_path / "test.db")
    for month, rows in MONTHS.items():
        u = parse.parse_usage_text(usage_text(1000, rows))
        db.load_month(c, "gen9ou", month, 1695, u.total_battles, u.table, parse.parse_chaos(chaos(rows)))
    c.execute("INSERT INTO events VALUES ('gen9ou', '2024-02', 'Test ban', 'ban', '')")
    c.commit()
    yield c
    c.close()
