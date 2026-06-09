"""
Database connection and session management.
Uses SQLAlchemy with SQLite (can be swapped to PostgreSQL).
"""

from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from backend.config import settings
import os

# Create engine
# For SQLite, we need check_same_thread=False for FastAPI async support
engine_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    engine_args["connect_args"] = {"check_same_thread": False}

engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,  # Log SQL queries in debug mode
    **engine_args
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db() -> Session:
    """Get a database session. Use as FastAPI dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database - create all tables."""
    # Import models to register them with Base
    from backend.database import models
    Base.metadata.create_all(bind=engine)
    print("✅ Database initialized successfully")


def get_db_session() -> Session:
    """Get a database session for direct use (not as generator)."""
    return SessionLocal()
