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
| 1 | p06 | Alex | 2020-03-08 | **Sen**: dłuższy sen daje dobre dni (przepis); wzorce złych dni (sen < 6 h, późne zasypianie, wybudzenia) są słabsze i nie dają „possible reason” | 4, 3, 3, 4 |
| 2 | p01 | Robin | 2020-03-06 | **Wysiłek**: dzień po ciężkim treningu jest gorszy; brak przepisu (tylko 3 dobre dni) | 3, 2, 2, 3 |
| 3 | p10 | Sam | 2020-02-14 | **Niespokojne noce + lekki ruch**: wzorce w obie strony, najlepsza do pokazania | 3, 1, 2, 2 |
| 4 | p16 | Kim (zapas) | 2020-02-27 | **Nocny marek**: krótki sen i bardzo późne zasypianie | 3, 2, 3, 2 |

**Odpowiedzi trzeba wpisać dokładnie**, najlepiej przyciskiem z `demo_answers`. Etykieta liczy się
z mood, fatigue i stress, a `sleep_quality` nie ma na nią wpływu. Odporność na pomyłkę:

| Persona | Odporność |
| --- | --- |
| Kim | dowolny suwak ±1 nadal daje zły dzień |
| Robin | wyraźny margines od progu |
| Sam, Alex | tylko dokładne odpowiedzi. U Sama mood, fatigue albo stress o 1 wyżej daje dzień neutralny („Typical day for you”) |

Ostrzeżenie na ekranie Today nie zmienia się po wypełnieniu ankiety, bo jest liczone z danych sprzed
niej.

## Scenariusz (ok. 6 min)

**1. Problem (slajd).** Zegarek pokazuje liczby, nikt nie mówi, dlaczego czujesz się źle.

**2. Przełącznik person → Sam (p10).** „Prawdziwa osoba z badania PMData: ponad 3 miesiące
danych z zegarka i codziennych ankiet.” (102 dni w kalendarzu, 66 pełnych dni z ankietą i
zegarkiem.)

**3. Ekran Today, jeszcze przed ankietą** (`GET /users/p10/today`):

> Tougher day possible
> **Heads-up:** awake 12.5% of night
> *Awake over 12% of night: 15 of 27 days bad*

Punkt do omówienia: aplikacja wie to rano, z samego zegarka, bo to wzorzec tej konkretnej osoby.

**4. Ankieta na żywo:** mood 3, fatigue 1, sleep quality 2, stress 2 (`PUT /users/p10/surveys/2020-02-14`).
Wynik: `label = bad`, a Today pokazuje:

> Possible reason: awake 12.5% of night

**5. Widok dnia** (`GET /users/p10/days/2020-02-14`):
- „Possible reason” (z istotnego wzorca),
- porównanie ze średnim dobrym dniem: *Sleep HR +15 bpm vs good days*, *Sleep -2h55 vs good days*,
- wartości na tle zakresu dobrych dni (`features[].norm`).

**6. Kalendarz, grudzień 2019** (`GET /users/p10/days?from=2019-12-01&to=2019-12-31`): kolorowe dni,
13 z nich ma „possible reason” (najwięcej ze wszystkich miesięcy).

**7. Wzorce i przepis:**
- `/patterns` (3): *Awake over 12% of night: 15 of 27 days bad*, *Under 7h sleep: 11 of 20 days bad*,
  *REM under 18%: 6 of 10 days bad*
- `/recipe` (3): *Over 5h20 light activity (day before): 13 of 16 days good*, *Over 7h30 sleep: 20
  of 32 days good*, *Sleep HR under 68 bpm: 13 of 18 days good*

Liczba wzorców na liście (złe dni / przepis): Sam 3 / 3, Kim 3 / 3, Alex 3 / 2, Robin 3 / 0.

**8. Personalizacja → Robin (p01).** Today: *Heads-up: 1h20 hard exercise (day before)*. Inna osoba, inna przyczyna. Przepis jest pusty („Not enough good days yet”), co pokazuje, że
aplikacja nie zmyśla.

**9. Alex (p06), dobry dzień.** Today: *Good sign: 7h23 sleep*. Przepis: *Over 6h30 sleep*. Wzorce złych dni (*Under 6h sleep*, *Asleep after 00:30*, *Awake over 12% of night*) są na liście, ale słabsze (`preliminary` / `exploratory`), więc w kalendarzu nie dają „possible reason”.

**10. Wiarygodność (slajd).**
- Na losowych etykietach ~5% fałszywych alarmów.
- Sztucznie wstrzyknięty efekt znaleziony z poprawnym progiem.
- Wzorce trzymają się bez weekendów.
- „Possible reason” tylko z istotnych wzorców, w pozostałe dni uczciwe *No clear reason*.

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
- **Kim (p16) po ankiecie na żywo**: trzeci wzorzec złych dni (czuwanie > 13% nocy) zmienia się ze
  słabszego na istotny, bo nowy dzień przesuwa go poniżej p = 0,05. Lista ma nadal 3 pozycje, ale
  zmieniają się liczby w tekście. U pozostałych person wzorce po ankiecie zostają takie same.
- **Kim (p16)** zasypia rano (*Heads-up: asleep at 09:41*). Opowiadać jako „nocny marek”
  albo pominąć.
- **Robin (p01) ma 3 dobre dni**: porównania idą do średniego dnia (`norm_reference = all_days`),
  a `leans` jest zawsze `null`. Na ekranie porównań i w kalendarzu lepiej pokazywać Sama.
- **Teksty frontendu:** wzorce `significant`, `preliminary` i `exploratory` wyświetlamy tak samo; `status != ok` to
  stany puste z gotowym zdaniem w `summary`.
- **Pierwsze zapytanie po starcie** liczy analizy (~0,4 s), potem odpowiedzi są z cache.
