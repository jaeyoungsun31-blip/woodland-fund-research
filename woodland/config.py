"""Configuration loading for the Woodland Fund."""

from __future__ import annotations

import os
from pathlib import Path
from typing import cast

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "universe.yaml"


def load_config(path: Path | str = CONFIG_PATH) -> dict:
    """Load the YAML config. Raises FileNotFoundError / yaml.YAMLError on problems."""
    with open(path) as f:
        return cast(dict, yaml.safe_load(f))


def all_tickers(cfg: dict | None = None) -> list[str]:
    """Flatten the universe groups into one ticker list (order preserved, no dupes)."""
    cfg = cfg or load_config()
    seen: dict[str, None] = {}
    for group in cfg["universe"].values():
        for t in group:
            seen[t] = None
    return list(seen)



ENV_PATH = ROOT / ".env"


def load_env(path: Path | str | None = None) -> dict[str, str]:
    """Parse KEY=VALUE lines from a .env file. Missing file -> empty dict.

    Deliberately tiny (no python-dotenv dependency) and deliberately quiet:
    values are secrets and must never be logged, echoed, or put in a URL
    query string. `.env` is gitignored — see CLAUDE.md rule 8.
    """
    path = Path(path if path is not None else ENV_PATH)
    if not path.exists():
        return {}
    out: dict[str, str] = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def get_secret(name: str, path: Path | str | None = None) -> str | None:
    """Look up a secret: real environment first, then .env. Never logs it."""
    return os.environ.get(name) or load_env(path).get(name) or None
