import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def _load_database_url_from_env_file() -> str | None:
    env_path = Path(".env")
    if not env_path.exists():
        return None
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("DATABASE_URL="):
            return stripped.split("=", 1)[1].strip()
    return None


database_url = os.getenv("DATABASE_URL") or _load_database_url_from_env_file()
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    database_url or "postgresql+psycopg2://postgres:postgres@localhost:5432/job_agent",
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    future=True,
)
