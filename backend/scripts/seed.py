"""Sample data. Run with: uv run python -m scripts.seed"""

from sqlmodel import Session, func, select

from app.models import Item

SAMPLE_ITEMS: list[dict[str, str]] = [
    {
        "name": "Rower miejski Veturilo",
        "description": "Stacja przy Rondzie ONZ, 12 wolnych rowerów.",
    },
    {
        "name": "Laptop Dell Latitude 7440",
        "description": "Sprzęt firmowy, przypisany do działu IT.",
    },
    {
        "name": "Sala konferencyjna Wisła",
        "description": "Piętro 3, 12 miejsc, projektor i tablica.",
    },
    {
        "name": "Bilet miesięczny ZTM",
        "description": "Strefa 1, ważny do końca miesiąca.",
    },
    {
        "name": "Kawa ziarnista Etiopia Yirgacheffe",
        "description": None,
    },
]


def seed(session: Session) -> None:
    session.add_all([Item(**data) for data in SAMPLE_ITEMS])
    session.commit()


def seed_if_empty(session: Session) -> bool:
    """Seed only when the Item table is empty. Returns True if data was inserted."""
    count = session.exec(select(func.count()).select_from(Item)).one()
    if count:
        return False
    seed(session)
    return True


if __name__ == "__main__":
    from app.db import engine, init_db

    init_db(engine)
    with Session(engine) as session:
        inserted = seed_if_empty(session)
    print("Seeded sample items." if inserted else "Item table not empty, skipping seed.")
