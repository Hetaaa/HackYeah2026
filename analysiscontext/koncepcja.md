# Opis aplikacji – hackaton wellness (PMData)

Oct 3, 2026 · @Kuba

## W skrócie

Webowa aplikacja (desktop), która łączy dane z zegarka sportowego z krótką codzienną ankietą samopoczucia i pokazuje użytkownikowi, co różni jego gorsze dni od dobrych. Zamiast kolejnego dashboardu z krokami i tętnem dajemy odpowiedź na pytanie „dlaczego czułem się źle?”.

**Slogany:**

- Curious about your body? Check it.
- Your bad days have reasons. Find them.
- Know why you feel the way you feel.

**Propozycje nazw** (robocze, do wyboru przez zespół):

- **Why Today** – wprost mówi, co robi apka.
- **Baseline** – nawiązuje do porównywania z własną normą.
- **Moodprint** – „odcisk” samopoczucia, każdy ma swój wzorzec.
- **Daycheck** – krótkie, pasuje do sloganu „Check it”.

## Problem i grupa docelowa

Zegarki i aplikacje fitness zbierają mnóstwo danych, ale pokazują je jako surowe liczby i wykresy. Użytkownik widzi, że spał 6h i zrobił 4000 kroków, ale nie wie, czy to ma jakikolwiek związek z tym, że miał kiepski dzień.

**Dla kogo:** zwykli ludzie, którzy są ciekawi własnego ciała i chcą zrozumieć, co i dlaczego się z nimi dzieje. Nie sportowcy wyczynowi i nie pacjenci. Nie muszą znać się na danych ani statystyce.

**Czego chcą:** prostej odpowiedzi w ludzkim języku, co wpływa na ich samopoczucie, oraz wskazówki, co zrobić, żeby dobrych dni było więcej.

## Główna idea i wyróżnik

Centralną metryką aplikacji jest **wellness**: jedna etykieta dnia złożona z odpowiedzi w ankiecie (nastrój, zmęczenie, jakość snu, stres). Sposób łączenia tych cech w jedną etykietę ustalamy w trakcie hackatonu. Każdy dzień użytkownika jest dzięki temu oznaczony jako dobry, neutralny albo zły.

Na tej podstawie aplikacja:

1. Buduje osobisty profil **dobrego dnia** użytkownika (jak wyglądają jego dane, kiedy czuje się dobrze).
2. Porównuje z nim każdy gorszy dzień i wskazuje cechy, które najbardziej odbiegały od normy.
3. Szuka **powtarzających się wzorców** w złych dniach, a nie tylko pojedynczych odchyleń.

**Wyróżnik na tle konkurencji:** inne aplikacje pokazują dane, my tłumaczymy je. Analiza jest w pełni spersonalizowana (każdy porównywany jest ze sobą, nie ze średnią populacji) i deterministyczna: te same dane zawsze dają te same, możliwe do wyjaśnienia wnioski. Formułujemy je jako „możliwe przyczyny”, nie diagnozę – aplikacja nie jest wyrobem medycznym.

## Dane

Na hackaton używamy datasetu PMData (Simula), który symuluje to, co w prawdziwym produkcie przychodziłoby z zegarka i z ankiety. Bierzemy tylko dwie części: dane z Fitbita i ankietę wellness.

| Źródło | Hackaton | Realny produkt | Przykładowe cechy |
| --- | --- | --- | --- |
| Dane obiektywne | Fitbit z PMData | Synchronizacja z zegarkiem sportowym | Sen, tętno spoczynkowe, kroki, minuty aktywności, kalorie |
| Dane subiektywne | Ankieta wellness z PMData | Codzienna ankieta w aplikacji | Nastrój, zmęczenie, jakość snu, stres (skala 1–5) |

W realnym produkcie nowy użytkownik przechodzi krótki onboarding (połączenie zegarka, pierwsza ankieta, wyjaśnienie, że wnioski pojawią się po zebraniu kilku tygodni danych).

## Główne funkcje

Aplikacja ma sześć kluczowych funkcji plus onboarding. Wszystkie wnioski są generowane deterministycznie, bez modeli językowych.

| Funkcja | Co robi | Co widzi użytkownik |
| --- | --- | --- |
| Kalendarz samopoczucia | Pokazuje każdy dzień oznaczony etykietą wellness | Miesiąc z kolorami dni; przy każdym dniu 1–2 cechy, które najbardziej odbiegały od dobrych dni |
| Widok dnia | Szczegóły wybranego dnia na tle osobistej normy | Wszystkie statystyki dnia, wyróżnione odchylenia i krótkie zdanie-wyjaśnienie, np. „Spałeś 1h40 krócej niż w swoje dobre dni” |
| Wzorce złych dni | Szuka cech, które powtarzają się w wielu złych dniach | Lista najczęstszych możliwych przyczyn, np. „W większości twoich złych dni spałeś poniżej 6h” |
| Przepis na dobry dzień | Odwrotność wzorców: co łączy najlepsze dni | Krótka „recepta” z 3–5 składnikami dobrego dnia użytkownika |
| Prognoza dnia | Na podstawie snu i ostatnich dni ocenia ryzyko gorszego dnia | Rano: przewidywane samopoczucie i główny powód, np. „Dziś możesz mieć słabszy dzień – druga krótka noc z rzędu” |
| Codzienna ankieta | Zbiera dane subiektywne | Jeden ekran, 4 suwaki 1–5, wypełnienie w około 10 sekund |
| Onboarding | Wprowadza nowego użytkownika | 2–3 ekrany: czym jest aplikacja, połączenie zegarka, pierwsza ankieta |

## Flow użytkownika i ekrany

Użytkownik przechodzi onboarding raz, a potem każdego dnia wypełnia ankietę i trafia na ekran główny z prognozą, skąd może wejść w kalendarz, wzorce albo przepis na dobry dzień.

&#91;embedded content: flow użytkownika · 7 ekranów\]

W demo dochodzi przełącznik persony (2–3 użytkowników z PMData), dostępny z każdego ekranu.

## Kontekst dla backendu

Backend zamienia surowe dane jednego użytkownika w gotowe wnioski dla frontendu. Na poziomie ogólnym przetwarzanie wygląda tak:

1. **Wczytanie i złączenie danych** z Fitbita i ankiety wellness w jedną tabelę: jeden wiersz = jeden dzień jednego użytkownika.
2. **Etykieta dnia**: złożenie cech z ankiety w jedną etykietę wellness (dobry / neutralny / zły).
3. **Osobista norma**: profil cech użytkownika w jego dobre dni.
4. **Odchylenia dnia**: dla każdego dnia, które cechy i o ile odbiegały od normy, posortowane od największego.
5. **Wzorce i przepis**: cechy częste w złych dniach, a rzadkie w dobrych (i odwrotnie dla przepisu na dobry dzień).
6. **Prognoza**: ocena ryzyka gorszego dnia na podstawie ostatnich danych.
7. **Teksty wyjaśnień**: zdania generowane z szablonów na podstawie wyników (bez LLM).

Ważne założenia: samopoczucie danego dnia zależy też od poprzednich dni (sen z poprzedniej nocy, aktywność z dnia wcześniej), co trzeba uwzględnić przy liczeniu cech. Szczegóły metod ustalamy osobno.

Frontend potrzebuje dla wybranego użytkownika: listy dni z etykietą i głównymi odchyleniami (kalendarz), pełnych danych jednego dnia, listy wzorców, przepisu na dobry dzień i prognozy. Na demo wyniki można policzyć wcześniej i serwować jako gotowe dane.

## Kierunek wizualny i ton

Aplikacja ma wyglądać jak spokojny, ciekawski przewodnik po własnym ciele, a nie jak medyczny raport czy sportowy dashboard. Platforma docelowa: web na desktop.

- **Najpierw wniosek, potem liczby.** Każdy ekran zaczyna się od zdania w ludzkim języku; szczegółowe statystyki są dostępne po kliknięciu.
- **Kolor niesie etykietę dnia.** Spójna, łagodna skala kolorów dla dobrych, neutralnych i złych dni, używana wszędzie (kalendarz, widok dnia, prognoza). Złe dni bez alarmowej czerwieni.
- **Odchylenia jako porównanie z normą.** Wartość dnia pokazana na tle zakresu dobrych dni użytkownika, żeby od razu było widać, w którą stronę i jak mocno odstaje.
- **Ton tekstów:** ciepły, prosty, w drugiej osobie, bez żargonu i bez straszenia. „Możliwa przyczyna” zamiast „przyczyna”. Zamiast ocen – ciekawość: „Sprawdź, co się działo”.
- **Język interfejsu:** angielski (spójnie ze sloganami).

## Zakres demo na hackaton

Demo pokazuje pełną ścieżkę na 2–3 uczestnikach z PMData, między którymi można przełączać się w interfejsie jak między personami. Każda persona powinna mieć wyraźnie inny wzorzec złych dni, żeby było widać, że analiza jest spersonalizowana.

**W demo:**

- [ ] Przełącznik użytkownika (2–3 persony)
- [ ] Kalendarz samopoczucia
- [ ] Widok dnia ze wszystkimi statystykami i odchyleniami
- [ ] Wzorce złych dni
- [ ] Przepis na dobry dzień
- [ ] Prognoza dnia
- [ ] Ekran codziennej ankiety
- [ ] Krótki onboarding (2–3 ekrany)

**Poza demo (tylko na slajdzie):** synchronizacja z prawdziwym zegarkiem, konta użytkowników, powiadomienia.
