from app.insights import config as C
from app.insights import texts
from app.schemas import FeatureRead


def list_features() -> list[FeatureRead]:
    return [
        FeatureRead(
            feature=name,
            label=f.label,
            unit=f.unit,
            group=f.group,
            group_label=texts.GROUPS[f.group],
            when="last_night" if f.night else "day_before",
            tested_direction="lower" if f.bad_when == "below" else "higher",
            can_be_pattern=f.mode == "search",
            description=texts.DESCRIPTIONS[name],
        )
        for name, f in C.FEATURES.items()
    ]
