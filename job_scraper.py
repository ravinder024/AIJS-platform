import argparse
import json
import csv
import os
import logging
import time
from typing import List, Dict, Any, Optional
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor, as_completed

# Import our scraping modules
from job_scrapers import (
    scrape_naukri, scrape_indeed, scrape_remoteok, 
    scrape_wellfound, scrape_linkedin
)
from output_handlers import save_jobs, print_job_summary

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('job_scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def get_job_template() -> Dict[str, Any]:
    """Return the standard job schema template."""
    return {
        "job_id": "",
        "title": "",
        "company_name": "",
        "company_id": "",
        "description": "",
        "requirements": "",
        "salary_min": None,
        "salary_max": None,
        "location": "",
        "remote_type": "",
        "employment_type": "",
        "experience_level": "",
        "industry": "",
        "source": "",
        "source_url": ""
    }

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Job Scraper for Multiple Job Boards")
    parser.add_argument('--keyword', required=True, help='Search keyword, e.g., "Product Manager"')
    parser.add_argument('--days', type=int, default=7, help='Posted within days (1, 7, 14, 30)')
    parser.add_argument('--location', required=True, help='Job location, e.g., "India" or "Remote"')
    parser.add_argument('--setting', choices=['remote', 'hybrid', 'onsite'], help='Job setting (remote, hybrid, onsite)')
    parser.add_argument('--exclude', nargs='*', default=[], help='Exclude keywords (space separated)')
    parser.add_argument('--company_size', type=str, help='Company size, e.g., "100-250 employees"')
    parser.add_argument('--output', choices=['json', 'csv', 'gsheet'], default='json', help='Output format')
    parser.add_argument('--sources', nargs='*', default=['naukri', 'indeed', 'remoteok', 'wellfound'], 
                       choices=['naukri', 'indeed', 'remoteok', 'wellfound', 'linkedin'],
                       help='Job boards to scrape (default: all except LinkedIn)')
    parser.add_argument('--filename', type=str, help='Custom output filename (without extension)')
    parser.add_argument('--parallel', action='store_true', help='Run scrapers in parallel (faster but may be detected)')
    return parser.parse_args()

def run_scraper(scraper_func, source_name: str, **kwargs) -> List[Dict[str, Any]]:
    """Run a single scraper with error handling and timing."""
    start_time = time.time()
    logger.info(f"🔍 Starting {source_name} scraper...")
    
    try:
        jobs = scraper_func(**kwargs)
        elapsed = time.time() - start_time
        logger.info(f"✅ {source_name} scraper completed in {elapsed:.2f}s - Found {len(jobs)} jobs")
        return jobs
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"❌ {source_name} scraper failed after {elapsed:.2f}s: {e}")
        return []

def scrape_all_sources(keyword: str, location: str, days: int, job_setting: Optional[str], 
                      exclude_keywords: List[str], company_size: Optional[str], 
                      sources: List[str], parallel: bool = False) -> List[Dict[str, Any]]:
    """Scrape all specified job sources."""
    
    # Define scraper mapping
    scrapers = {
        'naukri': scrape_naukri,
        'indeed': scrape_indeed,
        'remoteok': scrape_remoteok,
        'wellfound': scrape_wellfound,
        'linkedin': scrape_linkedin
    }
    
    # Prepare common arguments
    scraper_args = {
        'keyword': keyword,
        'location': location,
        'days': days,
        'job_setting': job_setting,
        'exclude_keywords': exclude_keywords,
        'company_size': company_size
    }
    
    all_jobs = []
    
    if parallel:
        # Run scrapers in parallel
        logger.info(f"🚀 Running {len(sources)} scrapers in parallel...")
        with ThreadPoolExecutor(max_workers=4) as executor:
            future_to_source = {
                executor.submit(run_scraper, scrapers[source], source, **scraper_args): source 
                for source in sources if source in scrapers
            }
            
            for future in as_completed(future_to_source):
                source = future_to_source[future]
                try:
                    jobs = future.result()
                    all_jobs.extend(jobs)
                except Exception as e:
                    logger.error(f"❌ Parallel scraper {source} failed: {e}")
    else:
        # Run scrapers sequentially
        logger.info(f"🔄 Running {len(sources)} scrapers sequentially...")
        for source in sources:
            if source in scrapers:
                jobs = run_scraper(scrapers[source], source, **scraper_args)
                all_jobs.extend(jobs)
                
                # Add delay between scrapers to be respectful
                if len(sources) > 1:
                    time.sleep(2)
    
    return all_jobs

def filter_jobs(jobs: List[Dict[str, Any]], exclude_keywords: List[str]) -> List[Dict[str, Any]]:
    """Additional filtering of jobs (already done in scrapers, but double-check)."""
    if not exclude_keywords:
        return jobs
    
    filtered_jobs = []
    for job in jobs:
        title = job.get('title', '').lower()
        description = job.get('description', '').lower()
        company = job.get('company_name', '').lower()
        
        # Check if any exclude keyword is present
        if not any(kw.lower() in f"{title} {description} {company}" for kw in exclude_keywords):
            filtered_jobs.append(job)
        else:
            logger.debug(f"Filtered out job: {job.get('title')} (matched exclude keywords)")
    
    return filtered_jobs

def deduplicate_jobs(jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove duplicate jobs based on title and company."""
    seen = set()
    unique_jobs = []
    
    for job in jobs:
        # Create a key from title and company name (normalized)
        key = f"{job.get('title', '').strip().lower()}|{job.get('company_name', '').strip().lower()}"
        
        if key not in seen and key != '|':  # Avoid empty keys
            seen.add(key)
            unique_jobs.append(job)
        else:
            logger.debug(f"Removed duplicate: {job.get('title')} at {job.get('company_name')}")
    
    removed_count = len(jobs) - len(unique_jobs)
    if removed_count > 0:
        logger.info(f"🔄 Removed {removed_count} duplicate jobs")
    
    return unique_jobs

def main():
    """Main function to orchestrate the job scraping process."""
    args = parse_args()
    
    logger.info("🎯 Starting Job Scraper")
    logger.info(f"Search: {args.keyword} | Location: {args.location} | Days: {args.days}")
    logger.info(f"Sources: {', '.join(args.sources)} | Output: {args.output}")
    
    start_time = time.time()
    
    try:
        # Scrape all sources
        all_jobs = scrape_all_sources(
            keyword=args.keyword,
            location=args.location,
            days=args.days,
            job_setting=args.setting,
            exclude_keywords=args.exclude,
            company_size=args.company_size,
            sources=args.sources,
            parallel=args.parallel
        )
        
        logger.info(f"📊 Initial scraping completed - Found {len(all_jobs)} total jobs")
        
        # Additional filtering
        if args.exclude:
            logger.info(f"🔍 Applying exclude filter for keywords: {', '.join(args.exclude)}")
            all_jobs = filter_jobs(all_jobs, args.exclude)
            logger.info(f"📊 After filtering: {len(all_jobs)} jobs remain")
        
        # Remove duplicates
        logger.info("🔄 Removing duplicate jobs...")
        unique_jobs = deduplicate_jobs(all_jobs)
        
        # Print summary
        print_job_summary(unique_jobs)
        
        # Save results
        if unique_jobs:
            filename = args.filename
            if filename and not any(filename.endswith(ext) for ext in ['.json', '.csv']):
                # Add appropriate extension if not provided
                if args.output == 'csv':
                    filename += '.csv'
                elif args.output == 'json':
                    filename += '.json'
            
            saved_file = save_jobs(unique_jobs, args.output, filename)
            
            if saved_file:
                total_time = time.time() - start_time
                logger.info(f"✅ Job scraping completed successfully in {total_time:.2f}s")
                logger.info(f"📁 Results saved to: {saved_file}")
            else:
                logger.error("❌ Failed to save results")
        else:
            logger.warning("⚠️ No jobs found matching your criteria")
    
    except KeyboardInterrupt:
        logger.info("🛑 Scraping interrupted by user")
    except Exception as e:
        logger.error(f"❌ Scraping failed: {e}")
        raise

if __name__ == "__main__":
    main()
