"""Sends new job postings to a Discord channel via webhook."""

import time

import requests

from notifier.models import Job

EMBEDS_PER_MESSAGE = 10  # Discord's limit
DELAY_BETWEEN_MESSAGES_SECONDS = 1

# Stable color per source family so pings are scannable at a glance.
_SOURCE_COLORS = {
    "simplify": 0x95A5A6,  # gray — aggregator baseline
    "amazon": 0xFF9900,
    "google": 0x4285F4,
    "eightfold": 0xE50914,  # Netflix red
    "workday": 0x76B900,
    "greenhouse": 0x24A47F,
    "ashby": 0x6B4EFF,
    "lever": 0x939498,
}
_DEFAULT_COLOR = 0x2ECC71


def _job_to_embed(job: Job) -> dict:
    locations = ", ".join(job.locations) or "Not specified"
    if len(locations) > 200:
        locations = locations[:197] + "..."

    family = job.source.split("/", 1)[0]
    embed = {
        "title": f"{job.company}: {job.title}"[:256],
        "url": job.url,
        "color": _SOURCE_COLORS.get(family, _DEFAULT_COLOR),
        "fields": [{"name": "Locations", "value": locations, "inline": False}],
        "footer": {"text": f"via {job.source}"},
    }
    if job.posted_at:
        embed["fields"].append(
            {"name": "Posted", "value": job.posted_at, "inline": True}
        )
    return embed


def _chunks(items, size):
    for i in range(0, len(items), size):
        yield items[i : i + size]


def send_new_jobs(webhook_url: str, jobs: list[Job]) -> None:
    """POST one Discord message per chunk of up to EMBEDS_PER_MESSAGE jobs."""
    embeds = [_job_to_embed(job) for job in jobs]

    for chunk in _chunks(embeds, EMBEDS_PER_MESSAGE):
        response = requests.post(webhook_url, json={"embeds": chunk}, timeout=30)
        response.raise_for_status()
        time.sleep(DELAY_BETWEEN_MESSAGES_SECONDS)
