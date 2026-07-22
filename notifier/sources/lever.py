"""Generic Lever adapter (official public postings API)."""

from datetime import datetime, timezone

import requests

from notifier.filters import compile_extra, is_new_grad_title, job_in_us
from notifier.models import Job


def _to_jobs(payload: list, source: str, company: str, extra_include=None) -> list[Job]:
    jobs = []
    for item in payload:
        categories = item.get("categories") or {}
        location = categories.get("location") or ""
        created_ms = item.get("createdAt")
        posted_at = None
        if created_ms:
            posted_at = (
                datetime.fromtimestamp(created_ms / 1000, tz=timezone.utc)
                .date()
                .isoformat()
            )
        job = Job(
            source=source,
            native_id=str(item["id"]),
            company=company,
            title=item["text"],
            url=item["hostedUrl"],
            locations=[location] if location else [],
            posted_at=posted_at,
        )
        if is_new_grad_title(job.title, extra_include) and job_in_us(job):
            jobs.append(job)
    return jobs


def fetch(entry: dict) -> list[Job]:
    slug = entry["slug"]
    response = requests.get(
        f"https://api.lever.co/v0/postings/{slug}?mode=json", timeout=30
    )
    response.raise_for_status()
    return _to_jobs(
        response.json(),
        f"lever/{slug}",
        entry["company"],
        compile_extra(entry.get("extra_include")),
    )
