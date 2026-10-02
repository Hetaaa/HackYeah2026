from fastapi import APIRouter, HTTPException, status
from sqlmodel import Session

from app.db import SessionDep
from app.models import Item
from app.schemas import ItemCreate, ItemRead, ItemUpdate
from app.services import items as items_service

router = APIRouter(prefix="/items", tags=["items"])


def _get_or_404(session: Session, item_id: int) -> Item:
    item = items_service.get_item(session, item_id)
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"Item {item_id} not found")
    return item


@router.get("", response_model=list[ItemRead])
def list_items(session: SessionDep) -> list[Item]:
    return items_service.list_items(session)


@router.get("/{item_id}", response_model=ItemRead)
def get_item(item_id: int, session: SessionDep) -> Item:
    return _get_or_404(session, item_id)


@router.post("", response_model=ItemRead, status_code=status.HTTP_201_CREATED)
def create_item(data: ItemCreate, session: SessionDep) -> Item:
    return items_service.create_item(session, data)


@router.patch("/{item_id}", response_model=ItemRead)
def update_item(item_id: int, data: ItemUpdate, session: SessionDep) -> Item:
    item = _get_or_404(session, item_id)
    return items_service.update_item(session, item, data)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(item_id: int, session: SessionDep) -> None:
    item = _get_or_404(session, item_id)
    items_service.delete_item(session, item)
