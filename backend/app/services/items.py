from sqlmodel import Session, select

from app.models import Item
from app.schemas import ItemCreate, ItemUpdate


def list_items(session: Session) -> list[Item]:
    return list(session.exec(select(Item).order_by(Item.id)).all())


def get_item(session: Session, item_id: int) -> Item | None:
    return session.get(Item, item_id)


def create_item(session: Session, data: ItemCreate) -> Item:
    item = Item.model_validate(data)
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


def update_item(session: Session, item: Item, data: ItemUpdate) -> Item:
    item.sqlmodel_update(data.model_dump(exclude_unset=True))
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


def delete_item(session: Session, item: Item) -> None:
    session.delete(item)
    session.commit()
