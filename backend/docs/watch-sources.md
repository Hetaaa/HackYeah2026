# Z jakich zegarków możemy brać dane

Stan na 3.10.2026. Dla zespołu i na slajd „co dalej”. Źródła na końcu.

## Czego potrzebuje nasz algorytm

| Cecha | Z jakich danych surowych | Konieczna? |
| --- | --- | --- |
| `sleep_h`, `bedtime_h` | sesja snu: start, koniec, czas snu | **tak** (najsilniejsze wzorce) |
| `wake_pct`, `rem_pct` | **fazy snu** (czuwanie, REM, głęboki, lekki) | bardzo przydatne |
| `hr_sleep_mean` | **próbki tętna** w czasie snu | przydatne |
| `steps` | kroki dziennie | **tak** |
| `mvpa` / `z_cardio_peak` | minuty umiarkowanej i intensywnej aktywności albo minuty w strefach tętna (da się policzyć z próbek tętna) | przydatne |
| `lightly` | minuty lekkiej aktywności (typowe dla Fitbita) | opcjonalne |
| filtr noszenia | pokrycie dnia próbkami tętna | przydatne (bez niego zakładamy, że zegarek był noszony) |

**Minimum:** sesje snu z fazami, próbki tętna i kroki. Resztę da się z nich policzyć.

Algorytm jest osobisty: porównuje osobę tylko z nią samą. Różne definicje u producentów
(np. „exercise minutes” Apple vs „intensity minutes” Garmina) więc nie przeszkadzają. Przeszkadza
dopiero zmiana zegarka w trakcie, bo urywa ciągłość danych.

## Źródła

| Zegarek / ekosystem | Udział w rynku 2025 | Jak dostać dane | Fazy snu | Tętno | Kroki / aktywność | Dostęp dla nas | Ocena |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **Fitbit, Google Pixel Watch** | – | **Google Health API** (chmura, Google OAuth). Fitbit Web API wyłączone 30.09.2026. | ✅ | ✅ próbki, strefy | ✅ kroki, active minutes, czas w strefach | otwarte (OAuth) | ✅ najprostsze, nasz algorytm powstał na danych Fitbita |
| **Apple Watch** | 17% (2.) | **HealthKit** tylko na iPhonie. Brak API serwer–serwer, potrzebna aplikacja iOS, która czyta dane i wysyła na backend. | ✅ (watchOS 9+: awake/core/deep/REM) | ✅ próbki | ✅ kroki, exercise minutes; brak „light minutes” | aplikacja iOS | ⚠️ pełne dane, ale wymaga apki mobilnej |
| **Xiaomi (Mi Band, Redmi Watch)** | 18% (1.) | **Brak publicznego API.** Mi Fitness zapisuje do **Health Connect** (Android) i Apple Health (iOS). | ⚠️ sesje snu tak, szczegółowa analiza zostaje w aplikacji Xiaomi | ✅ co minutę | ✅ kroki | przez Health Connect / HealthKit | ⚠️ możliwe, jakość faz do sprawdzenia |
| **Huawei** | 16% (3.) | **Huawei Health Kit** (chmura, dla zatwierdzonych partnerów) albo agregator (np. Thryve) | ✅ | ✅ | ✅ | wniosek partnerski | ⚠️ możliwe, ale formalności |
| **Samsung Galaxy Watch** | 9% (4.) | **Samsung Health Data SDK** (Android) albo **Health Connect** | ✅ | ✅ | ✅ | aplikacja Android | ⚠️ wymaga apki mobilnej |
| **Garmin** | 5% (5.) | **Garmin Health API** (chmura, push). **Program wstrzymany dla nowych deweloperów od wiosny 2026.** Alternatywy: agregator (Terra) albo Garmin → Apple Health / Health Connect. | ✅ | ✅ | ✅ kroki, intensity minutes | obecnie zamknięty | ❌ bezpośrednio teraz nie, ✅ pośrednio |
| **Amazfit (Zepp)** | – | Brak otwartego API chmurowego; Zepp zapisuje do **Health Connect** / Apple Health | ⚠️ jak Xiaomi | ✅ | ✅ | przez Health Connect / HealthKit | ⚠️ |
| **Polar** | – | **AccessLink API v3** (chmura, OAuth, darmowa rejestracja) | ✅ Sleep Plus Stages | ✅ continuous HR | ✅ dzienna aktywność, treningi | otwarte | ✅ łatwe |
| **Oura** (pierścień) | – | **Oura API v2** (OAuth, webhooki) | ✅ | ✅ próbki | ✅ kroki, czas aktywności | otwarte | ✅ łatwe |
| **Whoop** (opaska) | – | **Whoop API v2** (OAuth) | ✅ | ✅ podsumowania, strefy w treningach | ⚠️ strain zamiast kroków | otwarte | ⚠️ brak kroków (do weryfikacji) |
| **Withings** | – | Withings Public API (OAuth) | ✅ | ✅ | ✅ | otwarte | ✅ |

## Wnioski

1. **Dwie drogi pokrywają większość rynku:**
   - **Chmura (OAuth na backendzie):** Google Health API (Fitbit, Pixel), Polar, Oura, Withings,
     Whoop. Klienci w `app/clients/`, każdy z adapterem do `UserData` (jak `app/insights/fitbit.py`).
   - **Aplikacja mobilna:** iOS czyta HealthKit, Android czyta Health Connect, obie wysyłają dane
     na backend. Ta jedna droga obejmuje Apple Watch, Samsunga, Xiaomi, Amazfit, Pixel i pośrednio
     Garmina. To łącznie ok. **50%** rynku (Xiaomi 18%, Apple 17%, Samsung 9%, Garmin 5%).
2. **Najmniejszym kosztem** pierwsze prawdziwe źródło to **Google Health API**. Dane są
   najbliższe PMData (algorytm był walidowany na Fitbicie), a OAuth działa na backendzie bez apki
   mobilnej. Nasz parser `fitbit.py` obsługuje format starego Fitbit Web API, więc do Google Health
   API trzeba nowego adaptera (inny JSON, limity zakresów zapytań 14/90 dni).
3. **Huawei** (16% rynku) wymaga wniosku partnerskiego albo agregatora. **Garmin** chwilowo tylko
   pośrednio.
4. **Skrót przez agregator:**
   - **Open Wearables** (MIT, self-hosted, bez opłat za użytkownika): Garmin, Polar, Whoop, Strava,
     Apple Health, Samsung Health, Health Connect, Suunto, Oura.
   - **Terra** (od $499/mies.): ma też dostęp do Garmina mimo wstrzymanego programu.

   Adapter: jeden format agregatora → `UserData`.

## Co to znaczy dla kodu

- `app/insights/user.UserData` jest już niezależny od źródła. Każde nowe źródło to adapter
  produkujący noce (start, koniec, fazy, tętno w czasie snu) i dni (kroki, minuty aktywności,
  noszenie), zapisany jako wiersze `Day`.
- Brakujące cechy nie są błędem: algorytm pomija je w wyszukiwaniu wzorców (np. Apple bez
  `lightly`).
- Dla źródeł bez gotowych minut w strefach tętna liczymy je z próbek tętna (strefy jak u Fitbita:
  % tętna maksymalnego 220 − wiek).
- **Strefa czasowa per użytkownik** staje się konieczna, gdy pojawią się prawdziwi użytkownicy
  (teraz jest na sztywno `Europe/Oslo`).

## Źródła

- Google Health API i koniec Fitbit Web API: [About the Google Health API](https://developers.google.com/health/about), [Google Health API data types](https://developers.google.com/health/data-types?hl=en), [Momentum: Fitbit Web API deprecation](https://www.themomentum.ai/blog/fitbit-web-api-deprecation-google-health-migration), [Thryve: Fitbit shutdown September 2026](https://www.thryve.health/blog/fitbit-shutdown-september-2026-migration-options)
- Google Fit → Health Connect: [Mindbowser: Google Fit to Health Connect 2026](https://www.mindbowser.com/fetch-google-fit-data-continuously)
- Apple HealthKit: [Open Wearables: Apple HealthKit API](https://openwearables.io/blog/apple-healthkit-api-what-data-you-can-access-and-how), [WWDC22: What's new in HealthKit](https://developer.apple.com/wwdc22/10005)
- Garmin: [Terra: Garmin Connect Developer Program pause](https://tryterra.co/blog/garmin-connect-developer-program-pause), [Garmin Health API](https://developer.garmin.com/gc-developer-program/health-api/)
- Xiaomi / Amazfit: [Fitmesh: Xiaomi & Amazfit via Health Connect](https://www.fitmesh.fit/en/blog/xiaomi-amazfit-health-connect-data-dashboard), [Sahha: Xiaomi integration](https://sahha.ai/integrations/xiaomi/)
- Samsung: [Samsung Health SDK suite](https://samsungmobilepress.com/press-releases/samsungs-new-health-software-development-kit-suite-powers-advancements-in-healthcare-innovation), [Open Wearables: Samsung Health API](https://openwearables.io/blog/samsung-health-api-galaxy-watch-data-for-developers)
- Huawei: [Huawei Health Kit](https://developer.huawei.com/consumer/en/doc/HMSCore-Guides/overview-0000001177423513), [Thryve: Huawei Health Kit](https://www.thryve.health/huawei-health-kit-api-integration)
- Oura / Whoop / Polar: [Open Wearables integrations](https://openwearables.io/integrations), [Terra: WHOOP API 2026](https://tryterra.co/blog/whoop-api-data-access-permissions-limitations-2026), [Polar AccessLink API v3](https://www.polar.com/accesslink-api/)
- Agregatory: [Open Wearables vs Terra](https://openwearables.io/compare/terra), [Terra pricing](https://tryterra.co/community/pricing)
- Rynek: [MacTech: Apple 17% of wearables 2025](https://www.mactech.com/2026/02/27/apple-had-17-of-the-global-wearable-device-market-in-2025), [GSMArena: Huawei tops Q2 2025](https://m.gsmarena.com/huawei_tops_global_smartwatch_shipments_in_q2_2025-news-69270.php)
