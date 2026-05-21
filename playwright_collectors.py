from __future__ import annotations

import logging
import random
import time
from typing import Any

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

logger = logging.getLogger(__name__)


def _random_delay(min_seconds: float = 1.0, max_seconds: float = 2.5) -> None:
    time.sleep(random.uniform(min_seconds, max_seconds))


def scrape_linkedin_jobs_playwright(keyword: str, location: str, days: int = 7) -> list[dict[str, Any]]:
    """
    Playwright-based LinkedIn Jobs collector.
    Notes:
    - Uses public jobs pages for v1.
    - For authenticated scraping, persist session using user_data_dir.
    """
    jobs: list[dict[str, Any]] = []
    query = keyword.replace(" ", "%20")
    loc = location.replace(" ", "%20")
    url = (
        "https://www.linkedin.com/jobs/search/"
        f"?keywords={query}&location={loc}&f_TPR=r{days * 24 * 3600}"
    )

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=45000)
            _random_delay()

            for _ in range(4):
                page.mouse.wheel(0, 5000)
                _random_delay(0.8, 1.8)

            cards = page.query_selector_all(".base-card")
            for card in cards[:60]:
                title = (card.query_selector(".base-search-card__title") or card).inner_text().strip()
                company_el = card.query_selector(".base-search-card__subtitle")
                location_el = card.query_selector(".job-search-card__location")
                link_el = card.query_selector("a.base-card__full-link")
                posted_el = card.query_selector("time")

                company = company_el.inner_text().strip() if company_el else ""
                job_location = location_el.inner_text().strip() if location_el else location
                job_url = link_el.get_attribute("href") if link_el else ""
                posted_at = posted_el.get_attribute("datetime") if posted_el else ""

                if not title or not company or not job_url:
                    continue

                jobs.append(
                    {
                        "title": title,
                        "company_name": company,
                        "location": job_location,
                        "description": "",
                        "source_url": job_url,
                        "posted_at": posted_at,
                        "source_confidence": 0.85,
                        "remote_type": "unknown",
                        "employment_type": "",
                    }
                )

            browser.close()
    except PlaywrightTimeoutError:
        logger.warning("LinkedIn collector timed out and returned partial data.")
    except Exception as exc:
        logger.exception("LinkedIn collector failed: %s", exc)

    return jobs


def scrape_company_careers_playwright(base_url: str, role_query: str, location: str) -> list[dict[str, Any]]:
    """
    Generic company careers page collector.
    Supports basic card/list discovery. Site-specific selectors should be added later.
    """
    jobs: list[dict[str, Any]] = []
    role_query_lower = role_query.lower()

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(base_url, wait_until="domcontentloaded", timeout=45000)
            _random_delay()

            for _ in range(5):
                page.mouse.wheel(0, 6000)
                _random_delay(0.6, 1.6)

            anchors = page.query_selector_all("a[href]")
            seen = set()
            for a in anchors:
                text = (a.inner_text() or "").strip()
                href = a.get_attribute("href") or ""
                if not text or not href:
                    continue

                blob = f"{text} {href}".lower()
                if "job" not in blob and "career" not in blob and role_query_lower not in blob:
                    continue

                if href.startswith("/"):
                    href = base_url.rstrip("/") + href

                key = (text.lower(), href.lower())
                if key in seen:
                    continue
                seen.add(key)

                jobs.append(
                    {
                        "title": text,
                        "company_name": base_url.split("//")[-1].split("/")[0],
                        "location": location,
                        "description": "",
                        "source_url": href,
                        "source_confidence": 0.65,
                        "remote_type": "",
                        "employment_type": "",
                    }
                )
                if len(jobs) >= 60:
                    break

            browser.close()
    except Exception as exc:
        logger.exception("Company careers collector failed for %s: %s", base_url, exc)

    return jobs
