from typing import Iterator

from sqlmodel import SQLModel, create_engine, Session
from config.settings import DATABASE_URL


# Normalize Neon-style URLs to use psycopg v3 driver automatically
normalized_url = DATABASE_URL
if normalized_url and normalized_url.startswith("postgresql://"):
    normalized_url = normalized_url.replace("postgresql://", "postgresql+psycopg://", 1)


if not normalized_url:
    print("⚠ Warning: DATABASE_URL not set, using SQLite (not recommended for production)")
    engine = create_engine("sqlite:///./app.db", echo=False)
else:
    try:
        engine = create_engine(normalized_url, echo=False)
        # Test connection (SQLAlchemy 2.0+ compatible)
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✓ Database connection successful")
    except Exception as e:
        print(f"⚠ Warning: Database connection failed: {e}")
        print("   App will continue but database features may not work")
        # Create a dummy engine to prevent crashes
        engine = create_engine("sqlite:///./app.db", echo=False)


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
