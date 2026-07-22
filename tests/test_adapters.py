"""Parse tests for each adapter's pure _to_jobs function, using minimal
fixtures mirroring the real response shapes (verified live 2026-07-21)."""

from notifier.sources import amazon, ashby, eightfold, greenhouse, lever, simplify, workday


def test_greenhouse_parse():
    payload = {
        "jobs": [
            {
                "id": 123,
                "title": "Software Engineer, New Grad",
                "absolute_url": "https://boards.greenhouse.io/stripe/jobs/123",
                "location": {"name": "San Francisco, CA"},
                "updated_at": "2026-07-20T10:00:00-04:00",
            },
            {  # non-US -> dropped
                "id": 124,
                "title": "Software Engineer, New Grad",
                "absolute_url": "https://boards.greenhouse.io/stripe/jobs/124",
                "location": {"name": "London, UK"},
                "updated_at": "2026-07-20T10:00:00-04:00",
            },
            {  # senior -> dropped
                "id": 125,
                "title": "Senior Software Engineer",
                "absolute_url": "https://boards.greenhouse.io/stripe/jobs/125",
                "location": {"name": "San Francisco, CA"},
                "updated_at": "2026-07-20T10:00:00-04:00",
            },
        ]
    }
    jobs = greenhouse._to_jobs(payload, "greenhouse/stripe", "Stripe")
    assert [j.native_id for j in jobs] == ["123"]
    assert jobs[0].uid == "greenhouse/stripe:123"
    assert jobs[0].posted_at == "2026-07-20"


def test_ashby_parse():
    payload = {
        "jobs": [
            {
                "id": "uuid-1",
                "title": "Software Engineer, New Grad",
                "jobUrl": "https://jobs.ashbyhq.com/openai/uuid-1",
                "location": "San Francisco",
                "secondaryLocations": [{"location": "New York, NY"}],
                "isListed": True,
                "isRemote": False,
                "publishedAt": "2026-07-19T00:00:00Z",
            },
            {  # unlisted -> dropped
                "id": "uuid-2",
                "title": "Software Engineer, New Grad",
                "jobUrl": "u",
                "location": "San Francisco, CA",
                "isListed": False,
            },
        ]
    }
    jobs = ashby._to_jobs(payload, "ashby/openai", "OpenAI")
    assert [j.native_id for j in jobs] == ["uuid-1"]
    assert jobs[0].locations == ["San Francisco", "New York, NY"]


def test_lever_parse():
    payload = [
        {
            "id": "abc",
            "text": "New Grad Software Engineer",
            "hostedUrl": "https://jobs.lever.co/x/abc",
            "categories": {"location": "Austin, TX"},
            "createdAt": 1752969600000,
        }
    ]
    jobs = lever._to_jobs(payload, "lever/x", "X")
    assert jobs[0].uid == "lever/x:abc"
    assert jobs[0].posted_at == "2025-07-20"


def test_workday_parse():
    payload = {
        "jobPostings": [
            {
                "title": "Software Engineer - New College Grad",
                "externalPath": "/job/US-CA-Santa-Clara/SWE_JR123",
                "locationsText": "US, CA, Santa Clara",
                "postedOn": "Posted Today",
                "bulletFields": ["JR123"],
            },
            {  # hardware role without software keyword -> dropped
                "title": "ASIC Design - New College Grad",
                "externalPath": "/job/x/ASIC_JR124",
                "locationsText": "US, CA, Santa Clara",
                "bulletFields": ["JR124"],
            },
            {  # multi-location placeholder -> treated as unknown, kept
                "title": "Software Engineer - New Grad",
                "externalPath": "/job/x/SWE_JR125",
                "locationsText": "3 Locations",
                "bulletFields": ["JR125"],
            },
        ]
    }
    jobs = workday._to_jobs(
        payload, "workday/nvidia", "NVIDIA",
        "nvidia.wd5.myworkdayjobs.com", "NVIDIAExternalCareerSite",
    )
    assert [j.native_id for j in jobs] == ["JR123", "JR125"]
    assert jobs[1].locations == []
    assert jobs[0].url == (
        "https://nvidia.wd5.myworkdayjobs.com/en-US/NVIDIAExternalCareerSite"
        "/job/US-CA-Santa-Clara/SWE_JR123"
    )


def test_eightfold_parse():
    payload = {
        "positions": [
            {
                "id": 790298,
                "name": "Software Engineer 1 - Streaming",
                "location": "Los Gatos, CA",
                "locations": ["Los Gatos, CA", "Remote - US"],
                "canonicalPositionUrl": "https://explore.jobs.netflix.net/careers/job/790298",
                "t_create": 1752969600,
            }
        ]
    }
    jobs = eightfold._to_jobs(payload, "eightfold/netflix.com", "Netflix")
    assert jobs[0].native_id == "790298"
    assert jobs[0].locations == ["Los Gatos, CA", "Remote - US"]


def test_amazon_parse():
    payload = {
        "jobs": [
            {
                "id_icims": "111",
                "title": "Software Development Engineer",  # flag-only new grad
                "university_job": True,
                "is_intern": False,
                "is_manager": False,
                "job_path": "/en/jobs/111/sde",
                "normalized_location": "Seattle, Washington, USA",
                "posted_date": "July 20, 2026",
            },
            {  # intern -> dropped despite university flag
                "id_icims": "112",
                "title": "SDE Intern",
                "university_job": True,
                "is_intern": True,
                "job_path": "/en/jobs/112/x",
            },
            {  # experienced role, no flag -> dropped
                "id_icims": "113",
                "title": "Software Development Engineer",
                "university_job": False,
                "job_path": "/en/jobs/113/x",
            },
        ]
    }
    jobs = amazon._to_jobs(payload)
    assert [j.native_id for j in jobs] == ["111"]
    assert jobs[0].url == "https://www.amazon.jobs/en/jobs/111/sde"


def test_simplify_parse():
    payload = [
        {  # legacy category value -> kept
            "id": "s1",
            "active": True,
            "is_visible": True,
            "category": "Software Engineering",
            "company_name": "Meta",
            "title": "Software Engineer, University Grad",
            "url": "https://example.com/1",
            "locations": ["Menlo Park, CA"],
        },
        {  # current main category -> kept
            "id": "s2",
            "active": True,
            "is_visible": True,
            "category": "Software",
            "company_name": "Google",
            "title": "Software Engineer, New Grad",
            "url": "https://example.com/2",
            "locations": ["Mountain View, CA"],
        },
        {  # AI/ML/Data included in full -> kept
            "id": "s3",
            "active": True,
            "is_visible": True,
            "category": "AI/ML/Data",
            "company_name": "OpenAI",
            "title": "Machine Learning Engineer, New Grad",
            "url": "https://example.com/3",
            "locations": ["San Francisco, CA"],
        },
        {  # Quant included in full -> kept
            "id": "s4",
            "active": True,
            "is_visible": True,
            "category": "Quant",
            "company_name": "HRT",
            "title": "Quantitative Researcher, New Grad",
            "url": "https://example.com/4",
            "locations": ["NYC"],
        },
        {  # Hardware -> dropped
            "id": "s7",
            "active": True,
            "is_visible": True,
            "category": "Hardware",
            "company_name": "X",
            "title": "ASIC Design Engineer, New Grad",
            "url": "u",
            "locations": ["NYC"],
        },
        {  # inactive -> dropped
            "id": "s5",
            "active": False,
            "is_visible": True,
            "category": "Software",
            "company_name": "X",
            "title": "T",
            "url": "u",
            "locations": ["NYC"],
        },
        {  # unrelated category -> dropped
            "id": "s6",
            "active": True,
            "is_visible": True,
            "category": "Product",
            "company_name": "X",
            "title": "Product Manager, New Grad",
            "url": "u",
            "locations": ["NYC"],
        },
    ]
    jobs = simplify._to_jobs(payload)
    assert [j.native_id for j in jobs] == ["s1", "s2", "s3", "s4"]
    assert jobs[0].source == "simplify"
