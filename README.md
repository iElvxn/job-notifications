# job-notifications

Watches for new-grad SWE postings across many sources and pings a Discord
channel via webhook, usually within 15 minutes of a role going live. Runs free
on a GitHub Actions cron — no server to maintain.

## Sources

| Source | What it covers | How |
|---|---|---|
| `simplify` | Broad baseline: hundreds of companies incl. Microsoft/Apple/Meta/Google | [SimplifyJobs/New-Grad-Positions](https://github.com/SimplifyJobs/New-Grad-Positions) `listings.json` (curated, updated hourly) |
| `amazon` | Amazon SDE new-grad roles, minutes after posting | amazon.jobs `search.json` (unofficial GET API) |
| `greenhouse/*` | Stripe, Databricks, Anthropic | official public board API |
| `ashby/*` | OpenAI, Ramp, Notion | official public posting API |
| `lever/*` | (none yet — adapter ready) | official public postings API |
| `workday/*` | NVIDIA, Salesforce | unofficial cxs API (POST, 20 results/page) |
| `eightfold/*` | Netflix | unofficial Eightfold API |

Direct-company sources apply a **balanced new-grad title filter** (matches
"new grad" / "university graduate" / "entry level" / "SWE I" / class-year
tokens; rejects senior/staff/intern/PhD/level-II+) plus a **US-only location
filter**. SimplifyJobs is already new-grad-curated, so only the location
filter applies there.

## How it works

1. `notifier/sources/` — one adapter per source family; generic ATS adapters
   (Greenhouse/Lever/Ashby/Workday/Eightfold) are driven by
   `config/companies.yml`, so adding a company is a config edit, not code.
   Every adapter returns normalized `Job`s with `uid = "<source>:<native_id>"`.
2. `notifier/state.py` — `data/seen.json` records every uid already notified
   (plus which sources have been seeded). Committed back to the repo after
   each run so state persists with human-readable diffs.
3. `notifier/main.py` — polls every source with per-source error isolation
   (one broken API never kills the run; the run only fails if *all* sources
   fail), then posts genuinely new jobs to Discord as embeds, color-coded by
   source.
4. **First run of any source seeds silently** — adding a new company never
   spams the channel with its backlog.

## Setup

1. In Discord: **Channel Settings → Integrations → Webhooks → New Webhook**,
   copy the webhook URL.
2. In the GitHub repo: **Settings → Secrets and variables → Actions → New
   repository secret**, name `DISCORD_WEBHOOK_URL`, paste the URL.
3. Trigger the "Poll new-grad SWE jobs" workflow manually (**Actions → Run
   workflow**) to do the initial silent seeding run.
4. It then runs every 15 minutes and pings only on genuinely new postings.

### Adding a company

Find the company's ATS from its careers-page URL and add an entry to
`config/companies.yml`:

- `boards.greenhouse.io/<token>` → `greenhouse:` block
- `jobs.ashbyhq.com/<board>` → `ashby:` block
- `jobs.lever.co/<slug>` → `lever:` block
- `<tenant>.wd<N>.myworkdayjobs.com/<site>` → `workday:` block
- Eightfold-powered sites (`/api/apply/v2/jobs` in network tab) → `eightfold:` block

The new source seeds silently on its next run.

If a company uses nonstandard titling for new-grad roles, add an
`extra_include` regex to its entry — e.g. Salesforce calls the level
"AMTS"/"MTS", so its entry carries `extra_include: '\ba?mts\b'`. The pattern
is OR'd with the standard new-grad signals (senior/staff/intern exclusions
still apply).

### Running locally

```bash
pip install -r requirements.txt
export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."   # PowerShell: $env:DISCORD_WEBHOOK_URL="..."
python -m notifier.main
pytest   # filter + adapter parsing tests
```

## Phase 2 ideas (not built)

- **Microsoft / Apple / Meta / Google bespoke adapters** — their career sites
  need CSRF/GraphQL tokens or client-side RPC (Google embeds no job JSON in
  the page at all, verified 2026-07-21). Covered by `simplify` meanwhile. An
  Apify-actor-backed adapter is a drop-in fallback if faster coverage is ever
  worth paying for.
- **LinkedIn/Indeed** — intentionally excluded; both actively fight scrapers.
