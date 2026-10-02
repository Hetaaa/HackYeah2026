"""Drop all tables, recreate them and seed. Run with: uv run python -m scripts.reset_db

Drops tables instead of deleting the .db file, so it also works on Windows while the dev
server keeps the file open.
"""

from sqlmodel import Session, SQLModel

from app.db import engine, init_db
from scripts.seed import seed


def reset_db() -> None:
    SQLModel.metadata.drop_all(engine)
    init_db(engine)
    with Session(engine) as session:
        seed(session)


if __name__ == "__main__":
    reset_db()
    print(f"Database reset and seeded: {engine.url}")
