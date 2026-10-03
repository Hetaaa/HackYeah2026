# CLAUDE.md

Hackathon project (24h). Priorities: simple, readable, fast to extend. No overengineering.

## Stack

- Backend (`backend/`): Python 3.12, uv, FastAPI, SQLModel, SQLite, pydantic-settings, pytest, ruff.
- Frontend (`frontend/`): React + Vite, owned by a separate team. Talks to the backend via `/api`.

## Backend layout

```text
backend/
  app/
    main.py       FastAPI app, CORS, lifespan (create_all + seed if empty), routers under /api
    config.py     Settings from .env (DATABASE_URL, CORS_ORIGINS comma-separated, ENV)
    db.py         engine, get_session, SessionDep
    models.py     SQLModel tables + shared *Base field classes
    schemas.py    request/response models: XCreate, XUpdate, XRead
    analysis.py   adapter: Day rows -> app/insights -> API schemas; services only call its functions
    insights/     wellness algorithm (pandas): cleaning, pattern engine, day texts; owned by the
                  algorithms team, see backend/docs/insights.md
    deps.py       PersonaDep: resolves {user_id} from the path or returns 404
    routers/      one file per area, thin HTTP layer
    services/     one file per area (same name as the router), plain functions
    clients/      external API integrations only
  data/demo/      PMData demo personas as CSV (seed source)
  docs/           insights.md (algorithm, data contract, validation)
  scripts/        seed.py, reset_db.py, import_days.py (CSV import), import_pmdata.py (PMData -> CSV)
  tests/          pytest, in-memory SQLite per test
```

## Architecture rules

- Routers are thin: validate input, call a service, return a schema. No business logic in routers (raising 404 is fine).
- Services are plain functions that take `session: Session` as the first argument. No classes, no abstract interfaces, no repository layer, no DI containers.
- Routers get the session via `session: SessionDep` (Annotated `Depends(get_session)`).
- External integrations only in `app/clients/`, called from services.
- No migrations. Lifespan runs `create_all` and seeds if `Persona` is empty. Schema change: `uv run python -m scripts.reset_db`.
- Build table rows from input via `X.model_validate(x_create)`: `table=True` models skip validation when constructed directly (`Day(mood=9)` is accepted).
- Run uvicorn with a single worker: startup seeding is check-then-insert and would duplicate rows with several workers.
- PATCH: `XUpdate` has all fields optional; apply with `item.sqlmodel_update(data.model_dump(exclude_unset=True))`.
- Datetimes: store UTC (`datetime.now(UTC)`); `XRead` marks naive values from SQLite as UTC.
- No auth.
- Type hints everywhere; short docstrings only where something is not obvious.
- Tests use the `client` / `session` fixtures from `tests/conftest.py`; never touch `app.db`.
- App code gets sessions via `SessionDep` (or `db.engine` through the module). Never `from app.db import engine` in `app/`: tests swap `db.engine` and a direct import would bypass that.
- Don't wrap `TestClient(app)` in `with`: that runs lifespan and seeds the test DB.

## Naming

- Area `events`: `app/routers/events.py` + `app/services/events.py` + `tests/test_events.py`.
- Models singular (`Event`), URL paths plural (`/api/events`).

## Commands (run in `backend/`)

```bash
uv sync                                   # install
uv run uvicorn app.main:app --reload      # dev server, docs at /docs
uv run pytest                             # tests
uv run ruff check . && uv run ruff format .   # lint + format
uv run python -m scripts.reset_db         # drop, recreate, seed DB
```

Before finishing a change: `uv run ruff check .`, `uv run ruff format --check .` and `uv run pytest` must pass.

## Do NOT add without an explicit request

- Alembic or any migration tool
- Authentication / authorization
- Service classes, repository layer, DI containers, abstract base classes
- New dependencies for things the stack already covers
