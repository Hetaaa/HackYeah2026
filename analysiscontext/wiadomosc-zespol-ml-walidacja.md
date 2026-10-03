# Do zespołu analizy danych: dane wyczyszczone, silnik zwalidowany

Hej! Dzięki za ustalenia z datasetu. Na ich podstawie mamy już wyczyszczone dane, silnik wzorców, kalendarz i walidację. Szczegóły są w `koncepcja-analityczna.md` (sekcje 3, 4, 5.1 i 8a), a wszystko odpala się jedną komendą: `analysis/run_pipeline.sh`.

## Co zamroziliśmy

- **Etykieta dnia:**
  - pola: mood + fatigue + stress,
  - centrowanie medianą osoby, liczone na dniach przed 12.03.2020,
  - zły dzień: z < −0,5; dobry: z > +0,5.
- **Cechy** (tylko z zegarka, po jednej z grupy):

  | Grupa | Cecha |
  | --- | --- |
  | Długość snu | `sleep_h` |
  | Pora snu | `bedtime_h` |
  | Ciągłość snu | `wake_pct` |
  | Kroki | `steps` |
  | Intensywny wysiłek | `z_cardio_peak` (albo `mvpa`) |
  | Lekka aktywność | `lightly` |
  | Faza REM | `rem_pct` |
  | Tętno w czasie snu | `hr_sleep_mean` |

- **Bramki:**
  - zostaje 12 osób; odpadają P02, P03, P12 i P13,
  - przepis na dobry dzień jest wyłączony u P01, P05 i P11, bo mają mniej niż 15 dobrych dni.
- **Wyczyszczone dane:** `analysis/output/daily_clean.csv` (12 osób, 1399 dni) i `daily_personas.csv`.

## Wyniki walidacji

| Test | Wynik |
| --- | --- |
| Fałszywe alarmy na losowych etykietach | 4,4–5,6% (cel ≤ 5%) |
| Fałszywe alarmy bez limitu 50% / z `sleep_eff` zamiast `wake_pct` | 4,2–6,8% |
| Sztucznie wstrzyknięty efekt snu | znaleziony w 72% przebiegów, z poprawnym progiem |
| Wzorce sprawdzone na drugiej połowie okresu | 54% się powtarza; wzorce person P01 i P06 tak, wstępne nie |
| Wzorce na samych dniach roboczych | 7/7 się trzyma |

Decyzje podjęte po obejrzeniu wyników (limit 50%, `wake_pct`) nie zawyżają fałszywych alarmów, więc zostają.

## Co znaleźliśmy

**Istotne wzorce ma 5 z 12 osób.** Pozostałe dostaną „not enough evidence”.

| Persona | Wzorzec |
| --- | --- |
| P01 | dzień po > 10 min w strefach cardio/peak tętna → 79% złych dni (vs 38%) |
| P06 | sen > 6,5 h → 36% dobrych dni (vs 7%) |
| P10 | wybudzenia > 12% nocy → 53% złych dni (vs 15%); lekka aktywność > 320 min → 83% dobrych (vs 38%) |
| P16 (zapas) | sen < 6 h → 79% złych dni (vs 21%) |

Wzorce istotne statystycznie, ale poza personami:
- P09: sen < 5,5 h → zły dzień,
- P16: kroki → dobry dzień.

## Co zmieniliśmy po walidacji

- **Fallback „Unusual” w kalendarzu jest usunięty.** Odpalał w 41% złych dni i w 34% neutralnych, czyli losowo.
- **W zamian każdy dzień dostaje opisowe porównanie z przeciętnym dobrym dniem osoby**, np. „You slept 1 h 40 min less than on your average good day”. To opis, a nie przyczyna.
- Przyczynę („Possible reason”) ma 12% złych dni ogółem, a u person: P10 63%, P01 35%, P06 0%.

## Pytania do was

1. Czy widzicie problem w definicji etykiety albo w bramkach, który mógłby tłumaczyć, dlaczego 7 osób nie ma wzorców? Podejrzewamy po prostu słabe efekty: korelacje rzędu 0,15.
2. P01: wzorzec „wysiłek → zły dzień” to pewnie zmęczenie po treningu. Czy na demo opisujemy to jako „you feel more tired after hard training days”?

Dzięki!
