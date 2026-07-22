"""Entry point: poll all sources, notify Discord of new postings, update state.

Run with: python -m notifier.main

Behavior:
- A source seen for the first time is seeded silently (no notification spam
  when a new company is added to the config).
- One source failing never kills the run; the run only fails (non-zero exit)
  if every source failed.
"""

import os
import sys
import traceback

from notifier.discord import send_new_jobs
from notifier.sources import build_sources
from notifier.state import load_state, save_state, today


def main() -> None:
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        print("DISCORD_WEBHOOK_URL is not set", file=sys.stderr)
        sys.exit(1)

    sources = build_sources()
    state = load_state()
    seen = state["seen"]
    seeded = set(state["seeded_sources"])

    new_jobs = []
    failures = []
    for name, fetch in sources:
        try:
            jobs = fetch()
        except Exception:
            failures.append(name)
            print(f"[{name}] FAILED:\n{traceback.format_exc()}", file=sys.stderr)
            continue

        if name not in seeded:
            seeded.add(name)
            for job in jobs:
                seen[job.uid] = today()
            print(f"[{name}] first run: seeded {len(jobs)} job(s), no notifications")
            continue

        fresh = [job for job in jobs if job.uid not in seen]
        for job in fresh:
            seen[job.uid] = today()
        new_jobs.extend(fresh)
        print(f"[{name}] {len(jobs)} matching, {len(fresh)} new")

    if new_jobs:
        send_new_jobs(webhook_url, new_jobs)
        print(f"Notified {len(new_jobs)} new job(s)")
    else:
        print("No new jobs")

    state["seeded_sources"] = sorted(seeded)
    save_state(state)

    if failures and len(failures) == len(sources):
        print("All sources failed", file=sys.stderr)
        sys.exit(1)
    if failures:
        print(f"{len(failures)} source(s) failed: {', '.join(failures)}", file=sys.stderr)


if __name__ == "__main__":
    main()
