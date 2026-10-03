# Analiza PMData – ustalenia dla algorytmu „why today”

Oct 3, 2026 · zespół analizy danych · skrypty: `analysis/` · cache: `analysis/cache/` · wykres: `analysis/plots/trends.png`

## TL;DR

- **Ankieta jest poranna u 13/16 osób** (mediana 09:12, 77% przed 12:00). Wyjątki: P16 (mediana 15:52), P09 (12:13). Reguła: raporty 00:00–04:59 → dzień poprzedni, sen liczy się tylko, gdy skończył się ≤ 60 min po ankiecie, pierwsza ankieta dnia.
- **Wszystkie skale: wyżej = lepiej** (fatigue, stress, soreness też). Etykieta = **mood + fatigue + stress**. Bez readiness (P05 ma 60× „0”, ρ=0,93 z wersją bez niego), bez soreness (zależy od treningu, ρ=−0,27 z sRPE D-1).
- **Etykieta centrowana medianą osoby** zamiast średnią. Przy wersji ze specyfikacji „typowy dzień” (same 3) dostaje etykietę *good* u P01, P05 i P11. Bramka: SD surowego wyniku ≥ 0,20, ≥ 60 pełnych dni, a osobno ≥ 15 złych (wzorce) i ≥ 15 dobrych (przepis).
- **Dni bez zegarka:** dzień aktywności jest ważny, gdy ma **≥ 720 min noszenia w 06–24** (z `heart_rate.json`). Reguła „sedentary ≥ 1400” łapie tylko 10 z 88 takich dni. `sedentary` jest zawyżane przez brak noszenia w nocy, więc wypada z cech.
- **Cechy:** `sleep_h`, `bedtime_h`, `sleep_eff`, `steps`, `lightly`, `mvpa`, `srpe_load` (tylko u osób, które regularnie logują trening). **Tętno spoczynkowe:** bierzemy `sleep_score.csv` (noc kończąca się w D), ale nie do wyszukiwania wzorców, bo jest mocno wygładzone, a jego związki z samopoczuciem idą w złą stronę.
- **Lockdown:** wzorce szukamy tylko na dniach < 2020-03-12. Aktywność w wartościach bezwzględnych; odchylenie od 28-dniowej mediany nic nie dało.
- **Korelacje są słabe, jak zakładano:** najsilniejszy wspólny sygnał to sen D → wynik dnia (ρ=0,15 w danych łącznych, dodatni u 13/15 osób, idzie głównie przez fatigue i stress, nie przez mood).
- **Persony:** **P06 „Sen”** (krótki sen → zły dzień, ρ=0,38, 144 dni), **P01 „Trening”** (trening D-1 → zły dzień: 79% vs 37%), **P16 „Nocny marek: sen + ruch”** (sen < 5,5 h → 10/10 złych). Rezerwa: **P10** (sen + lekka aktywność, bez okresu lockdownu).
- **Problem w algorytmie:** wynik `Wilson_lower(in) − rate_out` wybiera zdegenerowane progi („śpisz < 8,5 h → 33% vs 0%”). Rekomendacja: warunek musi obejmować ≤ 50% dni.
- **Do zgłoszenia:** pole `timestamp` w `sleep_score.csv` ma sufiks „Z”, ale jest w czasie lokalnym. P16 chodzi spać ok. 06–07 rano i robi ok. 1,6 tys. kroków dziennie. P04 i P13 nie mają `resting_heart_rate.json` przez większość okresu albo wcale (P04 tylko od 26.02).

---

## 0. Format danych – co zaskoczyło

| Plik | Format / pułapka |
| --- | --- |
| `pmsys/wellness.csv` | `effective_time_frame` w UTC (`...Z`), 1747 wierszy (zgodnie z publikacją). Na skalach 1–5 występuje **0** (13 wartości) → NaN. `readiness` = 0 74× (**P05: 60×**), niejednoznaczne. `soreness_area` to lista ID (pomijamy). |
| `fitbit/sleep.json` | Klucz to **`mainSleep`**, nie `isMainSleep`. `startTime` ma format `YYYY-MM-DD HH:MM:SS`, `endTime` ma format `...THH:MM:SS.000` (oba lokalne). 2% wpisów to typ `classic` (efektywność liczona inaczej). 61 dat ma 2+ główne sny. 89 głównych snów zaczyna się po 06:00 (82 z nich to P16). Są też drzemki oznaczone jako główny sen. `efficiency` = 0 w 2 wpisach. |
| `fitbit/sleep_score.csv` | `timestamp` ma „Z”, ale **= lokalny `endTime` snu** (sufiks Z jest fałszywy). Łączymy przez `sleep_log_entry_id` = `logId`. |
| `fitbit/resting_heart_rate.json` | `value.value`; **0 = brak** (do 51× u P03). **Brak pliku u P12 i P13.** P04 od 2020-02-26, P02 od 01.01, P05 od 28.12, P11 od 25.12. |
| `fitbit/steps|distance|calories.json` | Minutowe, lokalne. `distance` w cm. |
| `fitbit/*_active_minutes`, `sedentary_minutes` | Dzienne. **P12 nie ma `lightly_active_minutes.json`.** `sedentary` nie obejmuje snu, ale **nienoszony czas jest liczony jako siedzący** (doba bez zegarka = 1440). |
| `fitbit/heart_rate.json` | Ok. 5 s, 47–120 MB na osobę. Minuty noszenia liczone skanem regex (`build_wear.py`, ok. 1 min na wszystkich). |
| `pmsys/srpe.csv` | `end_date_time` w UTC, 783 sesje (11 bez RPE lub czasu). P08 nie ma `injury.csv`. |
| `fitbit/exercise.json` | `startTime` lokalny. 60–80% to automatycznie wykryte „Walk”. |

## 1. Godzina ankiety

Godziny lokalne (Europe/Oslo, zmiana czasu 29.03 obsłużona przez tz):

| pid | raporty | dni z >1 | mediana h | p10–p90 | % <10 | % 10–12 | % 12–18 | % ≥18 |
| --- | --: | --: | --: | --: | --: | --: | --: | --: |
| p01 | 138 | 0 | 9.4 | 7.8–18.2 | 60 | 18 | 11 | 11 |
| p02 | 99 | 0 | 11.4 | 9.0–21.1 | 35 | 18 | 21 | **25** |
| p03 | 82 | 7 | 9.9 | 1.9–21.9 | 51 | 6 | 23 | 20 |
| p04 | 145 | 2 | 9.0 | 5.8–21.3 | 69 | 15 | 3 | 14 |
| p05 | 137 | 3 | 7.5 | 6.6–12.4 | 84 | 4 | 4 | 7 |
| p06 | 147 | 0 | 9.0 | 7.2–13.1 | 78 | 10 | 11 | 1 |
| p07 | 133 | 1 | 9.0 | 7.4–10.1 | 89 | 8 | 3 | 1 |
| p08 | 104 | 1 | 9.1 | 7.6–13.3 | 63 | 18 | 16 | 3 |
| p09 | 102 | 0 | **12.2** | 9.0–17.0 | 24 | 25 | 45 | 7 |
| p10 | 96 | 1 | 9.5 | 8.1–13.4 | 59 | 27 | 13 | 1 |
| p11 | 107 | 0 | 8.8 | 6.6–11.9 | 76 | 14 | 8 | 3 |
| p12 | 83 | 0 | 9.1 | 6.4–21.4 | 71 | 12 | 1 | 16 |
| p13 | 72 | 4 | 11.5 | 9.0–21.2 | 36 | 17 | 25 | 22 |
| p14 | 125 | 1 | 9.0 | 7.7–9.8 | 91 | 6 | 1 | 2 |
| p15 | 95 | 2 | 9.1 | 7.0–13.8 | 72 | 13 | 7 | 8 |
| p16 | 82 | 0 | **15.9** | 11.6–19.5 | 2 | 11 | **67** | 20 |
| **ALL** | 1747 | 22 | 9.2 | 7.1–17.2 | 63 | 14 | 14 | 9 |

- **Raporty 00:00–04:59:** 29 (P04 14, P03 11, P13 3, P14 1). To wieczorne raporty z poprzedniego dnia, wypełnione po północy (np. P04 o 01:57, a sen trwał 20:49–08:27).
- **Kilka raportów w dniu:** 22 dni kalendarzowe (mediana odstępu 10 h, 14 z identycznymi odpowiedziami, czyli duplikaty). Po przesunięciu nocnych raportów zostaje 16 takich dni.
- **Ankieta przed końcem snu z Fitbita:** 47 z 1478 (po regułach). Większość to wypełnienie w łóżku kilka minut przed `endTime`. 16 przypadków z różnicą > 60 min (P04 11).

**Decyzja (reguła):**
1. Datę ankiety liczymy w czasie lokalnym. Raport z godzin **00:00–04:59 → dzień D-1**. Jeśli D-1 ma już raport dzienny, nocny odpada.
2. Z kilku raportów w dniu bierzemy **pierwszy**.
3. Sen nocy kończącej się w D liczymy tylko wtedy, gdy `endTime ≤ ankieta + 60 min`. W przeciwnym razie `sleep_*_lag1` = NaN, a avg3 liczymy z nocy D-1 i D-2.
4. **Raportów popołudniowych i wieczornych nie odrzucamy.** Reguła „aktywność z D-1” jest nadal bezpieczna, tylko konserwatywna: u P16 cechy pochodzą sprzed ok. 40 h.

## 2. Kierunek skal

Spearman w obrębie osoby, z-score per osoba, dane połączone. Readiness bez zer.

| | mood | fatigue | stress | readiness | soreness | sleep_q | sleep_dur |
| --- | --: | --: | --: | --: | --: | --: | --: |
| mood | 1 | **0.30** | **0.40** | 0.16 | 0.10 | 0.27 | 0.07 |
| fatigue | | 1 | 0.21 | **0.44** | 0.22 | 0.38 | 0.25 |
| stress | | | 1 | 0.10 | 0.05 | 0.24 | 0.15 |
| readiness | | | | 1 | 0.24 | 0.21 | 0.06 |
| soreness | | | | | 1 | 0.07 | 0.00 |

Liczba osób z ρ > 0: mood–fatigue 16/16, mood–stress 16/16, fatigue–readiness 16/16, mood–soreness 14/16, stress–soreness 9/16.

| Pole | Kierunek | Uwagi |
| --- | --- | --- |
| mood, fatigue, stress, soreness, sleep_quality (1–5) | **wyżej = lepiej** | Fatigue 5 = wypoczęty, stress 5 = zrelaksowany, soreness 5 = brak bólu. Nic nie trzeba odwracać. |
| readiness (0–10) | wyżej = lepiej | Wartości 0 niejednoznaczne (P05 60×, w te dni mood 1–3). |

## 3. Etykieta dnia

| pid | n | SD mood | SD fatigue | SD stress | SD surowego M+F+S | % dni 3/3/3 | % mood = moda | bad/good (spec: średnia) | bad/good (mediana) | stan „3/3/3” w spec |
| --- | --: | --: | --: | --: | --: | --: | --: | --: | --: | --- |
| p01 | 138 | 0.28 | 0.54 | 0.33 | 0.27 | 50 | 94 | 20/72 | 66/3 | **good** |
| p02 | 99 | 0.22 | 0.17 | 0.17 | **0.14** | **92** | 95 | 3/5 | 3/5 | neutral |
| p03 | 80 | 0.30 | 0.29 | 0.27 | **0.18** | **81** | 95 | 12/3 | 12/3 | neutral |
| p04 | 143 | 0.75 | 0.66 | 0.83 | 0.56 | 18 | 51 | 48/30 | 46/46 | neutral |
| p05 | 134 | 0.80 | 0.61 | 0.84 | 0.62 | 42 | 56 | 35/73 | 55/14 | **good** |
| p06 | 147 | 0.30 | 0.53 | 0.69 | 0.36 | 1 | 90 | 28/72 | 72/24 | bad |
| p07 | 132 | 0.50 | 0.48 | 0.74 | 0.39 | 31 | 73 | 36/49 | 30/51 | neutral |
| p08 | 103 | 0.64 | 0.86 | 0.88 | 0.56 | 3 | 70 | 31/29 | 31/50 | neutral |
| p09 | 102 | 0.77 | 0.91 | 0.92 | 0.67 | 14 | 50 | 24/35 | 24/32 | neutral |
| p10 | 95 | 0.56 | 0.78 | 0.65 | 0.50 | 11 | 68 | 29/24 | 27/46 | good |
| p11 | 107 | 0.21 | 0.44 | 0.42 | 0.26 | 69 | 95 | 33/74 | 32/0 | **good** |
| p12 | 83 | 0.36 | 0.71 | 0.47 | 0.38 | 37 | 89 | 32/18 | 32/18 | neutral |
| p13 | 69 | 0.73 | 0.99 | 0.63 | 0.56 | 13 | 49 | 25/22 | 16/22 | good |
| p14 | 123 | 0.41 | 0.61 | 0.54 | 0.39 | 33 | 80 | 55/27 | 56/23 | neutral |
| p15 | 93 | 0.60 | 0.85 | 0.64 | 0.54 | 10 | 52 | 34/34 | 42/34 | bad |
| p16 | 82 | 0.56 | 0.62 | 0.70 | 0.49 | 35 | 71 | 27/25 | 27/25 | neutral |

Wnioski:
- **Problem z wersją ze specyfikacji:** z-score ze średnią na skośnych danych dyskretnych przesuwa „typowy dzień”. U P01, P05 i P11 dni 3/3/3 (50–69% dni) dostają etykietę **good**. „Przepis na dobry dzień” byłby wtedy przepisem na zwykły dzień.
- **Rekomendacja: centrowanie medianą osoby.** Dla każdego pola liczymy `(x − mediana_osoby) / SD_osoby` (pole z SD = 0 daje 0), potem średnią z 3 pól i dzielimy przez SD wyniku, bez ponownego centrowania. Progi zostają: zły < −0,5, dobry > +0,5. Typowy dzień zawsze wychodzi neutralny. Ranking dni jest identyczny jak w wersji spec (ρ = 1,00), więc korelacje się nie zmieniają, a różni się tylko podział na bad i good.
- **Koszt tej wersji:** u części osób rozkład etykiet jest bardzo nierówny (P01 66/3, P11 32/0, P06 72/24). To uczciwe: P01 prawie nigdy nie zgłasza dnia lepszego niż zwykle. UI pokazuje wtedy „not enough good days yet” w przepisie.
- **Pola w etykiecie:** M+F+S. Readiness dodaje mało (ρ = 0,93 między wynikami z nim i bez niego), a ma problem zer u P05. Soreness słabo wiąże się z mood (0,05–0,10), a mocno z treningiem dnia poprzedniego (ρ = −0,27 z `srpe_load_lag1`), więc zrobiłby z treningu trywialną „przyczynę”. Sleep_quality i sleep_duration odpadają, bo pokrywają się z Fitbitem.
- **Bramka wariancji:**
  - Osoba: **SD surowej średniej M+F+S ≥ 0,20** oraz ≥ 60 pełnych dni. Odpadają P02 (0,14, 92% dni 3/3/3) i P03 (0,18, 81%), a P12 i P13 nie mają danych.
  - Kierunek: wzorce złych dni wymagają ≥ 15 złych dni, przepis wymaga ≥ 15 dobrych dni (w pełnych dniach). Przepis jest niedostępny u P01 (3), P05 (7) i P11 (0).

## 4. Kompletność (dni)

Reguły finalne: aktywność z D-1 przechodzi filtr noszenia (pkt 5), noc kończąca się w D jest ważna (pkt 9 planu) i skończyła się przed ankietą.

| pid | dni ankiety | etykieta OK | dni Fitbit (noszone) | główny sen | RHR dzienne | RHR nocne | sen D | kroki D-1 | RHR dzienne D-1 | RHR nocne D | **PEŁNE** | pełne < 12.03 |
| --- | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: |
| p01 | 138 | 138 | 147 | 150 | 152 | 149 | 137 | 133 | 133 | 137 | **133** | 117 |
| p02 | 99 | 99 | 142 | 142 | 89 | 138 | 96 | 93 | 55 | 93 | **92** | 84 |
| p03 | 80 | 80 | 50 | 76 | 101 | 73 | 49 | 30 | 30 | 48 | **24** | 23 |
| p04 | 143 | 142 | 140 | 141 | 35 | 139 | 123 | 131 | 30 | 123 | **119** | 102 |
| p05 | 134 | 134 | 137 | 117 | 86 | 116 | 102 | 120 | 71 | 102 | **100** | 83 |
| p06 | 147 | 147 | 151 | 149 | 150 | 146 | 145 | 146 | 145 | 143 | **144** | 126 |
| p07 | 132 | 132 | 142 | 142 | 144 | 140 | 124 | 127 | 127 | 123 | **122** | 108 |
| p08 | 103 | 103 | 132 | 132 | 139 | 131 | 94 | 94 | 94 | 94 | **92** | 83 |
| p09 | 102 | 102 | 115 | 135 | 147 | 131 | 94 | 82 | 82 | 92 | **77** | 71 |
| p10 | 95 | 95 | 102 | 99 | 110 | 98 | 80 | 84 | 83 | 80 | **76** | 76 |
| p11 | 107 | 106 | 119 | 119 | 80 | 119 | 107 | 107 | 68 | 107 | **106** | 104 |
| p12 | 83 | 83 | 88 | 1 | 0 | 1 | 1 | 57 | 0 | 1 | **1** | 1 |
| p13 | 69 | 68 | 54 | 50 | 0 | 47 | 35 | 35 | 0 | 32 | **28** | 28 |
| p14 | 123 | 123 | 110 | 116 | 129 | 112 | 101 | 96 | 96 | 99 | **90** | 80 |
| p15 | 93 | 93 | 142 | 142 | 144 | 140 | 93 | 92 | 92 | 93 | **92** | 83 |
| p16 | 82 | 82 | 144 | 144 | 152 | 142 | 81 | 78 | 78 | 81 | **77** | 75 |
| **SUM** | 1730 | 1727 | 1915 | 1855 | 1658 | 1822 | 1462 | 1505 | 1184 | 1448 | **1373** | 1244 |

PEŁNE = etykieta + sen D + kroki D-1 (z noszeniem). Wykluczamy **P12** (1 dzień), **P13** (28), **P03** (24) i **P02** (bramka wariancji). Do analizy zostaje **12 osób, 76–144 dni** (pre-lockdown: 71–126).

## 5. Dni bez zegarka

Minuty noszenia = minuty z ≥ 1 odczytem HR (`cache/wear_minutes.csv`, liczone osobno dla całej doby i dla 00–06).

Kroki względem mediany osoby (w obrębie osoby) w zależności od noszenia w 06–24 (max 1080 min):

| noszenie 06–24 (min) | ≤ 300 | 300–600 | 600–720 | 720–840 | 840–900 | 900–1020 | 1020–1080 |
| --- | --: | --: | --: | --: | --: | --: | --: |
| kroki / mediana osoby | 0.03 | 0.62 | 0.82 | **1.02** | 1.10 | ~1.0 | 1.00 |
| sedentary − mediana osoby (min) | +575 | +142 | +85 | +22 | −8 | ~+15 | 0 |

- Całkowite noszenie 900–1200 min to głównie noce bez zegarka (ładowanie), przy pełnym dniu. Kroki są wtedy poprawne, ale **sedentary rośnie o +80–110 min**, bo niezarejestrowany sen jest liczony jako siedzenie.
- Reguła „sedentary ≥ 1400” łapie tylko doby kompletnie bez zegarka: **10 dni vs 88** dni wyłapanych przez regułę noszenia.

| pid | sen D (n) | sed ≥ 1400 | całkowite < 1000 | **06–24 < 720** | zostaje |
| --- | --: | --: | --: | --: | --: |
| p01 | 137 | 0 | 2 | 4 | 133 |
| p02 | 96 | 2 | 4 | 4 | 92 |
| p03 | 49 | 2 | 22 | 25 | 24 |
| p04 | 123 | 0 | 5 | 4 | 119 |
| p05 | 102 | 0 | 3 | 2 | 100 |
| p06 | 145 | 1 | 1 | 1 | 144 |
| p07 | 124 | 0 | 2 | 2 | 122 |
| p08 | 94 | 0 | 6 | 2 | 92 |
| p09 | 94 | 2 | 15 | **17** | 77 |
| p10 | 80 | 0 | 5 | 4 | 76 |
| p11 | 107 | 0 | 0 | 0 | 107 |
| p13 | 35 | 1 | 5 | 7 | 28 |
| p14 | 101 | 1 | 14 | **11** | 90 |
| p15 | 93 | 0 | 0 | 1 | 92 |
| p16 | 81 | 1 | 2 | 4 | 77 |
| **SUM** | 1462 | 10 | 87 | **88** | 1374 |

**Decyzja:**
- Dzień D-1 jest ważny dla aktywności (kroki, minuty aktywności), gdy **noszenie 06:00–24:00 ≥ 720 min (12 h)**. W przeciwnym razie aktywność = NaN, a dzień nie wchodzi do avg3.
- `sedentary` jest wiarygodne tylko przy noszeniu całej doby ≥ 1200 min. Ponieważ i tak jest redundantne (pkt 7), **usuwamy je z cech**.
- Fallback bez `heart_rate.json` (realny produkt): `sedentary < 1400 AND steps ≥ 500`.

## 6. Lista cech, RHR, trening

| pid | RHR dzienne D-1 | RHR nocne D | ρ dzienne vs nocne | sesje sRPE | dni z sRPE D-1 > 0 | dni z ćwiczeniem nie-Walk D-1 |
| --- | --: | --: | --: | --: | --: | --: |
| p01 | 133 | 137 | 0.97 | 34 | 29 | 34 |
| p02 | 55 | 93 | 0.96 | 97 | 48 | 56 |
| p04 | **30** | 123 | 0.95 | 85 | 78 | 84 |
| p05 | 71 | 102 | 0.93 | **9** | 6 | 34 |
| p06 | 145 | 143 | 0.99 | 46 | 43 | 72 |
| p07 | 127 | 123 | 0.99 | 110 | 97 | 110 |
| p08 | 94 | 94 | 0.99 | 113 | 80 | 85 |
| p09 | 82 | 92 | 0.99 | **3** | 3 | 5 |
| p10 | 83 | 80 | 0.99 | 27 | 26 | 19 |
| p11 | 68 | 107 | 0.98 | 30 | 28 | 32 |
| p13 | **0** | 32 | – | 10 | 5 | 8 |
| p14 | 96 | 99 | 0.99 | 62 | 50 | 48 |
| p15 | 92 | 93 | 0.98 | 104 | 74 | 72 |
| p16 | 78 | 81 | 0.98 | **11 (0 z RPE)** | 0 | 1 |

- **Oba źródła RHR mierzą to samo.** Wartość z `sleep_score` dla nocy kończącej się w D równa się `resting_heart_rate` z D-1 w 50% przypadków (MAE 0,53 bpm), a w obrębie osoby ρ = 0,93–0,99.
- **Sygnał jest mocno wygładzony:** mediana zmiany dzień do dnia to 0,75–1 bpm, p90 to 2 bpm, a zakres p10–p90 w obrębie osoby ok. 5 bpm. Avg3 ≈ lag1 (ρ = 0,90).
- **Decyzja RHR:** jeśli używamy, to `rhr_night` z `sleep_score.csv` (lepsze pokrycie: 1448 vs 1184 dni, P04 123 vs 30, P13 32 vs 0; mierzone przed ankietą). **Nie do wyszukiwania wzorców:** w danych łącznych ρ z wynikiem dnia jest dodatnie (+0,06, czyli w złą stronę), u P01 i P14 „wyższe tętno → lepszy dzień”, a u P14 to efekt trendu w czasie (n_eff = 25, ρ częściowe 0,17). Zostaje w widoku dnia i w fallbacku |z| > 2.
- **Decyzja trening:** `srpe_load` (RPE × min, suma z dnia D-1; dzień bez sesji w okresie logowania = 0) włączamy tylko u osób z **≥ 25 sesjami** (P01, P02, P04, P06, P07, P08, P10, P11, P14, P15). Kierunek ustalamy z góry: wysokie obciążenie → gorszy dzień. U P01 to najsilniejszy sygnał w danych (pkt korelacji). `exercise.json` (nie-Walk) ma ρ ≈ 0,5 z sRPE i jest dostępny u wszystkich, ale zawiera auto-detekcję; zostaje tylko jako zapas dla osób bez sRPE.
- **Sen:** `sleep_h` (minutesAsleep/60), `bedtime_h` (godziny od 18:00 dnia D-1), `sleep_eff`. `time_in_bed` jest redundantne z `sleep_h` (ρ = 0,98).

## 7. Grupy współliniowe

Spearman w obrębie osoby (z-score per osoba, potem dane łączone). W nawiasie mediana per osoba. Cechy lag1, 12 osób.

| para | ρ | para | ρ |
| --- | --: | --- | --: |
| steps–distance | 0.98 (0.99) | lightly–steps | 0.40 (0.44) |
| steps–calories | 0.88 (0.90) | lightly–mvpa | 0.04 (0.08) |
| steps–very | 0.74 (0.79) | lightly–active_total | 0.78 (0.82) |
| steps–mvpa | 0.75 (0.76) | sedentary–active_total | −0.65 (−0.66) |
| steps–active_total | 0.77 (0.79) | sedentary–steps | −0.54 (−0.48) |
| mvpa–very | 0.92 (0.92) | srpe_load–very | 0.56 (0.57) |
| mvpa–moderately | 0.81 (0.85) | srpe_load–mvpa | 0.47 (0.51) |
| sleep_h–time_in_bed | 0.98 (0.98) | sleep_h–bedtime | −0.34 (−0.31) |
| rhr_night–rhr_day | 0.97 (0.98) | sleep_h–aktywność D-1 | −0.05 do −0.10 |
| sleep_eff–cokolwiek | ≤ 0.07 | ex_min–mvpa | 0.67 (0.70) |

Lag1 vs avg3 tej samej cechy: sen 0,54, kroki 0,63, lightly 0,66, mvpa 0,59. Warianty są więc wystarczająco różne, żeby trzymać oba.

**Grupy (algorytm bierze po jednej cesze z grupy):**

| Grupa | Członkowie | Reprezentant |
| --- | --- | --- |
| A. Ilość snu | sleep_h, time_in_bed | **sleep_h** |
| B. Pora snu | bedtime_h | **bedtime_h** |
| C. Jakość snu | sleep_eff | **sleep_eff** (słaby, opcjonalny) |
| D. Objętość ruchu | steps, distance, calories, active_total | **steps** |
| E. Intensywny wysiłek | mvpa, very, moderately, srpe_load, ex_min | **mvpa**, albo **srpe_load** u osób logujących |
| F. Lekka aktywność | lightly | **lightly** (słabo skorelowana z mvpa, osobny sygnał, jedyny powiązany z mood) |
| – | sedentary, rhr_* | poza wyszukiwaniem (pkt 5 i 6) |

Uwaga: grupy D i E zachodzą na siebie (ρ = 0,75). Jeśli zespół chce mniej testów, można połączyć je w jedną grupę „ruch”.

## 8. Zakresy i siatka progów

Lag1, dni ankiety, z filtrem noszenia, 12 osób.

| cecha | p10 | p50 | p90 | p1–p99 | p10–p90 w obrębie osoby (mediana, min–max) | **krok** |
| --- | --: | --: | --: | --: | --: | --- |
| sleep_h | 5.3 | 6.8 | 8.3 | 3.2–10.0 | 2.5 (1.9–3.9) | **0,5 h** |
| bedtime_h (od 18:00) | 4.1 (22:06) | 5.8 (23:48) | 8.9 (02:54) | 1.9–14.1 | 2.4 (1.4–5.7) | **0,5 h** |
| sleep_eff | 90 | 95 | 98 | 85–100 | 6.9 | **1 pkt** |
| rhr_night | 49 | 59 | 68 | 45–72 | 5.0 (3–8) | **1 bpm** (2 bpm daje 2–3 progi) |
| steps | 4 750 | 12 430 | 19 860 | 760–28 400 | 10 500 (3 550–14 240) | **1000** (500, gdy p90−p10 osoby < 5000, np. P16) |
| lightly | 121 | 225 | 349 | 56–514 | 155 | **20 min** |
| mvpa | 0 | 69 | 150 | 0–246 | 116 | **10 min** (dużo zer) |
| sedentary | 503 | 645 | 827 | 348–1081 | 255 | (30 min, cecha wypada) |
| srpe_load | 0 | 0 | 480 | 0–1260 | 358 | **próg 0 („trening wczoraj”) + co 100 AU** |

Progi szukamy w zakresie p5–p95 osoby. Wychodzi ok. 5–15 progów na cechę.

## 9. Trendy, święta, lockdown

- **Kroki (dane łączne, względem mediany osoby):** XI 1,03 · XII 1,00 · I 1,03 · II 1,05 · **III 0,83**.
- **Wynik dnia (z):** XI −0,22 · XII −0,12 · I −0,13 · II 0,01 · **III −0,29**.

| pid | kroki przed / po 12.03 | Δ wyniku po − przed | dni po | święta 21.12–01.01 (kroki ×) | weekend / dzień roboczy (kroki ×) |
| --- | --- | --: | --: | --: | --: |
| p01 | 12 990 / **8 330** | **−0.54** | 18 | 1.04 | 1.24 |
| p04 | 10 340 / 9 010 | −0.31 | 19 | 0.77 | 0.74 |
| p05 | 12 410 / **8 830** | −0.01 | 17 | 0.79 | 0.90 |
| p06 | 14 300 / 14 230 | **−0.50** | 18 | **0.57** | **0.52** |
| p07 | 16 420 / 12 550 | +0.05 | 15 | 0.90 | 0.89 |
| p08 | 17 210 / 13 660 | +0.90 | 11 | 0.89 | 0.97 |
| p09 | 5 940 / **1 450** | −0.01 | 9 | 0.93 | **1.52** |
| p10 | 12 190 / – (koniec 29.02) | – | 0 | 1.07 | 1.28 |
| p14 | 11 410 / 8 590 | **−0.65** | 18 | 0.82 | 1.33 |
| p15 | 14 040 / 10 290 | −0.03 | 10 | 1.19 | 1.03 |
| p16 | 1 610 / 1 490 | +0.89 | 3 | 1.16 | 0.60 |

- Po lockdownie kroki spadają u 7/11 osób (do −76% u P09), a wynik dnia spada u P01, P06 i P14. To klasyczny fałszywy wzorzec „mniej ruchu → gorszy dzień”.
- Na wykresie (`plots/trends.png`) widać epizody, w których kroki i wynik spadają razem (P08 w połowie stycznia, prawdopodobnie choroba lub kontuzja, P07 w okresie świąt). To jeden epizod, nie wiele niezależnych dowodów.
- Weekend mocno zmienia aktywność (×0,52–1,57, kierunek zależy od osoby).
- **Odchylenie od 28-dniowej mediany nic nie daje.** W danych łącznych ρ z wynikiem dnia: `steps` 0,007 vs `steps_dev28` 0,017; `mvpa` 0,014 vs 0,012; `sleep_h` 0,153 vs 0,156.

**Decyzja:**
- **Wartości bezwzględne** (czytelne zdania: „under 6,000 steps”).
- **Wzorce szukamy na dniach D < 2020-03-12** (traci się ok. 9% pełnych dni: 1373 → 1244). Dni po tej dacie są w kalendarzu i dostają przyczyny z zamrożonych wzorców, z flagą `post_lockdown`.
- Wersję `dev28` zostawiamy jako opcję, ale jej nie używamy.

---

## 10. Korelacje cecha → samopoczucie

> Zespół ML prosił o nieliczenie tych korelacji przed zamrożeniem parametrów. Zrobiliśmy je na wyraźne życzenie, wyłącznie do **wyboru person i sprawdzenia, czy algorytm ma szansę coś znaleźć**. Parametry z pkt 1–9 ustaliliśmy na podstawie struktury danych, nie tych wyników. Wyjątek to reguła „minority” (pkt 11.3), patrz ryzyka.

**Metoda:**
- Spearman cecha (lag1 lub avg3, tylko dane sprzed ankiety) vs (a) **mood** surowy, (b) **wynik dnia** M+F+S.
- **p_eff** liczone z efektywnym n (Bartlett: `n·(1−r1x·r1y)/(1+r1x·r1y)`, r1 = autokorelacja rang).
- **BH-FDR (q)** w obrębie osoby i targetu (ok. 27 testów).
- Autokorelacja wyniku dnia (lag 1): P05 0,64, P14 0,56, pozostali 0,0–0,3.
- Analiza: 15 osób (bez P12). Wyniki w `cache/corr_person.csv` i `cache/corr_pooled.csv`.

### 10.1 Dane łączne w obrębie osoby

„p między osobami” to t-test na ρ per osoba.

| cecha | ρ łączne (wynik dnia) | śr. ρ per osoba | osoby z ρ > 0 | osoby z p_eff < 0,05 | p między osobami | ρ łączne (mood) |
| --- | --: | --: | --: | --: | --: | --: |
| **sleep_h_lag1** | **0.153** | 0.147 | **13/15** | 5 | **0.007** | 0.023 |
| sleep_h_avg3 | 0.116 | 0.108 | 11/15 | 4 | 0.018 | 0.025 |
| sleep_eff_lag1 | 0.086 | 0.068 | 13/15 | 3 | 0.035 | 0.071 |
| bedtime_h_lag1 | 0.012 | 0.012 | 7/15 | 2 | 0.73 | 0.027 |
| rhr_night_lag1 | +0.063 (zły kierunek) | 0.074 | 11/15 | 2 | 0.041 | 0.038 |
| steps_lag1 | 0.007 | 0.012 | 9/15 | 1 | 0.78 | 0.047 |
| **lightly_lag1** | 0.094 | 0.103 | 11/15 | 3 | 0.029 | **0.142** (14/15 > 0, p < 0,001) |
| mvpa_lag1 | 0.014 | 0.014 | 8/15 | 1 | 0.72 | 0.015 |
| sedentary_lag1 | −0.045 | −0.034 | 3/15 | 1 | 0.46 | −0.054 |
| srpe_load_lag1 | −0.011 | −0.021 | 8/13 | 1 | 0.60 | −0.004 |
| steps_dev28_lag1 | 0.017 | 0.034 | 8/13 | 0 | 0.21 | 0.046 |

Składowe (dane łączne, ρ):

| cecha D-1 | mood | fatigue | stress | soreness |
| --- | --: | --: | --: | --: |
| sleep_h | 0,02 | **0,17** | 0,11 | – |
| lightly | **0,14** | 0,02 | 0,06 | – |
| srpe_load | – | −0,03 | – | **−0,27** |

**Wniosek:**
- Jedyny spójny efekt w populacji to sen D → wynik dnia (zmęczenie i stres), oraz lekka aktywność → mood.
- Kroki, MVPA, pora snu i trening nie mają efektu wspólnego dla wszystkich. Mogą działać tylko u pojedynczych osób, i to w różnych kierunkach.
- **Mood jako jedyny target jest słaby:** u 5 osób mood ma ≥ 90% jednej wartości. Zostajemy przy wyniku M+F+S.

### 10.2 Per osoba (wynik dnia)

`*` p_eff < 0,05, `**` q_BH < 0,10. Pełna wersja z mood: `cache/report_person.out.md`.

| pid | n | sleep_h l1 | sleep_h a3 | eff l1 | bedtime l1 | rhr_n a3 | steps l1 | steps a3 | lightly l1 | lightly a3 | mvpa a3 | srpe l1 |
| --- | --: | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| p01 | 137 | +.04 | +.08 | +.03 | +.06 | +.28** | −.03 | +.10 | +.15 | +.19 | +.03 | **−.32**** |
| p02 | 97 | +.01 | −.09 | −.21* | +.06 | +.09 | +.01 | −.03 | +.24* | +.15 | −.05 | −.04 |
| p04 | 141 | +.09 | +.02 | +.09 | −.18* | −.09 | +.07 | +.06 | +.09 | +.12 | −.04 | +.02 |
| p05 | 122 | +.10 | +.14 | +.10 | −.01 | +.03 | −.05 | +.01 | +.20 | +.12 | +.12 | +.14 |
| p06 | 146 | **+.38**** | +.35** | +.13 | −.12 | −.01 | −.08 | −.06 | −.01 | −.11 | −.03 | +.11 |
| p07 | 131 | +.15 | +.10 | +.06 | +.04 | +.11 | −.15 | −.09 | −.05 | −.04 | +.02 | +.02 |
| p08 | 102 | +.27** | **+.30**** | +.17 | −.02 | +.03 | +.04 | +.05 | +.03 | +.07 | +.16 | +.06 |
| p09 | 98 | **+.33**** | −.01 | +.02 | −.03 | +.08 | +.15 | +.14 | +.18 | +.17 | +.02 | −.24 |
| p10 | 89 | +.31** | +.25* | +.24* | −.02 | −.13 | +.08 | −.02 | +.19 | **+.32**** | −.18 | +.02 |
| p11 | 106 | +.03 | −.06 | +.05 | −.07 | −.08 | +.12 | +.12 | +.05 | +.08 | +.16 | +.16 |
| p13 | 66 | −.20 | +.08 | .00 | +.17 | −.03 | −.37 | −.43* | −.33 | −.40 | −.49* | +.04 |
| p14 | 120 | −.05 | +.01 | −.01 | +.27* | +.42* | +.02 | −.07 | +.23* | +.20 | −.03 | −.10 |
| p15 | 93 | +.06 | +.06 | +.10 | +.18 | −.04 | −.04 | −.07 | −.02 | −.09 | −.06 | −.15 |
| p16 | 82 | **+.47**** | +.43** | +.26** | −.21 | +.05 | +.33** | +.31** | +.27** | +.18 | +.23** | – |

- Przy ok. 27 testach na osobę spodziewamy się ok. 1,4 wyniku z p < 0,05 przypadkiem.
- Wyniki z q < 0,10 skupiają się u kilku osób: P16 (12), P06 (5), P01 (4), P08 (4), P09 (3), P10 (2), P04 (1). U pozostałych ośmiu osób nic nie przechodzi FDR.

### 10.3 Kontrola zakłóceń (najsilniejsze związki)

- **robocze** = tylko D ∈ wt–pt (D i D-1 są dniami roboczymi);
- **pre** = tylko D < 12.03;
- **częściowe** = ρ rang z kontrolą: weekend D-1, po lockdownie, trend liniowy.

| pid | cecha | ρ | n (n_eff) | robocze | pre | częściowe | ocena |
| --- | --- | --: | --- | --: | --: | --: | --- |
| p06 | sleep_h_lag1 | 0.38 | 145 (142) | 0.50 | 0.40 | 0.36 | **solidne** |
| p16 | sleep_h_lag1 | 0.47 | 81 | 0.52 | 0.42 | 0.44 | **solidne** |
| p16 | steps_lag1 | 0.33 | 78 (72) | **0.17** | 0.36 | 0.26 | częściowo weekend |
| p16 | lightly_lag1 | 0.27 | 78 | **0.08** | 0.28 | 0.21 | **głównie weekend** |
| p01 | srpe_load_lag1 | −0.32 | 119 | −0.40 | −0.31 | −0.32 | **solidne** |
| p01 | rhr_night_avg3 | +0.28 | 136 (101) | 0.34 | 0.27 | 0.25 | zły kierunek, wolny trend; nie pokazujemy |
| p08 | sleep_h_avg3 | 0.30 | 97 | 0.40 | 0.24 | 0.26 | solidne, umiarkowane |
| p09 | sleep_h_lag1 | 0.33 | 94 | 0.32 | 0.35 | 0.36 | solidne |
| p10 | sleep_h_lag1 | 0.31 | 80 | 0.37 | 0.31 | 0.31 | solidne (brak lockdownu) |
| p10 | lightly_avg3 | 0.32 | 89 (76) | 0.26 | 0.32 | 0.32 | solidne |
| p04 | bedtime_h_avg3 | −0.26 | 131 | **−0.14** | −0.26 | −0.24 | częściowo weekend |
| p14 | rhr_night_lag1 | +0.42 | 99 (**25**) | 0.39 | 0.26 | **0.18** | trend w czasie i lockdown; **artefakt** |
| p13 | mvpa_avg3 | −0.49 | 36 (26) | −0.32 | −0.49 | −0.36 | za mało danych; osoba wykluczona |

**Choroba nie jest kontrolowana** (brak danych; `injury.csv` prawie pusty). Epizody, w których spadają razem kroki i samopoczucie (P08 w styczniu), mogą tworzyć wzorce typu „mało ruchu → zły dzień”. Test z cyklicznym przesunięciem częściowo to łagodzi.

### 10.4 Medianowe wartości cech: dni złe / neutralne / dobre

Etykieta centrowana medianą. Pełna tabela: `cache/bad_good_medians.csv`.

| pid | cecha | zły | neutralny | dobry |
| --- | --- | --: | --: | --: |
| p06 | sleep_h_lag1 | 5.97 h | 6.18 h | **7.07 h** |
| p16 | sleep_h_lag1 | 6.04 h | 6.73 h | 6.88 h |
| p16 | steps_avg3 | 1 307 | 1 748 | 2 037 |
| p10 | sleep_h_lag1 | 6.93 h | 7.35 h | 7.60 h |
| p10 | lightly_avg3 | 254 | 271 | 285 |
| p09 | sleep_h_lag1 | 5.95 h | 6.84 h | 7.18 h |
| p08 | sleep_h_avg3 | 7.08 h | 7.24 h | 7.32 h |
| p04 | bedtime_h_avg3 | 23:34 | 23:05 | 22:59 |

Różnice to typowo 0,5–1 h snu, czyli wykrywalne, ale przy dużym nakładaniu się rozkładów.

---

## 11. Wybór person

### 11.1 Ranking wszystkich 16

- „PEŁNE” = dni z kompletem danych.
- „stump istotny” = szybka implementacja 2.2 + 2.3 z regułą minority, p_global < 0,05 (`stump_check.py --minority`).

| # | pid | PEŁNE | bad/good | najsilniejszy związek (ρ, q) | stump istotny | decyzja / powód |
| --: | --- | --: | --- | --- | --- | --- |
| 1 | **P06** | 144 | 71/23 | sleep_h_lag1 +0.38, q < 0,001 | good: sen > 6,5 h | **Persona „Sen”.** Najwięcej dni, efekt najsolidniejszy w kontrolach. |
| 2 | **P01** | 133 | 64/3 | srpe_load_lag1 −0.32, q = 0,01 | bad: trening D-1 > 0 | **Persona „Trening”.** Wyjątkowy i zrozumiały wzorzec. Brak przepisu (3 dobre dni). |
| 3 | **P16** | 77 | 25/23 | sleep_h_lag1 +0.47, q < 0,001; steps +0.33 | bad: sen < 5,5 h, bedtime > 08:00; good: kroki avg3 > 3000 | **Persona „Nocny marek: sen + ruch”.** Najsilniejsze liczby, ale nietypowy rytm dnia. |
| 4 | P10 | 76 | 23/37 | lightly_avg3 +0.32, sleep_h +0.31, q = 0,07 | bad: sen < 7 h; good: lightly avg3 > 340 | **Rezerwa za P16.** Sen + lekka aktywność; dane kończą się 29.02, więc lockdown nie zakłóca. Mniej dni. |
| 5 | P08 | 92 | 28/45 | sleep_h_avg3 +0.30, q = 0,04 | – | Drugi wariant „sen” (avg3, dług snu), wzorzec nie przechodzi testu globalnie. |
| 6 | P09 | 77 | 17/26 | sleep_h_lag1 +0.33, q = 0,01 | bad: sedentary avg3 > 750 | Sen; tylko 17 złych dni; kroki −76% po lockdownie. |
| 7 | P04 | 119 | 37/40 | bedtime_h_avg3 −0.26, q = 0,09 | – | Ciekawa „pora snu”, ale słabnie w dni robocze (−0,14). |
| 8 | P15 | 92 | 42/34 | bedtime +0.18, ns | – | Nic istotnego (wzorzec sRPE tylko bez reguły minority). |
| 9 | P07 | 122 | 28/46 | steps −0.15, ns | – | Nic. |
| 10 | P14 | 90 | 36/17 | rhr_night +0.42 (n_eff 25) | – | Artefakt trendu; wynik dnia silnie autokorelowany. |
| 11 | P05 | 100 | 45/7 | lightly +0.20, ns | – | Nic; zera w readiness; 7 dobrych dni. |
| 12 | P11 | 106 | 32/0 | srpe +0.16, ns | – | Mood w 95% stały, 0 dobrych dni. |
| 13 | P02 | 92 | 3/3 | – | – | Odpada na bramce wariancji (92% dni 3/3/3). |
| 14 | P13 | 28 | 6/5 | (mvpa −0.49) | – | Za mało danych, brak pliku RHR. |
| 15 | P03 | 24 | 8/0 | – | – | Za mało danych noszenia (mediana 13 h na dobę). |
| 16 | P12 | 1 | – | – | – | Brak snu i RHR. |

### 11.2 Wybrane persony – cechy i progi (sanity check stumpa)

Kolumna „bad: w warunku / poza” to odsetek złych dni.

**P06 – „Sen”** (M, 42 l.; 147 ankiet; poranne ankiety ok. 09:00; mood w 90% = 3, więc etykietę niosą fatigue i stress)

| cecha | lag | kierunek | ρ | n | warunek | bad: w warunku / poza | good: w warunku / poza |
| --- | --- | --- | --: | --: | --- | --- | --- |
| sleep_h | lag1 | więcej = lepiej | +0.38 | 145 | < 6,0 h | **36/56 = 64% vs 39%** | 0% vs 27% |
| sleep_h | lag1 | | | | > 6,5 h (przepis) | – | **19/54 = 35% vs 5%** (stump p = 0,02) |
| sleep_h | avg3 | więcej = lepiej | +0.35 | 146 | < 6,5 h | 54/95 = 57% vs 35% | 8% vs 29% |
| bedtime_h | lag1 | wcześniej = lepiej | −0.12 (ns) | 145 | po 00:30 | 52% vs 48% | – |

Przykładowe zdanie: *„When you sleep over 6.5 h, 19 of 54 days were good days (vs 5% otherwise).”* Ryzyko: przy etykiecie centrowanej medianą 49% dni P06 to „bad”; przy etykiecie spec byłoby to 19%.

**P01 – „Trening”** (M, 48 l.; mood w 94% = 3, więc etykieta to głównie zmęczenie)

| cecha | lag | kierunek | ρ | n | warunek | bad: w warunku / poza |
| --- | --- | --- | --: | --: | --- | --- |
| srpe_load | lag1 | mniej = lepiej | −0.32 | 119 | > 0 (był trening) | **23/29 = 79% vs 37%** (stump p_global < 0,01; pre-lockdown 22/28) |
| srpe_load | lag1 | | | | > 300 AU | 9/11 = 82% vs 44% |
| ex_min nie-Walk | lag1 | | −0.31 | 119 | > 0 | 25/34 = 74% vs 36% |
| lightly | lag1 | więcej = lepiej | +0.15 (ns; mood +0.28**) | 133 | < 200 min | 20/32 = 62% vs 44% |
| rhr_night | avg3 | (zły kierunek) | +0.28 | 136 | – | **nie pokazywać** (kierunek ustalony z góry go odrzuci) |

Zdanie: *„After days with a logged workout, 23 of 29 days were bad days (vs 37% otherwise).”* Przepis jest niedostępny (3 dobre dni), co dobrze pokazuje ekran „not enough good days yet”. Uwaga: dodatni kierunek treningu (więcej treningu → gorzej) trzeba dodać do tabeli 2.1 jako cechę „obciążenie”, jak przewiduje uwaga o aktywności.

**P16 – „Nocny marek: sen + ruch”** (M, 23 l.; zasypia ok. 06:15, ankieta ok. 16:00, ok. 1,6 tys. kroków dziennie)

| cecha | lag | kierunek | ρ | n | warunek | bad: w warunku / poza | good: w warunku / poza |
| --- | --- | --- | --: | --: | --- | --- | --- |
| sleep_h | lag1 | więcej = lepiej | +0.47 | 81 | < 5,5 h | **10/10 = 100% vs 23%** (p < 0,01) | 0% vs 35% |
| sleep_h | lag1 | | | | < 6,0 h | 13/16 = 81% vs 20% | |
| steps | avg3 | więcej = lepiej | +0.31 | 82 | < 2000 | 22/51 = 43% vs 16% | |
| steps | avg3 | | | | > 3000 (przepis) | | **9/14 = 64% vs 24%** (p = 0,02) |
| lightly | lag1 | więcej = lepiej | +0.27 | 78 | < 100 min | 23/55 = 42% vs 13% | (w dni robocze ρ = 0,08, więc to weekend) |
| bedtime_h | lag1 | wcześniej = lepiej | −0.21 | 81 | po 07:00 | 13/27 = 48% vs 24% | |

Ryzyka:
- Nietypowe liczby („went to bed at 7 am”, „under 2,000 steps”) mogą w demo wyglądać jak błąd danych. Wymaga to fabuły persony („student, night owl”) albo zamiany na P10.
- Tylko 77 dni.
- Efekt kroków częściowo wynika z weekendu.

**Rezerwa P10 – „Sen + lekka aktywność”** (K, 38 l.; 76 dni; brak dni po lockdownie)

| cecha | warunek | wynik |
| --- | --- | --- |
| sleep_h lag1 | < 7 h | bad 13/23 = 57% vs 19% (stump p = 0,03) |
| lightly avg3 | > 340 min | good 10/10 vs 42% (p < 0,01; tylko 10 dni) |
| lightly avg3 | < 260 min | bad 39% vs 22% |

### 11.3 Wnioski dla algorytmu ze sprawdzenia stumpa

1. **Zdegenerowane progi.** Score `Wilson_lower(P(zły|warunek)) − P(zły|reszta)` premiuje warunki, w których „reszta” to ok. 10 skrajnych dni z 0% złych. Przykłady bez ograniczenia:
   - P08: „sleep < 8,5 h → 27/81 = 33% vs 0/15”;
   - P15: „sRPE > 100 → 55% vs 10%” na 71 z 93 dni.

   **Rekomendacja:** warunek musi obejmować ≤ 50% ważnych dni danej cechy. Lepsze, ale bardziej złożone rozwiązanie to `Wilson_lower(in) − Wilson_upper(out)`. Z regułą minority zdania robią się sensowne, a liczba istotnych wzorców spada.
2. Przy MIN_SUPPORT = 10 i ok. 25 złych dniach wzorce 10/10 są możliwe i są wtedy najsilniejsze w rankingu (P16, P10).
3. Wzorzec istotny po teście globalnym (cykliczne przesunięcie, maksimum ze wszystkich kandydatów) ma tylko **5 osób z 12** (P01, P06, P09, P10, P16). Ekrany „Preliminary signals” i „Not enough evidence yet” będą częste, zgodnie z założeniem.
4. Wybór etykiety mocno zmienia wzorce. Przy etykiecie spec P06 dostaje wzorzec „bedtime > 01:00 → 7/10 złych”, a P01 dostaje „steps avg3 < 9000”. **Etykietę trzeba zamrozić przed finalnym przebiegiem.**

---

## 12. Plan czyszczenia i przygotowania (specyfikacja na następny krok)

Bazą jest `analysis/build_daily.py`; większość kroków jest już zaimplementowana. Poniżej pełna lista, z której zrobimy finalny `clean.py` i config.

1. **Uczestnicy.** Wczytujemy p01–p16 i logujemy wszystkich. Wykluczamy P12 (brak snu), P13 (28 pełnych dni, brak pliku RHR), P03 (24 pełne dni, noszenie ok. 13 h na dobę) i P02 (bramka wariancji). **Zostaje 12 osób.** Wykluczenia wynikają z reguł w krokach 11–12, nie są ręczne.
2. **Ankieta** (`pmsys/wellness.csv`):
   - `effective_time_frame` (UTC) → `Europe/Oslo`, zostawiamy `ts_local`.
   - Wartości spoza 1–5 w mood/fatigue/stress/soreness/sleep_quality → NaN; readiness 0 → flaga, readiness poza etykietą.
   - `hour < 5` → `date = date_cal − 1` (raport wieczorny).
   - Na dzień bierzemy pierwszy raport (dzienny ma pierwszeństwo przed przeniesionym nocnym).
   - Logujemy liczbę duplikatów.
3. **Etykieta.**
   - Pola M, F, S, wszystkie trzy wymagane.
   - Dla każdego pola `(x − mediana_osoby) / SD_osoby` (SD = 0 → 0); `comp = średnia`; `z = comp / SD(comp)`.
   - **zły: z < −0,5; dobry: z > +0,5**; reszta neutralne.
   - Mediany i SD liczymy na **dniach analizy** (pre-lockdown) i zamrażamy.
4. **Sen** (`fitbit/sleep.json`):
   - Tylko `mainSleep == True`, przypisany do `dateOfSleep`.
   - Ważny, gdy start w [18:00 D-1, 12:00 D], `minutesAsleep ≥ 120` i `efficiency > 0`. Przy kilku ważnych bierzemy najdłuższy.
   - Cechy: `sleep_h = minutesAsleep/60`; `bedtime_h = (startTime − (D − 6 h))` w godzinach, bez zawijania, bo P16 ma 12–14 h; `sleep_eff`; `wake_h`.
   - Łączymy `sleep_score.csv` po `sleep_log_entry_id = logId` → `rhr_night` (0 → NaN).
5. **Dostępność snu przed ankietą.** Gdy `endTime > ts_local + 60 min`, to `sleep_*_lag1 = NaN`, a avg3 liczymy z nocy D-1 i D-2. Dotyczy 16 dni (P04 11).
6. **Aktywność** (doba kalendarzowa, lokalnie):
   - `steps` = suma minut z `steps.json`.
   - `lightly`, `moderately`, `very`, `sedentary` z plików dziennych; `mvpa = moderately + very`.
   - `distance` i `calories` liczymy tylko do kontroli, nie jako cechy.
7. **Noszenie.**
   - `wear_min` i `wear_min_night` (00–06) z `cache/wear_minutes.csv` (`build_wear.py`); `wear_day = wear_min − wear_min_night`.
   - **`wear_day < 720` → wszystkie cechy aktywności tego dnia = NaN.**
   - `sedentary` NaN też przy `wear_min < 1200`, ale cecha i tak nie wchodzi do wyszukiwania.
   - Fallback bez HR: `sedentary ≥ 1400 OR steps < 500` → NaN.
8. **Trening.**
   - `srpe.csv`: `end_date_time` UTC → lokalna data; `load = RPE × duration`, suma na dzień; NaN RPE → pomijamy sesję.
   - W okresie od pierwszej do ostatniej sesji dni bez sesji = 0.
   - **Cecha aktywna tylko przy ≥ 25 sesjach** (P01, P04, P06, P07, P08, P10, P11, P14, P15; P02 wykluczony).
   - Kierunek: wyższe obciążenie → gorszy dzień. Dodatkowo próg binarny „> 0” („trening wczoraj”).
9. **Wyrównanie i lagi** (kluczowe, potrzebny test jednostkowy):
   - Sen: lag1 = noc kończąca się w D; avg3 = noce D, D-1, D-2.
   - Aktywność, trening, RHR: lag1 = dzień D-1; avg3 = D-1, D-2, D-3.
   - avg3 wymaga ≥ 2 z 3 ważnych wartości (NaN po filtrach się nie liczy).
   - Lagi liczymy po **dniach kalendarzowych**, nie po wierszach ankiet.
   - **Test:** P01, 2019-11-02. Ankieta 11:00 lokalnie; sen 00:09–07:19 (6,30 h, logId 24486013387, rhr_night 53); kroki z 2019-11-01 = 17 873; lightly = 245; mvpa = 130; wear_min (D-1) = 1421.
10. **Okno analizy.** Wzorce szukamy na dniach **D < 2020-03-12**. Późniejsze dni zostają w kalendarzu z flagą `post_lockdown` i wzorcami zamrożonymi na okresie wcześniejszym. Flagi `weekend_Dm1` (D-1 = sob/nd) i `holiday` (21.12–01.01) służą do kontroli zakłóceń.
11. **Dzień analizowalny („pełny”):** etykieta OK + `sleep_h_lag1` + `steps_lag1` nie są NaN. W wyszukiwaniu każda cecha używa swoich ważnych dni (parami); MIN_SUPPORT liczymy na tych dniach.
12. **Bramki.**
    - Osoba: SD surowej średniej M+F+S ≥ 0,20 oraz ≥ 60 pełnych dni.
    - Wzorce złych dni: ≥ 15 złych dni. Przepis: ≥ 15 dobrych dni. W przeciwnym razie API zwraca `insufficient_variation`, `insufficient_bad_days` lub `insufficient_good_days`.
13. **Outliery.** Bez winsoryzacji: metody rangowe i progowe są odporne. Twarde reguły walidacji:

    | cecha | NaN, gdy |
    | --- | --- |
    | sleep_h | < 2 albo > 14 |
    | sleep_eff | 0 |
    | rhr | 0 albo poza 30–110 |
    | steps | > 60 000 (nie wystąpiło) |

    Progi szukamy tylko w zakresie p5–p95 osoby.
14. **Braki.** Nie imputujemy. Brak ankiety → dzień wypada. Brak cechy → cecha NaN tylko w tym dniu, a dzień zostaje dla innych cech.
15. **Finalna lista cech do wyszukiwania wzorców** (kierunek złego dnia, siatka):

    | cecha | warianty | zły dzień, gdy | krok | grupa |
    | --- | --- | --- | --- | --- |
    | sleep_h | lag1, avg3 | poniżej X | 0,5 h | A |
    | bedtime_h | lag1, avg3 | później niż X | 0,5 h | B |
    | sleep_eff | lag1 | poniżej X | 1 pkt | C (opcjonalnie) |
    | steps | lag1, avg3 | poniżej X | 1000 (500 dla osób z zakresem < 5000) | D |
    | mvpa | lag1, avg3 | poniżej X | 10 min | E |
    | srpe_load | lag1, avg3 | powyżej X (0, 100, 200…) | 100 AU | E (tylko osoby logujące; zastępuje mvpa w grupie E) |
    | lightly | lag1, avg3 | poniżej X | 20 min | F |

    Tylko widok dnia i fallback (bez wyszukiwania): `rhr_night` (lag1, krok 1 bpm), `sedentary`, `time_in_bed`, `distance`, `calories`.
16. **Algorytm (poprawki do 2.2):** warunek obejmuje ≤ 50% ważnych dni cechy; MIN_SUPPORT = 10 bez zmian; jedna cecha z każdej grupy A–F.
17. **Logowanie N** per osoba po każdym kroku: ankiety → po deduplikacji → z etykietą → ze snem → z noszeniem → pełne → pre-lockdown. Wzorzec: tabela w pkt 4.
18. **Wyjście:** `daily_clean.parquet` (1 wiersz = osoba × D, kolumny `*_lag1` i `*_avg3`, flagi, `label`, `z`) oraz `participants.json` (bramki, mediany i SD etykiety, aktywne cechy).

---

## 13. Otwarte kwestie, niespodzianki, ryzyka

| # | Kwestia | Wpływ / propozycja |
| --- | --- | --- |
| 1 | **Wybór etykiety (mediana vs średnia)** zmienia liczbę złych i dobrych dni oraz wzorce (pkt 11.3). | Zamrozić przed finalnym przebiegiem. Rekomendujemy medianę (uzasadnienie semantyczne z pkt 3, sprzed korelacji). |
| 2 | **Regułę minority zaproponowaliśmy po obejrzeniu wyników stumpa** (ryzyko ręcznego przeuczenia). | Zweryfikować walidacją z pkt 5 koncepcji (przetasowane etykiety ≤ 5% osób z wzorcem) na wszystkich osobach. |
| 3 | Efekty są małe (ρ 0,15 w danych łącznych, 0,3–0,47 u najlepszych osób). U 7 z 12 osób nic nie przechodzi FDR ani testu globalnego. | Zgodnie z koncepcją; UI musi dobrze obsłużyć „not enough evidence”. |
| 4 | **P16 jest nietypowy:** sen ok. 06–14, ankieta ok. 16, ok. 1,6 tys. kroków przy ok. 21 h noszenia (możliwe, że zegarek liczy kroki słabo albo osoba prawie nie chodzi). | Jeśli zespół uzna liczby za nienaturalne w demo, bierzemy P10. |
| 5 | **RHR jest wygładzane** przez Fitbit, a jego związki idą w złą stronę (P01, P14). | Poza wyszukiwaniem wzorców (pkt 6). |
| 6 | sRPE: brak wpisu może znaczyć brak logowania, a nie odpoczynek. U P01 34 sesje przy 117 dniach z ćwiczeniem w `exercise.json`. | Wzorzec P01 („wpisany trening → zmęczenie”) może częściowo odzwierciedlać to, że ciężkie treningi są częściej logowane. Komunikować ostrożnie. |
| 7 | Weekend: związki P16 z ruchem i P04 z porą snu słabną w dni robocze. | Kontrola z pkt 5.4 koncepcji jest konieczna; wynik pokazać jako flagę przy wzorcu. |
| 8 | Choroba i epizody (P08 w styczniu, święta) nie są kontrolowane. | Test z cyklicznym przesunięciem częściowo to łagodzi; split-half to dodatkowa kontrola. |
| 9 | Zamieszanie ze strefami czasowymi: wellness i sRPE w UTC, Fitbit lokalnie, `sleep_score.timestamp` z fałszywym „Z”. Zmiana czasu 29.03.2020. | Obsłużone w `build_daily.py`; potrzebny test jednostkowy z pkt 12.9. |
| 10 | Ankiety po południu (P16, P09, P02, P13) nie są „poranne”, ale reguła D-1 jest bezpieczna. | Opcja: dla osób z ankietą po 12:00 rozważyć w przyszłości aktywność z D do godziny ankiety (poza demo). |
| 11 | Readiness 0 u P05 (60×) i 13 zer na skalach 1–5. | Traktujemy jako NaN; readiness nie wchodzi do etykiety. |
| 12 | Wyniki poza zakresem pytań: soreness reaguje na trening (ρ −0,27), sen wpływa na fatigue i stress, a nie na mood. | Do tekstów UI: „you feel more tired”, a nie „you're in a worse mood”. |

## Pliki

| Plik | Zawartość |
| --- | --- |
| `analysis/build_wear.py` | Minuty noszenia z `heart_rate.json` → `cache/wear_minutes.csv` |
| `analysis/build_daily.py` | Tabele `survey.csv`, `fitbit_day.csv`, `sleep_night.csv`, `daily.csv` (baza do czyszczenia) |
| `analysis/common.py` | Etykiety (spec i mediana), listy cech |
| `analysis/eda_survey.py` | Pkt 1–4 → `cache/eda_survey.out.md` |
| `analysis/eda_features.py` | Pkt 5–9 → `cache/eda_features.out.md`, `plots/trends.png` |
| `analysis/corr_target.py` | Korelacje cecha → wynik dnia → `cache/corr_person.csv`, `corr_pooled.csv`, `bad_good_medians.csv`, `analysis_table.csv` |
| `analysis/report_person.py` | Macierze per osoba → `cache/report_person.out.md` |
| `analysis/stump_check.py` | Szybki stump + test permutacyjny (`--minority`, `--spec`, `--prelock`) → `cache/stump_check*.csv/.out.md` |
| `analysis/persona.py` | Ranking i profile person → `cache/persona.out.md` |

Uruchamianie: `uv run --with pandas --with numpy --with scipy --with tabulate --with pyarrow --with matplotlib python <skrypt>.py`, w kolejności: build_wear → build_daily → eda_* → corr_target → stump_check `--minority` → persona.
