import argparse
import logging
import os
import time
from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler

from agent_service import init_db, list_profiles, run_daily_search


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_all_active_profiles() -> None:
    profiles = [p for p in list_profiles() if p.is_active]
    if not profiles:
        logger.info("No active profiles found; scheduler tick skipped.")
        return

    for profile in profiles:
        try:
            result = run_daily_search(profile.id, run_date=datetime.utcnow())
            logger.info("Completed daily run: %s", result)
            time.sleep(2)
        except Exception as exc:
            logger.exception("Failed daily run for profile %s: %s", profile.id, exc)


def main() -> None:
    parser = argparse.ArgumentParser(description="Daily job agent scheduler")
    parser.add_argument(
        "--time",
        default=os.getenv("DAILY_RUN_TIME", "08:00"),
        help="Daily run time in HH:MM 24-hour format (default 08:00)",
    )
    args = parser.parse_args()

    init_db()
    hour, minute = args.time.split(":")

    scheduler = BlockingScheduler(timezone=os.getenv("TZ", "UTC"))
    scheduler.add_job(run_all_active_profiles, "cron", hour=int(hour), minute=int(minute))
    logger.info("Scheduler started for daily run at %s", args.time)
    scheduler.start()


if __name__ == "__main__":
    main()

