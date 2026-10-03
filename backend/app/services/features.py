from app.insights import config as C
from app.schemas import FeatureRead


def list_features() -> list[FeatureRead]:
    return [
        FeatureRead(
            feature=name,
            label=f.label,
            unit=f.unit,
            group=f.group,
            group_label=C.GROUPS[f.group],
            when="last_night" if f.night else "day_before",
            better="lower" if f.bad_when == "above" else "higher",
            in_patterns=f.mode == "search",
            description=C.DESCRIPTIONS[name],
        )
        for name, f in C.FEATURES.items()
    ]
