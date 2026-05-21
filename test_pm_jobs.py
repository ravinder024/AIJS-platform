#!/usr/bin/env python
"""Test script to scrape Product Management jobs and verify database storage."""

from datetime import datetime
import sys
from sqlalchemy import delete, select, func
from collectors import collect_from_source
from db import SessionLocal, engine
from models import Base, Job, Run, SearchProfile
from job_scrapers import scrape_remoteok, scrape_indeed, scrape_naukri, scrape_wellfound

def init_database():
    """Initialize database schema."""
    print("🔧 Initializing database schema...")
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ Database schema initialized")
        return True
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return False

def clear_database():
    """Clear all jobs from the database."""
    print("\n🧹 Clearing previous job listings...")
    try:
        session = SessionLocal()
        # Count before clearing
        count_before = session.query(Job).count()
        print(f"  Found {count_before} existing jobs")
        
        # Delete all jobs
        session.execute(delete(Job))
        session.commit()
        
        count_after = session.query(Job).count()
        print(f"✅ Cleared database. Remaining jobs: {count_after}")
        session.close()
        return True
    except Exception as e:
        print(f"❌ Error clearing database: {e}")
        return False

def test_scrapers():
    """Test individual scrapers for Product Management jobs."""
    print("\n🌐 Testing scrapers for Product Management roles...")
    
    all_jobs = []
    
    scrapers = {
        'RemoteOK': scrape_remoteok,
        'Indeed': scrape_indeed,
        'Naukri': scrape_naukri,
        'Wellfound': scrape_wellfound,
    }
    
    for name, scraper_func in scrapers.items():
        print(f"\n  🔄 Testing {name}...")
        try:
            jobs = scraper_func(
                keyword="Product Manager",
                location="Remote",
                days=7,
                job_setting="remote",
                exclude_keywords=[],
                company_size=""
            )
            print(f"     ✅ {name}: Found {len(jobs)} jobs")
            if jobs:
                all_jobs.extend(jobs)
                # Show first job as sample
                first_job = jobs[0]
                print(f"     📄 Sample: {first_job.get('title', 'N/A')} @ {first_job.get('company_name', 'N/A')}")
        except Exception as e:
            print(f"     ⚠️  {name} error: {e}")
    
    print(f"\n📊 Total jobs scraped: {len(all_jobs)}")
    return all_jobs

def store_jobs_in_database(jobs):
    """Store jobs in the database."""
    if not jobs:
        print("\n❌ No jobs to store")
        return 0
    
    print(f"\n💾 Storing {len(jobs)} jobs in database...")
    
    try:
        session = SessionLocal()
        
        # Create or get a test profile
        profile = session.query(SearchProfile).filter_by(name="PM Test Profile").first()
        if not profile:
            profile = SearchProfile(
                name="PM Test Profile",
                role_query="Product Manager",
                location="Remote",
                work_settings=["remote"],
                is_active=True
            )
            session.add(profile)
            session.flush()
        
        # Create a run record
        run = Run(
            profile_id=profile.id,
            status="completed",
            started_at=datetime.utcnow(),
            finished_at=datetime.utcnow(),
            total_collected=len(jobs),
            total_new=len(jobs)
        )
        session.add(run)
        session.flush()
        
        # Store jobs (limit to 8 most recent)
        stored_count = 0
        for i, job_data in enumerate(jobs[:8]):
            try:
                job = Job(
                    run_id=run.id,
                    profile_id=profile.id,
                    source=job_data.get('source', 'unknown'),
                    source_url=job_data.get('source_url', ''),
                    title=job_data.get('title', ''),
                    company_name=job_data.get('company_name', ''),
                    location=job_data.get('location', ''),
                    description=job_data.get('description', '')[:2000],  # Truncate for storage
                    salary_min=job_data.get('salary_min'),
                    salary_max=job_data.get('salary_max'),
                    remote_type=job_data.get('remote_type', ''),
                    employment_type=job_data.get('employment_type', ''),
                    source_confidence=job_data.get('source_confidence', 0.75),
                    fingerprint=f"{job_data.get('title', '')}|{job_data.get('company_name', '')}|{job_data.get('source_url', '')}"[:64],
                    raw_payload=job_data
                )
                session.add(job)
                stored_count += 1
            except Exception as e:
                print(f"    ⚠️  Error storing job {i+1}: {e}")
        
        session.commit()
        print(f"✅ Stored {stored_count} jobs in database")
        
        # Display stored jobs
        print("\n📋 Stored Jobs:")
        stored_jobs = session.query(Job).filter_by(run_id=run.id).all()
        for i, job in enumerate(stored_jobs, 1):
            print(f"\n  {i}. {job.title}")
            print(f"     Company: {job.company_name}")
            print(f"     Location: {job.location}")
            print(f"     Source: {job.source}")
            print(f"     URL: {job.source_url}")
        
        session.close()
        return stored_count
        
    except Exception as e:
        print(f"❌ Database storage error: {e}")
        import traceback
        traceback.print_exc()
        return 0

def verify_database():
    """Verify jobs are in the database."""
    print("\n🔍 Verifying database contents...")
    try:
        session = SessionLocal()
        total_jobs = session.query(func.count(Job.id)).scalar()
        print(f"✅ Total jobs in database: {total_jobs}")
        
        # Show stats by source
        source_counts = session.query(Job.source, func.count(Job.id)).group_by(Job.source).all()
        if source_counts:
            print("\n   Jobs by source:")
            for source, count in source_counts:
                print(f"     • {source}: {count}")
        
        session.close()
        return total_jobs
    except Exception as e:
        print(f"❌ Database verification error: {e}")
        return 0

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 Product Management Job Scraper Test")
    print("=" * 60)
    
    # Step 1: Initialize database
    if not init_database():
        print("Failed to initialize database")
        sys.exit(1)
    
    # Step 2: Clear previous data
    if not clear_database():
        print("Failed to clear database")
        sys.exit(1)
    
    # Step 3: Test scrapers
    jobs = test_scrapers()
    
    # Step 4: Store in database
    if jobs:
        stored = store_jobs_in_database(jobs)
    else:
        print("⚠️  No jobs found from any scraper")
        stored = 0
    
    # Step 5: Verify
    verify_database()
    
    print("\n" + "=" * 60)
    print(f"✅ Test complete. Stored {stored} jobs in database.")
    print("=" * 60)
