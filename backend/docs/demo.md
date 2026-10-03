# Demo „Why Today” – przygotowanie i scenariusz

Dla prowadzących prezentację i dla frontendu. Wszystkie teksty poniżej to prawdziwe odpowiedzi API
na danych demo.

## Uruchomienie

```bash
cd backend
uv sync
uv run python -m scripts.reset_db        # baza od nowa: 4 persony z PMData (data/demo/*.csv)
DEMO_RESET=true uv run uvicorn app.main:app   # API: http://localhost:8000/api, Swagger: /docs
```

`reset_db` jest wymagany po pobraniu zmian. Stara `app.db` nie ma nowych kolumn (`create_all`
ich nie dodaje), więc endpointy person zwracają **500** (`no such column persona.demo_today`).

**Między przebiegami prezentacji** cofnij ankiety wpisane na żywo:

```bash
curl -X POST http://localhost:8000/api/demo/reset    # {"personas": 4, "days": 477}
```

Reset działa tylko z `DEMO_RESET=true` (inaczej 403), więc publiczny deploy nie da się wyczyścić z
zewnątrz. Przywraca wyłącznie persony demo, innych użytkowników nie rusza.

## Zegar demo

Persony to nagrane dane z PMData (listopad 2019 – marzec 2020). Każda ma własne **„dziś”**
(`PersonaRead.today`):

- dane kończą się na tym dniu,
- ankieta z „dziś” jest pusta, żeby wypełnić ją na żywo,
- prawdziwe odpowiedzi tej osoby z tego dnia są w `demo_answers` (frontend powinien dać przycisk
  „wypełnij jak Sam” albo ustawić suwaki),
- ankieta na późniejszą datę zwraca 422.

Frontend powinien traktować `today` z persony jako bieżącą datę: ekran Today, otwarty miesiąc
kalendarza, data ankiety.

## Persony

| Kolejność | id | Imię | „Dziś” | Historia | Odpowiedzi demo (mood, fatigue, sleep q., stress) |
| --- | --- | --- | --- | --- | --- |
| 1 | p06 | Alex | 2020-03-08 | **Sen**: dłuższy sen daje dobre dni (przepis); wzorzec złych dni to tylko wczesny sygnał | 4, 3, 3, 4 |
| 2 | p01 | Robin | 2020-03-06 | **Wysiłek**: dzień po ciężkim treningu jest gorszy; brak przepisu (tylko 3 dobre dni) | 3, 2, 2, 3 |
| 3 | p10 | Sam | 2020-02-14 | **Niespokojne noce + lekki ruch**: wzorce w obie strony, najlepsza do pokazania | 3, 1, 2, 2 |
| 4 | p16 | Kim (zapas) | 2020-02-27 | **Nocny marek**: krótki sen i bardzo późne zasypianie | 3, 2, 3, 2 |

**Odpowiedzi trzeba wpisać dokładnie**, najlepiej przyciskiem z `demo_answers`. Etykieta liczy się
z mood, fatigue i stress, a `sleep_quality` nie ma na nią wpływu. Odporność na pomyłkę:

| Persona | Odporność |
| --- | --- |
| Kim | dowolny suwak ±1 nadal daje zły dzień |
| Robin | wyraźny margines od progu |
| Sam, Alex | tylko dokładne odpowiedzi. U Sama mood, fatigue albo stress o 1 wyżej daje dzień neutralny („Check-in saved: a typical day for you.”) |

Ostrzeżenie na ekranie Today nie zmienia się po wypełnieniu ankiety, bo jest liczone z danych sprzed
niej.

## Scenariusz (ok. 6 min)

**1. Problem (slajd).** Zegarek pokazuje liczby, nikt nie mówi, dlaczego czujesz się źle.

**2. Przełącznik person → Sam (p10).** „Prawdziwa osoba z badania PMData: ponad 3 miesiące
danych z zegarka i codziennych ankiet.” (102 dni w kalendarzu, 66 pełnych dni z ankietą i
zegarkiem.)

**3. Ekran Today, jeszcze przed ankietą** (`GET /users/p10/today`):

> Today may be tougher than usual. Check in to see how you feel.
> **Heads-up:** you were awake 12.5% of last night.
> *When you are awake over 12% of the night, 15 of 27 days were bad days (vs 13% otherwise).*

Punkt do omówienia: aplikacja wie to rano, z samego zegarka, bo to wzorzec tej konkretnej osoby.

**4. Ankieta na żywo:** mood 3, fatigue 1, sleep quality 2, stress 2 (`PUT /users/p10/surveys/2020-02-14`).
Wynik: `label = bad`, a Today pokazuje:

> Possible reason: you were awake 12.5% of last night.

**5. Widok dnia** (`GET /users/p10/days/2020-02-14`):
- „Possible reason” (z istotnego wzorca),
- „Compared with your average good day”: *Your heart rate during sleep was 15 bpm higher… You slept
  2 h 55 min less…*,
- wartości na tle zakresu dobrych dni (`features[].norm`).

**6. Kalendarz, grudzień 2019** (`GET /users/p10/days?from=2019-12-01&to=2019-12-31`): kolorowe dni,
13 z nich ma „possible reason” (najwięcej ze wszystkich miesięcy).

**7. Wzorce i przepis:**
- `/patterns`: *When you are awake over 12% of the night, 15 of 27 days were bad days (vs 13% otherwise).*
- `/recipe`: *When you get over 320 min of light activity the day before, 13 of 16 days were good days
  (vs 38% otherwise).*

**8. Personalizacja → Robin (p01).** Today: *Heads-up: you spent 80 min in high heart-rate zones the day
before.* Inna osoba, inna przyczyna. Przepis jest pusty („Not enough good days yet…”), co pokazuje, że
aplikacja nie zmyśla.

**9. Alex (p06), dobry dzień.** Today: *Good sign: you slept 7 h 23 min last night.* Przepis: sen
powyżej 6 h 30 min. Wzorzec złych dni to tylko „Early signal”, bo nie przeszedł testu istotności.

**10. Wiarygodność (slajd).**
- Na losowych etykietach ~5% fałszywych alarmów.
- Sztucznie wstrzyknięty efekt znaleziony z poprawnym progiem.
- Wzorce trzymają się bez weekendów.
- „Possible reason” tylko z istotnych wzorców, w pozostałe dni uczciwe *No clear pattern explains
  this day.*

## Ekrany → endpointy

| Ekran | Endpoint | Kluczowe pola |
| --- | --- | --- |
| Przełącznik person | `GET /api/users` | `name`, `description`, `today`, `demo_answers`, `insights_status` |
| Today (home) | `GET /api/users/{id}/today` | `outlook`, `summary`, `heads_up[]`, `good_signs[]`, `survey` |
| Ankieta | `PUT /api/users/{id}/surveys/{today}` | zwraca `label`, `score` |
| Kalendarz | `GET /api/users/{id}/days?from=&to=` | `label`, `has_reason`, `headline`, `top_deviations` (`leans`: bad = czerwony, good = zielony, null = neutralny) |
| Widok dnia | `GET /api/users/{id}/days/{date}` | `summary`, `reasons[]`, `deviations[]`, `features[]` (`display`, `norm`), `timeline[]` (D-3..D, `highlight`) |
| Onboarding | `POST /api/users` | zwraca nowego użytkownika (`insights_status = insufficient_days`) |
| Wzorce złych dni | `GET /api/users/{id}/patterns` | `status`, `summary`, `patterns[]` (`text`, `level`, `rate_in`, `rate_out`) |
| Wykres wzorca | `GET /api/users/{id}/patterns/{feature}?kind=` | `points[]` (`value`, `label`, `in_condition`), `threshold`, `op` |
| Legenda / opisy cech | `GET /api/features` | `label`, `unit`, `description`, `tested_direction` |
| Przepis | `GET /api/users/{id}/recipe` | `status`, `summary`, `ingredients[]` |
| Tabela dobre vs złe dni | `GET /api/users/{id}/stats` | `features[]` (`good`, `bad`: `average`, `display`, `days`), `analysed_days`, `date_from`, `date_to` |
| Reset demo | `POST /api/demo/reset` | |

## Na co uważać

- **Daty 2019/2020** to zegar demo. Na scenie warto powiedzieć: „nagrane dane prawdziwych osób”.
- **Kim (p16)** zasypia rano (*you fell asleep at 09:41 last night*). Opowiadać jako „nocny marek”
  albo pominąć.
- **Robin (p01) ma 3 dobre dni**: porównania idą do średniego dnia (`norm_reference = all_days`),
  a `leans` jest zawsze `null`. Na ekranie porównań i w kalendarzu lepiej pokazywać Sama.
- **Teksty frontendu:** `level = preliminary` oznaczać jako „early signal”; `status != ok` to
  stany puste z gotowym zdaniem w `summary`.
- **Pierwsze zapytanie po starcie** liczy analizy (~0,4 s), potem odpowiedzi są z cache.
