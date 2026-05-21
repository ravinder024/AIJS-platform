"""
Enhanced job scraper with anti-bot evasion and ScrapeGraphAI fallback.
Wraps existing scrapers and adds resilience layer.
"""

import logging
from typing import Any, Optional
from anti_bot_evasion import UserAgentRotator, RequestDelay, request_delay, source_health
import job_scrapers

logger = logging.getLogger(__name__)


def scrape_with_anti_bot(
    scraper_func: callable,
    source_name: str,
    keyword: str,
    location: str,
    days: int = 7,
    job_setting: Optional[str] = None,
    exclude_keywords: list = None,
    company_size: Optional[str] = None,
) -> list[dict[str, Any]]:
    """
    Scrape jobs with anti-bot protection and retry logic.

    Args:
        scraper_func: The scraper function to wrap
        source_name: Name of the source (for tracking and delays)
        keyword: Job search keyword
        location: Job location
        days: Posted within days
        job_setting: Remote/hybrid/onsite preference
        exclude_keywords: Keywords to exclude
        company_size: Company size filter

    Returns:
        List of job dictionaries
    """
    if exclude_keywords is None:
        exclude_keywords = []

    # Add anti-bot delay before scraping
    request_delay.wait(source_name)

    try:
        logger.info(f"[Enhanced Scraper] Starting {source_name} scraper with anti-bot protection")
        
        # Call original scraper
        jobs = scraper_func(
            keyword=keyword,
            location=location,
            days=days,
            job_setting=job_setting,
            exclude_keywords=exclude_keywords,
            company_size=company_size,
        )

        # Record success
        source_health.record_success(source_name, len(jobs))
        logger.info(f"[Enhanced Scraper] {source_name}: Found {len(jobs)} jobs")
        
        return jobs

    except Exception as e:
        # Check if it's a blocking error
        is_blocked = "403" in str(e) or "blocked" in str(e).lower()
        source_health.record_failure(source_name, is_blocked=is_blocked)
        logger.error(f"[Enhanced Scraper] {source_name} error: {e}")
        
        if is_blocked:
            logger.warning(f"[Enhanced Scraper] {source_name} appears to be blocking. Will try fallback.")
        
        return []


def scrape_all_sources_with_health_check(
    keyword: str,
    location: str,
    days: int = 7,
    job_setting: Optional[str] = None,
    exclude_keywords: list = None,
    company_size: Optional[str] = None,
) -> list[dict[str, Any]]:
    """
    Scrape from all sources with health checks and smart selection.

    Args:
        keyword: Job search keyword
        location: Job location
        days: Posted within days
        job_setting: Remote/hybrid/onsite preference
        exclude_keywords: Keywords to exclude
        company_size: Company size filter

    Returns:
        Combined list of jobs from all sources
    """
    if exclude_keywords is None:
        exclude_keywords = []

    sources = {
        "remoteok": job_scrapers.scrape_remoteok,
        "indeed": job_scrapers.scrape_indeed,
        "naukri": job_scrapers.scrape_naukri,
        "wellfound": job_scrapers.scrape_wellfound,
        "linkedin": job_scrapers.scrape_linkedin,
    }

    all_jobs = []

    for source_name, scraper_func in sources.items():
        # Check source health
        if not source_health.should_scrape(source_name):
            logger.warning(f"[Health Check] Skipping {source_name} due to high block rate")
            continue

        # Scrape with anti-bot
        try:
            jobs = scrape_with_anti_bot(
                scraper_func,
                source_name,
                keyword,
                location,
                days,
                job_setting,
                exclude_keywords,
                company_size,
            )
            all_jobs.extend(jobs)
        except Exception as e:
            logger.error(f"[Scraper] Unexpected error from {source_name}: {e}")
            continue

    # Print health summary
    source_health.print_summary()

    return all_jobs


def scrape_with_fallback(
    keyword: str,
    location: str,
    days: int = 7,
    job_setting: Optional[str] = None,
    exclude_keywords: list = None,
    company_size: Optional[str] = None,
    use_scrapegraph: bool = False,
) -> list[dict[str, Any]]:
    """
    Scrape jobs with fallback to ScrapeGraphAI if primary sources fail.

    Args:
        keyword: Job search keyword
        location: Job location
        days: Posted within days
        job_setting: Remote/hybrid/onsite preference
        exclude_keywords: Keywords to exclude
        company_size: Company size filter
        use_scrapegraph: Whether to use ScrapeGraphAI as primary (experimental)

    Returns:
        List of job dictionaries
    """
    if exclude_keywords is None:
        exclude_keywords = []

    jobs = scrape_all_sources_with_health_check(
        keyword,
        location,
        days,
        job_setting,
        exclude_keywords,
        company_size,
    )

    # If we got decent results, return them
    if len(jobs) >= 5:
        logger.info(f"[Fallback] Got {len(jobs)} jobs from standard sources")
        return jobs

    # Try ScrapeGraphAI fallback if enabled and low results
    if use_scrapegraph and len(jobs) < 5:
        logger.info("[Fallback] Trying ScrapeGraphAI for additional jobs...")
        try:
            from scrapegraph_wrapper import ScrapeGraphAIWrapper
            
            wrapper = ScrapeGraphAIWrapper()
            
            # Use ScrapeGraphAI to search for jobs (LinkedIn Jobs is a common target)
            job_urls = [
                f"https://www.linkedin.com/jobs/search/?keywords={keyword.replace(' ', '%20')}&location={location.replace(' ', '%20')}",
            ]
            
            sg_jobs = wrapper.scrape_multiple_jobs(job_urls)
            logger.info(f"[ScrapeGraphAI] Found {len(sg_jobs)} additional jobs")
            jobs.extend(sg_jobs)

        except Exception as e:
            logger.warning(f"[ScrapeGraphAI] Fallback failed: {e}")

    return jobs


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Test
    print("Testing enhanced scrapers...")
    jobs = scrape_all_sources_with_health_check(
        keyword="Product Manager",
        location="Remote",
        days=7,
    )
    print(f"Found {len(jobs)} jobs total")
    for job in jobs[:3]:
        print(f"  - {job.get('title')} @ {job.get('company_name')}")
