from typing import Iterator

from sqlmodel import SQLModel, create_engine, Session
from config.settings import DATABASE_URL


# Normalize Neon-style URLs to use psycopg v3 driver automatically
normalized_url = DATABASE_URL
if normalized_url and normalized_url.startswith("postgresql://"):
    normalized_url = normalized_url.replace("postgresql://", "postgresql+psycopg://", 1)


if not normalized_url:
    engine = create_engine("sqlite:///./app.db", echo=False)
else:
    engine = create_engine(normalized_url, echo=False)


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
