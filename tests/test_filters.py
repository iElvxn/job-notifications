from notifier.filters import is_new_grad_title, is_us_location, job_in_us
from notifier.models import Job

# --- title filter ------------------------------------------------------------

NEW_GRAD_TITLES = [
    "Software Engineer, New Grad",
    "New Graduate Software Engineer",
    "Software Engineer I",
    "Software Engineer 1",
    "Software Development Engineer - 2026 (Grad)",
    "University Graduate - Software Engineer",
    "Early Career Software Engineer",
    "Entry-Level Software Developer",
    "Campus Hire - Backend Engineer",
    "SWE I, Infrastructure",
    "Junior Software Engineer",
]

REJECTED_TITLES = [
    "Senior Software Engineer",
    "Staff Software Engineer, New Products",  # staff outranks the weak signal
    "Software Engineer II",
    "Software Engineer III, Google Cloud",
    "Engineering Manager, Early Career Programs",
    "Software Engineering Intern (2026)",
    "New Grad PhD Software Engineer",  # PhD excluded by choice
    "Principal Engineer",
    "Sr. Software Engineer",
    "Account Executive, New Grad",  # not a software role
    "Machine Learning Co-op 2026",
    "Director of Engineering",
    "Experienced Software Engineer",
]


def test_accepts_new_grad_titles():
    for title in NEW_GRAD_TITLES:
        assert is_new_grad_title(title), title


def test_rejects_non_new_grad_titles():
    for title in REJECTED_TITLES:
        assert not is_new_grad_title(title), title


def test_extra_include_pattern():
    from notifier.filters import compile_extra

    mts = compile_extra(r"\ba?mts\b")  # Salesforce's new-grad level naming
    assert is_new_grad_title("Software Engineering MTS", mts)
    assert is_new_grad_title("Software Engineering AMTS", mts)
    assert not is_new_grad_title("Software Engineering SMTS", mts)  # senior
    assert not is_new_grad_title("Software Engineering LMTS", mts)  # lead
    assert not is_new_grad_title("Software Engineering MTS")  # without extra


# --- location filter ---------------------------------------------------------

US_LOCATIONS = [
    "San Francisco, CA",
    "New York, NY, USA",
    "United States",
    "Seattle, Washington",
    "Remote - US",
    "US, CA, Santa Clara",  # Workday's locationsText format
    "Remote",  # bare remote assumed US-inclusive
    "Austin, Texas, United States of America",
]

NON_US_LOCATIONS = [
    "London, UK",
    "Toronto, Ontario, Canada",
    "Bengaluru, India",
    "Remote - Europe",
    "Dublin, Ireland",
    "Singapore",
]


def test_accepts_us_locations():
    for loc in US_LOCATIONS:
        assert is_us_location(loc), loc


def test_rejects_non_us_locations():
    for loc in NON_US_LOCATIONS:
        assert not is_us_location(loc), loc


def _job(locations):
    return Job(
        source="test", native_id="1", company="X", title="T", url="u",
        locations=locations,
    )


def test_job_in_us_any_location_matches():
    assert job_in_us(_job(["London, UK", "San Francisco, CA"]))
    assert not job_in_us(_job(["London, UK"]))


def test_job_with_unknown_locations_passes():
    assert job_in_us(_job([]))


# --- cross-source dedup key --------------------------------------------------


def test_dedup_key_normalizes_company_and_title():
    from notifier.filters import dedup_key

    a = Job(source="amazon", native_id="1", company="Amazon.com Services LLC",
            title="Software Dev Engineer I - AWS", url="u")
    b = Job(source="simplify", native_id="x", company="Amazon",
            title="Software Dev Engineer I – AWS", url="u2")
    assert dedup_key(a) == dedup_key(b) == "amazon|software dev engineer i aws"

    c = Job(source="simplify", native_id="y", company="Amazon",
            title="Software Dev Engineer I - Alexa", url="u3")
    assert dedup_key(c) != dedup_key(a)
