from typing import Annotated, Any

from fastapi import Depends, HTTPException, Path, status

from app.db import SessionDep
from app.models import Persona
from app.schemas import ErrorRead
from app.services import users as users_service

NOT_FOUND: dict[int | str, dict[str, Any]] = {
    status.HTTP_404_NOT_FOUND: {"model": ErrorRead, "description": "Persona or data not found"}
}


def get_persona(
    user_id: Annotated[str, Path(description="Persona id", examples=["p01"])],
    session: SessionDep,
) -> Persona:
    persona = users_service.get_persona(session, user_id)
    if persona is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"Persona {user_id} not found")
    return persona


PersonaDep = Annotated[Persona, Depends(get_persona)]
