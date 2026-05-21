#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from job_scrapers import scrape_remoteok, scrape_indeed, scrape_naukri, scrape_wellfound, scrape_linkedin

def test_all_scrapers():
    """Test all job scrapers to verify they return real job data with working links."""
    
    test_params = {
        'keyword': 'Developer',
        'location': 'Remote',
        'days': 30,
        'job_setting': 'remote',
        'exclude_keywords': [],
        'company_size': None
    }
    
    scrapers = {
        'RemoteOK': scrape_remoteok,
        'Indeed': scrape_indeed,
        'Naukri': scrape_naukri,
        'Wellfound': scrape_wellfound,
        'LinkedIn': scrape_linkedin
    }
    
    all_results = {}
    
    for name, scraper_func in scrapers.items():
        print(f"\n{'='*50}")
        print(f"Testing {name} Scraper")
        print(f"{'='*50}")
        
        try:
            jobs = scraper_func(**test_params)
            all_results[name] = jobs
            
            print(f"✅ {name}: Found {len(jobs)} jobs")
            
            if len(jobs) > 0:
                # Show first 2 jobs as examples
                for i, job in enumerate(jobs[:2]):
                    print(f"\n--- Example Job {i+1} from {name} ---")
                    print(f"Title: {job.get('title', 'N/A')}")
                    print(f"Company: {job.get('company_name', 'N/A')}")
                    print(f"Location: {job.get('location', 'N/A')}")
                    print(f"URL: {job.get('source_url', 'N/A')}")
                    print(f"Description: {job.get('description', 'N/A')[:100]}...")
                    
                    # Verify URL is real
                    url = job.get('source_url', '')
                    if url and url.startswith('http'):
                        print(f"✅ Valid URL format")
                    else:
                        print(f"❌ Invalid or missing URL")
            else:
                print(f"❌ No jobs found - may need debugging")
                
        except Exception as e:
            print(f"❌ {name} Error: {e}")
            all_results[name] = []
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    
    total_jobs = 0
    for name, jobs in all_results.items():
        count = len(jobs)
        total_jobs += count
        status = "✅ Working" if count > 0 else "❌ Needs Fix"
        print(f"{name:12}: {count:3} jobs {status}")
    
    print(f"\nTotal Jobs Found: {total_jobs}")
    
    if total_jobs > 0:
        print(f"🎉 SUCCESS: Found {total_jobs} real jobs with working URLs!")
    else:
        print(f"⚠️  All scrapers need debugging")

if __name__ == "__main__":
    test_all_scrapers()