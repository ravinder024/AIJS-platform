from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any, Callable

from job_scrapers import scrape_indeed, scrape_naukri, scrape_remoteok, scrape_wellfound
from enhanced_scrapers import scrape_with_anti_bot
from playwright_collectors import (
    scrape_company_careers_playwright,
    scrape_linkedin_jobs_playwright,
)


def compute_fingerprint(job: dict[str, Any]) -> str:
    raw = "|".join(
        [
            (job.get("title") or "").strip().lower(),
            (job.get("company_name") or "").strip().lower(),
            (job.get("location") or "").strip().lower(),
            (job.get("source_url") or "").strip().lower(),
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:64]


def normalize_job(raw: dict[str, Any], source: str) -> dict[str, Any]:
    normalized = {
        "source": source,
        "source_url": raw.get("source_url", ""),
        "title": raw.get("title", ""),
        "company_name": raw.get("company_name", ""),
        "location": raw.get("location", ""),
        "description": raw.get("description", ""),
        "salary_min": raw.get("salary_min"),
        "salary_max": raw.get("salary_max"),
        "remote_type": raw.get("remote_type", ""),
        "employment_type": raw.get("employment_type", ""),
        "source_confidence": raw.get("source_confidence", 0.75),
        "posted_at": raw.get("posted_at") or raw.get("date") or raw.get("published_at"),
        "collected_at": datetime.utcnow(),
        "raw_payload": raw,
    }
    normalized["fingerprint"] = compute_fingerprint(normalized)
    return normalized


def collect_from_source(source: str, profile: dict[str, Any]) -> list[dict[str, Any]]:
    keyword = profile.get("role_query", "")
    location = profile.get("location", "Remote")
    exclude_keywords = profile.get("exclude_keywords", [])
    posted_within_hours = profile.get("posted_within_hours")
    days = 7
    try:
        if posted_within_hours is not None:
            days = max(1, min(30, int((float(posted_within_hours) + 23.999) // 24)))
    except (TypeError, ValueError):
        days = 7

    static_map: dict[str, Callable[..., list[dict[str, Any]]]] = {
        "remoteok": scrape_remoteok,
        "indeed": scrape_indeed,
        "naukri": scrape_naukri,
        "wellfound": scrape_wellfound,
    }

    if source == "linkedin_jobs":
        raw_jobs = scrape_linkedin_jobs_playwright(keyword=keyword, location=location, days=days)
        return [normalize_job(job, source) for job in raw_jobs]

    if source.startswith("company_site:"):
        company_site_url = source.split(":", 1)[1]
        raw_jobs = scrape_company_careers_playwright(
            base_url=company_site_url,
            role_query=keyword,
            location=location,
        )
        return [normalize_job(job, "company_site") for job in raw_jobs]

    scraper = static_map.get(source)
    if not scraper:
        return []

    # Use enhanced scraper with anti-bot protection
    raw_jobs = scrape_with_anti_bot(
        scraper_func=scraper,
        source_name=source,
        keyword=keyword,
        location=location,
        days=days,
        exclude_keywords=exclude_keywords,
    )
    return [normalize_job(job, source) for job in raw_jobs]
