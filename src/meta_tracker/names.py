"""Readable item and move names. Smogon stats use ids like 'heavydutyboots'.

data/names.json is built from Pokémon Showdown's data files by `meta-tracker names`.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

import requests

from . import config

NAMES_JSON = config.DATA_DIR / "names.json"
SHOWDOWN_DATA = "https://play.pokemonshowdown.com/data"
# items.js is JavaScript, not JSON. `name` isn't always an item's first field, so skip up to it,
# stepping over nested {...} values.
ITEM_RE = re.compile(r'[{,]"?([a-z0-9]+)"?:\{(?:[^{}]|\{[^{}]*\})*?(?<=[{,])name:"([^"]+)"')
SPECIAL = {"nothing": "No item"}


def download(path: Path = NAMES_JSON) -> Path:
    """Fetch the current id -> name tables from Showdown and save them."""
    headers = {"User-Agent": "pokemon-meta-tracker/0.1"}
    moves = requests.get(f"{SHOWDOWN_DATA}/moves.json", headers=headers, timeout=60)
    moves.raise_for_status()
    items = requests.get(f"{SHOWDOWN_DATA}/items.js", headers=headers, timeout=60)
    items.raise_for_status()
    item_names = dict(sorted(ITEM_RE.findall(items.text)))
    if not item_names:
        raise ValueError("No items found in items.js - has Showdown's file format changed?")
    data = {
        "items": item_names,
        "moves": dict(sorted((k, v["name"]) for k, v in moves.json().items())),
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=0), encoding="utf-8")
    _tables.cache_clear()
    return path


@lru_cache
def _tables() -> dict[str, dict[str, str]]:
    if not NAMES_JSON.exists():
        return {"items": {}, "moves": {}}
    return json.loads(NAMES_JSON.read_text(encoding="utf-8"))


def item_name(item_id: str) -> str:
    return SPECIAL.get(item_id) or _tables()["items"].get(item_id) or item_id.title()


def move_name(move_id: str) -> str:
    return _tables()["moves"].get(move_id) or move_id.title()
