from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy import Engine
from sqlmodel import Session, SQLModel, create_engine

from app import models  # noqa: F401  (registers tables on SQLModel.metadata)
from app.config import settings


def make_engine(url: str) -> Engine:
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args)


# Tests swap this module attribute for an in-memory engine (see tests/conftest.py).
engine = make_engine(settings.database_url)


def init_db(engine: Engine) -> None:
    SQLModel.metadata.create_all(engine)


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]
