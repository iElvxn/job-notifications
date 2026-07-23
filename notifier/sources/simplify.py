"""SimplifyJobs New-Grad-Positions adapter — the broad-coverage baseline.

Fetches the raw listings.json behind the repo's README tables. Safety net for
companies without a direct adapter (Apple, Meta, Google, Tesla, Uber, ...).

The feed needs more screening than its "curated for new grads" reputation
suggests (verified 2026-07-23):

- Simplify's bot flips old listings back to active (link re-verified, role
  reopened), so "newly active" is not "newly posted" — over half the active
  feed is months old. Listings whose date_posted is older than MAX_AGE_DAYS
  are skipped so reactivations never notify.
- The category=Software tail includes senior, support, and academic roles
  ("Senior Software Engineer", "Graduate Research Assistant - Developer"),
  so titles go through is_swe_title (exclusions apply, but no new-grad token
  is required — bare "Software Engineer" is normal in this feed).
"""

from datetime import date, datetime, timedelta, timezone

import requests

from notifier.filters import is_swe_title, job_in_us
from notifier.models import Job

LISTINGS_URL = (
    "https://raw.githubusercontent.com/SimplifyJobs/"
    "New-Grad-Positions/dev/.github/scripts/listings.json"
)

# Simplify's current main category is "Software"; "Software Engineering" is a
# legacy value still present on a handful of listings. SWE only by user choice
# (2026-07-22): AI/ML/Data, Quant, Hardware, and Product excluded.
_CATEGORIES = {
    "Software",
    "Software Engineering",
}

# New listings reach Simplify within days of posting, so anything older than
# this on first sight is a reactivation, not news. Genuinely reopened roles
# are the accepted trade-off: Simplify keeps the original posted date, and
# reactivation churn vastly outnumbers real reopenings.
MAX_AGE_DAYS = 14


def _to_jobs(payload: list, today: date | None = None) -> list[Job]:
    cutoff = (today or date.today()) - timedelta(days=MAX_AGE_DAYS)
    jobs = []
    for item in payload:
        if not (
            item.get("active")
            and item.get("is_visible")
            and item.get("category") in _CATEGORIES
            and is_swe_title(item.get("title", ""))
        ):
            continue
        posted = item.get("date_posted")
        posted_date = (
            datetime.fromtimestamp(posted, tz=timezone.utc).date() if posted else None
        )
        if posted_date is not None and posted_date < cutoff:
            continue
        job = Job(
            source="simplify",
            native_id=str(item["id"]),
            company=item["company_name"],
            title=item["title"],
            url=item["url"],
            locations=item.get("locations") or [],
            posted_at=posted_date.isoformat() if posted_date else None,
        )
        if job_in_us(job):
            jobs.append(job)
    return jobs


def fetch(entry: dict | None = None) -> list[Job]:
    response = requests.get(LISTINGS_URL, timeout=30)
    response.raise_for_status()
    return _to_jobs(response.json())
