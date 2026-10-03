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

Przy starcie tworzą się tabele, a jeśli `Persona` jest pusta, ładuje się seed: 4 persony z PMData (`data/demo/`), a bez tych plików 3 wygenerowane persony (`p01`–`p03`).

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

Ścieżki i kształty odpowiedzi są stabilne; algorytm tylko dodał pola (np. `reasons`, `status`,
`has_reason`, `headline`, `insights_status`). Szczegóły i przykłady w Swaggerze.

## Analiza (zespół od algorytmów)

Algorytm jest w pakiecie `app/insights/` (pandas/numpy), a `app/analysis.py` to adapter: zamienia
wiersze `Day` jednej persony na wejście algorytmu i mapuje wynik na schematy API. Serwisy wołają
`analyze(days, window_end)` raz na zapytanie (ok. 0,1 s, wynik w cache do zmiany danych) i czytają
z wyniku funkcjami:

| Funkcja | Zwraca |
| ------- | ------ |
| `analyze(days, window_end)` | pełna analiza persony (cache) |
| `label_day(analysis, date)` / `score_day(...)` | etykieta / osobisty z-score dnia |
| `day_summary(analysis, date)` | `DaySummary` (kafelek kalendarza) |
| `day_detail(analysis, day, survey)` | `DayDetail` (widok dnia: przyczyny, porównanie, cechy) |
| `bad_day_patterns(analysis)` | `PatternReport` |
| `good_day_recipe(analysis)` | `Recipe` |
| `insights_status(analysis)` | `ok` albo powód, dla którego wzorców jeszcze nie ma |

Najważniejsze zasady (szczegóły i uzasadnienie: [docs/insights.md](docs/insights.md)):

- **Etykieta dnia jest osobista**: mood + fatigue + stress względem mediany danej osoby
  (`sleep_quality` zbieramy, ale nie wchodzi do etykiety). Przy < 14 ankietach: próg 3,5 / 2,5.
- **Wzorce** to progi typu „sen < 6 h → 11 z 14 dni złych” z testem permutacyjnym (p ≤ 0,05).
  Wymagają 60 dni z ankietą i danymi z zegarka; wcześniej `status = insufficient_days`.
- **„Possible reason”** w widoku dnia pojawia się tylko z istotnego wzorca. Pole `deviations`
  to opisowe porównanie z przeciętnym dobrym dniem, nie przyczyna.
- Dane dnia `D`: noc zakończona rano `D` + aktywność z kalendarzowego dnia `D`. Algorytm sam
  bierze aktywność z dnia przed ankietą.

## Dane demo i import

Seed ładuje prawdziwe persony z PMData z `data/demo/*.csv` (p06 Alex, p01 Robin, p10 Sam,
p16 Kim); bez tych plików generuje 3 syntetyczne persony. CSV powstaje z surowego PMData
(spoza repo) tym samym adapterem Fitbita, którego użyje synchronizacja zegarka:

```bash
uv run python -m scripts.import_pmdata ../../pmdata          # -> data/demo/*.csv
uv run python -m scripts.reset_db                            # baza od nowa z nowymi CSV
```

Własny CSV (jeden wiersz = jeden dzień; kolumny `user_id, date` + dowolne pola `Day`, puste
komórki dozwolone, istniejące dni są nadpisywane):

```bash
uv run python -m scripts.import_days data/days.csv [data/personas.csv]
```

Test regresji na pełnym PMData (pomijany w CI): `PMDATA_DIR=../../pmdata uv run pytest`.

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
