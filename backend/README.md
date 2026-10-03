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

Przy starcie tworzą się tabele, a jeśli `Persona` jest pusta, ładuje się seed: 3 wygenerowane persony (`p01`–`p03`) po 150 dni, każda z innym wzorcem złych dni.

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

## API

Brak auth: persona to `user_id` w ścieżce. Szczegóły i przykłady w Swaggerze (`/docs`).

| Metoda | Ścieżka | Ekran |
| ------ | ------- | ----- |
| GET | `/api/users` | przełącznik persony |
| GET | `/api/users/{user_id}` | persona |
| GET | `/api/users/{user_id}/days?from=&to=` | kalendarz samopoczucia |
| GET | `/api/users/{user_id}/days/{date}` | widok dnia |
| GET | `/api/users/{user_id}/patterns` | wzorce złych dni |
| GET | `/api/users/{user_id}/recipe` | przepis na dobry dzień |
| GET | `/api/users/{user_id}/surveys/{date}` | czy ankieta wypełniona (404 jeśli nie) |
| PUT | `/api/users/{user_id}/surveys/{date}` | zapis ankiety, zwraca etykietę dnia |

## Analiza (zespół od algorytmów)

Cała logika liczenia jest w `app/analysis.py`. Serwisy wołają tylko te funkcje, więc wystarczy
podmienić ich środek bez zmiany sygnatur:

| Funkcja | Zwraca |
| ------- | ------ |
| `score_day(day)` | wynik dnia z ankiety albo `None` |
| `label_day(day)` | `"good"` / `"neutral"` / `"bad"` albo `None` |
| `personal_norm(days)` | `dict[cecha, NormRange]` z dobrych dni |
| `day_deviations(days, date)` | `list[Deviation]` posortowana od największego odchylenia |
| `explain_day(days, date)` | zdanie podsumowania dnia |
| `bad_day_patterns(days)` | `PatternReport` |
| `good_day_recipe(days)` | `Recipe` |

`days` to wszystkie dni jednej persony (`app.models.Day`) posortowane po dacie. Typy wyników są
w `app/schemas.py` i trafiają 1:1 do JSON-a. Lista cech i ich jednostek: `FEATURES` w `analysis.py`.

Obecna implementacja to prosty stub (kwartyle z dobrych dni), żeby frontend miał realistyczne dane.

## Import danych

CSV, jeden wiersz = jeden dzień jednej persony. Kolumny: `user_id, date, sleep_minutes,
resting_hr, steps, active_minutes, calories, mood, fatigue, sleep_quality, stress`
(puste komórki dozwolone, istniejące dni są nadpisywane):

```bash
uv run python -m scripts.import_days data/days.csv
```

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
