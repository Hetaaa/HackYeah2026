# Integracja frontendu z backendem

Przewodnik dla frontendu: który endpoint podpiąć pod który ekran i na co uważać. Pełne schematy
pól i przykłady są w Swaggerze (`http://localhost:8000/docs`). Wszystkie przykłady poniżej to
prawdziwe odpowiedzi API dla persony Sam (`p10`).

## Start

```bash
cd backend
uv sync
uv run python -m scripts.reset_db              # baza od nowa z 4 personami demo
DEMO_RESET=true uv run uvicorn app.main:app    # API na :8000
```

```bash
cd frontend
npm install && npm run dev                     # Vite na :5173
```

Vite przekierowuje `/api` na `localhost:8000` (`vite.config.js`). W kodzie wołamy więc ścieżki
względne, np. `fetch('/api/users')`, bez CORS i bez pełnego adresu.

Po każdym `git pull` z backendu uruchom `reset_db`. Stara `app.db` nie ma nowych kolumn i endpointy
person zwracają 500.

## Zasady wspólne dla wszystkich ekranów

**1. Użytkownik = persona.** Nie ma logowania. Wybrany użytkownik to `id` z `GET /api/users`,
wstawiany w ścieżkę: `/api/users/{id}/...`.

**2. „Dziś” bierzemy z persony, nie z zegara przeglądarki.** Persony demo to nagrane dane z
2019/2020 i każda ma własne `today` (np. Sam: `2020-02-14`). Ekran główny, data ankiety i
otwarty miesiąc kalendarza używają `persona.today`. Dla nowych użytkowników `today` to prawdziwa
data, więc kod jest ten sam.

**3. Tekst do wyświetlenia jest gotowy.** Pola `display`, `text`, `summary`, `headline`,
`condition` mają sformatowane wartości („4h53”, „02:24”, „12.5%”). Nie formatuj `value`
samodzielnie. `value` służy do wykresów i porównań.

**4. Jednostki (`unit`):** `h`, `clock`, `%`, `bpm`, `steps`, `min`, `pts`. `clock` (pora
zaśnięcia) to godziny od 18:00 poprzedniego dnia (6.33 = 00:20). Na wykresie oś działa poprawnie,
ale etykiety bierz z `display`.

**5. Kolory lepiej / gorzej: pole `leans`.** Wartość odbiega od średniego dobrego dnia w stronę:

| `leans` | Znaczenie | Kolor |
| --- | --- | --- |
| `"bad"` | złych dni tej osoby | czerwony |
| `"good"` | dobrych dni tej osoby | zielony |
| `null` | brak danych albo dobre i złe dni się nie różnią | neutralny |

Kierunek pochodzi z danych tej osoby. Nie zakładaj na froncie, że „więcej snu = lepiej”.

**6. Statusy zamiast pustych ekranów.** `/patterns` i `/recipe` mają `status` i gotowe zdanie w
`summary`. Gdy `status != "ok"`, pokazujemy `summary` jako stan pusty.

| `status` | Kiedy | Co pokazać |
| --- | --- | --- |
| `ok` | są istotne wzorce | listę |
| `preliminary` | tylko wczesne sygnały | listę z etykietą „Early signal” |
| `insufficient_days` | nowy użytkownik | `summary` + pasek postępu `days_with_data / days_needed` z persony |
| `insufficient_bad_days` / `insufficient_good_days` | za mało złych / dobrych dni | `summary` |
| `not_enough_evidence` | dane są, wzorca brak | `summary` |
| `insufficient_variation` | ankiety prawie zawsze takie same | `summary` |

**7. Poziom wzorca:** `level = "significant"` to „Strong pattern”, a `"preliminary"` to „Early
signal”. Nie pokazujemy `p_value`.

**8. Po zapisaniu ankiety odśwież dane.** Algorytm liczy wszystko od nowa (wynik jest w cache po
stronie backendu, więc to szybkie). Po `PUT /surveys` pobierz ponownie: `today`, dzień w
kalendarzu, `/patterns`, `/recipe`, `/stats`.

## Ekran 1 (główny)

### Przełącznik użytkownika

`GET /api/users` zwraca listę person w kolejności do pokazania.

| Pole | Do czego |
| --- | --- |
| `id`, `name`, `description` | lista |
| `today` | „bieżąca” data, patrz zasada 2 |
| `is_demo` | persony demo nie da się usunąć |
| `demo_answers` | prawdziwe odpowiedzi z dziś, do przycisku „wypełnij” (patrz ankieta) |
| `insights_status`, `days_with_data`, `days_needed` | pasek postępu dla nowych użytkowników |
| `norm_reference` | `"all_days"`: porównania idą do średniego dnia, nie dobrego (patrz pułapki) |

### Najważniejsze bad patterns

`GET /api/users/{id}/patterns`

```json
{
  "status": "ok",
  "summary": "1 possible reason for bad days",
  "bad_days_count": 20,
  "patterns": [{
    "feature": "wake_pct", "label": "Awake at night", "condition": "Awake over 12% of night",
    "level": "significant", "when": "last_night",
    "days_in_condition": 27, "target_days_in_condition": 15,
    "rate_in": 0.5556, "rate_out": 0.1282,
    "text": "Awake over 12% of night: 15 of 27 days bad",
    "example_dates": ["2020-01-29", "2020-02-03", "..."]
  }]
}
```

Na karcie wystarczą `label`, `condition` i porównanie `rate_in` z `rate_out`. Pełne zdanie (`text`)
i liczby dni dajemy w szczegółach na ekranie 2. Maksymalnie 3 wzorce, posortowane od
najsilniejszego.

### Good day recipe

`GET /api/users/{id}/recipe` ma ten sam układ co `/patterns`, tylko z `ingredients[]` zamiast
`patterns[]` i `good_days_count`. `rate_in` to odsetek dobrych dni, gdy warunek był spełniony.

### Popup ankiety wellness

- Sprawdzenie, czy już wypełniona: `GET /api/users/{id}/surveys/{today}` (404 = jeszcze nie).
- Zapis: `PUT /api/users/{id}/surveys/{today}` z ciałem
  `{"mood": 3, "fatigue": 1, "sleep_quality": 2, "stress": 2}`.

Wszystkie pola są wymagane i przyjmują liczby całkowite 1–5. **Każda skala to „wyżej = lepiej”**:

| Pole | 1 | 5 |
| --- | --- | --- |
| `mood` | bardzo zły nastrój | bardzo dobry |
| `fatigue` | bardzo zmęczony | wypoczęty |
| `sleep_quality` | bardzo zły sen | bardzo dobry |
| `stress` | bardzo zestresowany | zrelaksowany |

Uwaga na `fatigue` i `stress`: suwak „zmęczenie 5” nie znaczy „bardzo zmęczony”. Etykiety skrajne
na suwakach muszą to jasno mówić.

Odpowiedź zawiera `label` (`good` / `neutral` / `bad`) i `score`, więc od razu możemy pokazać
„Typical day for you” albo „Possible reason: …”. Ten sam `PUT` służy do poprawienia ankiety. Data późniejsza niż `today`
zwraca 422.

**Demo:** przycisk „Fill in as Sam”, który ustawia suwaki na `persona.demo_answers`. Na scenie
odpowiedzi trzeba wpisać dokładnie, bo o 1 wyżej daje u Sama dzień neutralny.

### Wczorajsze statystyki vs average good day

Najprościej użyć `GET /api/users/{id}/today`, który ma wszystko dla ekranu głównego. Alternatywa to
`GET /api/users/{id}/days/{today}` (te same `features` i `deviations`). Dla nowego użytkownika bez
danych z dziś zwraca 404.

**Dzień D = poranek D:** ostatnia noc (zakończona rano) i aktywność z wczoraj. Dlatego statystyki
„wczorajsze” pobieramy dla daty `today`, nie `today - 1`. Pole `when` mówi, czego dotyczy wartość
(`last_night` / `day_before`).

Pola `today`:

| Pole | Do czego |
| --- | --- |
| `outlook` + `summary` | nagłówek: `tough` / `promising` / `mixed` / `neutral` / `unknown` + zdanie |
| `heads_up[]` | ostrzeżenia z wzorców złych dni (`text`, np. „Heads-up: awake 12.5% of night”), w szczegółach `pattern_text` |
| `good_signs[]` | to samo dla przepisu („Good sign: …”) |
| `deviations[]` | do 2 największych różnic od średniego dobrego dnia, gotowe `text` + `leans` |
| `features[]` | wszystkie cechy: `display` (dziś), `norm.average` (średni dobry dzień), `leans`, `in_patterns` |
| `survey` | `null` przed ankietą, potem odpowiedzi z `label` |

Pole `features[]` daje tabelę „dziś vs średni dobry dzień”:

```json
{"feature": "sleep_h", "label": "Sleep", "unit": "h", "when": "last_night",
 "value": 4.883, "display": "4h53",
 "norm": {"average": 7.793, "median": 7.667, "low": 7.171, "high": 8.146},
 "in_patterns": true, "leans": "bad"}
```

- `norm.average` to średni dobry dzień. `norm.low`–`norm.high` to typowy zakres dobrych dni
  (25.–75. percentyl), dobry na pasek z zaznaczoną dzisiejszą wartością.
- Wartość referencyjna nie ma pola `display`. Dla `h` i `clock` sformatuj ją tak jak `display` albo
  pokaż różnicę z `deviations[].text`.
- `value`, `display`, `norm` i `leans` mogą być `null` (brak danych z zegarka, np. noc bez faz
  snu albo nowy użytkownik, który dostaje `outlook = "unknown"`). Pokazujemy wtedy „–”.
- Cechy z `in_patterns = false` to kontekst. Można je pokazać mniejsze albo zwinięte.
- `heads_up` i `good_signs` nie zmieniają się po wypełnieniu ankiety (liczone z danych sprzed niej).
  Zmienia się `summary`: po ankiecie pokazuje „Possible reason: …” albo „Typical day for you”.

## Ekran 2 (szczegóły)

### Bad patterns ze szczegółami

Lista z `GET /api/users/{id}/patterns` (jak na ekranie 1), a po kliknięciu wzorca:

`GET /api/users/{id}/patterns/{feature}?kind=bad` (dla przepisu `kind=good`)

```json
{
  "feature": "wake_pct", "label": "Awake at night", "unit": "%",
  "op": "above", "threshold": 12.0, "display_threshold": "12%", "condition": "Awake over 12% of night",
  "variant": "lag1", "when": "last_night",
  "text": "Awake over 12% of night: 15 of 27 days bad",
  "points": [
    {"date": "2019-11-16", "value": 11.945, "display": "11.9%", "label": "good", "in_condition": false}
  ]
}
```

Wykres: oś X to `date`, oś Y to `value`, kolor kropki z `label`, linia na `threshold`.
`in_condition` zaznacza dni, w których warunek był spełniony. `op` mówi, po której stronie progu
jest warunek. `variant = "avg3"` oznacza średnią z 3 nocy lub dni. `example_dates` z `/patterns`
mogą linkować do widoku dnia.

404 = ta osoba nie ma wzorca na tej cesze. Linkuj tylko z cech na liście wzorców.

### Tabela: ile średnio w dobre dni, a ile w złe

`GET /api/users/{id}/stats`

```json
{
  "analysed_days": 66, "date_from": "2019-11-16", "date_to": "2020-02-13",
  "good_days_count": 32, "bad_days_count": 20,
  "features": [{
    "feature": "sleep_h", "label": "Sleep", "unit": "h", "when": "last_night", "in_patterns": true,
    "good": {"average": 7.793, "display": "7h48", "days": 32},
    "bad":  {"average": 7.078, "display": "7h05", "days": 20},
    "difference": -0.715
  }]
}
```

- Kolumny tabeli: `label` | `good.display` | `bad.display`.
- Podpis: „Based on {analysed_days} days ({date_from} – {date_to})”.
- `display` / `average` = `null` przy mniej niż 3 dniach w grupie. Wtedy pokazujemy „–”.
- Najpierw cechy z `in_patterns = true`, resztę można zwinąć.
- Tabela tylko opisuje dane. Nie podpisujemy jej „przyczyny”: różnica w tabeli to nie wzorzec.

### Kalendarz

`GET /api/users/{id}/days?from=2019-12-01&to=2019-12-31` zwraca jeden kafelek na dzień:

```json
{"date": "2019-12-06", "label": "bad", "score": -1.319,
 "has_reason": true,
 "headline": "Possible reason: awake 14.5% of night",
 "top_deviations": [
   {"feature": "wake_pct", "label": "Awake at night", "direction": "higher", "leans": "bad",
    "text": "Awake at night +3% vs good days"}
 ]}
```

- Kolor kafelka bierzemy z `label`. `null` = brak ankiety, kafelek szary.
- `has_reason` = ikonka „jest możliwy powód”.
- `headline` to jedno zdanie do tooltipa lub podglądu.
- Lista cech lepiej / gorzej niż średni dobry dzień: `top_deviations[]` (do 2 na dzień), czyli
  `label` + strzałka z `direction` + kolor z `leans` + `text`. Dzień bez wyraźnych różnic ma
  pustą listę.
- Domyślnie otwieramy miesiąc z `persona.today`.

### Widok dnia (po kliknięciu kafelka)

`GET /api/users/{id}/days/{date}`

| Pole | Do czego |
| --- | --- |
| `summary` | główne zdanie: „Possible reason: …” albo „No clear reason” |
| `reasons[]` | do 2 możliwych powodów (`text`, `pattern_text`) |
| `deviations[]` | porównanie z średnim dobrym dniem (`text`, `leans`) |
| `features[]` | wszystkie wartości dnia z `norm` i `leans`, jak na ekranie głównym |
| `survey` | odpowiedzi z tego dnia albo `null` |
| `timeline[]` | dni D-3…D: `night[]` i `activity[]`, `highlight = true` dla danych, z których wziął się powód |
| `outside_window` | `true`: dzień po końcu okresu analizy, nie był użyty do szukania wzorców. U obecnych person demo nie występuje |

## Pozostałe endpointy

| Endpoint | Do czego |
| --- | --- |
| `GET /api/features` | słownik cech: `label`, `unit`, `description` (tooltipy, legenda), `group_label` |
| `POST /api/users` `{"name": "Ola"}` | onboarding. 201 zwraca nową personę z `insights_status = "insufficient_days"` |
| `DELETE /api/users/{id}` | usunięcie (204). Persony demo: 403 |
| `POST /api/demo/reset` | cofa ankiety wpisane na żywo, między przebiegami demo. Działa tylko z `DEMO_RESET=true` |

`GET /api/features` ma pole `tested_direction`. To hipoteza algorytmu, a nie porada. Nie
wyświetlamy jej jako „lower is better”. Do kolorów służy `leans`.

## Kody błędów

| Kod | Kiedy | Co zrobić |
| --- | --- | --- |
| 404 | nieznany `user_id`; brak danych z dnia (`/days/{date}`); brak ankiety (`GET /surveys/{date}`); brak wzorca (`/patterns/{feature}`) | stan pusty, nie błąd |
| 422 | zła wartość ankiety (poza 1–5) albo data ankiety później niż `today` | komunikat przy formularzu |
| 403 | usunięcie persony demo, reset bez `DEMO_RESET` | ukryć przycisk |
| 500 `no such column` | stara baza | `reset_db` |

Błędy mają format `{"detail": "..."}`.

## Pułapki

- **Robin (`p01`) ma tylko 3 dobre dni.** `norm_reference = "all_days"`, więc porównania idą do
  średniego dnia, a teksty mówią „vs usual” (np. „Sleep -53 min vs usual”). `leans` jest zawsze `null`, a przepis ma
  status `insufficient_good_days`. Gdy `norm_reference == "all_days"`, zmień podpis na „vs your
  average day”. Ekrany z porównaniami pokazujemy na Samie (`p10`).
- **Porównania są ze średnim dobrym dniem** („vs good days”), a nie ze zwykłym dniem. Wyjątek to
  osoby z < 10 dobrymi dniami (`norm_reference = "all_days"`, teksty „vs usual”). Teksty z
  backendu (`app/insights/texts.py`) już to rozróżniają.
- **„Possible reason”, nie „cause”.** To korelacje w danych danej osoby. Nie dopisuj diagnoz ani
  porad.
- **Pierwsze zapytanie** po starcie backendu trwa ok. 0,4 s (liczenie analiz), kolejne są z cache.
- **Kim (`p16`) zasypia rano** („asleep at 09:41”). To prawdziwe dane nocnego marka, nie
  błąd.

Scenariusz prezentacji i odpowiedzi do wpisania na scenie: [demo.md](demo.md). Jak działa
algorytm: [insights.md](insights.md).
