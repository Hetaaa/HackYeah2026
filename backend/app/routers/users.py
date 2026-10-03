from fastapi import APIRouter

from app.db import SessionDep
from app.deps import NOT_FOUND, PersonaDep
from app.schemas import PersonaRead
from app.services import users as users_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", summary="List demo personas")
def list_users(session: SessionDep) -> list[PersonaRead]:
    return users_service.list_personas(session)


@router.get("/{user_id}", summary="Get one persona", responses=NOT_FOUND)
def get_user(persona: PersonaDep, session: SessionDep) -> PersonaRead:
    return users_service.to_read(session, persona)
