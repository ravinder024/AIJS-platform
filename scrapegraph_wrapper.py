"""
ScrapeGraphAI wrapper for LLM-powered web scraping.
Provides fallback scraping for job listings and company information.
"""

import logging
from typing import Any, Optional
import os

try:
    from scrapegraphai.graphs import SmartScraperGraph, SmartScraperMultiGraph
except ImportError:
    SmartScraperGraph = None
    SmartScraperMultiGraph = None

logger = logging.getLogger(__name__)


class ScrapeGraphAIWrapper:
    """Wrapper for ScrapeGraphAI with fallback handling."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize ScrapeGraphAI wrapper.

        Args:
            api_key: OpenRouter API key (defaults to OPENROUTER_API_KEY env var)
            model: LLM model to use in OpenRouter format, e.g. "openai/gpt-3.5-turbo"
        """
        if SmartScraperGraph is None:
            raise ImportError(
                "scrapegraphai not installed. Run: pip install scrapegraphai"
            )

        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable not set")

        self.model = model or os.getenv("OPENROUTER_MODEL", "openai/gpt-3.5-turbo")
        self.base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        self.config = {
            "llm": {
                "api_key": self.api_key,
                "model": self.model,
                "base_url": self.base_url,
            },
            "browser_config": {
                "headless": True,
                "disable_image_loading": True,
            },
            "verbose": False,
            "timeout": 30,
        }

    def scrape_job_details(
        self,
        url: str,
        prompt: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Scrape job details from a single URL.

        Args:
            url: Job listing URL
            prompt: Custom scraping prompt (default: generic job details)

        Returns:
            Dictionary with extracted job details
        """
        if not prompt:
            prompt = """Extract the following job details from this page:
- Job title
- Company name
- Location (city and country if available)
- Job description or overview
- Required qualifications/skills
- Salary range if available
- Work setting (remote, hybrid, onsite)
- Employment type (full-time, part-time, contract)
- Application link or instructions

Return as JSON."""

        try:
            scraper = SmartScraperGraph(
                prompt=prompt,
                source=url,
                config=self.config,
            )
            result = scraper.run()
            logger.info(f"[ScrapeGraphAI] Successfully scraped job from {url}")
            return result if isinstance(result, dict) else {"raw_data": result}
        except Exception as e:
            logger.error(f"[ScrapeGraphAI] Error scraping {url}: {e}")
            return {"error": str(e)}

    def scrape_company_info(
        self,
        url: str,
        prompt: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Scrape company information from a URL.

        Args:
            url: Company website or careers page URL
            prompt: Custom scraping prompt

        Returns:
            Dictionary with company information
        """
        if not prompt:
            prompt = """Extract the following company information:
- Company name
- Industry
- Number of employees (if available)
- Headquarters location
- Company description/mission
- Recent job openings (titles and count)
- Any mention of funding stage or recent funding
- Remote work policy
- Career/jobs page link

Return as JSON."""

        try:
            scraper = SmartScraperGraph(
                prompt=prompt,
                source=url,
                config=self.config,
            )
            result = scraper.run()
            logger.info(f"[ScrapeGraphAI] Successfully scraped company from {url}")
            return result if isinstance(result, dict) else {"raw_data": result}
        except Exception as e:
            logger.error(f"[ScrapeGraphAI] Error scraping company from {url}: {e}")
            return {"error": str(e)}

    def scrape_contacts(
        self,
        url: str,
        prompt: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """
        Scrape contact information from a company page.

        Args:
            url: Company website or team page URL
            prompt: Custom scraping prompt

        Returns:
            List of contact information dictionaries
        """
        if not prompt:
            prompt = """Extract contact information for key team members:
- Full name
- Title/Position (CPO, VP Product, Hiring Manager, etc.)
- Department
- Email address (if visible)
- LinkedIn profile link (if available)
- Phone number (if public)

Return as JSON array of contacts."""

        try:
            scraper = SmartScraperGraph(
                prompt=prompt,
                source=url,
                config=self.config,
            )
            result = scraper.run()
            
            if isinstance(result, list):
                logger.info(f"[ScrapeGraphAI] Successfully scraped {len(result)} contacts from {url}")
                return result
            elif isinstance(result, dict) and "contacts" in result:
                logger.info(f"[ScrapeGraphAI] Successfully scraped contacts from {url}")
                return result["contacts"]
            else:
                logger.warning(f"[ScrapeGraphAI] Unexpected result format from {url}")
                return []
        except Exception as e:
            logger.error(f"[ScrapeGraphAI] Error scraping contacts from {url}: {e}")
            return []

    def scrape_multiple_jobs(
        self,
        urls: list[str],
        prompt: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """
        Scrape job details from multiple URLs in parallel.

        Args:
            urls: List of job listing URLs
            prompt: Custom scraping prompt

        Returns:
            List of job details dictionaries
        """
        if not SmartScraperMultiGraph:
            # Fallback to sequential scraping
            logger.warning("[ScrapeGraphAI] MultiGraph not available, using sequential scraping")
            return [self.scrape_job_details(url, prompt) for url in urls]

        if not prompt:
            prompt = """Extract job details: title, company, location, description, 
            requirements, salary, work setting, employment type. Return as JSON."""

        try:
            scraper = SmartScraperMultiGraph(
                prompt=prompt,
                sources=urls,
                config=self.config,
            )
            result = scraper.run()
            
            if isinstance(result, list):
                logger.info(f"[ScrapeGraphAI] Successfully scraped {len(result)} jobs from {len(urls)} URLs")
                return result
            else:
                logger.warning("[ScrapeGraphAI] Unexpected result format from multi-scrape")
                return []
        except Exception as e:
            logger.error(f"[ScrapeGraphAI] Error in multi-scrape: {e}")
            return []


def scrape_with_fallback(
    url: str,
    scraper_type: str = "job",
    custom_prompt: Optional[str] = None,
) -> dict[str, Any]:
    """
    Scrape a URL with ScrapeGraphAI as fallback for existing scrapers.

    Args:
        url: URL to scrape
        scraper_type: Type of scraper ('job', 'company', 'contacts')
        custom_prompt: Custom scraping prompt

    Returns:
        Dictionary with scraped data
    """
    try:
        wrapper = ScrapeGraphAIWrapper()

        if scraper_type == "job":
            return wrapper.scrape_job_details(url, custom_prompt)
        elif scraper_type == "company":
            return wrapper.scrape_company_info(url, custom_prompt)
        elif scraper_type == "contacts":
            contacts = wrapper.scrape_contacts(url, custom_prompt)
            return {"contacts": contacts}
        else:
            logger.error(f"Unknown scraper type: {scraper_type}")
            return {"error": f"Unknown scraper type: {scraper_type}"}

    except Exception as e:
        logger.error(f"Error in scrape_with_fallback: {e}")
        return {"error": str(e)}


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)

    # Test company scraping
    wrapper = ScrapeGraphAIWrapper()
    
    print("Testing ScrapeGraphAI wrapper...")
    company_result = wrapper.scrape_company_info("https://www.linkedin.com/company/microsoft/")
    print(f"Company result: {company_result}")
