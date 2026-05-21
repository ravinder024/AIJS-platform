from collectors import compute_fingerprint, normalize_job


def test_normalize_job_builds_stable_fingerprint():
    raw = {
        "title": "Software Engineer",
        "company_name": "Example Inc",
        "location": "Remote",
        "source_url": "https://example.com/jobs/1",
    }
    first = normalize_job(raw, "company_site")
    second = normalize_job(raw, "company_site")

    assert first["fingerprint"] == second["fingerprint"]
    assert first["source"] == "company_site"
    assert len(compute_fingerprint(first)) == 64

