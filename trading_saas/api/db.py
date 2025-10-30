from contextlib import contextmanager
from typing import Iterator

from sqlmodel import SQLModel, create_engine, Session
from config.settings import DATABASE_URL


if not DATABASE_URL:
    # Use a local SQLite for development if no DB url is provided
    engine = create_engine("sqlite:///./app.db", echo=False)
else:
    engine = create_engine(DATABASE_URL, echo=False)


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)


@contextmanager
def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
