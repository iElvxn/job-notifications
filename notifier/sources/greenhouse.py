"""Generic Greenhouse adapter (official public job-board API)."""

import requests

from notifier.filters import compile_extra, is_new_grad_title, job_in_us
from notifier.models import Job


def _to_jobs(payload: dict, source: str, company: str, extra_include=None) -> list[Job]:
    jobs = []
    for item in payload.get("jobs", []):
        location = (item.get("location") or {}).get("name") or ""
        job = Job(
            source=source,
            native_id=str(item["id"]),
            company=company,
            title=item["title"],
            url=item["absolute_url"],
            locations=[location] if location else [],
            posted_at=(item.get("first_published") or item.get("updated_at") or "")[:10]
            or None,
        )
        if is_new_grad_title(job.title, extra_include) and job_in_us(job):
            jobs.append(job)
    return jobs


def fetch(entry: dict) -> list[Job]:
    token = entry["token"]
    response = requests.get(
        f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs", timeout=30
    )
    response.raise_for_status()
    return _to_jobs(
        response.json(),
        f"greenhouse/{token}",
        entry["company"],
        compile_extra(entry.get("extra_include")),
    )
