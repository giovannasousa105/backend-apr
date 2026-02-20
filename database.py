import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from env_loader import load_environment

load_environment()


def _normalize_database_url(raw_url: str) -> str:
    url = raw_url.strip()
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg2://", 1)
    if url.startswith("postgresql://") and "+psycopg2" not in url:
        return url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return url


raw_database_url = os.getenv("DATABASE_URL", "").strip()
if not raw_database_url:
    raise RuntimeError(
        "DATABASE_URL nao definido. Configure backend/.env (ou variavel de ambiente) "
        "com a string Postgres do Supabase."
    )

DATABASE_URL = _normalize_database_url(raw_database_url)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
