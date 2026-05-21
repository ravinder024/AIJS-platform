#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from job_scrapers import scrape_remoteok

def test_remoteok():
    print("Testing RemoteOK scraper...")
    jobs = scrape_remoteok(
        keyword="Developer",
        location="Remote", 
        days=30,
        job_setting="remote",
        exclude_keywords=[],
        company_size=None
    )
    
    print(f"Found {len(jobs)} jobs")
    
    for i, job in enumerate(jobs[:3]):  # Show first 3 jobs
        print(f"\n--- Job {i+1} ---")
        print(f"Title: '{job.get('title', 'N/A')}'")
        print(f"Company: '{job.get('company_name', 'N/A')}'")
        print(f"Description: '{job.get('description', 'N/A')[:100]}...'")
        print(f"URL: '{job.get('source_url', 'N/A')}'")
        
        # Check deduplication key
        title = job.get('title', '').strip().lower()
        company = job.get('company_name', '').strip().lower()
        key = f"{title}|{company}"
        print(f"Dedup key: '{key}'")

if __name__ == "__main__":
    test_remoteok()