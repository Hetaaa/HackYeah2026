# Backend

FastAPI + SQLModel + SQLite. Wszystkie komendy uruchamiaj z katalogu `backend/`.

## Wymagania

- Python 3.12
- [uv](https://docs.astral.sh/uv/getting-started/installation/) (`pip install uv` też działa)
- Docker (opcjonalnie)

## Instalacja

```bash
uv sync
cp .env.example .env    # opcjonalnie, domyślne wartości działają bez .env
```

## Uruchomienie (dev)

```bash
uv run uvicorn app.main:app --reload
```

Przy starcie tworzą się tabele, a jeśli `Item` jest pusta, ładuje się seed (5 rekordów).

- API: <http://localhost:8000/api>
- Dokumentacja (Swagger): <http://localhost:8000/docs>
- ReDoc: <http://localhost:8000/redoc>
- Schemat OpenAPI: <http://localhost:8000/openapi.json>

## Testy

```bash
uv run pytest
```

Testy używają osobnej bazy SQLite w pamięci (świeża dla każdego testu) i nie ruszają `app.db`.

## Lint i formatowanie

```bash
uv run ruff check .          # dodaj --fix, żeby poprawić automatycznie
uv run ruff format .
```

## Reset bazy

Nie ma migracji. Po zmianie modeli:

```bash
uv run python -m scripts.reset_db
```

Usuwa i tworzy na nowo wszystkie tabele, potem ładuje seed. Działa też przy włączonym serwerze.

## Konfiguracja (`.env`)

| Zmienna        | Domyślnie                 | Opis                                        |
| -------------- | ------------------------- | ------------------------------------------- |
| `DATABASE_URL` | `sqlite:///./app.db`      | URL bazy (SQLAlchemy)                       |
| `CORS_ORIGINS` | `http://localhost:5173`   | Dozwolone originy, rozdzielone przecinkami  |
| `ENV`          | `dev`                     | Nazwa środowiska                            |

## Jak dodać nowy zasób

Kopiuj wzorzec `Item`. Przykład dla `Event`:

1. **Model**: w `app/models.py` dodaj `EventBase(SQLModel)` ze wspólnymi polami i `Event(EventBase, table=True)` z `id` (i ewentualnie `created_at`).
2. **Schematy**: w `app/schemas.py` dodaj `EventCreate(EventBase)`, `EventUpdate` (wszystkie pola opcjonalne) i `EventRead(EventBase)` z `id`.
3. **Serwis**: utwórz `app/services/events.py` ze zwykłymi funkcjami `list_events`, `get_event`, `create_event`, `update_event`, `delete_event`, które przyjmują `session: Session`.
4. **Router**: utwórz `app/routers/events.py` z `APIRouter(prefix="/events", tags=["events"])`. Router woła tylko serwis i zwraca 404, gdy rekordu brak.
5. **Podpięcie**: w `app/main.py` dodaj `app.include_router(events.router, prefix="/api")`.
6. **Test**: utwórz `tests/test_events.py` na wzór `tests/test_items.py` (fixture `client`).
7. **Baza**: `uv run python -m scripts.reset_db`.

Integracje z zewnętrznymi API trafiają do `app/clients/` i są wołane z serwisów.

## Współpraca z frontendem

- Wszystkie endpointy są pod `/api`, CORS domyślnie wpuszcza `http://localhost:5173` (Vite).
- Alternatywa dla CORS w dev: proxy w `vite.config.ts`:

  ```ts
  server: { proxy: { "/api": "http://localhost:8000" } }
  ```

- Typy TypeScript wygenerowane ze schematu (przy włączonym backendzie):

  ```bash
  npx openapi-typescript http://localhost:8000/openapi.json -o src/api/schema.ts
  ```

## Docker

```bash
docker build -t hackathon-backend .
docker run --rm -p 8000:8000 hackathon-backend
```

Port bierze się ze zmiennej `PORT` (domyślnie 8000), więc obraz działa bez zmian na Render i Railway.
Baza tworzy się i seeduje sama przy starcie.

> SQLite na Render/Railway leży na efemerycznym dysku: każdy redeploy i restart przywraca bazę do stanu seeda.
> Na demo to wystarcza; jeśli dane mają przetrwać, podepnij dysk (volume) albo ustaw `DATABASE_URL` na Postgres.
> Darmowy Render usypia instancję po bezczynności, więc pierwsze zapytanie trwa ok. 30 s. Obudź ją przed prezentacją.
