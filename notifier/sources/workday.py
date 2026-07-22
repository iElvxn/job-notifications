"""Generic Workday adapter (unofficial cxs API used by Workday's own frontend).

Etiquette: one POST per company per run, limit=20 (Workday's hard cap per
page). We poll every 15 minutes, so the newest 20 search hits are plenty.
"""

import re

import requests

from notifier.filters import compile_extra, is_new_grad_title, job_in_us
from notifier.models import Job

PAGE_LIMIT = 20  # Workday returns an empty list for anything larger

_HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (job-notifications personal notifier)",
}


def _to_jobs(
    payload: dict, source: str, company: str, host: str, site: str, extra_include=None
) -> list[Job]:
    jobs = []
    for item in payload.get("jobPostings", []):
        title = item.get("title") or ""
        external_path = item.get("externalPath") or ""
        if not title or not external_path:
            continue
        bullet_fields = item.get("bulletFields") or []
        native_id = bullet_fields[0] if bullet_fields else external_path
        location = item.get("locationsText") or ""
        # Multi-location postings say just "3 Locations" — treat as unknown
        # so the US filter passes them rather than dropping them.
        if re.fullmatch(r"\d+ locations", location, re.IGNORECASE):
            location = ""
        job = Job(
            source=source,
            native_id=native_id,
            company=company,
            title=title,
            url=f"https://{host}/en-US/{site}{external_path}",
            locations=[location] if location else [],
            posted_at=item.get("postedOn"),  # relative text, e.g. "Posted Today"
        )
        if is_new_grad_title(job.title, extra_include) and job_in_us(job):
            jobs.append(job)
    return jobs


def fetch(entry: dict) -> list[Job]:
    host, tenant, site = entry["host"], entry["tenant"], entry["site"]
    response = requests.post(
        f"https://{host}/wday/cxs/{tenant}/{site}/jobs",
        json={
            "appliedFacets": {},
            "limit": PAGE_LIMIT,
            "offset": 0,
            "searchText": entry.get("search", "new grad software engineer"),
        },
        headers=_HEADERS,
        timeout=30,
    )
    response.raise_for_status()
    return _to_jobs(
        response.json(),
        f"workday/{tenant}",
        entry["company"],
        host,
        site,
        compile_extra(entry.get("extra_include")),
    )
