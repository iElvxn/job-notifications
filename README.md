# job-notifications

Watches [SimplifyJobs/New-Grad-Positions](https://github.com/SimplifyJobs/New-Grad-Positions)
for new active Software Engineering new-grad postings and sends new ones to a Discord
channel via webhook. Runs on a GitHub Actions cron schedule (every 30 minutes) — no
server to maintain.

## How it works

1. `scraper/fetch.py` downloads the repo's `listings.json` and filters to postings
   that are `active`, `is_visible`, and in the `Software Engineering` category.
2. `scraper/store.py` keeps a SQLite file (`data/seen_jobs.db`) of job IDs already
   notified about, so nothing gets sent twice. This file is committed back to the repo
   after each run so state persists between Action runs.
3. `scraper/notify.py` posts new jobs to Discord as embeds (title, company, locations,
   sponsorship, application link), batched up to Discord's 10-embeds-per-message limit.
4. `scraper/main.py` ties it together. On the very first run it seeds the database
   with all currently-active jobs *without* notifying, so you don't get spammed with
   the entire backlog.

## Setup

1. In Discord: **Channel Settings → Integrations → Webhooks → New Webhook**, copy the
   webhook URL.
2. In the GitHub repo: **Settings → Secrets and variables → Actions → New repository
   secret**, name it `DISCORD_WEBHOOK_URL`, paste the webhook URL.
3. Push to `main` (or trigger the "Scrape new-grad SWE jobs" workflow manually via
   **Actions → Run workflow**) to do the initial seeding run.
4. After that, the workflow runs automatically every 30 minutes and only notifies on
   genuinely new postings.

### Running locally

```bash
pip install -r requirements.txt
export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."   # PowerShell: $env:DISCORD_WEBHOOK_URL="..."
python -m scraper.main
```

## Future sources

Currently this only pulls from SimplifyJobs, which already aggregates hundreds of
companies' career pages and is updated hourly. LinkedIn/Indeed are intentionally
excluded — both actively fight scrapers (Cloudflare, ToS enforcement), making them a
poor fit for a low-maintenance personal tool.

If you want to add specific companies not covered by SimplifyJobs, these ATS vendors
publish legitimate public JSON APIs (the same data that powers their own careers
pages, no auth or scraping required):

| ATS | Endpoint | Notes |
|---|---|---|
| Greenhouse | `https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true` | `{token}` is the slug in `boards.greenhouse.io/{token}` |
| Lever | `https://api.lever.co/v0/postings/{company}?mode=json` | `{company}` is the slug in `jobs.lever.co/{company}` |
| Ashby | `https://api.ashbyhq.com/posting-api/job-board/{company}` | `{company}` is the slug in `jobs.ashbyhq.com/{company}` |
| Workday | no single public API; per-tenant endpoints vary | more brittle, lowest priority |

To add one, write a module (e.g. `scraper/fetch_greenhouse.py`) that returns a list of
dicts in the same shape used internally (`id`, `company_name`, `title`, `url`,
`locations`), then merge its results into the job list in `scraper/main.py`. Prefix
each source's `id` with the source name (e.g. `f"greenhouse:{job['id']}"`) before
dedup so IDs from different sources can't collide.
