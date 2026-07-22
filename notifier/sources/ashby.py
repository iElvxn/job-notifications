"""Generic Ashby adapter (official public posting API)."""

import requests

from notifier.filters import compile_extra, is_new_grad_title, job_in_us
from notifier.models import Job


def _to_jobs(payload: dict, source: str, company: str, extra_include=None) -> list[Job]:
    jobs = []
    for item in payload.get("jobs", []):
        if not item.get("isListed", True):
            continue
        locations = [item.get("location") or ""]
        locations += [
            sec.get("location", "") for sec in item.get("secondaryLocations") or []
        ]
        locations = [loc for loc in locations if loc]
        if item.get("isRemote") and not locations:
            locations = ["Remote"]
        job = Job(
            source=source,
            native_id=str(item["id"]),
            company=company,
            title=item["title"],
            url=item["jobUrl"],
            locations=locations,
            posted_at=(item.get("publishedAt") or "")[:10] or None,
        )
        if is_new_grad_title(job.title, extra_include) and job_in_us(job):
            jobs.append(job)
    return jobs


def fetch(entry: dict) -> list[Job]:
    board = entry["board"]
    response = requests.get(
        f"https://api.ashbyhq.com/posting-api/job-board/{board}", timeout=30
    )
    response.raise_for_status()
    return _to_jobs(
        response.json(),
        f"ashby/{board}",
        entry["company"],
        compile_extra(entry.get("extra_include")),
    )
