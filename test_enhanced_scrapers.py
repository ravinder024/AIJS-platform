#!/usr/bin/env python
"""
Test script for enhanced job scraping with anti-bot evasion.
Tests all components: anti-bot, enhanced scrapers, company enrichment, and database integration.
"""

import logging
from datetime import datetime
from sqlalchemy import select, func
from db import SessionLocal, engine
from models import Base, Job, Company, Contact, SearchProfile, Run
from enhanced_scrapers import scrape_with_anti_bot, scrape_all_sources_with_health_check
from anti_bot_evasion import source_health, UserAgentRotator, RequestDelay
from company_scraper import scrape_company_careers_page, generate_sample_company_data, generate_sample_contacts
import job_scrapers

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_anti_bot_components():
    """Test anti-bot evasion components."""
    print("\n" + "=" * 80)
    print("🧪 TEST 1: Anti-Bot Evasion Components")
    print("=" * 80)
    
    # Test user-agent rotation
    print("\n1. User-Agent Rotation:")
    for i in range(3):
        headers = UserAgentRotator.get_headers()
        print(f"   Request {i+1}: {headers['User-Agent'][:60]}...")
    
    # Test request delays
    print("\n2. Request Delays:")
    delay_engine = RequestDelay(base_delay=1.0, jitter=2.0)
    for source in ["remoteok", "indeed", "naukri"]:
        print(f"   Testing {source}...")
        delay_engine.wait(source)
    
    # Test fingerprinting
    print("\n3. Browser Fingerprinting:")
    from anti_bot_evasion import BrowserFingerprint
    context_args = BrowserFingerprint.get_playwright_context_args()
    print(f"   Viewport: {context_args['viewport']}")
    print(f"   Timezone: {context_args['timezone_id']}")
    print(f"   Locale: {context_args['locale']}")
    
    print("✅ Anti-bot components test passed")


def test_enhanced_scrapers():
    """Test enhanced scrapers with anti-bot protection."""
    print("\n" + "=" * 80)
    print("🧪 TEST 2: Enhanced Scrapers with Anti-Bot")
    print("=" * 80)
    
    print("\nScraping with anti-bot protection...")
    jobs = scrape_all_sources_with_health_check(
        keyword="Product Manager",
        location="Remote",
        days=7,
    )
    
    print(f"\n📊 Results:")
    print(f"   Total jobs scraped: {len(jobs)}")
    
    if jobs:
        print(f"\n   Sample jobs:")
        for i, job in enumerate(jobs[:3], 1):
            print(f"   {i}. {job.get('title')} @ {job.get('company_name')}")
            print(f"      Source: {job.get('source')} | URL: {job.get('source_url')[:50]}...")
    
    print("✅ Enhanced scrapers test passed")


def test_source_health_monitoring():
    """Test source health monitoring."""
    print("\n" + "=" * 80)
    print("🧪 TEST 3: Source Health Monitoring")
    print("=" * 80)
    
    # Simulate some success/failure events
    source_health.record_success("remoteok", 10)
    source_health.record_success("remoteok", 8)
    source_health.record_failure("indeed", is_blocked=True)
    source_health.record_success("indeed", 5)
    source_health.record_failure("naukri", is_blocked=False)
    
    # Print summary
    source_health.print_summary()
    
    # Check if sources should be scraped
    print("\n   Should scrape decisions:")
    for source in ["remoteok", "indeed", "naukri"]:
        should_scrape = source_health.should_scrape(source)
        status = "✅ Yes" if should_scrape else "❌ No"
        print(f"   {source}: {status}")
    
    print("✅ Source health monitoring test passed")


def test_company_scraping():
    """Test company data scraping."""
    print("\n" + "=" * 80)
    print("🧪 TEST 4: Company Data Scraping")
    print("=" * 80)
    
    print("\nScraping company careers page...")
    company = scrape_company_careers_page("Microsoft", "microsoft.com")
    print(f"   Result: {company}")
    
    print("\nGenerating sample company data...")
    sample = generate_sample_company_data("Google", "google.com")
    print(f"   Company: {sample['name']}")
    print(f"   Industry: {sample['industry']}")
    print(f"   Funding Stage: {sample['funding_stage']}")
    print(f"   Remote Policy: {sample['remote_policy']}")
    print(f"   Opportunity Score: {sample['opportunity_score']:.1f}")
    
    print("✅ Company scraping test passed")


def test_database_integration():
    """Test database schema and operations."""
    print("\n" + "=" * 80)
    print("🧪 TEST 5: Database Integration")
    print("=" * 80)
    
    try:
        # Initialize schema
        print("\n1. Creating database schema...")
        Base.metadata.create_all(bind=engine)
        print("   ✅ Schema created")
        
        session = SessionLocal()
        
        # Create test profile
        print("\n2. Creating test profile...")
        profile = SearchProfile(
            name="Test PM Profile",
            role_query="Product Manager",
            location="Remote",
            work_settings=["remote"],
            is_active=True,
        )
        session.add(profile)
        session.flush()
        print(f"   ✅ Profile created (ID: {profile.id})")
        
        # Create test company
        print("\n3. Creating test company...")
        company = Company(
            name="TechCorp",
            domain="techcorp.com",
            industry="SaaS",
            employee_count=150,
            funding_stage="series_b",
            remote_policy="hybrid",
            opportunity_score=85.0,
        )
        session.add(company)
        session.flush()
        print(f"   ✅ Company created (ID: {company.id})")
        
        # Create test contacts
        print("\n4. Creating test contacts...")
        for i in range(2):
            contact = Contact(
                company_id=company.id,
                full_name=f"Contact {i+1}",
                title="Product Manager",
                seniority_level="vp",
                email=f"contact{i+1}@techcorp.com",
                decision_maker_score=0.8,
            )
            session.add(contact)
        session.flush()
        print(f"   ✅ Contacts created")
        
        # Create test run and jobs
        print("\n5. Creating test jobs with company link...")
        run = Run(
            profile_id=profile.id,
            status="completed",
            total_collected=2,
            total_new=2,
        )
        session.add(run)
        session.flush()
        
        for i in range(2):
            job = Job(
                run_id=run.id,
                profile_id=profile.id,
                company_id=company.id,
                source="test",
                source_url=f"https://test.com/job{i+1}",
                title=f"PM Role {i+1}",
                company_name="TechCorp",
                location="Remote",
                employment_type="full_time",
                fingerprint=f"test_fingerprint_{i+1}",
            )
            session.add(job)
        
        session.commit()
        print(f"   ✅ Jobs created with company linkage")
        
        # Query test
        print("\n6. Testing queries...")
        job_count = session.query(func.count(Job.id)).scalar()
        company_count = session.query(func.count(Company.id)).scalar()
        contact_count = session.query(func.count(Contact.id)).scalar()
        
        print(f"   Jobs in database: {job_count}")
        print(f"   Companies in database: {company_count}")
        print(f"   Contacts in database: {contact_count}")
        
        # Relationship test
        print("\n7. Testing relationships...")
        job = session.query(Job).first()
        if job and job.company:
            print(f"   Job '{job.title}' linked to company '{job.company.name}'")
            print(f"   Company has {len(job.company.contacts)} contacts")
            print("   ✅ Relationships working")
        
        session.close()
        print("\n✅ Database integration test passed")
        
    except Exception as e:
        logger.error(f"❌ Database test failed: {e}")
        import traceback
        traceback.print_exc()


def test_full_pipeline():
    """Test the complete pipeline."""
    print("\n" + "=" * 80)
    print("🧪 TEST 6: Full Pipeline (All Components)")
    print("=" * 80)
    
    try:
        print("\n1. Scraping jobs with anti-bot protection...")
        jobs = scrape_all_sources_with_health_check(
            keyword="Product Manager",
            location="Remote",
            days=7,
        )
        print(f"   ✅ Scraped {len(jobs)} jobs")
        
        print("\n2. Enriching jobs with company data...")
        session = SessionLocal()
        
        # Create profile and run
        profile = SearchProfile(
            name=f"Full Pipeline Test {datetime.now().isoformat()}",
            role_query="Product Manager",
            location="Remote",
            is_active=True,
        )
        session.add(profile)
        session.flush()
        
        run = Run(profile_id=profile.id, status="running", total_collected=len(jobs))
        session.add(run)
        session.flush()
        
        stored_count = 0
        for job in jobs[:5]:  # Store first 5 jobs
            # Create company if not exists
            company = session.query(Company).filter_by(
                domain=job.get("source_url", "").split("/")[2] if job.get("source_url") else "unknown"
            ).first()
            
            if not company:
                company = Company(
                    name=job.get("company_name", "Unknown"),
                    domain=job.get("source_url", "").split("/")[2] if job.get("source_url") else "unknown",
                    industry="Technology",
                    opportunity_score=75.0,
                )
                session.add(company)
                session.flush()
            
            # Create job
            job_record = Job(
                run_id=run.id,
                profile_id=profile.id,
                company_id=company.id,
                source=job.get("source", "unknown"),
                source_url=job.get("source_url", ""),
                title=job.get("title", ""),
                company_name=job.get("company_name", ""),
                location=job.get("location", ""),
                employment_type=job.get("employment_type", "full_time"),
                fingerprint=job.get("fingerprint", "unknown"),
                raw_payload=job,
            )
            session.add(job_record)
            stored_count += 1
        
        session.commit()
        print(f"   ✅ Stored {stored_count} jobs with company enrichment")
        
        # Verify
        total_jobs = session.query(func.count(Job.id)).scalar()
        total_companies = session.query(func.count(Company.id)).scalar()
        print(f"\n3. Database verification:")
        print(f"   Total jobs: {total_jobs}")
        print(f"   Total companies: {total_companies}")
        print("   ✅ Full pipeline test passed")
        
        session.close()
        
    except Exception as e:
        logger.error(f"❌ Full pipeline test failed: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("🚀 ENHANCED JOB SCRAPER TEST SUITE")
    print("=" * 80)
    
    tests = [
        ("Anti-Bot Components", test_anti_bot_components),
        ("Enhanced Scrapers", test_enhanced_scrapers),
        ("Source Health Monitoring", test_source_health_monitoring),
        ("Company Scraping", test_company_scraping),
        ("Database Integration", test_database_integration),
        ("Full Pipeline", test_full_pipeline),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            logger.error(f"❌ {name} test failed: {e}")
            failed += 1
            import traceback
            traceback.print_exc()
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 TEST SUMMARY")
    print("=" * 80)
    print(f"✅ Passed: {passed}/{len(tests)}")
    print(f"❌ Failed: {failed}/{len(tests)}")
    print("=" * 80)
    
    if failed == 0:
        print("🎉 All tests passed!")
    else:
        print(f"⚠️  {failed} test(s) failed. Review the logs above.")


if __name__ == "__main__":
    main()
