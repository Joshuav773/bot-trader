from typing import Iterator

from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy import text
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
    _ensure_orderflow_columns()


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session


def _ensure_orderflow_columns() -> None:
    """Add new columns to order_flow table when upgrading schema."""
    try:
        with engine.begin() as conn:
            dialect = engine.dialect.name
            if dialect == "sqlite":
                existing = {
                    row[1] for row in conn.exec_driver_sql("PRAGMA table_info('order_flow')")
                }
                if "display_ticker" not in existing:
                    conn.exec_driver_sql("ALTER TABLE order_flow ADD COLUMN display_ticker VARCHAR")
                if "instrument" not in existing:
                    conn.exec_driver_sql("ALTER TABLE order_flow ADD COLUMN instrument VARCHAR DEFAULT 'equity'")
                if "option_type" not in existing:
                    conn.exec_driver_sql("ALTER TABLE order_flow ADD COLUMN option_type VARCHAR")
                if "contracts" not in existing:
                    conn.exec_driver_sql("ALTER TABLE order_flow ADD COLUMN contracts INTEGER")
                if "option_strike" not in existing:
                    conn.exec_driver_sql("ALTER TABLE order_flow ADD COLUMN option_strike FLOAT")
                if "option_expiration" not in existing:
                    conn.exec_driver_sql("ALTER TABLE order_flow ADD COLUMN option_expiration DATETIME")
                if "order_side" not in existing:
                    conn.exec_driver_sql("ALTER TABLE order_flow ADD COLUMN order_side VARCHAR")
                if "size" not in existing:
                    conn.exec_driver_sql("ALTER TABLE order_flow ADD COLUMN size FLOAT")
                conn.exec_driver_sql(
                    "UPDATE order_flow SET instrument='equity' WHERE instrument IS NULL"
                )
            else:
                conn.execute(text("ALTER TABLE order_flow ADD COLUMN IF NOT EXISTS display_ticker VARCHAR(255)"))
                conn.execute(text("ALTER TABLE order_flow ADD COLUMN IF NOT EXISTS instrument VARCHAR(50) DEFAULT 'equity'"))
                conn.execute(text("ALTER TABLE order_flow ADD COLUMN IF NOT EXISTS option_type VARCHAR(10)"))
                conn.execute(text("ALTER TABLE order_flow ADD COLUMN IF NOT EXISTS contracts INTEGER"))
                conn.execute(text("ALTER TABLE order_flow ADD COLUMN IF NOT EXISTS option_strike DOUBLE PRECISION"))
                conn.execute(text("ALTER TABLE order_flow ADD COLUMN IF NOT EXISTS option_expiration TIMESTAMP"))
                conn.execute(text("ALTER TABLE order_flow ADD COLUMN IF NOT EXISTS order_side VARCHAR(10)"))
                conn.execute(text("ALTER TABLE order_flow ADD COLUMN IF NOT EXISTS size DOUBLE PRECISION"))
                conn.execute(text("UPDATE order_flow SET instrument='equity' WHERE instrument IS NULL"))
    except Exception as exc:
        print(f"⚠ Warning: Failed to ensure order_flow columns: {exc}")
