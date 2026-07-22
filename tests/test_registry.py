"""Registry parses the real companies.yml with tier support."""

from notifier.sources import build_sources


def test_build_sources_tiers():
    sources = build_sources()
    by_name = {s.name: s for s in sources}

    # Bespoke sources are always tier 1
    assert by_name["simplify"].tier == 1
    assert by_name["amazon"].tier == 1

    # Config-driven tier assignments
    assert by_name["greenhouse/stripe"].tier == 1  # default
    assert by_name["greenhouse/figma"].tier == 1  # promoted
    assert by_name["greenhouse/robinhood"].tier == 2
    assert by_name["workday/adobe"].tier == 2
    assert by_name["eightfold/snowflake.com"].tier == 2

    # No duplicate source names, and the roster is wide
    assert len(by_name) == len(sources)
    assert len(sources) >= 40
    assert sum(1 for s in sources if s.tier == 1) >= 15