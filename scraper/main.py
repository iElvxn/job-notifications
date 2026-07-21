"""Entry point: fetch new-grad SWE jobs, notify Discord of new ones, update state.

Run with: python -m scraper.main
"""

import os
import sys

from scraper.fetch import fetch_jobs
from scraper.notify import send_new_jobs
from scraper.store import get_seen_ids, init_db, is_empty, mark_seen


def main():
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        print("DISCORD_WEBHOOK_URL is not set", file=sys.stderr)
        sys.exit(1)

    conn = init_db()
    jobs = fetch_jobs()
    print(f"Fetched {len(jobs)} active Software Engineering new-grad postings")

    if is_empty(conn):
        # First run: seed the seen-set silently instead of notifying the entire backlog.
        mark_seen(conn, [job["id"] for job in jobs])
        print(f"Seeded database with {len(jobs)} jobs (no notifications sent)")
        return

    seen_ids = get_seen_ids(conn)
    new_jobs = [job for job in jobs if job["id"] not in seen_ids]

    if new_jobs:
        send_new_jobs(webhook_url, new_jobs)
        mark_seen(conn, [job["id"] for job in new_jobs])
        print(f"Notified {len(new_jobs)} new job(s)")
    else:
        print("No new jobs")


if __name__ == "__main__":
    main()
