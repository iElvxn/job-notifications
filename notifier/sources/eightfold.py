"""Generic Eightfold adapter (unofficial JSON API behind Eightfold-powered
career sites, e.g. Netflix's explore.jobs.netflix.net)."""

from datetime import datetime, timezone

import requests

from notifier.filters import compile_extra, is_new_grad_title, job_in_us
from notifier.models import Job

RESULT_LIMIT = 100

_HEADERS = {"User-Agent": "Mozilla/5.0 (job-notifications personal notifier)"}


def _to_jobs(payload: dict, source: str, company: str, extra_include=None) -> list[Job]:
    jobs = []
    for item in payload.get("positions", []):
        locations = item.get("locations") or []
        if not locations and item.get("location"):
            locations = [item["location"]]
        created = item.get("t_create")
        posted_at = None
        if created:
            posted_at = (
                datetime.fromtimestamp(created, tz=timezone.utc).date().isoformat()
            )
        job = Job(
            source=source,
            native_id=str(item["id"]),
            company=company,
            title=item.get("name") or "",
            url=item.get("canonicalPositionUrl") or "",
            locations=locations,
            posted_at=posted_at,
        )
        if (
            job.title
            and job.url
            and is_new_grad_title(job.title, extra_include)
            and job_in_us(job)
        ):
            jobs.append(job)
    return jobs


def fetch(entry: dict) -> list[Job]:
    base, domain = entry["base"].rstrip("/"), entry["domain"]
    response = requests.get(
        f"{base}/api/apply/v2/jobs",
        params={
            "domain": domain,
            "query": entry.get("query", "software engineer"),
            "num": RESULT_LIMIT,
            "start": 0,
            "sort_by": "new",
        },
        headers=_HEADERS,
        timeout=30,
    )
    response.raise_for_status()
    return _to_jobs(
        response.json(),
        f"eightfold/{domain}",
        entry["company"],
        compile_extra(entry.get("extra_include")),
    )
