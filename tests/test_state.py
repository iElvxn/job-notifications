from notifier.state import load_state, save_state


def test_missing_file_returns_empty_state(tmp_path):
    state = load_state(tmp_path / "nope.json")
    assert state == {"seeded_sources": [], "seen": {}}


def test_round_trip_sorts_and_dedupes(tmp_path):
    path = tmp_path / "seen.json"
    save_state(
        {
            "seeded_sources": ["b", "a", "b"],
            "seen": {"b:2": "2026-07-21", "a:1": "2026-07-20"},
        },
        path,
    )
    state = load_state(path)
    assert state["seeded_sources"] == ["a", "b"]
    assert list(state["seen"]) == ["a:1", "b:2"]
    assert state["seen"]["a:1"] == "2026-07-20"
