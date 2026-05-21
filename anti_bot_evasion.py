"""
Anti-bot evasion layer for web scraping.
Implements user-agent rotation, request delays, browser fingerprinting, and health monitoring.
"""

import random
import time
from typing import Optional
from datetime import datetime, timedelta


class UserAgentRotator:
    """Rotate realistic user-agent headers to avoid blocking."""

    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3.1 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0",
        "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_3_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3.1 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (iPad; CPU OS 17_3_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3.1 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ]

    @staticmethod
    def get_random() -> str:
        """Get a random user-agent."""
        return random.choice(UserAgentRotator.USER_AGENTS)

    @staticmethod
    def get_headers() -> dict:
        """Get random headers with rotated user-agent."""
        return {
            "User-Agent": UserAgentRotator.get_random(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Cache-Control": "max-age=0",
        }


class RequestDelay:
    """Implement smart delays between requests to avoid rate limiting."""

    def __init__(self, base_delay: float = 2.0, jitter: float = 3.0, aggressive_delay: float = 10.0):
        """
        Initialize delay strategy.

        Args:
            base_delay: Minimum seconds between requests
            jitter: Maximum random seconds to add
            aggressive_delay: Delay for known aggressive sites (Indeed, Wellfound)
        """
        self.base_delay = base_delay
        self.jitter = jitter
        self.aggressive_delay = aggressive_delay
        self.aggressive_sources = {"indeed", "wellfound"}
        self.last_request_time = {}

    def wait(self, source: str = "default") -> None:
        """
        Wait before next request based on source and last request time.

        Args:
            source: Name of scraper source
        """
        if source not in self.last_request_time:
            self.last_request_time[source] = datetime.now()
            return

        is_aggressive = source.lower() in self.aggressive_sources
        delay = self.aggressive_delay if is_aggressive else self.base_delay
        jitter = random.uniform(0, self.jitter)
        total_delay = delay + jitter

        time_since_last = (datetime.now() - self.last_request_time[source]).total_seconds()
        if time_since_last < total_delay:
            wait_time = total_delay - time_since_last
            print(f"[Rate Limit] Waiting {wait_time:.1f} seconds before {source} request...")
            time.sleep(wait_time)

        self.last_request_time[source] = datetime.now()

    def batch_wait(self, batch_size: int = 10, cooldown: float = 3.0) -> None:
        """
        Wait after processing a batch of requests.

        Args:
            batch_size: Number of requests in batch
            cooldown: Seconds to wait after batch
        """
        if batch_size > 0:
            print(f"[Batch] Processed {batch_size} requests, cooling down for {cooldown:.1f} seconds...")
            time.sleep(cooldown)


class BrowserFingerprint:
    """Randomize browser fingerprint for Playwright to avoid detection."""

    @staticmethod
    def get_playwright_context_args() -> dict:
        """Get random browser context arguments for Playwright."""
        return {
            "viewport": random.choice([
                {"width": 1920, "height": 1080},
                {"width": 1366, "height": 768},
                {"width": 1440, "height": 900},
                {"width": 1280, "height": 720},
            ]),
            "user_agent": UserAgentRotator.get_random(),
            "locale": random.choice(["en-US", "en-GB", "en-AU"]),
            "timezone_id": random.choice(["America/New_York", "America/Los_Angeles", "Europe/London"]),
            "geolocation": random.choice([
                {"latitude": 40.7128, "longitude": -74.0060},  # NYC
                {"latitude": 34.0522, "longitude": -118.2437},  # LA
                {"latitude": 51.5074, "longitude": -0.1278},  # London
            ]),
            "permissions": [],
            "extra_http_headers": {
                "Referer": random.choice([
                    "https://www.google.com/",
                    "https://www.linkedin.com/",
                    "https://www.github.com/",
                ]),
            },
        }

    @staticmethod
    def get_browser_launch_args() -> dict:
        """Get random browser launch arguments."""
        return {
            "headless": True,
            "args": [
                "--disable-blink-features=AutomationControlled",
                f"--window-size={random.randint(1280, 1920)},{random.randint(720, 1080)}",
            ],
        }


class SourceHealth:
    """Track health metrics for each scraper source."""

    def __init__(self):
        self.metrics = {}

    def record_success(self, source: str, jobs_count: int = 0) -> None:
        """Record successful scrape."""
        if source not in self.metrics:
            self.metrics[source] = {
                "total_requests": 0,
                "successful_requests": 0,
                "failed_requests": 0,
                "block_events": 0,
                "last_update": None,
                "avg_jobs": 0.0,
                "success_rate": 1.0,
                "block_rate": 0.0,
            }

        self.metrics[source]["total_requests"] += 1
        self.metrics[source]["successful_requests"] += 1
        self.metrics[source]["last_update"] = datetime.now()
        self.metrics[source]["avg_jobs"] = (
            (self.metrics[source]["avg_jobs"] * (self.metrics[source]["successful_requests"] - 1) + jobs_count)
            / self.metrics[source]["successful_requests"]
        )
        self._update_rates(source)

    def record_failure(self, source: str, is_blocked: bool = False) -> None:
        """Record failed scrape."""
        if source not in self.metrics:
            self.metrics[source] = {
                "total_requests": 0,
                "successful_requests": 0,
                "failed_requests": 0,
                "block_events": 0,
                "last_update": None,
                "avg_jobs": 0.0,
                "success_rate": 1.0,
                "block_rate": 0.0,
            }

        self.metrics[source]["total_requests"] += 1
        self.metrics[source]["failed_requests"] += 1
        if is_blocked:
            self.metrics[source]["block_events"] += 1
        self.metrics[source]["last_update"] = datetime.now()
        self._update_rates(source)

    def _update_rates(self, source: str) -> None:
        """Update success and block rates."""
        m = self.metrics[source]
        if m["total_requests"] > 0:
            m["success_rate"] = m["successful_requests"] / m["total_requests"]
            m["block_rate"] = m["block_events"] / m["total_requests"]

    def get_health(self, source: str) -> dict:
        """Get health metrics for source."""
        return self.metrics.get(source, {})

    def should_scrape(self, source: str) -> bool:
        """Determine if source should be scraped (not over-blocked)."""
        if source not in self.metrics:
            return True
        health = self.metrics[source]
        # Skip if block rate > 50%
        return health.get("block_rate", 0.0) < 0.5

    def print_summary(self) -> None:
        """Print health summary for all sources."""
        print("\n📊 Source Health Summary:")
        print("-" * 80)
        for source, metrics in self.metrics.items():
            print(
                f"  {source.upper()}: Success={metrics['success_rate']:.1%} | "
                f"Blocks={metrics['block_rate']:.1%} | "
                f"Avg Jobs={metrics['avg_jobs']:.1f} | "
                f"Total Requests={metrics['total_requests']}"
            )
        print("-" * 80)


# Global instances
request_delay = RequestDelay()
source_health = SourceHealth()
