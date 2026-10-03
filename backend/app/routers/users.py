from fastapi import APIRouter, HTTPException, status

from app.db import SessionDep
from app.deps import NOT_FOUND, PersonaDep
from app.schemas import PersonaCreate, PersonaRead
from app.services import users as users_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", summary="List demo personas")
def list_users(session: SessionDep) -> list[PersonaRead]:
    return users_service.list_personas(session)


@router.post(
    "",
    summary="Create a user (onboarding)",
    description="Creates a real (non-demo) user. Insights appear after 60 days with a check-in "
    "and watch data; until then `insights_status` is `insufficient_days` with a day counter.",
    status_code=status.HTTP_201_CREATED,
)
def create_user(data: PersonaCreate, session: SessionDep) -> PersonaRead:
    return users_service.to_read(session, users_service.create_persona(session, data))


@router.get("/{user_id}", summary="Get one persona", responses=NOT_FOUND)
def get_user(persona: PersonaDep, session: SessionDep) -> PersonaRead:
    return users_service.to_read(session, persona)


@router.delete(
    "/{user_id}",
    summary="Delete a user",
    description="Deletes a non-demo user and all their days. Demo personas cannot be deleted "
    "(403); use POST /api/demo/reset to undo demo check-ins.",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=NOT_FOUND,
)
def delete_user(persona: PersonaDep, session: SessionDep) -> None:
    if persona.demo_today is not None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Demo personas cannot be deleted")
    users_service.delete_persona(session, persona)
