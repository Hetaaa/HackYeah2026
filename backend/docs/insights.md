# Algorytm „Why Today” – jak działa i jak go zasilać

Dokument dla backendu i zespołu od algorytmów. Kod: `app/insights/` (algorytm) i `app/analysis.py`
(adapter do API).

## Przepływ danych

```text
zegarek (Fitbit Web API) ──► app/insights/fitbit.py ──► wiersze Day ──┐
PMData (eksport Fitbita) ──► scripts/import_pmdata.py ─► data/demo/*.csv ─► seed ─► Day
ankieta w aplikacji ──► PUT /surveys/{date} ──► Day (mood, fatigue, sleep_quality, stress, survey_at)
                                                       │
Day (wszystkie dni osoby) ─► sources/rows.py ─► UserData ─► analyze_user ─► app/analysis.py ─► API
```

- **Demo**: persony z PMData trafiają do `data/demo/*.csv` (surowe dane zostają poza repo), a seed
  ładuje je do bazy.
- **Prawdziwy użytkownik**: synchronizacja zegarka zapisuje wiersze `Day` (do zrobienia, patrz niżej),
  a ankieta zapisuje się przez `PUT /surveys`. Algorytm liczy się przy zapytaniu: ok. 0,1 s na osobę,
  z cache do momentu zmiany danych.

## Kontrakt danych: wiersz `Day`

Jeden wiersz to jeden użytkownik i jedna data `D`. Wszystkie pola są opcjonalne.

| Grupa | Pola | Znaczenie |
| --- | --- | --- |
| Noc | `sleep_minutes`, `sleep_start`, `sleep_end`, `time_in_bed_minutes`, `sleep_type`, `wake_minutes`, `wake_pct`, `rem_pct`, `deep_pct`, `sleep_hr_mean`, `sleep_efficiency`, `sleep_score`, `resting_hr` | główny sen, który **zakończył się rano `D`**; czasy lokalne zegarka |
| Aktywność | `steps`, `active_minutes` (moderate + vigorous), `light_minutes`, `sedentary_minutes`, `cardio_peak_minutes`, `calories`, `wear_minutes`, `wear_minutes_day` | **kalendarzowy dzień `D`** |
| Ankieta | `mood`, `fatigue`, `sleep_quality`, `stress` (1–5), `survey_at` (UTC) | samopoczucie dnia `D` |

Zasady, które stosuje algorytm:

- **Ankieta jest poranna**: samopoczucie dnia `D` zależy tylko od nocy kończącej się w `D` i
  aktywności z `D-1` lub wcześniej (`lag1`, średnia z 3 dni `avg3`).
- **Sen kończący się ponad 60 min po ankiecie** nie jest użyty jako „ostatnia noc”.
- **Dzień noszony < 12 h** między 06:00 a 24:00: aktywność tego dnia jest ignorowana. Brak
  `wear_minutes_day` = zakładamy, że zegarek był noszony.
- **Noce typu `classic`** (bez faz snu) nie mają `wake_pct`, `rem_pct` i `deep_pct`.

## Algorytm w skrócie

1. **Etykieta dnia**:
   - mood + fatigue + stress, każde pole odchylone od mediany osoby, potem z-score,
   - zły dzień: z < −0,5; dobry: z > +0,5,
   - przy < 14 ankietach albo identycznych odpowiedziach (brak osobistej bazy): średnia
     ≥ 3,5 to dobry dzień, ≤ 2,5 zły (`label_mode = absolute`).
2. **Cechy do szukania wzorców** (po jednej z grupy): sen, pora zaśnięcia, % czuwania w nocy, kroki,
   wysiłek (minuty w strefach cardio i peak albo `active_minutes`), lekka aktywność, % REM, tętno w
   czasie snu.
3. **Wzorzec**:
   - próg typu „sen < 6 h”, który obejmuje ≤ 50% dni i ma ≥ 10 dni po obu stronach,
   - score: dolna granica Wilsona P(zły | warunek) − P(zły | bez warunku),
   - istotność: test permutacyjny z przesunięciem cyklicznym etykiet, porównanie z maksimum ze
     wszystkich kandydatów, p ≤ 0,05.
4. **Bramki**:
   - ≥ 60 dni z ankietą i danymi z zegarka, inaczej `insufficient_days`,
   - wystarczająca zmienność odpowiedzi, inaczej `insufficient_variation`,
   - ≥ 15 złych (dobrych) dni, inaczej `insufficient_bad_days` / `insufficient_good_days`,
   - persony demo: wzorce tylko z dni przed 12.03.2020 (`Persona.analysis_window_end`, COVID).
5. **Widok dnia**:
   - **„Possible reason”** tylko z istotnego wzorca, którego warunek był spełniony tego dnia
     (maks. 2). W pozostałe dobre i złe dni: „No clear pattern explains this day.”
   - **`deviations`**: opisowe porównanie z przeciętnym dobrym dniem, do 2 cech odchylonych o ≥ 1 SD.
     Pojawia się każdego dnia i nie jest przyczyną.
6. **`leans`** (w `deviations` i `features`): czy wartość odbiega od punktu odniesienia w stronę
   złych, czy dobrych dni **tej osoby** (kierunek z różnicy średnich w złe i dobre dni). Brak
   (`null`) przy < 5 dobrych lub złych dniach albo gdy średnie różnią się o < 0,2 SD. Służy do
   kolorowania w kalendarzu, a nie jest poradą typu „więcej snu = lepiej”.
7. **Tabela dobre vs złe dni** (`/stats`): średnia każdej cechy (lag1) w dobre i w złe dni okna
   analizy, od 3 dni w grupie. Opis bez testu istotności: różnica w tabeli nie jest wzorcem.

Parametry są zamrożone w `app/insights/config.py`. Zmiana wymaga powtórzenia walidacji (skrypty w
`analysis/validate.py`, poza repo).

## Walidacja (PMData, 12 osób)

| Test | Wynik |
| --- | --- |
| Fałszywe alarmy na losowych etykietach | 4,4–5,6% (cel ≤ 5%) |
| Wstrzyknięty efekt „sen < 6 h” | znaleziony w 72% przebiegów, z poprawnym progiem |
| Wzorce na samych dniach roboczych | 7/7 się trzyma |
| Wzorce na drugiej połowie okresu | 54% ogółem, wzorce person tak |

Wzorce ma 5 z 12 osób. „Possible reason” ma ok. 12% złych dni ogółem (u person: P10 63%, P16 48%,
P01 35%, P06 0%). Porównanie z dobrym dniem daje treść w ok. 88% dni.

## Persony demo

| id | Imię | Wzorce |
| --- | --- | --- |
| p06 | Alex | sen > 6,5 h → 17 z 48 dni dobre (vs 7%); wzorzec złych dni tylko jako early signal (sen < 6 h) |
| p01 | Robin | > 10 min w strefach cardio/peak dzień wcześniej → 21 z 27 dni złe (vs 40%); brak przepisu (3 dobre dni) |
| p10 | Sam | czuwanie > 12% nocy → 15 z 27 dni złe (vs 13%); lekka aktywność > 320 min → 13 z 16 dni dobre (vs 38%) |
| p16 | Kim (zapas) | sen < 6 h → 10 z 13 dni złe (vs 19%); zaśnięcie po 08:00 → 8 z 12 dni złe (vs 22%); średnio > 3000 kroków → 9 z 14 dni dobre (vs 23%) |

Liczby to odpowiedzi API dla „dziś” person demo przed wpisaniem ankiety (dane do dnia poprzedniego).

## Ograniczenia i TODO

- Strefa czasowa jest stała (`Europe/Oslo`, jak w PMData). Dla prawdziwych użytkowników trzeba
  ją przechowywać per osoba.
- Synchronizacji zegarka jeszcze nie ma. Fitbit Web API zostało wyłączone 30.09.2026, więc
  `app/insights/fitbit.py` obsługuje już tylko eksporty (PMData). Dla prawdziwych zegarków
  potrzebny jest nowy adapter, np. Google Health API, Health Connect / HealthKit przez aplikację
  mobilną albo agregator. Analiza źródeł: [watch-sources.md](watch-sources.md).
- Brak prognozy dnia (poza zakresem).
- `PUT /surveys` przyjmuje daty od 2000-01-01 do jutra (UTC), a `survey_at` ustawia tylko przy
  pierwszym wypełnieniu (edycja nie przesuwa czasu ankiety).
- To korelacje w danych użytkownika, nie diagnoza. Teksty mówią „possible reason”.
