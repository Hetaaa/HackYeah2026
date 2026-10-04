# why. – przewodnik dla jury

**<https://hack-yeah2026.vercel.app>**

> - Użytkownicy to **prawdziwi, anonimowi ludzie** ze zbioru [PMData](https://datasets.simula.no/pmdata/) (zegarek Fitbit + codzienna ankieta).
> - **Imię w prawym górnym rogu** przełącza osobę. Możesz to robić w każdej chwili. To funkcja tylko na potrzeby demo.
> - Najlepiej na pełnym ekranie (`F11`). Za małe? `Ctrl` + `+`.
> - Pierwsze ładowanie może potrwać do minuty, bo serwer się wybudza.

**Idea:** aplikacja uczy się na **twoich** dniach, co z zegarka poprzedza **twoje** gorsze dni. Rano ostrzega, a po ankiecie wyjaśnia dzień.

## 1. Sam: ostrzeżenie rano

1. Imię → **Sam Carter**.
2. **Today**, ciemna karta: *„Heads-up: awake 12.5% of night”*. Ostrzeżenie jeszcze **przed** ankietą.
3. **Tell us how you feel today** → **3, 1, 2, 2** → **Save**. Wynik: *„Possible reason: awake 12.5% of night”*, czyli ostrzeżenie się sprawdziło.

## 2. Sam: dowody

**Patterns**:
- **×4.3**: po niespokojnej nocy gorszy dzień jest 4,3 razy bardziej prawdopodobny.
- **„Mostly: …”**: co się wtedy zmienia.
- **View all data**: dobre dni obok gorszych.

## 3. Każdy dzień wyjaśniony

**Days** → kliknij **3 lutego**:
- *„Possible reason”* z wzorca Sama;
- porównanie z jego przeciętnym dobrym dniem.

Dzień bez powodu jest opisany jako *„not necessarily a cause”*.

## 4. Inna osoba, inny powód

- **Kim** → **Patterns**: krótki sen (*Under 6h sleep*, ×4).
- **Robin** → **Patterns**: po treningu tylko *„more tired”*. Aplikacja nie mówi „przestań trenować”, a pusty przepis = za mało dobrych dni, więc nie zgaduje.

## Co jeszcze warto zobaczyć

- **Today**:
  - prognoza (*„77% chance of a tougher day”*, model XGBoost);
  - ostatnie 7 dni na tle dobrych dni;
  - przepis na dobry dzień.
- **Reset today's check-in** w oknie ankiety: wypełnij jeszcze raz, inaczej.
- **Days**: strzałki miesięcy (od listopada 2019) i odpowiedzi z dawnych ankiet.
- **Alex** → **Good-day recipe**: sen powyżej 6h30.
- **You**:
  - **24-hour format**, **Privacy**;
  - Apple Health i „Other sources” to w demo makiety.
- API (Swagger): <https://whytoday-api.onrender.com/docs>
