from fastapi import APIRouter

from app.schemas import FeatureRead
from app.services import features as features_service

router = APIRouter(prefix="/features", tags=["features"])


@router.get(
    "",
    summary="Feature catalogue",
    description="Labels, units, groups and short descriptions of every watch feature the API "
    "returns. `in_patterns=false` features are context only. Which exercise feature a "
    "user's patterns use (cardio zones or brisk minutes) depends on the user.",
)
def list_features() -> list[FeatureRead]:
    return features_service.list_features()
