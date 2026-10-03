from typing import Literal

from fastapi import APIRouter, HTTPException, status

from app.db import SessionDep
from app.deps import NOT_FOUND, PersonaDep
from app.schemas import PatternChart, PatternReport, Recipe
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
    description="Up to 3 things the user's good days have in common (significant patterns).",
)
def get_recipe(persona: PersonaDep, session: SessionDep) -> Recipe:
    return insights_service.get_recipe(session, persona.id)


@router.get(
    "/patterns/{feature}",
    summary="Pattern chart",
    description="Every analysed day's value of the pattern's feature against its threshold, "
    "with the day label: the data behind one bad-day pattern (kind=bad) or recipe "
    "ingredient (kind=good). 404 when the persona has no such pattern.",
)
def get_pattern_chart(
    persona: PersonaDep, feature: str, session: SessionDep, kind: Literal["bad", "good"] = "bad"
) -> PatternChart:
    chart = insights_service.get_pattern_chart(session, persona.id, feature, kind)
    if chart is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, detail=f"No {kind}-day pattern for {feature}"
        )
    return chart
