# HackYeah 2026

Monorepo projektu hackathonowego.

| Katalog     | Zawartość                                  | Dokumentacja                             |
| ----------- | ------------------------------------------ | ---------------------------------------- |
| `backend/`  | API: FastAPI + SQLModel + SQLite           | [backend/README.md](backend/README.md)   |
| `frontend/` | React + Vite (w przygotowaniu)             | _TBD_                                    |

## Konfiguracja środowiska

Jeden skrypt instaluje uv (jeśli go brak), Pythona 3.12 i zależności, tworzy `backend/.env` i odpala lint i testy:

```powershell
# Windows
powershell -ExecutionPolicy Bypass -File .\init.ps1            # -SkipChecks pomija lint i testy
```

```bash
# Linux / macOS
./init.sh                                                      # --skip-checks pomija lint i testy
```

## Szybki start (backend)

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload
```

## Dokumentacja API (Swagger)

Przy włączonym serwerze:

- **Swagger UI** (testowanie endpointów w przeglądarce): <http://localhost:8000/docs>
- **ReDoc** (wersja do czytania): <http://localhost:8000/redoc>
- **Schemat OpenAPI** (np. do generowania typów TS): <http://localhost:8000/openapi.json>

Konwencje dla agentów AI: [CLAUDE.md](CLAUDE.md).
