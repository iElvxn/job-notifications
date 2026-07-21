"""Sends new job postings to a Discord channel via webhook."""

import time

import requests

EMBEDS_PER_MESSAGE = 10  # Discord's limit
DELAY_BETWEEN_MESSAGES_SECONDS = 1


def _job_to_embed(job):
    locations = ", ".join(job.get("locations") or []) or "Not specified"
    if len(locations) > 200:
        locations = locations[:197] + "..."

    return {
        "title": f"{job['company_name']}: {job['title']}",
        "url": job["url"],
        "color": 0x2ECC71,
        "fields": [
            {"name": "Locations", "value": locations, "inline": False},
            {
                "name": "Sponsorship",
                "value": job.get("sponsorship") or "Not specified",
                "inline": True,
            },
        ],
    }


def _chunks(items, size):
    for i in range(0, len(items), size):
        yield items[i : i + size]


def send_new_jobs(webhook_url, jobs):
    """POST one Discord message per chunk of up to EMBEDS_PER_MESSAGE jobs."""
    embeds = [_job_to_embed(job) for job in jobs]

    for chunk in _chunks(embeds, EMBEDS_PER_MESSAGE):
        response = requests.post(webhook_url, json={"embeds": chunk}, timeout=30)
        response.raise_for_status()
        time.sleep(DELAY_BETWEEN_MESSAGES_SECONDS)
