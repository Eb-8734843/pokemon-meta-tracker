"""Paths and defaults. Override the data folder with the META_TRACKER_DATA env var."""

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.environ.get("META_TRACKER_DATA", PROJECT_ROOT / "data"))
RAW_DIR = DATA_DIR / "raw"
DB_PATH = DATA_DIR / "meta.db"
EVENTS_CSV = DATA_DIR / "events.csv"
REPORTS_DIR = PROJECT_ROOT / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"

SMOGON_BASE = "https://www.smogon.com/stats"
DEFAULT_FORMAT = "gen9ou"
# Rating cutoff of the stats file. OU publishes 0/1500/1695/1825; lower tiers use 0/1500/1630/1760.
DEFAULT_CUTOFF = 1695

# Only keep detailed (teammates/moves/items) data for Pokémon above this usage, to keep the DB small.
DETAIL_MIN_USAGE_PCT = 1.0
TOP_TEAMMATES = 30
TOP_MOVES = 20
TOP_ITEMS = 15
