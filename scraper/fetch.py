"""Fetches and filters new-grad SWE job listings from the SimplifyJobs repo."""

import requests

LISTINGS_URL = (
    "https://raw.githubusercontent.com/SimplifyJobs/"
    "New-Grad-Positions/dev/.github/scripts/listings.json"
)


def fetch_jobs():
    """Return active, visible, Software Engineering job postings."""
    response = requests.get(LISTINGS_URL, timeout=30)
    response.raise_for_status()
    listings = response.json()

    return [
        job
        for job in listings
        if job.get("active")
        and job.get("is_visible")
        and job.get("category") == "Software Engineering"
    ]
