"""Entry point: poll all sources, notify Discord of new postings, update state.

Run with: python -m notifier.main

Behavior:
- Tier-1 sources are polled every run; tier-2 sources only when >=25 minutes
  have passed since the last tier-2 poll (cron-jitter-proof ~30 min cadence).
- Sources are fetched in parallel (I/O-bound), with per-source error
  isolation: one broken API never kills the run; the run only fails
  (non-zero exit) if every polled source failed.
- A source seen for the first time is seeded silently (no notification spam
  when a new company is added to the config).
- Cross-source dedup: a role already notified under the same normalized
  company|title key (e.g. via SimplifyJobs) is marked seen but not re-sent.
"""

import os
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor

from notifier.discord import send_new_jobs
from notifier.filters import dedup_key
from notifier.sources import build_sources
from notifier.state import load_state, now_iso, save_state, tier2_due, today

MAX_FETCH_WORKERS = 8


def main() -> None:
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        print("DISCORD_WEBHOOK_URL is not set", file=sys.stderr)
        sys.exit(1)

    state = load_state()
    seen = state["seen"]
    notified_keys = state["notified_keys"]
    seeded = set(state["seeded_sources"])

    include_tier2 = tier2_due(state)
    sources = [s for s in build_sources() if s.tier == 1 or include_tier2]
    if include_tier2:
        state["last_tier2_at"] = now_iso()
    else:
        print("Tier-1-only run (tier 2 polled <25 min ago)")

    with ThreadPoolExecutor(max_workers=MAX_FETCH_WORKERS) as executor:
        futures = {source.name: executor.submit(source.fetch) for source in sources}

    new_jobs = []
    failures = []
    for name, future in futures.items():
        try:
            jobs = future.result()
        except Exception:
            failures.append(name)
            print(f"[{name}] FAILED:\n{traceback.format_exc()}", file=sys.stderr)
            continue

        if name not in seeded:
            seeded.add(name)
            for job in jobs:
                seen[job.uid] = today()
                notified_keys[dedup_key(job)] = today()
            print(f"[{name}] first run: seeded {len(jobs)} job(s), no notifications")
            continue

        fresh = [job for job in jobs if job.uid not in seen]
        to_notify = []
        for job in fresh:
            seen[job.uid] = today()
            key = dedup_key(job)
            if key in notified_keys:
                print(f"[{name}] duplicate of already-notified role, skipping: {job.title}")
                continue
            notified_keys[key] = today()
            to_notify.append(job)
        new_jobs.extend(to_notify)
        print(f"[{name}] {len(jobs)} matching, {len(to_notify)} new")

    if new_jobs:
        send_new_jobs(webhook_url, new_jobs)
        print(f"Notified {len(new_jobs)} new job(s)")
    else:
        print("No new jobs")

    state["seeded_sources"] = sorted(seeded)
    save_state(state)

    if failures and len(failures) == len(futures):
        print("All sources failed", file=sys.stderr)
        sys.exit(1)
    if failures:
        print(f"{len(failures)} source(s) failed: {', '.join(failures)}", file=sys.stderr)


if __name__ == "__main__":
    main()
