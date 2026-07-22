"""Source registry: builds the list of (name, fetch_callable) pairs from
config/companies.yml plus the always-on bespoke sources."""

import functools
from collections.abc import Callable
from pathlib import Path

import yaml

from notifier.models import Job
from notifier.sources import amazon, ashby, eightfold, greenhouse, lever, simplify, workday

CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "companies.yml"

# ATS family -> (adapter module, key in the config entry that names the tenant)
_ATS_ADAPTERS = {
    "greenhouse": (greenhouse, "token"),
    "ashby": (ashby, "board"),
    "lever": (lever, "slug"),
    "workday": (workday, "tenant"),
    "eightfold": (eightfold, "domain"),
}

Source = tuple[str, Callable[[], list[Job]]]


def build_sources(config_path: Path = CONFIG_PATH) -> list[Source]:
    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}

    sources: list[Source] = [
        ("simplify", simplify.fetch),
        ("amazon", amazon.fetch),
    ]
    for family, (module, slug_key) in _ATS_ADAPTERS.items():
        for entry in config.get(family) or []:
            name = f"{family}/{entry[slug_key]}"
            sources.append((name, functools.partial(module.fetch, entry)))
    return sources
