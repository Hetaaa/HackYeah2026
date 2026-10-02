import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from scripts.seed import SAMPLE_ITEMS, seed_if_empty


def create(client: TestClient, **payload: str | None) -> dict:
    response = client.post("/api/items", json={"name": "Test item", **payload})
    assert response.status_code == 201
    return response.json()


def test_list_empty(client: TestClient) -> None:
    response = client.get("/api/items")

    assert response.status_code == 200
    assert response.json() == []


def test_create_and_get(client: TestClient) -> None:
    created = create(client, name="Lamp", description="Desk lamp")

    assert created["id"] > 0
    assert created["name"] == "Lamp"
    assert created["description"] == "Desk lamp"
    assert created["created_at"].endswith("Z")

    response = client.get(f"/api/items/{created['id']}")
    assert response.status_code == 200
    assert response.json() == created


def test_list_returns_created(client: TestClient) -> None:
    create(client, name="A")
    create(client, name="B")

    names = [item["name"] for item in client.get("/api/items").json()]
    assert names == ["A", "B"]


def test_create_requires_name(client: TestClient) -> None:
    assert client.post("/api/items", json={"description": "no name"}).status_code == 422
    assert client.post("/api/items", json={"name": ""}).status_code == 422


def test_patch_updates_only_sent_fields(client: TestClient) -> None:
    created = create(client, name="Old", description="Keep me")

    response = client.patch(f"/api/items/{created['id']}", json={"name": "New"})

    assert response.status_code == 200
    assert response.json()["name"] == "New"
    assert response.json()["description"] == "Keep me"


def test_patch_can_clear_description(client: TestClient) -> None:
    created = create(client, description="Remove me")

    response = client.patch(f"/api/items/{created['id']}", json={"description": None})

    assert response.status_code == 200
    assert response.json()["description"] is None


def test_patch_rejects_null_name(client: TestClient) -> None:
    created = create(client)

    response = client.patch(f"/api/items/{created['id']}", json={"name": None})

    assert response.status_code == 422


def test_delete(client: TestClient) -> None:
    created = create(client)

    response = client.delete(f"/api/items/{created['id']}")

    assert response.status_code == 204
    assert client.get(f"/api/items/{created['id']}").status_code == 404


@pytest.mark.parametrize(
    ("method", "body"),
    [("get", None), ("patch", {"name": "X"}), ("delete", None)],
)
def test_missing_item_returns_404(client: TestClient, method: str, body: dict | None) -> None:
    response = client.request(method, "/api/items/999", json=body)

    assert response.status_code == 404
    assert response.json() == {"detail": "Item 999 not found"}


def test_seed_if_empty_runs_once(session: Session) -> None:
    assert seed_if_empty(session) is True
    assert seed_if_empty(session) is False


def test_seeded_items_are_listed(client: TestClient, session: Session) -> None:
    seed_if_empty(session)

    assert len(client.get("/api/items").json()) == len(SAMPLE_ITEMS)
