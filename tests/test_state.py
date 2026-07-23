import json
from datetime import datetime, timedelta

from notifier.state import (
    load_state,
    notified_date,
    notified_family,
    notified_value,
    save_state,
    tier2_due,
    today,
)


def test_missing_file_returns_empty_state(tmp_path):
    state = load_state(tmp_path / "nope.json")
    assert state == {
        "seeded_sources": [],
        "seen": {},
        "notified_keys": {},
        "last_tier2_at": None,
    }


def test_old_state_file_gains_new_fields(tmp_path):
    path = tmp_path / "seen.json"
    path.write_text(json.dumps({"seeded_sources": ["a"], "seen": {"a:1": "2026-07-20"}}))
    state = load_state(path)
    assert state["notified_keys"] == {}
    assert state["last_tier2_at"] is None


def test_round_trip_sorts_dedupes_and_prunes(tmp_path):
    path = tmp_path / "seen.json"
    save_state(
        {
            "seeded_sources": ["b", "a", "b"],
            "seen": {"b:2": "2026-07-21", "a:1": "2026-07-20"},
            "notified_keys": {"acme|swe": notified_value("greenhouse"),
                              "old|swe": "2020-01-01"},
            "last_tier2_at": "2026-07-22T00:00:00-04:00",
        },
        path,
    )
    state = load_state(path)
    assert state["seeded_sources"] == ["a", "b"]
    assert list(state["seen"]) == ["a:1", "b:2"]
    assert "acme|swe" in state["notified_keys"]
    assert "old|swe" not in state["notified_keys"]  # pruned (>7 days)
    assert state["last_tier2_at"] == "2026-07-22T00:00:00-04:00"


def test_notified_value_round_trip_and_legacy():
    value = notified_value("microsoft")
    assert notified_date(value) == today()
    assert notified_family(value) == "microsoft"
    # Legacy bare-date values (pre-source-tracking) have no family.
    assert notified_date("2026-07-22") == "2026-07-22"
    assert notified_family("2026-07-22") is None


def test_tier2_due():
    now = datetime.now().astimezone()
    assert tier2_due({"last_tier2_at": None})  # never polled -> due
    assert tier2_due({})  # missing field -> due
    recent = (now - timedelta(minutes=10)).isoformat(timespec="seconds")
    assert not tier2_due({"last_tier2_at": recent})
    stale = (now - timedelta(minutes=26)).isoformat(timespec="seconds")
    assert tier2_due({"last_tier2_at": stale})
