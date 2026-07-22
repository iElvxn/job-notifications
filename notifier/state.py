"""JSON-backed store of notified job UIDs and seeded sources.

data/seen.json:
    {"seeded_sources": ["simplify", ...], "seen": {"<uid>": "<first-seen date>"}}

Committed back to the repo after each Actions run so state persists between
runs, with human-readable diffs (unlike the old SQLite blob). Sources are
tracked explicitly (not inferred from seen uids) so a source whose first run
returns zero matches still counts as seeded — its first real posting must
notify, not silently seed.
"""

import json
from datetime import date
from pathlib import Path

STATE_PATH = Path(__file__).resolve().parent.parent / "data" / "seen.json"


def load_state(path: Path = STATE_PATH) -> dict:
    if not path.exists():
        return {"seeded_sources": [], "seen": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def save_state(state: dict, path: Path = STATE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = {
        "seeded_sources": sorted(set(state["seeded_sources"])),
        "seen": dict(sorted(state["seen"].items())),
    }
    path.write_text(json.dumps(normalized, indent=1) + "\n", encoding="utf-8")


def today() -> str:
    return date.today().isoformat()
