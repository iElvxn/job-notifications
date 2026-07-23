# job-notifications

Watches for new-grad SWE postings across 80+ sources and pings a Discord
channel via webhook, usually within 15 minutes of a role going live. Runs free
on a GitHub Actions cron — no server to maintain. (The repo is public so
Actions minutes are unlimited; the webhook URL lives in a repo secret.)

## Sources

| Source | What it covers | How |
|---|---|---|
| `simplify` | Broad baseline: hundreds of companies incl. Microsoft/Apple/Meta/Google; SWE category only (AI/ML/Data and Quant categories excluded by choice) | [SimplifyJobs/New-Grad-Positions](https://github.com/SimplifyJobs/New-Grad-Positions) `listings.json` (curated, updated hourly) |
| `amazon` | Amazon SDE new-grad roles, minutes after posting | amazon.jobs `search.json` (unofficial GET API) |
| `microsoft` | Microsoft entry-level SWE (bare "Software Engineer" / "IC2" titles = their entry band, plus explicit new-grad titles) | apply.careers.microsoft.com `api/pcsx/search` (unofficial Eightfold-PCSX API; newest 50, paginated 10/page, `sort_by=timestamp`) |
| `greenhouse/*` | Stripe, Databricks, Anthropic, Figma, Coinbase, Datadog, Waymo, xAI, SpaceX, Anduril, + ~30 more incl. quant (HRT, Jump, Akuna, IMC, Optiver, DRW, Five Rings, Point72, Squarepoint, ...) | official public board API |
| `ashby/*` | OpenAI, Ramp, Notion, Cursor, Linear, Modal, Perplexity, Sierra, Harvey, ElevenLabs, Vanta, Replit, Supabase, Benchling | official public posting API |
| `lever/*` | Palantir, Plaid, Zoox | official public postings API |
| `workday/*` | NVIDIA, Salesforce, Adobe (university site), Snap, Intel, Workday | unofficial cxs API (POST, 20 results/page) |
| `eightfold/*` | Netflix, Snowflake | unofficial Eightfold API |

**Tiers:** tier-1 companies (the dream list) are polled every run (~15 min);
tier-2 (`tier: 2` in the config) roughly every other run (~30 min), gated by
elapsed time in state rather than wall-clock minutes because Actions cron
fires late routinely.

**Cross-source dedup:** a role already notified under the same normalized
company+title by a *different* source family (e.g. via SimplifyJobs *and* a
direct adapter) is only sent once. Same-family repeats still notify —
distinct reqs legitimately share generic titles (Microsoft posts many bare
"Software Engineer" reqs). Keys are pruned after 7 days: long enough to
cover the cross-source arrival lag, short enough not to suppress genuinely
new same-titled postings.

**Not pollable (own portals, covered via `simplify` only):** Jane Street,
Two Sigma, Citadel, Tesla, Uber, Apple, Meta, Google, Qualcomm,
AMD, EA, ServiceNow, Atlassian, Rippling, Applied Intuition. Intuit's
Workday tenant rejects anonymous API calls. Details in `config/companies.yml`.

Direct-company sources apply a **balanced new-grad title filter** (matches
"new grad" / "university graduate" / "entry level" / "SWE I" / class-year
tokens; rejects senior/staff/intern/PhD/level-II+ and non-software
disciplines — mechanical/electrical/FPGA/etc., which SpaceX-type boards list
as new-grad "engineer" roles) plus a **US-only location filter**.
SimplifyJobs is already new-grad-curated, so only the SWE-category and
location filters apply there.

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

- **Apple / Meta / Google bespoke adapters** — their career sites need
  CSRF/GraphQL tokens or client-side RPC (Google embeds no job JSON in the
  page at all, verified 2026-07-21). Covered by `simplify` meanwhile. An
  Apify-actor-backed adapter is a drop-in fallback if faster coverage is ever
  worth paying for. (Microsoft graduated from this list 2026-07-23 — their
  Eightfold-PCSX search API turned out to accept anonymous GETs.)
- **LinkedIn/Indeed** — intentionally excluded; both actively fight scrapers.
