from fastapi.testclient import TestClient

from app.insights import config as C


def test_feature_catalogue(client: TestClient) -> None:
    features = {f["feature"]: f for f in client.get("/api/features").json()}

    assert set(features) == set(C.FEATURES)
    assert features["wake_pct"] == {
        "feature": "wake_pct",
        "label": "Awake at night",
        "unit": "%",
        "group": "C",
        "group_label": "Sleep continuity",
        "when": "last_night",
        "better": "lower",
        "in_patterns": True,
        "description": "Share of time in bed spent awake during the night.",
    }
    assert features["steps"]["when"] == "day_before" and features["steps"]["better"] == "higher"
    assert features["sleep_eff"]["in_patterns"] is False
