# Koncepcja analityczna – „dlaczego czuję się źle”

Oct 3, 2026 · uzupełnienie do [koncepcja.md](koncepcja.md)

## Cel i zakres

Dokument opisuje algorytmy dla dwóch głównych funkcji aplikacji:

1. **Wzorce z całego okresu** – zdania typu „Masz gorszy dzień, gdy śpisz mniej niż 6,5 h” i „Masz lepszy dzień, gdy dzień wcześniej robisz ponad 8000 kroków” (wzorce złych dni + przepis na dobry dzień).
2. **Kalendarz z możliwymi przyczynami** – przy każdym dniu etykieta samopoczucia i 0–2 możliwe przyczyny z ostatnich dni, np. „Possible reason: you walked under 3,000 steps yesterday”.

**Poza zakresem:** prognoza dnia (wraca później), modele ML, LLM.

Założenia z koncepcji produktu, które determinują wybór metod:

- analiza osobna dla każdej osoby, porównanie z własną normą,
- deterministyczna (te same dane → te same wnioski),
- wyjaśnialna jednym zdaniem z progiem i liczbą dni,
- „możliwa przyczyna”, nie diagnoza.

Obie funkcje korzystają z **jednego silnika**: funkcja 1 znajduje wzorce, funkcja 2 używa tych samych wzorców do tłumaczenia pojedynczych dni. Dzięki temu kalendarz pokazuje tylko przyczyny poparte powtarzalnym wzorcem, a nie przypadkowe odchylenia.

## Ograniczenia danych (dlaczego metody są takie proste)

- Okres to ~150 dni, ale ankiet jest średnio ~110 na osobę (1747 łącznie), a po złączeniu z danymi Fitbita zostanie zwykle 80–120 dni, z czego ~20–35 złych. Jedna osoba (P12) prawie nie ma danych o śnie i tętnie spoczynkowym. Wykrywalne są tylko silne efekty. Typowe zależności sen→nastrój u jednej osoby są słabe (r ≈ 0,1–0,3).
- Kolejne dni nie są niezależne (zły tydzień = jeden epizod, nie 7 dowodów).
- Etykieta jest gruba (skala 1–5) i część osób odpowiada prawie zawsze „3”.
- Ankiety bywają pomijane, częściej w złe dni. Bywają dni bez zegarka.
- Zakłócenia: weekend, trening, choroba, święta, początek COVID (marzec 2020).

Konsekwencja: **ciężkie ML odpada**, a część osób legalnie dostanie wynik „not enough evidence yet”. Projekt to akceptuje i obsługuje w UI.

## 1. Przygotowanie danych

### 1.1 Tabela dzienna

Jeden wiersz = jedna osoba × jeden dzień D (dzień ankiety).

| Źródło PMData | Agregacja |
| --- | --- |
| `fitbit/steps.json` (minutowe) | suma na dzień |
| `fitbit/*_active_minutes.json`, `sedentary_minutes.json` | już dzienne |
| `fitbit/resting_heart_rate.json` | już dzienne |
| `fitbit/sleep.json` | tylko `mainSleep`, przypisany do dnia pobudki (`dateOfSleep`) |
| `pmsys/wellness.csv` | jedna ankieta na dzień |
| `pmsys/srpe.csv` (opcjonalnie) | obciążenie treningowe na dzień (~50 sesji na osobę, nierówno) |
| `fitbit/sleep_score.csv` (opcjonalnie) | nocne tętno spoczynkowe, dostępne przed ankietą |

`fitbit/heart_rate.json` (bardzo duży) używamy **tylko raz, offline**, do policzenia minut noszenia zegarka na dzień (filtr dni bez zegarka). Jako cecha tętno spoczynkowe wystarcza.

### 1.1a Okno agregacji

Wszystko agregujemy do **dnia**, bo etykieta jest dzienna. Dzień kotwiczymy na ankiecie D:

- **sen** = główny sen (`mainSleep`) z `dateOfSleep = D`, czyli noc kończąca się rano D; przy dwóch głównych snach bierzemy dłuższy,
- **aktywność** = doba kalendarzowa D-1 (00:00–24:00 czasu lokalnego), zgodna z dziennymi plikami Fitbita,
- **ankieta**: `effective_time_frame` jest w UTC, konwertujemy na `Europe/Oslo` przed wyznaczeniem daty; przy kilku ankietach w dniu bierzemy pierwszą.

Krótsze okna (godzinowe) nie mają sensu przy dziennej etykiecie. Dłuższe (tygodniowe) dałyby ~20 punktów na osobę. Kumulację obsługuje wariant avg3.

### 1.2 Reguła dostępności przed ankietą (krytyczne)

Zakładamy, że ankieta jest wypełniana **rano** (publikacja PMData mówi tylko „typically once a day”, więc zespół analizy danych weryfikuje to w znacznikach czasu). Etykieta dnia D może zależeć tylko od tego, co wydarzyło się **przed ankietą**:

| Cecha | Wartość używana dla dnia D | Uwagi |
| --- | --- | --- |
| Sen (h), efektywność, godzina zaśnięcia | noc kończąca się rano D | kończy się przed ankietą |
| Kroki, aktywne minuty, minuty siedzące | dzień D-1 i wcześniej | dzień D dzieje się po ankiecie |
| Tętno spoczynkowe | dzień D-1 | Fitbit liczy je z całej doby D, więc wartość z D zawiera dane po ankiecie |
| Trening (sRPE), jeśli wchodzi | dzień D-1 | |

Ta reguła ma mieć **test jednostkowy** na jednym ręcznie sprawdzonym użytkowniku. Błąd tutaj psuje wszystkie wnioski.

### 1.3 Warianty czasowe (ile dni wstecz)

Każda cecha ma dwa warianty:

- **lag1** – ostatnia noc (sen) albo wczoraj (aktywność, tętno),
- **avg3** – średnia z 3 ostatnich nocy / dni (kumulacja, np. dług snu). Wymaga co najmniej 2 z 3 wartości.

**Maksymalnie 3 dni wstecz.** Efekty snu i aktywności trwają w literaturze ~1–2 dni, dług snu kumuluje się w ~3 noce, a każdy dodatkowy wariant zmniejsza moc testów. Użytkownik nie uwierzy też w przyczynę sprzed tygodnia.

### 1.4 Czyszczenie

- **Dni bez zegarka:** Fitbit liczy czas bez zegarka jako minuty siedzące, a brak kroków wygląda jak 0 kroków. Filtr opieramy na minutach noszenia z `heart_rate.json` (albo, prościej, na minutach siedzących bliskich 1440). Próg ustala zespół analizy danych.
- **Godzina zaśnięcia:** przesunąć skalę, żeby północ nie była skokiem (np. godziny od 18:00: 23:30 → 5,5, 00:30 → 6,5).
- **Aktywność względem normy:** kroki i aktywne minuty liczone dodatkowo jako odchylenie od kroczącej mediany z 28 dni, żeby sezon i lockdown nie udawały wzorca. Którą wersję używamy, decydujemy po EDA.
- **Dni bez ankiety** wypadają z analizy (nie imputujemy etykiety).
- **Logować N** po każdym filtrze, per osoba.

### 1.5 Etykieta dnia

1. Pola ankiety → ten sam kierunek („wyżej = lepiej”). **Kierunek każdej skali do weryfikacji w danych** (szczególnie fatigue i stress).
2. Z-score każdego pola w obrębie osoby, średnia → wynik dnia.
3. Ponowny z-score wyniku w obrębie osoby, potem:
   - **zły**: z < −0,5,
   - **dobry**: z > +0,5,
   - **neutralny**: pozostałe (także remisy).
4. **Bramka wariancji:** jeśli wynik osoby prawie się nie zmienia (np. zawsze „3”), analizy nie uruchamiamy i pokazujemy „not enough variation in your check-ins yet”.

**Dlaczego nie tercyle:** tercyle wymuszają 1/3 „złych” dni nawet u bardzo zadowolonej osoby, a przy odpowiedziach „zawsze 3” dzielą remisy losowo, czyli etykieta staje się szumem.

**`sleep_quality` w etykiecie:** jeśli wchodzi, sen z Fitbita „wygra” trywialnie (subiektywna jakość snu ≈ zmierzony sen). Rekomendacja: etykieta z mood + fatigue + stress (+ ewentualnie readiness), bez pól o śnie.

## 2. Funkcja 1 – wzorce z całego okresu

### 2.1 Kandydaci

Kierunek związku jest **ustalony z góry** na podstawie wiedzy domenowej, a nie wybierany przez algorytm. Daje to kilkukrotnie większą moc i eliminuje bzdurne wzorce („więcej snu → zły dzień”).

| Cecha | Warianty | Wzorzec złego dnia | Wzorzec dobrego dnia |
| --- | --- | --- | --- |
| Sen (h) | lag1, avg3 | poniżej X | powyżej X |
| Kroki | lag1, avg3 | poniżej X | powyżej X |
| Aktywne minuty | lag1, avg3 | poniżej X | powyżej X |
| Minuty siedzące | lag1, avg3 | powyżej X | poniżej X |
| Tętno spoczynkowe | lag1 | powyżej X | poniżej X |
| Godzina zaśnięcia | lag1 | później niż X | wcześniej niż X |

Lista cech i grupy współliniowe (kroki / dystans / kalorie / lightly active = jedna grupa) – do ustalenia z zespołem analizy danych.

**Uwaga o aktywności:** uczestnicy PMData mają różny poziom aktywności (od sportowców po osoby prawie nietrenujące). U aktywnych duża aktywność może dawać zmęczenie następnego dnia (zależność nieliniowa). Jeśli EDA to pokaże, dodajemy cechę obciążenia treningowego zamiast odwracać kierunek kroków.

### 2.2 Algorytm: progi + lift

Osobno dla etykiety „zły vs reszta” i „dobry vs reszta”. Dla każdej osoby:

```text
dla każdej cechy i wariantu (lag1 / avg3):
    dla każdego „ładnego” progu X (sen co 0,5 h, kroki co 1000, tętno co 2 bpm, ...):
        warunek = cecha po stronie ustalonego kierunku względem X
        jeśli w warunku albo poza nim jest < MIN_SUPPORT dni: pomiń
        score = Wilson_lower(P(zły | warunek)) − P(zły | brak warunku)
    zachowaj najlepszy próg dla cechy
zachowaj najlepszy wariant (lag1 albo avg3) dla cechy
w każdej grupie współliniowej zachowaj jedną cechę
```

- **Porównanie z dopełnieniem** („w 9 z 12 dni vs 20% w pozostałe”) daje wyraźny kontrast i naturalne zdanie.
- **Dolna granica przedziału Wilsona** (95%) zamiast surowego odsetka karze warunki z małą liczbą dni: 3 z 3 dni dostaje niższy wynik niż 10 z 13.
- **„Ładne” progi** od razu dają czytelne zdania i zmniejszają liczbę testowanych hipotez.

### 2.3 Istotność: test permutacyjny z przesunięciem cyklicznym

1. Szereg etykiet osoby przesuwamy cyklicznie o k dni, dla **każdego** k od 14 do n−14 (cechy zostają na miejscu). Przesunięcie zachowuje autokorelację etykiet (złe tygodnie zostają złymi tygodniami), a zrywa tylko związek z cechami.
2. Dla każdego przesunięcia uruchamiamy **całe** przeszukanie z 2.2 i zapisujemy **maksymalny** score ze wszystkich kandydatów.
3. Wzorzec jest **istotny**, gdy permutacyjne p ≤ 0,05, gdzie p = (1 + liczba przesunięć z maksimum ≥ score) / (1 + liczba przesunięć). Kryterium „powyżej 95. percentyla” z interpolacją przepuszczało wzorce z p ≈ 0,053, dlatego używamy p.

Porównanie z maksimum uwzględnia fakt, że wybieraliśmy najlepszy z wielu progów, cech i wariantów. Używamy wszystkich przesunięć, więc test jest w pełni deterministyczny (bez losowania i seeda).

### 2.4 Co widzi użytkownik

- Do **3 wzorców złych dni** i **3 wzorców dobrego dnia** (przepis), sortowane po score.
- Gdy żaden nie przejdzie, sekcja **„Preliminary signals”**: najlepszy wzorzec danej cechy, który przechodzi test porównany tylko z maksimami tej jednej cechy. Wyraźnie oznaczony jako wstępny („Early signal: …”). **Nie trafia do kalendarza.** Walidacja split-half pokazała, że wstępne wzorce zwykle się nie powtarzają.
- Gdy nie ma nawet tego: „Not enough evidence yet – keep checking in.”

Szablon zdania (wartości z danych):

> When you sleep under **6.5 h**, **9 of 12** days were bad days (vs **20%** otherwise).

Piszemy „days”, a nie „next days”: przy avg3 okna się nakładają, a kolejne dni to często jeden epizod. Liczby pokazujemy zawsze, żeby użytkownik sam ocenił wagę wzorca. Są nieco zawyżone (próg wybrany na tych samych danych), dlatego nie formułujemy ich jako prognozy.

## 3. Funkcja 2 – kalendarz z możliwymi przyczynami

### 3.1 Norma osoby

Dla każdej cechy (w jej wybranym wariancie) norma dobrych dni:

```text
z = (wartość − mediana_dobrych_dni) / max(1,4826 · MAD_dobrych_dni, minimalna_skala_cechy)
```

Minimalna skala (np. sen 0,25 h, kroki 500) zapobiega dzieleniu przez zero przy cechach o małym rozrzucie. Wymagane jest minimum ~10 dobrych dni. Inaczej norma = mediana wszystkich dni, z adnotacją w API.

### 3.2 Przyczyny dla złego dnia D

**A. Aktywne wzorce (główne źródło).** Spośród *istotnych* wzorców złych dni wybieramy te, których warunek był spełniony w dniu D. Sortujemy najpierw po sile wzorca, potem po |z|. Pokazujemy maksymalnie 2.

> Possible reason: you slept 5 h 40 min last night. When you sleep under 6.5 h, most of your days are bad.

**B. Brak aktywnego wzorca.**

> Nothing in your watch data stands out – the reason may be outside what we measure.

(Tekst do potwierdzenia z designem; propozycja: „No clear pattern explains this day”.)

**Usunięty fallback |z| > 2.** Pierwotnie planowaliśmy „Unusual: …” dla dni bez wzorca. Walidacja pokazała, że odpala w 41% złych dni i w 34% neutralnych, czyli w praktyce losowo. Usunięty decyzją z 3.10.2026.

Sprawdziliśmy też poluzowania (próg istotności 0,10, wstępne wzorce, „sen krótszy niż zwykle”). Każde obniża lift (częstość w złe dni / częstość w neutralne) z 3,5 do ~1,7, więc przyczyny zostają ścisłe. Pokrycie złych dni przyczyną: 12% ogółem, P10 63%, P16 48%, P01 35%, P06 0%.

Dobre dni obsługujemy symetrycznie (wzorce dobrego dnia). Dni neutralne nie mają przyczyn.

### 3.2a Porównanie z przeciętnym dobrym dniem (każdy dzień)

Osobny, **opisowy** poziom widoku dnia, który nie sugeruje przyczyny. Dla każdego dnia (złego, neutralnego i dobrego) pokazujemy do 2 cech wyszukiwania (lag1), które najbardziej odbiegały od **średniej z dobrych dni osoby**, o co najmniej 1 SD dobrych dni:

> You slept 1 h 40 min less than on your average good day.
> The day before you walked 6,308 fewer steps than on your average good day.

- Osoby z < 10 dobrymi dniami (P01, P05, P11) są porównywane z przeciętnym dniem („than on your average day”).
- Porównanie pojawia się w ~88% dni niezależnie od etykiety. W UI musi więc wyglądać inaczej niż „Possible reason” (np. szara sekcja „Compared with your average good day”).
- Dzięki temu 88% złych dni ma treść, a przyczyny zostają wiarygodne.

### 3.3 Oś czasu dnia

W widoku dnia mini-pasek D-3 … D-1 + ostatnia noc z wartościami cech. Dzień, z którego pochodzi przyczyna, jest podświetlony zgodnie z wariantem wzorca (ostatnia noc / wczoraj / ostatnie 3 dni).

## 4. Parametry

Parametry **zamrażamy przed obejrzeniem wyników wzorców**. Strojenie, aż persony dadzą ładne wzorce, to przeuczenie ręczne, które unieważnia test permutacyjny. Wartości startowe:

| Parametr | Start | Kto ustala |
| --- | --- | --- |
| Martwa strefa etykiety | ±0,5 z | zamrożone |
| Bramka wariancji etykiety | SD surowego M+F+S ≥ 0,20 i ≥ 60 pełnych dni | zamrożone |
| Bramka wzorców | ≥ 15 złych / ≥ 15 dobrych dni w oknie analizy | zamrożone |
| Filtr dni bez zegarka | ≥ 720 min noszenia w 06–24 | zamrożone |
| MIN_SUPPORT | 10 dni po każdej stronie progu | zamrożone |
| Pokrycie warunku | ≤ 50% ważnych dni cechy | zamrożone |
| Poziom istotności | permutacyjne p ≤ 0,05 względem maksimów | zamrożone |
| Zakres przesunięć | 14 … n−14 dni | zamrożone |
| Fallback w kalendarzu | brak (usunięty) | zamrożone |
| Porównanie z dobrym dniem | \|z\| ≥ 1 SD dobrych dni, max 2 cechy | zamrożone |
| Liczba wzorców / przyczyn | 3 + 3 / max 2 na dzień | zamrożone |

Jeśli parametry trzeba poprawić, robimy to wyłącznie na podstawie walidacji z punktu 5, na wszystkich 16 osobach.

## 5. Walidacja

Nie mamy „prawdziwych przyczyn”, więc sprawdzamy poprawność pośrednio:

1. **Przetasowane etykiety** – pipeline uruchomiony na losowo przetasowanych etykietach powinien znaleźć istotny wzorzec u ≤ 5% osób. Więcej oznacza, że test przepuszcza szum.
2. **Wstrzyknięty efekt** – na danych osoby sztucznie pogarszamy etykietę w dni z krótkim snem. Algorytm powinien to znaleźć z progiem blisko wstrzykniętego.
3. **Split-half** – wzorce z pierwszej połowy okresu sprawdzone na drugiej. Mierzymy, jaki odsetek się powtarza (kierunek + podobny próg).
4. **Kontrola zakłóceń** dla każdego istotnego wzorca:
   - czy trzyma się na samych dniach roboczych (weekend),
   - czy nie wynika tylko z okresu po 12.03.2020 (COVID).

### 5.1 Wyniki (3.10.2026, `analysis/validate.py`, szczegóły w `analysis/output/validation.md`)

| Test | Wynik |
| --- | --- |
| Fałszywe alarmy: przetasowane etykiety i etykiety innej osoby | 4,4–5,6% przebiegów z istotnym wzorcem (cel ≤ ~5%), więc test jest skalibrowany |
| Te same fałszywe alarmy bez limitu 50% / z `sleep_eff` | 4,2–6,8%, czyli decyzje podjęte po obejrzeniu wyników nie zawyżają fałszywych alarmów |
| Wstrzyknięty efekt (sen < 6 h → 70% złych dni vs 20%) | silnik znajduje go w 72% przebiegów, z progiem 6 ± 0,5 h |
| Split-half | 54% wszystkich wzorców się powtarza; wzorce P01 i P06 w obie strony, wstępne (P04) nie |
| Dni robocze | 7/7 istotnych wzorców trzyma się bez weekendów |
| COVID | wzorce szukamy tylko przed 12.03.2020, więc nie dotyczy |

Wniosek: przy silnym efekcie silnik działa, a fałszywych alarmów jest ~5%. Moc jest jednak ograniczona: nawet duży efekt umyka w ~28% przypadków, dlatego 7 z 12 osób nie ma istotnych wzorców.

## 6. Dane wyjściowe dla frontendu

Liczone offline dla wybranych person, serwowane jako gotowy JSON. Przykład wzorca:

```json
{
  "feature": "sleep_hours",
  "window": "last_night",
  "direction": "below",
  "threshold": 6.5,
  "kind": "bad",
  "level": "significant",
  "days_in_condition": 12,
  "target_days_in_condition": 9,
  "rate_in": 0.75,
  "rate_out": 0.20,
  "text": "When you sleep under 6.5 h, 9 of 12 days were bad days (vs 20% otherwise)."
}
```

Przykład dnia w kalendarzu:

```json
{
  "date": "2019-12-04",
  "label": "bad",
  "score_z": -1.3,
  "reasons": [
    {"source": "pattern", "feature": "sleep_hours", "window": "last_night",
     "value": 5.67, "norm": 7.4, "z": -2.6,
     "text": "Possible reason: you slept 5 h 40 min last night."}
  ]
}
```

Dokładne schematy ustala backend z frontendem.

## 7. Wybór person do demo

Po zamrożeniu parametrów uruchamiamy pipeline na **wszystkich 16 osobach**, dopiero potem wybieramy 2–3 persony. Kryteria:

- dużo dni z ankietą i z zegarkiem,
- etykieta przechodzi bramkę wariancji,
- co najmniej 2 istotne wzorce,
- **różne** wzorce u różnych person (np. jedna „sen”, druga „ruch”), żeby było widać personalizację.

Wybór person po fakcie jest w porządku, bo wybieramy przykłady do pokazania, a nie dopasowujemy algorytm.

## 8. Decyzje

| Decyzja | Status | Właściciel |
| --- | --- | --- |
| Ankieta rano → tylko cechy sprzed ankiety | ustalone, do weryfikacji w znacznikach czasu | zespół analizy danych |
| Warianty czasowe lag1 + avg3, max 3 dni | ustalone | – |
| Definicja etykiety, pola, `sleep_quality` | otwarte | zespół analizy danych |
| Kierunki skal w ankiecie | do weryfikacji w danych | zespół analizy danych |
| Filtr dni bez zegarka | otwarte | zespół analizy danych |
| Lista cech, cecha treningowa (sRPE) | otwarte | zespół analizy danych |
| Grupy współliniowe | otwarte | zespół analizy danych |
| Siatka „ładnych” progów | do potwierdzenia | zespół |
| Szablony tekstów | otwarte | zespół + frontend |
| Parametry statystyczne | wartości startowe z sekcji 4, zamrażane przed wynikami | zespół |

## 8a. Zamrożone ustawienia i format danych (stan na 3.10.2026)

Ustalenia z analiz [analiza-pmdata.md](analiza-pmdata.md) i [analiza-pmdata-runda2.md](analiza-pmdata-runda2.md) mają pierwszeństwo przed wcześniejszymi sekcjami tego dokumentu.

**Etykieta dnia:**
- pola: mood + fatigue + stress,
- centrowanie medianą osoby,
- mediana i SD liczone na dniach sprzed 12.03.2020,
- martwa strefa ±0,5.

**Cechy (tylko z zegarka, po jednej z grupy):**

| Grupa | Cecha |
| --- | --- |
| A. Długość snu | `sleep_h` |
| B. Pora snu | `bedtime_h` |
| C. Ciągłość snu | `wake_pct` |
| D. Objętość ruchu | `steps` |
| E. Intensywny wysiłek | `z_cardio_peak`, a gdy osoba ma < 20 dni z > 10 min: `mvpa` |
| F. Lekka aktywność | `lightly` |
| G. Struktura snu | `rem_pct` |
| I. Tętno nocne | `hr_sleep_mean` |

**Silnik wzorców:**
- warunek obejmuje maksymalnie 50% dni,
- MIN_SUPPORT = 10,
- wzorce szukamy tylko na dniach sprzed 12.03.2020.

**Persony:** P06 („sen”), P01 („wysiłek”), P10 („ciągłość snu + lekki ruch”). Zapasowa: P16.

**Pipeline:** `analysis/run_pipeline.sh` (clean → wzorce i kalendarz → walidacja → testy, ok. 1 min).

**Dane wyjściowe** (`analysis/clean.py` + `analysis/reasons.py` → `analysis/output/`):
- `daily_clean.csv`: 12 osób po bramkach,
- `daily_personas.csv`: same persony,
- `participants.json`: bramki, parametry etykiety, cecha grupy E,
- `feature_config.json`: katalog cech i parametry silnika,
- `cleaning_log.csv`: liczba dni po każdym kroku czyszczenia,
- `patterns.json`: wzorce z gotowymi tekstami,
- `calendar.json`: każdy dzień z etykietą, przyczynami, porównaniem z dobrym dniem i wartościami cech,
- `validation.md` / `validation.json`: wyniki walidacji.

Testy są w `analysis/test_clean.py` i `analysis/test_engine.py`.

## 9. Ograniczenia, które komunikujemy wprost

- To są **korelacje w danych użytkownika**, nie przyczyny. Stąd „possible reason”.
- Przy ~5 miesiącach danych widać tylko silne zależności. Brak wzorca nie znaczy, że zależności nie ma.
- Zegarek nie widzi większości tego, co wpływa na samopoczucie (ludzie, praca, zdrowie). Stąd komunikat „Nothing in your watch data stands out”.
- Podane liczby („9 of 12”) są opisem przeszłości, a nie skutecznością prognozy.
