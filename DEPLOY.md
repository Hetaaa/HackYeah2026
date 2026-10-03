# Deploy krok po kroku (za darmo)

Backend (FastAPI + SQLite) na **Render**, frontend (React + Vite) na **Vercel**. Oba w darmowych
planach, bez karty. Całość zajmuje ok. 20–30 minut.

```text
przeglądarka ──► Vercel (frontend, https://<projekt>.vercel.app)
                   │  /api/*  (przekierowanie w frontend/vercel.json)
                   ▼
                 Render (backend, https://whytoday-api.onrender.com/api)
```

Frontend woła względne ścieżki `/api/...`, tak jak lokalnie. Vercel przekazuje je do Render, więc
nie trzeba ustawiać adresu API we froncie ani walczyć z CORS.

Warunki darmowych planów (limity, usypianie) mogą się zmieniać. Sprawdź je przy zakładaniu kont.

## Krok 0. Przed startem

1. Wszystko, co ma być na produkcji, jest wypchnięte na `main` w GitHubie
   (`Hetaaa/HackYeah2026`). Oba serwisy budują się z `main`.
2. Lokalnie działa:
   ```bash
   cd backend && uv run pytest -q          # testy przechodzą
   cd ../frontend && npm ci && npm run build   # frontend się buduje
   ```
3. Frontend woła API ścieżkami względnymi, np. `fetch('/api/users')`, a nie
   `http://localhost:8000/...`. Pełny adres zadziała tylko lokalnie.

## Krok 1. Backend na Render

### 1.1 Konto

1. Wejdź na <https://render.com> i kliknij **Get Started**.
2. Zaloguj się przez **GitHub**. Najprościej kontem, które ma dostęp do repo `Hetaaa/HackYeah2026`.
3. Gdy Render zapyta o dostęp do repozytoriów, zaznacz `HackYeah2026` (albo wszystkie).

### 1.2 Utworzenie serwisu z Blueprintu (zalecane)

W repo jest gotowa konfiguracja: [render.yaml](render.yaml).

1. W panelu Render: **New +** → **Blueprint**.
2. Wybierz repo `HackYeah2026` i kliknij **Connect**.
3. Render pokaże serwis `whytoday-api` (Docker, plan Free, region Frankfurt).
4. Zapyta o wartość `CORS_ORIGINS`. Adresu frontendu jeszcze nie znasz, więc wpisz na razie
   `http://localhost:5173`. Poprawisz to w kroku 3.
5. Kliknij **Apply**. Pierwszy build trwa ok. 3–6 minut.

Jeśli nazwa `whytoday-api` jest zajęta, Render doda do adresu losową końcówkę (np.
`whytoday-api-x1y2.onrender.com`). Zapisz **dokładny adres** z panelu, bo będzie potrzebny w
kroku 2.

### 1.2b Alternatywa: ręcznie, bez Blueprintu

Gdyby Blueprint nie zadziałał:

1. **New +** → **Web Service** → wybierz repo `HackYeah2026`.
2. Ustaw:

   | Pole | Wartość |
   | --- | --- |
   | Name | `whytoday-api` |
   | Region | Frankfurt (EU Central) |
   | Branch | `main` |
   | Root Directory | `backend` |
   | Runtime / Language | **Docker** |
   | Instance Type | **Free** |

3. **Advanced** → **Environment Variables**:
   - `DEMO_RESET` = `true`
   - `CORS_ORIGINS` = `http://localhost:5173` (na razie)
4. **Advanced** → **Health Check Path**: `/api/health`.
5. **Create Web Service**.

### 1.3 Sprawdzenie backendu

Gdy w panelu pojawi się status **Live**, sprawdź (podmień adres na swój):

```bash
API=https://whytoday-api.onrender.com/api
curl $API/health                 # {"status":"ok"}
curl $API/users                  # 4 persony: Alex, Robin, Sam, Kim
curl $API/users/p10/today        # "outlook": "tough", heads-up o nocy
```

Swagger jest pod `https://whytoday-api.onrender.com/docs`.

Baza tworzy się i wypełnia danymi demo sama przy starcie. Nic nie trzeba uruchamiać ręcznie.

## Krok 2. Adres backendu we frontendzie

1. Otwórz [frontend/vercel.json](frontend/vercel.json).
2. W `destination` wpisz dokładny adres z Render, jeśli różni się od
   `https://whytoday-api.onrender.com`:
   ```json
   { "source": "/api/:path*", "destination": "https://TWOJ-ADRES.onrender.com/api/:path*" }
   ```
3. Druga reguła (`/(.*)` → `/index.html`) zostaje bez zmian. Dzięki niej odświeżenie strony na
   podstronie (np. `/calendar`) nie daje 404, bo aplikacja używa React Router.
4. Commit i push na `main`.

## Krok 3. Frontend na Vercel

### 3.1 Konto i projekt

1. Wejdź na <https://vercel.com> i kliknij **Sign Up**. Wybierz plan **Hobby** (darmowy) i zaloguj
   się przez **GitHub**.
2. **Add New…** → **Project** → przy `HackYeah2026` kliknij **Import**. Jeśli repo nie widać:
   **Adjust GitHub App Permissions** i dodaj dostęp do repo.
3. Ustaw:

   | Pole | Wartość |
   | --- | --- |
   | Framework Preset | **Vite** (wykrywa się sam) |
   | Root Directory | `frontend` (kliknij **Edit** i wybierz katalog) |
   | Build Command | `npm run build` (domyślne) |
   | Output Directory | `dist` (domyślne) |
   | Environment Variables | brak |

4. **Deploy**. Build trwa ok. 1 minutę. Dostaniesz adres typu `https://hack-yeah-2026.vercel.app`.

### 3.2 Uzupełnienie CORS w backendzie

Przy przekierowaniu przez Vercel CORS nie jest potrzebny, ale ustaw prawdziwy adres dla porządku
(i na wypadek, gdyby ktoś wołał API bezpośrednio):

1. Render → serwis `whytoday-api` → **Environment**.
2. `CORS_ORIGINS` = `https://hack-yeah-2026.vercel.app` (twój adres z Vercel, bez `/` na końcu).
   Kilka adresów oddziel przecinkami.
3. **Save Changes**. Render sam zrobi redeploy.

## Krok 4. Sprawdzenie całości

1. Otwórz adres z Vercel. Aplikacja się ładuje.
2. W przeglądarce otwórz `https://<twój-projekt>.vercel.app/api/users`. Powinien pokazać się
   JSON z 4 personami. Jeśli tak, przekierowanie do backendu działa.
3. W aplikacji: przełącz personę na Sama, otwórz ekran główny, wypełnij ankietę (przycisk
   „wypełnij jak Sam”), sprawdź kalendarz i wzorce.
4. Po teście wyczyść ankiety wpisane na żywo:
   ```bash
   curl -X POST https://<twój-projekt>.vercel.app/api/demo/reset    # {"personas":4,"days":477}
   ```

## Krok 5. Aktualizacje

Każdy push na `main` sam przebudowuje oba serwisy: Render backend, Vercel frontend. Vercel
dodatkowo robi podgląd (preview) dla każdego innego brancha i PR.

Po zmianie schematu bazy nic nie trzeba robić: przy każdym starcie na Render baza jest tworzona od
nowa z danymi demo.

## Krok 6. Przed prezentacją i oceną

- **Obudź backend 2–3 minuty wcześniej.** Darmowy Render usypia serwis po ok. 15 minutach bez
  ruchu, a pierwsze zapytanie po uśpieniu trwa ok. 30–60 s. Otwórz `.../api/health` i poczekaj na
  `{"status":"ok"}`.
- Na czas oceny możesz ustawić darmowy ping (np. <https://cron-job.org>): `GET .../api/health` co 10
  minut. Wtedy serwis nie zaśnie.
- Zrób `POST /api/demo/reset`, żeby persony miały puste dzisiejsze ankiety.
- **Na scenie uruchom aplikację lokalnie**, a link publiczny daj jurorom. Lokalnie nie ma usypiania
  ani ryzyka słabego Wi-Fi na sali:
  ```bash
  cd backend && uv run python -m scripts.reset_db && DEMO_RESET=true uv run uvicorn app.main:app
  cd frontend && npm run dev     # http://localhost:5173
  ```

## Gdy coś nie działa

| Objaw | Przyczyna | Rozwiązanie |
| --- | --- | --- |
| Pierwsze wejście ładuje się ok. 1 minutę | Render obudził uśpiony serwis | normalne w darmowym planie, patrz krok 6 |
| `/api/...` na Vercel zwraca 404 albo HTML | zły adres w `frontend/vercel.json` albo backend nie działa | porównaj adres z panelem Render, sprawdź `.../api/health` bezpośrednio na Render |
| Odświeżenie podstrony daje 404 | brak reguły `/(.*)` → `/index.html` | przywróć ją w `frontend/vercel.json` |
| Frontend działa lokalnie, a na Vercel nie widzi danych | kod woła `http://localhost:8000/...` | zmień na ścieżki względne `/api/...` |
| Błąd CORS w konsoli | frontend woła Render bezpośrednio, a nie przez `/api` | używaj `/api/...` albo dopisz adres Vercel do `CORS_ORIGINS` |
| Build Render: błąd w `uv sync --frozen` | `uv.lock` nieaktualny względem `pyproject.toml` | lokalnie `cd backend && uv lock`, commit, push |
| Build Vercel: błąd wersji Node | Vite wymaga nowszego Node | Vercel → Settings → General → Node.js Version: 22.x |
| Persony mają wpisane ankiety z poprzedniego testu | baza żyje do restartu serwisu | `POST /api/demo/reset` |
| `POST /api/demo/reset` zwraca 403 | brak `DEMO_RESET=true` | dodaj zmienną w Render → Environment |

## Ograniczenia publicznego demo

- **Dane nie są trwałe.** SQLite leży na dysku, który znika przy restarcie i redeployu. Nowi
  użytkownicy i ankiety znikają, a persony demo wracają do stanu startowego. Do demo to wystarcza.
  Trwałe dane wymagają płatnego dysku albo bazy Postgres (`DATABASE_URL`).
- **Brak logowania.** Każdy z linkiem może wypełnić ankietę za personę, dodać użytkownika albo
  zresetować demo. Persony demo nie da się usunąć (403). Nie wpisuj prawdziwych danych osobowych.
- **Jedna instancja.** Nie zwiększaj liczby instancji. Seed przy starcie zakłada jeden proces.
