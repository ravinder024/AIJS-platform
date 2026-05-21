from ranking import compute_feedback_bias, score_job, score_job_explained


def test_score_job_prefers_feedback_and_keywords():
    profile = {
        "role_query": "product manager",
        "location": "remote",
        "include_keywords": ["b2b", "ai"],
        "exclude_keywords": ["intern"],
        "include_companies": ["Acme"],
        "exclude_companies": [],
    }
    feedback_rows = [
        {"vote": "like", "reason_tags": ["ai"], "company_name": "Acme"},
        {"vote": "dislike", "reason_tags": ["intern"], "company_name": "BadCorp"},
    ]
    bias = compute_feedback_bias(feedback_rows)

    strong_job = {
        "source": "linkedin_jobs",
        "title": "Senior Product Manager - AI",
        "company_name": "Acme",
        "description": "B2B platform and AI workflows",
        "location": "Remote",
    }
    weak_job = {
        "source": "naukri",
        "title": "Intern Product Assistant",
        "company_name": "BadCorp",
        "description": "Intern role",
        "location": "Onsite",
    }

    assert score_job(strong_job, profile, bias) > score_job(weak_job, profile, bias)


def test_score_job_explained_returns_signals():
    profile = {"role_query": "software engineer", "location": "remote"}
    bias = compute_feedback_bias([])
    score, explanation = score_job_explained(
        {
            "source": "remoteok",
            "title": "Software Engineer",
            "company_name": "Example",
            "description": "Remote backend role",
            "location": "Remote",
        },
        profile,
        bias,
    )
    assert isinstance(score, float)
    assert explanation.get("final_score") == score
    assert isinstance(explanation.get("signals"), list)
