# why. – przewodnik dla jury (2 minuty)

**Otwórz:** <https://hack-yeah2026.vercel.app>

> **Zanim zaczniesz**
> - **Prawdziwi ludzie, prawdziwe dane.** Czterej użytkownicy (Sam, Kim, Robin, Alex) to prawdziwi,
>   anonimowi uczestnicy publicznego zbioru badawczego [PMData](https://datasets.simula.no/pmdata/):
>   dane z zegarka Fitbit i codzienna ankieta samopoczucia z lat 2019–2020. „Dziś” każdej osoby to
>   jeden dzień z tego nagrania.
> - **Przełączanie użytkownika jest tylko na potrzeby demo.** Kliknij **imię w prawym górnym rogu**.
>   Możesz przełączać w każdej chwili, żeby porównać osoby. Prawdziwy użytkownik widzi tylko swoje
>   dane.
> - **Najlepiej na pełnym ekranie:** `F11`, na Macu `Ctrl` + `Cmd` + `F`.
> - **Jeśli coś jest za małe:** powiększ przez `Ctrl` + `+` (Mac: `Cmd` + `+`), a wróć do normalnego
>   rozmiaru przez `Ctrl` + `0`.
> - **Pierwsze ładowanie** może potrwać do minuty, bo darmowy serwer się wybudza. Potem działa
>   szybko.

## Główna idea

Zegarek liczy sen i kroki, ale nikt nie mówi, **dlaczego** czujesz się gorzej.

**why.** uczy się na **twoich własnych** dniach, które sygnały z zegarka poprzedzają **twoje**
gorsze dni:
- ostrzega rano, zanim powiesz, jak się czujesz;
- potem wyjaśnia każdy dzień.

Bez średnich z populacji i bez ogólnych porad.

## 1. Sam: poranne ostrzeżenie (ok. 45 s)

Najpierw kliknij imię w prawym górnym rogu → **Sam Carter**.

| Kliknij | Zwróć uwagę |
| --- | --- |
| **Today** (ekran startowy) | 3 osobiste wzorce Sama wokół serca, np. **„Awake over 12% of night: 15 of 27 days were tough”**. |
| Przewiń do ciemnej karty | **„Today you may feel a little under the weather”** i **„Heads-up: awake 12.5% of night”**. To ostrzeżenie **przed** ankietą, tylko z danych zegarka z ostatniej nocy. |
| **Tell us how you feel today** → **Mood 3, Fatigue 1, Sleep quality 2, Stress 2** → **Save check-in** | Dzień potwierdza się jako gorszy, z **„Possible reason: awake 12.5% of night”**. Poranne ostrzeżenie się sprawdziło, a powód to własny wzorzec Sama. |

## 2. Sam: dlaczego temu wierzyć (ok. 30 s)

| Kliknij | Zwróć uwagę |
| --- | --- |
| **Patterns** (dolny pasek) | **Strongest signal ×4.3**: po niespokojnej nocy gorszy dzień jest 4,3 razy bardziej prawdopodobny, **u Sama**. |
| Pod każdym wzorcem | **„Mostly: more tired, lower mood, more stressed”**: co faktycznie zmienia się w te dni. |
| **View all data** (pod Strongest signal) | Wszystkie sygnały z zegarka: dobre dni Sama obok gorszych. |
| Zakładka **Good-day recipe** | Co łączy dobre dni Sama, np. **ponad 5h20 lekkiej aktywności dzień wcześniej**. |

## 3. Każdy dzień wyjaśniony (ok. 20 s)

| Kliknij | Zwróć uwagę |
| --- | --- |
| **Days** (dolny pasek) | Kalendarz pokolorowany według samopoczucia Sama. |
| Kliknij **3 lutego** | Gorszy dzień z **„Possible reason: awake 15.2% of night”**. Pod spodem każdy sygnał porównany z **przeciętnym dobrym dniem** Sama, z kolorem w stronę gorszych albo dobrych dni. |
| Kliknij dzień **bez** powodu | Aplikacja pokazuje tylko największą różnicę i pisze, że to **„not necessarily a cause”**. Nie wymyśla powodów. |

## 4. Inna osoba, inny powód (ok. 25 s)

| Kliknij | Zwróć uwagę |
| --- | --- |
| Imię → **Kim Lee** → **Patterns** | Gorsze dni Kim idą za **krótkim snem: „Under 6h sleep: 10 of 13 days were tough”, ×4** oraz bardzo późnym zasypianiem (Kim to nocny marek). Ta sama aplikacja, zupełnie inna historia. |
| Imię → **Robin Hayes** → **Patterns** | Po ciężkim treningu Robin jest **„Mostly: more tired”**, ale nie ma gorszego nastroju. To regeneracja, więc aplikacja nie mówi „przestań trenować”. Zakładka **Good-day recipe** jest pusta: przy 3 dobrych dniach aplikacja mówi to wprost, zamiast zgadywać. |

## Na co zwrócić uwagę

- **Osobiste, nie ogólne:** każda liczba pochodzi z historii danej osoby.
- **Ostrzega przed, wyjaśnia po:** rano ostrzeżenie z danych zegarka, po ankiecie „possible reason”.
- **Uczciwe:**
  - wzorce są testowane na losowo przemieszanych danych (ok. 5% fałszywych alarmów);
  - gdy nie ma wyraźnego wzorca, aplikacja to mówi;
  - wzorzec to korelacja, nie porada medyczna.

## Co jeszcze warto zobaczyć

- **Prognoza dnia (Today, ciemna karta).** Szansa na gorszy, typowy albo dobry dzień, np. **„77% chance of a tougher day”**. Liczy ją model XGBoost na przeszłych dniach, bez dzisiejszej ankiety.
- **Ostatnie 7 dni (Today, na dole).** Średni sen i kroki z ostatniego tygodnia na tle dobrych dni.
- **Przepis na dobry dzień (Today, karta „What helps you feel good”).** Skrót przepisu: składniki i jak często dni z nimi są dobre.
- **Cofnięcie ankiety.** W oknie ankiety przycisk **„Reset today’s check-in”** pozwala wypełnić ją jeszcze raz, np. inaczej, żeby zobaczyć inny wynik.
- **Historia w kalendarzu (Days).** Strzałki przy nazwie miesiąca prowadzą aż do listopada 2019. Pod miesiącem jest liczba dobrych, typowych i gorszych dni. Kliknięty dzień z przeszłości pokazuje też odpowiedzi z ankiety tamtego dnia.
- **Alex: przepis zamiast problemu.** Imię → **Alex Morgan** → **Patterns** → **Good-day recipe**: dobre dni Alexa idą za snem **powyżej 6h30**.
- **Ustawienia (You):**
  - przełącznik **24-hour format** zmienia wszystkie godziny w aplikacji na AM/PM;
  - **Privacy** wyjaśnia, jakie dane są używane i jak.
- **Integracje (You).** Karta Apple Health i lista „Other sources” to w demo **makiety**. Dane pochodzą z nagranego zbioru PMData. Jak podłączyć prawdziwe zegarki, opisujemy w `backend/docs/watch-sources.md`.
- **Dla technicznych:** dokumentacja API (Swagger) jest pod <https://whytoday-api.onrender.com/docs>.
