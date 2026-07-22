"""JSON-backed store of notified job UIDs, seeded sources, and dedup keys.

data/seen.json:
    {
      "seeded_sources": ["simplify", ...],
      "seen": {"<uid>": "<first-seen date>"},
      "notified_keys": {"<company|title dedup key>": "<date>"},
      "last_tier2_at": "<ISO datetime of last tier-2 poll>"
    }

Committed back to the repo after each Actions run so state persists between
runs, with human-readable diffs (unlike the old SQLite blob). Sources are
tracked explicitly (not inferred from seen uids) so a source whose first run
returns zero matches still counts as seeded — its first real posting must
notify, not silently seed.
"""

import json
from datetime import date, datetime, timedelta
from pathlib import Path

STATE_PATH = Path(__file__).resolve().parent.parent / "data" / "seen.json"

NOTIFIED_KEY_RETENTION_DAYS = 90


def load_state(path: Path = STATE_PATH) -> dict:
    if not path.exists():
        state = {}
    else:
        state = json.loads(path.read_text(encoding="utf-8"))
    # Default any fields added after the state file was first created.
    state.setdefault("seeded_sources", [])
    state.setdefault("seen", {})
    state.setdefault("notified_keys", {})
    state.setdefault("last_tier2_at", None)
    return state


def save_state(state: dict, path: Path = STATE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cutoff = (date.today() - timedelta(days=NOTIFIED_KEY_RETENTION_DAYS)).isoformat()
    normalized = {
        "seeded_sources": sorted(set(state["seeded_sources"])),
        "seen": dict(sorted(state["seen"].items())),
        "notified_keys": {
            key: seen_date
            for key, seen_date in sorted(state["notified_keys"].items())
            if seen_date >= cutoff
        },
        "last_tier2_at": state.get("last_tier2_at"),
    }
    path.write_text(json.dumps(normalized, indent=1) + "\n", encoding="utf-8")


def today() -> str:
    return date.today().isoformat()


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def tier2_due(state: dict, min_gap_minutes: int = 25) -> bool:
    """True when tier-2 sources should be polled this run. Uses elapsed time
    since the last tier-2 poll (not wall-clock minutes) because Actions cron
    fires late routinely. 25-minute gap approximates every-other 15-min run."""
    last = state.get("last_tier2_at")
    if not last:
        return True
    elapsed = datetime.now().astimezone() - datetime.fromisoformat(last)
    return elapsed >= timedelta(minutes=min_gap_minutes)
