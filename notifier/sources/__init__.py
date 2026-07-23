"""Source registry: builds the list of (name, fetch_callable, tier) triples
from config/companies.yml plus the always-on bespoke sources.

tier 1 (default) = polled every run (~15 min); tier 2 = polled roughly every
other run (~30 min) to stay polite as the company list grows.
"""

import functools
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

import yaml

from notifier.models import Job
from notifier.sources import (
    amazon,
    ashby,
    eightfold,
    greenhouse,
    lever,
    microsoft,
    simplify,
    workday,
)

CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "companies.yml"

# ATS family -> (adapter module, key in the config entry that names the tenant)
_ATS_ADAPTERS = {
    "greenhouse": (greenhouse, "token"),
    "ashby": (ashby, "board"),
    "lever": (lever, "slug"),
    "workday": (workday, "tenant"),
    "eightfold": (eightfold, "domain"),
}


class Source(NamedTuple):
    name: str
    fetch: Callable[[], list[Job]]
    tier: int


def build_sources(config_path: Path = CONFIG_PATH) -> list[Source]:
    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}

    sources = [
        Source("simplify", simplify.fetch, 1),
        Source("amazon", amazon.fetch, 1),
        Source("microsoft", microsoft.fetch, 1),
    ]
    for family, (module, slug_key) in _ATS_ADAPTERS.items():
        for entry in config.get(family) or []:
            name = f"{family}/{entry[slug_key]}"
            sources.append(
                Source(name, functools.partial(module.fetch, entry), entry.get("tier", 1))
            )
    return sources
