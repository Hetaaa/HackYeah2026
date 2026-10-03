from fastapi import APIRouter, status

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
