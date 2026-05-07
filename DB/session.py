from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

ROOT_DIR = Path(__file__).resolve().parents[1]

ENV_CANDIDATES = [
    ROOT_DIR / ".env",
    Path("/home/ubuntu/totem.env"),
]

for env_path in ENV_CANDIDATES:
    if env_path.exists():
        load_dotenv(env_path)

DATABASE_URL = (os.getenv("DATABASE_URL") or "").strip()

engine = None
SessionLocal = None

if DATABASE_URL:
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=3600,
    )

    SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )


def database_enabled() -> bool:
    return SessionLocal is not None


def get_db():
    if SessionLocal is None:
        raise RuntimeError(
            "Banco de dados indisponível. DATABASE_URL não configurada."
        )

    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()
