# Do zespołu analizy danych: ustalenia z PMData

Hej! Mamy gotową koncepcję algorytmu (szczegóły w `koncepcja-analityczna.md`). Zanim zaczniemy implementować, potrzebujemy od was kilku ustaleń z datasetu PMData. Bez nich backend nie ruszy.

> **Ważne:** sprawdzamy tylko **strukturę** danych. Nie liczcie jeszcze korelacji cech Fitbita z samopoczuciem (np. sen vs mood). Jeśli dobierzemy parametry pod wyniki, które już widzieliśmy, test istotności przestaje cokolwiek znaczyć.

**Co już wiemy z publikacji PMData:**

- P12 prawie nie ma snu ani tętna spoczynkowego, więc wykluczamy.
- Ankiet jest średnio ~110 na osobę (1747 łącznie).
- Skale 1–5: 3 = norma, 1–2 poniżej normy, 4–5 powyżej normy. Readiness 0–10, gdzie 10 = najlepiej.

---

## 1. Godzina ankiety (krytyczne)

Publikacja mówi tylko „typically once a day”, a cały algorytm zakłada ankietę poranną.

- Rozkład godzin `effective_time_frame` per uczestnik (UTC → przeliczyć na `Europe/Oslo`).
- Ile jest dni z więcej niż jedną ankietą oraz ile ankiet po południu lub wieczorem.

**Wynik:** potwierdzenie „rano” + reguła dla wyjątków (np. ankieta po 12:00 → odrzucić albo przypisać inaczej).

## 2. Kontrola kierunku skal

Publikacja sugeruje „wyżej = lepiej” dla wszystkich pól. Sprawdźcie szybko, czy fatigue, stress i soreness korelują dodatnio z mood i readiness (to korelacje wewnątrz ankiety, więc OK).

**Wynik:** tabela pole → kierunek.

## 3. Etykieta dnia

- Które pola wchodzą do wyniku. Nasza rekomendacja: mood + fatigue + stress (+ ewentualnie readiness), **bez** `sleep_quality` i `sleep_duration_h`, bo pokrywają się z danymi z Fitbita. Soreness do decyzji (raczej trening niż samopoczucie).
- Per uczestnik: SD wyniku i odsetek dni z samymi „3”.

**Wynik:** lista pól + próg minimalnej zmienności, poniżej którego nie analizujemy osoby.

## 4. Kompletność danych per uczestnik

Tabela z liczbą dni:

- z ankietą,
- z głównym snem (`isMainSleep`),
- z tętnem spoczynkowym,
- z pełnym kompletem: ankieta z dnia D + sen kończący się w D + aktywność z D-1.

**Wynik:** tabela uczestnik × liczby dni. Ostatnia kolumna to liczba dni, na której naprawdę będziemy liczyć.

## 5. Filtr dni bez zegarka

Fitbit liczy czas bez zegarka jako minuty siedzące, a brak kroków wygląda jak 0 kroków.

- Policzcie raz minuty noszenia na dzień z `heart_rate.json` (minuty z jakimkolwiek odczytem).
- Porównajcie z prostszą regułą „minuty siedzące ≥ ~1400”.

**Wynik:** reguła wykluczania dnia, np. „< 18 h noszenia → wykluczamy”.

## 6. Lista cech

- Potwierdźcie: sen (h, efektywność, godzina zaśnięcia), kroki, aktywne minuty (moderately + very), minuty siedzące, tętno spoczynkowe.
- Tętno spoczynkowe: `resting_heart_rate.json` (doba D-1) czy nocne z `sleep_score.csv` (noc przed ankietą, ale mniej wpisów)? Sprawdźcie pokrycie obu.
- Pokrycie `srpe.csv` / `exercise.json` per osoba: czy cecha treningowa ma sens dla kogokolwiek.

**Wynik:** finalna lista cech + decyzja w sprawie tętna i treningu.

## 7. Grupy cech współliniowych

Z góry wypadają kalorie (zawierają przemianę spoczynkową) i dystans (≈ kroki × długość kroku). Sprawdźcie korelacje **między cechami Fitbita** (bez etykiety): kroki vs lightly / moderately / very active vs sedentary.

**Wynik:** grupy, z których algorytm bierze po jednej cesze.

## 8. Zakresy do siatki progów

Percentyle p10–p90 dla każdej cechy (wszyscy uczestnicy razem).

**Wynik:** krok progu na cechę. Wstępnie: sen co 0,5 h, kroki co 1000, tętno co 2 bpm, aktywne minuty co 10.

## 9. Trend w czasie

Kroki i wynik ankiety w czasie, ze szczególną uwagą na święta i okres po 12.03.2020 (lockdown w Norwegii).

**Wynik:** czy aktywność liczymy w wartościach bezwzględnych, czy jako odchylenie od kroczącej mediany z 28 dni.

---

## Agregacja (dla kontekstu, już ustalona)

Wszystko agregujemy do **dnia**, zakotwiczonego na ankiecie z dnia D:

- **sen** = główny sen z `dateOfSleep = D` (noc kończąca się rano D),
- **aktywność** = doba kalendarzowa D-1 (00:00–24:00 czasu lokalnego),
- **ankieta** = pierwsza ankieta z dnia D (po przeliczeniu na czas lokalny).

## Czego potrzebujemy na koniec

Jeden notebook z wynikami punktów 1–9: tabele + krótkie decyzje. Na tej podstawie zamrażamy config, puszczamy pipeline na wszystkich osobach i dopiero wtedy wybieramy 2–3 persony do demo.

Pytania wrzucajcie do wątku. Dzięki!
