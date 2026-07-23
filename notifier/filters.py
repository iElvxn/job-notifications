"""Title and location filters ("balanced" strictness, US-only).

Direct-company sources use is_new_grad_title (a new-grad token is required —
their boards list all seniority levels). The SimplifyJobs source uses the
looser is_swe_title (no new-grad token required, since that repo is already
new-grad-curated, but the exclusions still apply: their bot tags plenty of
senior/support/research-assistant roles category=Software).
"""

import re

from notifier.models import Job

# --- Title: new-grad signals -------------------------------------------------

_INCLUDE = re.compile(
    r"""
    new[ -]?grad
    | university\ grad
    | college\ grad
    | early[ -]career
    | early[ -]in[ -]career
    | entry[ -]level
    | \bjunior\b
    | campus
    | \bgraduate\b
    | (software\ )?engineer\ (i|1)\b
    | \bswe\ (i|1)\b
    | \b20(2[6-9])\b          # class-year tokens: 2026-2029
    """,
    re.IGNORECASE | re.VERBOSE,
)

_EXCLUDE = re.compile(
    r"""
    \bsenior\b | \bstaff\b | \bprincipal\b | \bsr\.?\b | \blead\b
    | \bmanager\b | \bdirector\b | \bhead\b | \bvp\b
    | \bintern(ship)?\b | \bco[ -]?op\b
    | \bph\.?d\b | \bmba\b
    | \b(ii|iii|iv|v|vi)\b     # roman-numeral levels II and up
    | \bexperienced\b
    # Non-software engineering disciplines (SpaceX/Anduril/quant boards list
    # mechanical/electrical/FPGA new-grad roles that pass the loose
    # "engineer" gate). Titles like "Flight Software Engineer" are unaffected.
    | \bmechanical\b | \belectrical\b | \bpropulsion\b | \bstructural\b
    | \bcivil\b | \bthermal\b | \bmaterials\b | \bmanufacturing\b
    | \bindustrial\b | \bmechatronics\b | \bhardware\b | \bfpga\b
    | \basic\b | \bsilicon\b | \brf\b
    # Non-engineering functions whose titles still contain "engineering"
    # (e.g. "Early Career Engineering Finance Associate")
    | \bfinance\b | \baccounting\b | \bsales\b | \brecruit
    # Academic and support roles Simplify's bot tags category=Software
    # ("Graduate Research Assistant - Developer", "Application Support
    # Engineer")
    | research\ assistant | post[ -]?doc | professor | \bsupport\b
    """,
    re.IGNORECASE | re.VERBOSE,
)

# Titles must also look like software roles (Greenhouse/Workday boards list
# every department, not just engineering).
_SOFTWARE = re.compile(
    r"software | \bswe\b | developer | \bengineer",
    re.IGNORECASE | re.VERBOSE,
)


def compile_extra(pattern: str | None) -> re.Pattern | None:
    """Compile a per-company extra include pattern from companies.yml
    (e.g. Salesforce titles new-grad roles 'MTS'/'AMTS')."""
    return re.compile(pattern, re.IGNORECASE) if pattern else None


def is_new_grad_title(title: str, extra_include: re.Pattern | None = None) -> bool:
    included = _INCLUDE.search(title) or (
        extra_include is not None and extra_include.search(title)
    )
    return bool(
        included and not _EXCLUDE.search(title) and _SOFTWARE.search(title)
    )


def is_swe_title(title: str) -> bool:
    """Screen for pre-curated new-grad feeds (SimplifyJobs): no new-grad token
    required — bare "Software Engineer" is normal there — but the title must
    look like software and not hit the exclusions."""
    return bool(_SOFTWARE.search(title) and not _EXCLUDE.search(title))


# --- Location: US-only -------------------------------------------------------

_US_HINTS = re.compile(r"united\ states | \busa?\b | u\.s\.", re.IGNORECASE | re.VERBOSE)

_STATE_ABBRS = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID",
    "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS",
    "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK",
    "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV",
    "WI", "WY", "DC",
}

_STATE_NAMES = {
    "alabama", "alaska", "arizona", "arkansas", "california", "colorado",
    "connecticut", "delaware", "florida", "georgia", "hawaii", "idaho",
    "illinois", "indiana", "iowa", "kansas", "kentucky", "louisiana", "maine",
    "maryland", "massachusetts", "michigan", "minnesota", "mississippi",
    "missouri", "montana", "nebraska", "nevada", "new hampshire", "new jersey",
    "new mexico", "new york", "north carolina", "north dakota", "ohio",
    "oklahoma", "oregon", "pennsylvania", "rhode island", "south carolina",
    "south dakota", "tennessee", "texas", "utah", "vermont", "virginia",
    "washington", "west virginia", "wisconsin", "wyoming",
}


# Major US metros that often appear without a state qualifier.
_US_CITIES = {
    "nyc", "new york city", "san francisco", "sf", "seattle", "austin",
    "boston", "chicago", "los angeles", "san jose", "palo alto",
    "mountain view", "sunnyvale", "santa clara", "menlo park", "cupertino",
    "redmond", "bellevue", "denver", "atlanta", "miami", "dallas", "houston",
    "san diego", "irvine", "portland", "pittsburgh", "philadelphia",
    "washington dc", "washington d c", "salt lake city", "raleigh",
    "minneapolis", "nashville", "phoenix", "detroit", "charlotte",
}


def is_us_location(location: str) -> bool:
    if _US_HINTS.search(location):
        return True
    lowered = location.lower().strip()
    if lowered == "remote":  # bare "Remote" with no region — assume US-inclusive
        return True
    for token in re.split(r"[,;/()\-–]", location):
        token = token.strip()
        if (
            token in _STATE_ABBRS
            or token.lower() in _STATE_NAMES
            or token.lower() in _US_CITIES
        ):
            return True
    return False


def job_in_us(job: Job) -> bool:
    """True if any listed location looks US-based; unknown locations pass
    (better an occasional false positive than a missed posting)."""
    if not job.locations:
        return True
    return any(is_us_location(loc) for loc in job.locations)


# --- Cross-source dedup ------------------------------------------------------

_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def dedup_key(job: Job) -> str:
    """Normalized company|title key so the same role arriving from two sources
    (e.g. simplify and a direct adapter) only notifies once. Company collapses
    to its first alphanumeric token ("Amazon.com Services LLC" -> "amazon")."""
    company_tokens = _NON_ALNUM.split(job.company.lower())
    company = next((t for t in company_tokens if t), "")
    title = _NON_ALNUM.sub(" ", job.title.lower()).strip()
    return f"{company}|{title}"
