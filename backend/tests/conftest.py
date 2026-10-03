from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app import db
from app.main import app


@pytest.fixture
def engine(monkeypatch: pytest.MonkeyPatch) -> Iterator[Engine]:
    """Fresh in-memory DB per test. StaticPool keeps one connection, so tables don't vanish."""
    test_engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(test_engine)
    # get_session and lifespan both read db.engine, so the app never touches the dev app.db.
    monkeypatch.setattr(db, "engine", test_engine)
    yield test_engine
    test_engine.dispose()


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    with Session(engine) as session:
        yield session


@pytest.fixture
def client(engine: Engine) -> TestClient:
    # Not used as a context manager on purpose: lifespan (and its seed) is skipped,
    # so every test starts with an empty database.
    return TestClient(app)


@pytest.fixture
def demo(session: Session) -> Session:
    """Database with the PMData demo personas (data/demo/*.csv)."""
    from scripts.seed import seed

    seed(session)
    return session
