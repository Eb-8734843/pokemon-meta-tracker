"""Download monthly usage files from smogon.com/stats.

Two files are fetched per month:
  * usage text:  {BASE}/{month}/{format}-{cutoff}.txt          (rank, usage %, raw counts)
  * chaos JSON:  {BASE}/{month}/chaos/{format}-{cutoff}.json   (teammates, moves, items, ...)
The chaos file is large, so it is stored gzipped.
"""

from __future__ import annotations

import gzip
import re
import time
from pathlib import Path

import requests

from . import config

USER_AGENT = "pokemon-meta-tracker/0.1 (portfolio project; github.com)"
MONTH_RE = re.compile(r'href="(\d{4}-\d{2})/"')


def _session() -> requests.Session:
    s = requests.Session()
    s.headers["User-Agent"] = USER_AGENT
    return s


def usage_url(month: str, fmt: str, cutoff: int) -> str:
    return f"{config.SMOGON_BASE}/{month}/{fmt}-{cutoff}.txt"


def chaos_url(month: str, fmt: str, cutoff: int) -> str:
    return f"{config.SMOGON_BASE}/{month}/chaos/{fmt}-{cutoff}.json"


def available_months(session: requests.Session | None = None) -> list[str]:
    """Months listed on the Smogon stats index, oldest first (e.g. ['2014-11', ...])."""
    s = session or _session()
    resp = s.get(config.SMOGON_BASE + "/", timeout=30)
    resp.raise_for_status()
    return sorted(set(MONTH_RE.findall(resp.text)))


def month_range(start: str, end: str) -> list[str]:
    """Inclusive list of YYYY-MM strings between start and end."""
    y, m = map(int, start.split("-"))
    ey, em = map(int, end.split("-"))
    out = []
    while (y, m) <= (ey, em):
        out.append(f"{y:04d}-{m:02d}")
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


def _download(url: str, dest: Path, session: requests.Session, gzip_output: bool = False) -> Path:
    if dest.exists():
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    with session.get(url, stream=True, timeout=120) as resp:
        resp.raise_for_status()
        opener = gzip.open if gzip_output else open
        with opener(tmp, "wb") as fh:
            for chunk in resp.iter_content(chunk_size=1 << 16):
                fh.write(chunk)
    tmp.replace(dest)
    time.sleep(1)  # be polite to Smogon's server
    return dest


def fetch_month(
    month: str,
    fmt: str = config.DEFAULT_FORMAT,
    cutoff: int = config.DEFAULT_CUTOFF,
    raw_dir: Path = config.RAW_DIR,
    include_chaos: bool = True,
    session: requests.Session | None = None,
) -> tuple[Path, Path | None]:
    """Download (or reuse cached) files for one month. Returns (usage_path, chaos_path)."""
    s = session or _session()
    folder = raw_dir / month
    usage_path = _download(usage_url(month, fmt, cutoff), folder / f"{fmt}-{cutoff}.txt", s)
    chaos_path = None
    if include_chaos:
        chaos_path = _download(
            chaos_url(month, fmt, cutoff), folder / f"{fmt}-{cutoff}.json.gz", s, gzip_output=True
        )
    return usage_path, chaos_path
