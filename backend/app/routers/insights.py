from fastapi import APIRouter

from app.db import SessionDep
from app.deps import NOT_FOUND, PersonaDep
from app.schemas import PatternReport, Recipe
from app.services import insights as insights_service

router = APIRouter(prefix="/users/{user_id}", tags=["insights"], responses=NOT_FOUND)


@router.get(
    "/patterns",
    summary="Bad day patterns",
    description="Features that are common on bad days and rare on good days.",
)
def get_patterns(persona: PersonaDep, session: SessionDep) -> PatternReport:
    return insights_service.get_patterns(session, persona.id)


@router.get(
    "/recipe",
    summary="Good day recipe",
    description="3-5 things the user's good days have in common.",
)
def get_recipe(persona: PersonaDep, session: SessionDep) -> Recipe:
    return insights_service.get_recipe(session, persona.id)
