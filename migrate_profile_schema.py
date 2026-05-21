from sqlalchemy import text

from db import engine


ALTERS = [
    "ALTER TABLE search_profiles ADD COLUMN IF NOT EXISTS target_locations JSON NOT NULL DEFAULT '[]'::json",
    "ALTER TABLE search_profiles ADD COLUMN IF NOT EXISTS role_queries JSON NOT NULL DEFAULT '[]'::json",
    "ALTER TABLE search_profiles ADD COLUMN IF NOT EXISTS work_settings JSON NOT NULL DEFAULT '[]'::json",
    "ALTER TABLE search_profiles ADD COLUMN IF NOT EXISTS company_size_min INTEGER",
    "ALTER TABLE search_profiles ADD COLUMN IF NOT EXISTS company_size_max INTEGER",
    "ALTER TABLE search_profiles ADD COLUMN IF NOT EXISTS industries JSON NOT NULL DEFAULT '[]'::json",
    "ALTER TABLE search_profiles ADD COLUMN IF NOT EXISTS recently_funded_only BOOLEAN NOT NULL DEFAULT FALSE",
    "ALTER TABLE search_profiles ADD COLUMN IF NOT EXISTS job_types JSON NOT NULL DEFAULT '[]'::json",
    "ALTER TABLE search_profiles ADD COLUMN IF NOT EXISTS experience_min_years DOUBLE PRECISION",
    "ALTER TABLE search_profiles ADD COLUMN IF NOT EXISTS experience_max_years DOUBLE PRECISION",
    "ALTER TABLE search_profiles ADD COLUMN IF NOT EXISTS min_glassdoor_rating DOUBLE PRECISION",
    "ALTER TABLE search_profiles ADD COLUMN IF NOT EXISTS salary_min DOUBLE PRECISION",
    "ALTER TABLE search_profiles ADD COLUMN IF NOT EXISTS salary_max DOUBLE PRECISION",
    "ALTER TABLE search_profiles ADD COLUMN IF NOT EXISTS posted_within_hours DOUBLE PRECISION",
]


def main() -> None:
    with engine.begin() as conn:
        for stmt in ALTERS:
            conn.execute(text(stmt))
    print("search_profiles schema migration complete.")


if __name__ == "__main__":
    main()
