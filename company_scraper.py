"""
Company and contact enrichment scrapers.
Extracts company information and decision-maker contacts from various sources.
"""

import logging
from typing import Any, Optional
from anti_bot_evasion import UserAgentRotator, RequestDelay, request_delay, source_health
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)
request_delay = RequestDelay()


def scrape_company_careers_page(company_name: str, domain: str) -> dict[str, Any]:
    """
    Scrape company careers page for basic information.

    Args:
        company_name: Company name
        domain: Company domain (e.g., "microsoft.com")

    Returns:
        Dictionary with company information
    """
    urls_to_try = [
        f"https://{domain}/careers",
        f"https://{domain}/jobs",
        f"https://{domain}/company/careers",
        f"https://{domain}/work-with-us",
    ]

    request_delay.wait("company_scraper")

    for url in urls_to_try:
        try:
            response = requests.get(
                url,
                headers=UserAgentRotator.get_headers(),
                timeout=10,
            )

            if response.status_code == 200:
                soup = BeautifulSoup(response.content, "html.parser")
                
                # Extract basic info
                company_info = {
                    "name": company_name,
                    "domain": domain,
                    "careers_page": url,
                    "hiring_signals": {
                        "has_careers_page": True,
                        "open_jobs_mentioned": _extract_job_count(soup),
                    },
                    "raw_content_preview": response.text[:500],
                }
                
                source_health.record_success("company_scraper", 1)
                logger.info(f"[Company Scraper] Found careers page for {company_name} at {url}")
                return company_info

        except requests.RequestException as e:
            logger.debug(f"[Company Scraper] Failed to fetch {url}: {e}")
            continue

    source_health.record_failure("company_scraper")
    logger.warning(f"[Company Scraper] Could not find careers page for {company_name}")
    return {"name": company_name, "domain": domain, "error": "Careers page not found"}


def _extract_job_count(soup: BeautifulSoup) -> int:
    """Extract job count from page content."""
    text = soup.get_text().lower()
    
    # Look for patterns like "12 open positions" or "open jobs (5)"
    import re
    patterns = [
        r"(\d+)\s+(?:open\s+)?(?:job|position)s?",
        r"(?:job|position)s?.*?(\d+)",
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text)
        if matches:
            try:
                return int(matches[0])
            except (ValueError, IndexError):
                continue
    
    return 0


def scrape_linkedin_company_page(company_name: str, linkedin_url: Optional[str] = None) -> dict[str, Any]:
    """
    Scrape company information from LinkedIn.

    Args:
        company_name: Company name
        linkedin_url: LinkedIn company URL (optional)

    Returns:
        Dictionary with company information
    """
    if not linkedin_url:
        # Build URL from company name
        linkedin_url = f"https://www.linkedin.com/company/{company_name.lower().replace(' ', '-')}/"

    request_delay.wait("linkedin_company")

    try:
        response = requests.get(
            linkedin_url,
            headers=UserAgentRotator.get_headers(),
            timeout=10,
        )

        if response.status_code == 200:
            soup = BeautifulSoup(response.content, "html.parser")
            
            company_info = {
                "name": company_name,
                "linkedin_url": linkedin_url,
                "hiring_signals": {
                    "linkedin_page_found": True,
                },
            }
            
            source_health.record_success("linkedin_company", 1)
            logger.info(f"[LinkedIn Company] Successfully scraped {company_name}")
            return company_info
        else:
            logger.debug(f"[LinkedIn Company] Got status {response.status_code} for {linkedin_url}")
            source_health.record_failure("linkedin_company", is_blocked=(response.status_code == 403))

    except requests.RequestException as e:
        logger.error(f"[LinkedIn Company] Error: {e}")
        source_health.record_failure("linkedin_company")

    return {"name": company_name, "error": "LinkedIn page not accessible"}


def generate_sample_company_data(company_name: str, domain: str) -> dict[str, Any]:
    """
    Generate sample company data for testing/fallback.

    Args:
        company_name: Company name
        domain: Company domain

    Returns:
        Sample company data
    """
    industries = ["Technology", "SaaS", "FinTech", "Enterprise Software", "B2B"]
    funding_stages = ["series_a", "series_b", "series_c", "public"]
    
    import random
    
    return {
        "id": None,
        "name": company_name,
        "domain": domain,
        "industry": random.choice(industries),
        "employee_count": random.choice([50, 100, 250, 500, 1000, 5000]),
        "funding_stage": random.choice(funding_stages),
        "funding_amount": random.randint(1000000, 100000000),
        "remote_policy": random.choice(["remote", "hybrid", "onsite"]),
        "hiring_signals": {
            "has_careers_page": True,
            "open_jobs_mentioned": random.randint(5, 50),
            "source": "sample",
        },
        "ai_analysis": {
            "description": f"Sample data for {company_name}",
            "relevance_score": 0.6,
        },
        "opportunity_score": random.uniform(50, 90),
    }


def generate_sample_contacts(company_name: str) -> list[dict[str, Any]]:
    """
    Generate sample contact data for testing/fallback.

    Args:
        company_name: Company name

    Returns:
        List of sample contacts
    """
    titles = ["Chief Product Officer", "VP Product", "Senior Product Manager", "Hiring Manager"]
    seniorities = ["c_level", "vp", "director", "manager"]
    first_names = ["John", "Jane", "Alice", "Bob", "Sarah", "Michael"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia"]
    
    import random
    
    contacts = []
    for i in range(random.randint(2, 4)):
        contacts.append({
            "company_id": None,
            "full_name": f"{random.choice(first_names)} {random.choice(last_names)}",
            "title": random.choice(titles),
            "seniority_level": random.choice(seniorities),
            "email": None,  # Would need more data to extract
            "linkedin_url": None,
            "decision_maker_score": random.uniform(0.6, 0.95),
            "relationship_score": 0.0,
            "response_rate": 0.0,
            "source": "sample",
        })
    
    return contacts


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Test
    print("Testing company scrapers...")
    company = scrape_company_careers_page("Microsoft", "microsoft.com")
    print(f"Company data: {company}")
    
    sample = generate_sample_company_data("Google", "google.com")
    print(f"Sample company: {sample}")
    
    contacts = generate_sample_contacts("Microsoft")
    print(f"Sample contacts: {contacts}")
