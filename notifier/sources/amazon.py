"""Amazon adapter (unofficial search.json API behind amazon.jobs).

Pulls the 100 most recent US Software Development postings and filters
locally. Amazon helpfully exposes `university_job`, `is_intern`, and
`is_manager` flags, which we combine with the title filter.
"""

import requests

from notifier.filters import is_new_grad_title
from notifier.models import Job

SEARCH_URL = "https://www.amazon.jobs/en/search.json"
RESULT_LIMIT = 100

_HEADERS = {"User-Agent": "Mozilla/5.0 (job-notifications personal notifier)"}


def _to_jobs(payload: dict) -> list[Job]:
    jobs = []
    for item in payload.get("jobs", []):
        if item.get("is_intern") or item.get("is_manager"):
            continue
        title = item.get("title") or ""
        # university_job is Amazon's own new-grad flag; the title filter
        # catches postings where the flag is missing.
        if not (item.get("university_job") or is_new_grad_title(title)):
            continue
        location = item.get("normalized_location") or item.get("location") or ""
        job_path = item.get("job_path") or ""
        jobs.append(
            Job(
                source="amazon",
                native_id=str(item.get("id_icims") or item.get("id")),
                company="Amazon",
                title=title,
                url=f"https://www.amazon.jobs{job_path}",
                locations=[location] if location else [],
                posted_at=item.get("posted_date"),
            )
        )
    return jobs


def fetch(entry: dict | None = None) -> list[Job]:
    response = requests.get(
        SEARCH_URL,
        params={
            "category[]": "software-development",
            "normalized_country_code[]": "USA",
            "offset": 0,
            "result_limit": RESULT_LIMIT,
            "sort": "recent",
        },
        headers=_HEADERS,
        timeout=30,
    )
    response.raise_for_status()
    return _to_jobs(response.json())
