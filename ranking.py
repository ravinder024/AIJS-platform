from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any


BASE_SOURCE_WEIGHTS = {
    "linkedin_jobs": 1.15,
    "linkedin": 1.1,
    "company_site": 1.05,
    "remoteok": 1.0,
    "indeed": 0.95,
    "naukri": 0.9,
    "wellfound": 0.95,
}


def _contains_any(text: str, values: list[str]) -> bool:
    normalized = text.lower()
    return any(v.lower() in normalized for v in values)


def compute_feedback_bias(feedback_rows: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    """
    Build per-tag and per-company boosts from explicit feedback.
    Positive votes increase relevance, negative votes suppress.
    """
    tag_weight: dict[str, float] = defaultdict(float)
    company_weight: dict[str, float] = defaultdict(float)

    for row in feedback_rows:
        direction = 0.2 if row.get("vote") == "like" else -0.25
        for tag in row.get("reason_tags", []):
            tag_weight[tag.lower()] += direction
        company = (row.get("company_name") or "").strip().lower()
        if company:
            company_weight[company] += direction

    return {"tag_weight": dict(tag_weight), "company_weight": dict(company_weight)}


def score_job_explained(
    job: dict[str, Any],
    profile: dict[str, Any],
    feedback_bias: dict[str, Any],
    source_weight_overrides: dict[str, float] | None = None,
    keyword_weight_overrides: dict[str, float] | None = None,
) -> tuple[float, dict[str, Any]]:
    title = (job.get("title") or "").lower()
    company = (job.get("company_name") or "").lower()
    description = (job.get("description") or "").lower()
    location = (job.get("location") or "").lower()
    blob = " ".join([title, company, description, location])

    explanation: dict[str, Any] = {"signals": []}
    score = 0.0
    source = (job.get("source") or "").lower()
    base_source_weight = BASE_SOURCE_WEIGHTS.get(source, 0.85)
    if source_weight_overrides and source in source_weight_overrides:
        base_source_weight = source_weight_overrides[source]
    score += base_source_weight
    explanation["signals"].append({"type": "source_weight", "value": round(base_source_weight, 4), "source": source})

    include_keywords = profile.get("include_keywords", [])
    exclude_keywords = profile.get("exclude_keywords", [])
    include_companies = profile.get("include_companies", [])
    exclude_companies = profile.get("exclude_companies", [])
    role_query = (profile.get("role_query") or "").lower()
    target_location = (profile.get("location") or "").lower()

    if role_query and role_query in title:
        score += 1.0
        explanation["signals"].append({"type": "role_title_match", "value": 1.0})
    elif role_query and role_query in blob:
        score += 0.6
        explanation["signals"].append({"type": "role_context_match", "value": 0.6})

    if include_keywords:
        include_hits = sum(1 for kw in include_keywords if kw.lower() in blob)
        include_score = min(1.2, 0.25 * include_hits)
        score += include_score
        if include_score:
            explanation["signals"].append({"type": "include_keywords", "value": round(include_score, 4)})

    if exclude_keywords and _contains_any(blob, exclude_keywords):
        score -= 1.2
        explanation["signals"].append({"type": "exclude_keywords_penalty", "value": -1.2})

    if include_companies and company in [c.lower() for c in include_companies]:
        score += 1.1
        explanation["signals"].append({"type": "include_company", "value": 1.1})

    if exclude_companies and company in [c.lower() for c in exclude_companies]:
        score -= 2.0
        explanation["signals"].append({"type": "exclude_company_penalty", "value": -2.0})

    if target_location and (target_location in location or "remote" in location):
        score += 0.5
        explanation["signals"].append({"type": "location_match", "value": 0.5})

    tag_weight = feedback_bias.get("tag_weight", {})
    company_weight = feedback_bias.get("company_weight", {})

    for tag, weight in tag_weight.items():
        if tag in blob:
            score += weight
            explanation["signals"].append({"type": "feedback_tag_bias", "tag": tag, "value": round(weight, 4)})

    company_bias = company_weight.get(company, 0.0)
    if company_bias:
        explanation["signals"].append({"type": "feedback_company_bias", "company": company, "value": round(company_bias, 4)})
    score += company_bias

    if keyword_weight_overrides:
        for keyword, weight in keyword_weight_overrides.items():
            if keyword.lower() in blob:
                score += weight
                explanation["signals"].append(
                    {"type": "learned_keyword_weight", "keyword": keyword, "value": round(weight, 4)}
                )

    # Recency bonus based on collected timestamp if present.
    collected_at = job.get("collected_at")
    if isinstance(collected_at, datetime):
        age_hours = (datetime.utcnow() - collected_at).total_seconds() / 3600
        if age_hours < 24:
            score += 0.5
            explanation["signals"].append({"type": "recency", "value": 0.5})
        elif age_hours < 72:
            score += 0.2
            explanation["signals"].append({"type": "recency", "value": 0.2})

    final_score = round(score, 4)
    explanation["final_score"] = final_score
    return final_score, explanation


def score_job(
    job: dict[str, Any],
    profile: dict[str, Any],
    feedback_bias: dict[str, Any],
    source_weight_overrides: dict[str, float] | None = None,
    keyword_weight_overrides: dict[str, float] | None = None,
) -> float:
    score, _ = score_job_explained(
        job,
        profile,
        feedback_bias,
        source_weight_overrides=source_weight_overrides,
        keyword_weight_overrides=keyword_weight_overrides,
    )
    return score
