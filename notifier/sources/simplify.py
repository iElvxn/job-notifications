"""SimplifyJobs New-Grad-Positions adapter — the broad-coverage baseline.

The repo is already curated for new-grad roles (hundreds of companies,
updated hourly), so no title filter is applied here — only the US location
filter. This is also the safety net for companies without a direct adapter
yet (Microsoft, Apple, Meta, ...).
"""

from datetime import datetime, timezone

import requests

from notifier.filters import job_in_us
from notifier.models import Job

LISTINGS_URL = (
    "https://raw.githubusercontent.com/SimplifyJobs/"
    "New-Grad-Positions/dev/.github/scripts/listings.json"
)

# Simplify's current main category is "Software"; "Software Engineering" and
# "Data Science, AI & Machine Learning" are legacy values still present on a
# handful of listings. AI/ML/Data and Quant included in full by user choice
# (2026-07-22); Hardware and Product intentionally excluded.
_CATEGORIES = {
    "Software",
    "Software Engineering",
    "AI/ML/Data",
    "Data Science, AI & Machine Learning",
    "Quant",
}


def _to_jobs(payload: list) -> list[Job]:
    jobs = []
    for item in payload:
        if not (
            item.get("active")
            and item.get("is_visible")
            and item.get("category") in _CATEGORIES
        ):
            continue
        posted = item.get("date_posted")
        job = Job(
            source="simplify",
            native_id=str(item["id"]),
            company=item["company_name"],
            title=item["title"],
            url=item["url"],
            locations=item.get("locations") or [],
            posted_at=datetime.fromtimestamp(posted, tz=timezone.utc).date().isoformat()
            if posted
            else None,
        )
        if job_in_us(job):
            jobs.append(job)
    return jobs


def fetch(entry: dict | None = None) -> list[Job]:
    response = requests.get(LISTINGS_URL, timeout=30)
    response.raise_for_status()
    return _to_jobs(response.json())
