"""Microsoft adapter (unofficial Eightfold "PCSX" search API behind
apply.careers.microsoft.com).

Microsoft's tenant disables the standard Eightfold endpoint
(/api/apply/v2/jobs returns 403 "Not authorized for PCSX"), but the search
endpoint the careers frontend itself calls accepts anonymous GETs. We pull
the newest "software engineer" hits per run (sort_by=timestamp is the value
PCSX honors; "new" is silently ignored), paginating because the endpoint
caps every page at 10 results regardless of the num parameter.

Microsoft titles its entry level just "Software Engineer" (higher levels are
always named in the title: "Software Engineer II", "Senior ..."), so a bare
software-engineer title counts as a new-grad signal alongside the standard
ones; the standard exclusions still reject leveled/senior variants.
"""

from datetime import datetime, timezone

import requests

from notifier.filters import compile_extra, is_new_grad_title, job_in_us
from notifier.models import Job

SEARCH_URL = "https://apply.careers.microsoft.com/api/pcsx/search"
PAGE_SIZE = 10  # PCSX hard cap per page
PAGES = 5

# PCSX 403s obvious non-browser agents, so this adapter sends a browser UA
# (unlike the other adapters).
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://apply.careers.microsoft.com/careers?domain=microsoft.com",
}

# Bare "Software Engineer" (optionally with a team suffix) is Microsoft's
# entry level; the digit lookahead keeps out "Software Engineer 2/3". Some
# postings name the level instead ("Software Engineering IC2" — IC2 is the
# entry band).
_PLAIN_SE = compile_extra(r"^software engineer\b(?!\s*[23]\b)|\bic2\b")


def _to_jobs(payload: dict) -> list[Job]:
    jobs = []
    for item in (payload.get("data") or {}).get("positions", []):
        title = item.get("name") or ""
        position_id = item.get("id")
        if not title or position_id is None:
            continue
        posted = item.get("postedTs") or item.get("creationTs")
        job = Job(
            source="microsoft",
            native_id=str(position_id),
            company="Microsoft",
            title=title,
            url=(
                "https://apply.careers.microsoft.com/careers/job/"
                f"{position_id}?domain=microsoft.com"
            ),
            locations=item.get("locations") or [],
            posted_at=datetime.fromtimestamp(posted, tz=timezone.utc).date().isoformat()
            if posted
            else None,
        )
        if is_new_grad_title(job.title, _PLAIN_SE) and job_in_us(job):
            jobs.append(job)
    return jobs


def fetch(entry: dict | None = None) -> list[Job]:
    jobs: dict[str, Job] = {}  # by uid: pages can shift between requests
    for page in range(PAGES):
        response = requests.get(
            SEARCH_URL,
            params={
                "domain": "microsoft.com",
                "query": "software engineer",
                "num": PAGE_SIZE,
                "start": page * PAGE_SIZE,
                "sort_by": "timestamp",
                "hl": "en",
            },
            headers=_HEADERS,
            timeout=30,
        )
        response.raise_for_status()
        page_jobs = _to_jobs(response.json())
        for job in page_jobs:
            jobs[job.uid] = job
    return list(jobs.values())
