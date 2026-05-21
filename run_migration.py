#!/usr/bin/env python
"""
Database migration script to add company_id column and new tables.
"""

import logging
from sqlalchemy import text, inspect
from db import engine, SessionLocal
from models import Base, Company, Contact

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_migration():
    """Run database migrations."""
    print("\n" + "=" * 80)
    print("🔄 DATABASE MIGRATION")
    print("=" * 80)
    
    with engine.connect() as connection:
        # Check if company_id column exists
        inspector = inspect(engine)
        columns = [col['name'] for col in inspector.get_columns('jobs')]
        
        print(f"\n✓ Jobs table columns: {columns}")
        
        # Add company_id column if missing
        if 'company_id' not in columns:
            print("\n⚠️  Missing company_id column. Adding...")
            try:
                connection.execute(text("""
                    ALTER TABLE jobs 
                    ADD COLUMN company_id INTEGER REFERENCES companies(id) ON DELETE SET NULL
                """))
                connection.commit()
                print("✅ Added company_id column")
            except Exception as e:
                print(f"❌ Failed to add company_id: {e}")
                connection.rollback()
        else:
            print("✅ company_id column already exists")
        
        # Create companies table if missing
        if 'companies' not in inspector.get_table_names():
            print("\n⚠️  Missing companies table. Creating...")
            try:
                connection.execute(text("""
                    CREATE TABLE companies (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(255) NOT NULL,
                        domain VARCHAR(255) UNIQUE,
                        industry VARCHAR(100),
                        employee_count INTEGER,
                        funding_stage VARCHAR(50),
                        funding_amount BIGINT,
                        remote_policy VARCHAR(50),
                        hiring_signals JSONB,
                        ai_analysis JSONB,
                        opportunity_score FLOAT DEFAULT 0.0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                connection.execute(text("""
                    CREATE INDEX idx_companies_domain ON companies(domain)
                """))
                connection.commit()
                print("✅ Created companies table")
            except Exception as e:
                print(f"❌ Failed to create companies table: {e}")
                connection.rollback()
        else:
            print("✅ companies table already exists")
        
        # Create contacts table if missing
        if 'contacts' not in inspector.get_table_names():
            print("\n⚠️  Missing contacts table. Creating...")
            try:
                connection.execute(text("""
                    CREATE TABLE contacts (
                        id SERIAL PRIMARY KEY,
                        company_id INTEGER REFERENCES companies(id) ON DELETE CASCADE,
                        full_name VARCHAR(255),
                        title VARCHAR(255),
                        seniority_level VARCHAR(50),
                        email VARCHAR(255),
                        linkedin_url VARCHAR(500),
                        decision_maker_score FLOAT DEFAULT 0.0,
                        relationship_score FLOAT DEFAULT 0.0,
                        response_rate FLOAT,
                        last_contacted_at TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                connection.execute(text("""
                    CREATE INDEX idx_contacts_company_id ON contacts(company_id)
                """))
                connection.execute(text("""
                    CREATE INDEX idx_contacts_email ON contacts(email)
                """))
                connection.commit()
                print("✅ Created contacts table")
            except Exception as e:
                print(f"❌ Failed to create contacts table: {e}")
                connection.rollback()
        else:
            print("✅ contacts table already exists")
    
    # Verify migration
    print("\n" + "=" * 80)
    print("✅ MIGRATION COMPLETE")
    print("=" * 80)
    
    with engine.connect() as connection:
        inspector = inspect(engine)
        print(f"\n📊 Current tables: {inspector.get_table_names()}")
        print(f"📊 Jobs columns: {[col['name'] for col in inspector.get_columns('jobs')]}")
        print(f"📊 Companies columns: {[col['name'] for col in inspector.get_columns('companies')]}")
        print(f"📊 Contacts columns: {[col['name'] for col in inspector.get_columns('contacts')]}")


if __name__ == "__main__":
    run_migration()
