#!/usr/bin/env python
"""Display jobs currently stored in the database."""

from sqlalchemy import select
from db import SessionLocal
from models import Job

def display_jobs():
    """Fetch and display all jobs from the database."""
    try:
        session = SessionLocal()
        jobs = session.query(Job).order_by(Job.collected_at.desc()).all()
        
        if not jobs:
            print("❌ No jobs found in database")
            return
        
        print("\n" + "=" * 100)
        print(f"📋 SCRAPED JOBS - Total: {len(jobs)}")
        print("=" * 100)
        
        for i, job in enumerate(jobs, 1):
            print(f"\n[{i}] {job.title}")
            print(f"    Company:    {job.company_name}")
            print(f"    Location:   {job.location}")
            print(f"    Source:     {job.source.upper()}")
            print(f"    URL:        {job.source_url}")
            if job.salary_min or job.salary_max:
                sal_info = []
                if job.salary_min:
                    sal_info.append(f"${job.salary_min:,}")
                if job.salary_max:
                    sal_info.append(f"${job.salary_max:,}")
                print(f"    Salary:     {' - '.join(sal_info)}")
            if job.remote_type:
                print(f"    Remote:     {job.remote_type}")
            if job.employment_type:
                print(f"    Type:       {job.employment_type}")
            print(f"    Score:      {job.ranking_score:.2f}")
            
            # Show description preview
            if job.description:
                desc_preview = job.description[:150].replace('\n', ' ').strip()
                if len(job.description) > 150:
                    desc_preview += "..."
                print(f"    Desc:       {desc_preview}")
        
        print("\n" + "=" * 100)
        print(f"✅ Total jobs displayed: {len(jobs)}")
        print("=" * 100 + "\n")
        
        session.close()
    except Exception as e:
        print(f"❌ Error fetching jobs: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    display_jobs()
