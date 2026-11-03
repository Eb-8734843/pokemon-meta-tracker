# Pokémon Competitive Meta Tracker

Pipeline that loads Smogon's monthly usage stats into SQLite and explains how the meta changes.
Project 1 of 3 in a portfolio; see [docs/PORTFOLIO.md](docs/PORTFOLIO.md) for the whole picture and the
SwiftUI plan.

## Commands

```bash
python -m venv .venv && .venv\Scripts\activate     # macOS/Linux: source .venv/bin/activate
pip install -e ".[dashboard,dev]"
pytest -q
meta-tracker status
meta-tracker update                                   # load any new months (gen9ou by default)
meta-tracker --format gen9uu --cutoff 1630 update     # UU uses a different cutoff
meta-tracker report | charts | export                 # --format goes before the command word
meta-tracker events                                   # reload data/events.csv
meta-tracker names                                    # refresh item/move names from Showdown
streamlit run dashboard/app.py
```

## Layout

- `src/meta_tracker/`: `fetch` → `parse` → `db` (pipeline in `pipeline.py`), then `analysis`,
  `queries.sql` (named queries), `report`, `charts`, `export` (JSON for the Team Builder), `names`.
- `data/meta.db` is committed (the dashboard and Action read it). `data/raw/` is git-ignored cache.
- `exports/meta-<format>.json` is read live by the Team Builder, so keep its shape stable
  (`format, month, months, pokemon[{name, slug, rank, usage, history, teammates, items, moves}]`).
- `.github/workflows/update-data.yml` runs on the 3rd of each month and commits new data for OU and UU.

## Conventions

- Cutoffs: OU 1695, lower tiers such as UU 1630.
- `data/events.csv` entries must come from Smogon's tiering history (the SV OU forum rules thread) with
  exact dates. Findings in the README separate what the data shows from confirmed causes.
- Event analysis compares months before vs after and excludes the event month itself.
- Tests use synthetic files in Smogon's formats (`tests/conftest.py`) and need no network.
- On Windows PowerShell, files written with `Set-Content -Encoding utf8` get a BOM that breaks
  `pyproject.toml`; write files without one.
