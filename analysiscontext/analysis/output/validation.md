# Walidacja silnika wzorców

Null: 100 permutacji etykiet na osobę + podmiana etykiet innej osoby. Wskaźnik = odsetek przebiegów z ≥ 1 istotnym wzorcem (cel ≤ ~5% na rodzaj).

| ustawienie | shuffle bad | shuffle good | swap bad | swap good | osoby z istotnym wzorcem (prawdziwe etykiety) |
| --- | --: | --: | --: | --: | --: |
| frozen | 4.4% | 4.8% | 5.3% | 5.6% | 5 |
| no_cover_limit | 4.3% | 4.4% | 4.5% | 4.2% | 5 |
| sleep_eff | 4.2% | 4.7% | 6.8% | 4.2% | 6 |

## Istotne wzorce na prawdziwych etykietach

**frozen**

- p01 bad: z_cardio_peak_lag1 above 10 (22/28, p=0.033)
- p06 good: sleep_h_lag1 above 6.5 (18/50, p=0.01)
- p09 bad: sleep_h_lag1 below 5.5 (9/15, p=0.0222)
- p10 bad: wake_pct_lag1 above 12 (16/30, p=0.04)
- p10 good: lightly_lag1 above 320 (15/18, p=0.02)
- p16 bad: sleep_h_lag1 below 6 (11/14, p=0.0204)
- p16 good: steps_avg3 above 3000 (9/14, p=0.0204)

**no_cover_limit**

- p06 good: sleep_h_lag1 above 6 (22/76, p=0.01)
- p09 bad: sleep_h_lag1 below 5.5 (9/15, p=0.0222)
- p09 good: lightly_lag1 above 120 (25/56, p=0.0222); steps_lag1 above 4000 (25/58, p=0.0222)
- p10 good: rem_pct_lag1 above 18 (36/65, p=0.04); sleep_h_lag1 above 6.5 (36/65, p=0.04)
- p15 good: bedtime_h_avg3 below 6 (31/71, p=0.0175)
- p16 bad: sleep_h_lag1 below 6 (11/14, p=0.0204)

**sleep_eff**

- p01 bad: z_cardio_peak_lag1 above 10 (22/28, p=0.033)
- p06 good: sleep_h_lag1 above 6.5 (18/50, p=0.01)
- p08 bad: lightly_avg3 below 200 (9/12, p=0.0175)
- p09 bad: sleep_h_lag1 below 5.5 (9/15, p=0.0222)
- p10 good: lightly_lag1 above 320 (15/18, p=0.02)
- p16 bad: sleep_h_lag1 below 6 (11/14, p=0.0204)
- p16 good: steps_avg3 above 3000 (9/14, p=0.0204)

## Split-half

Wzorce z jednej połowy okna sprawdzone na drugiej: 7/13 zachowuje kierunek (rate_in > rate_out), czyli 54%.

| osoba | kierunek | rodzaj | poziom | wzorzec | połowa uczenia | połowa testu | powtarza się |
| --- | --- | --- | --- | --- | --- | --- | --- |
| p01 | 1->2 | bad | significant | z_cardio_peak_avg3 above 10 | 0.73 vs 0.32 | 0.55 vs 0.32 (n_in 31) | tak |
| p01 | 2->1 | bad | significant | z_cardio_peak_lag1 above 10 | 0.75 vs 0.33 | 0.83 vs 0.43 (n_in 12) | tak |
| p04 | 1->2 | bad | preliminary | lightly_avg3 below 180 | 0.88 vs 0.26 | 0.14 vs 0.38 (n_in 14) | nie |
| p04 | 1->2 | bad | preliminary | steps_avg3 below 9000 | 0.62 vs 0.27 | 0.20 vs 0.34 (n_in 10) | nie |
| p04 | 1->2 | good | preliminary | bedtime_h_avg3 below 4.5 | 0.86 vs 0.31 | 0.32 vs 0.34 (n_in 19) | nie |
| p04 | 1->2 | good | preliminary | wake_pct_lag1 below 13 | 0.67 vs 0.33 | 0.26 vs 0.45 (n_in 31) | nie |
| p06 | 1->2 | good | preliminary | sleep_h_lag1 above 6.5 | 0.50 vs 0.14 | 0.21 vs 0.00 (n_in 24) | tak |
| p06 | 1->2 | good | preliminary | bedtime_h_avg3 below 5 | 0.58 vs 0.22 | 0.00 vs 0.08 (n_in 3) | nie |
| p06 | 2->1 | good | preliminary | sleep_h_lag1 above 6.5 | 0.21 vs 0.00 | 0.50 vs 0.14 (n_in 26) | tak |
| p07 | 1->2 | bad | preliminary | z_cardio_peak_lag1 above 40 | 0.46 vs 0.25 | 0.17 vs 0.07 (n_in 23) | tak |
| p07 | 2->1 | bad | preliminary | wake_pct_lag1 above 16 | 0.44 vs 0.04 | 0.50 vs 0.33 (n_in 6) | tak |
| p07 | 2->1 | good | preliminary | wake_pct_lag1 below 13 | 0.59 vs 0.30 | 0.38 vs 0.24 (n_in 29) | tak |
| p11 | 2->1 | bad | preliminary | bedtime_h_lag1 above 6 | 0.57 vs 0.18 | 0.28 vs 0.35 (n_in 18) | nie |

## Kontrola weekendu (istotne wzorce, tylko dni z D-1 w dzień roboczy)

Trzyma się: 7/7.

| osoba | rodzaj | wzorzec | wszystkie dni | dni robocze | trzyma się |
| --- | --- | --- | --- | --- | --- |
| p01 | bad | z_cardio_peak_lag1 above 10 | 0.79 vs 0.38 | 0.80 vs 0.37 (n_in 25) | tak |
| p06 | good | sleep_h_lag1 above 6.5 | 0.36 vs 0.07 | 0.34 vs 0.07 (n_in 32) | tak |
| p09 | bad | sleep_h_lag1 below 5.5 | 0.60 vs 0.12 | 0.64 vs 0.14 (n_in 11) | tak |
| p10 | bad | wake_pct_lag1 above 12 | 0.53 vs 0.15 | 0.57 vs 0.14 (n_in 21) | tak |
| p10 | good | lightly_lag1 above 320 | 0.83 vs 0.38 | 0.77 vs 0.40 (n_in 13) | tak |
| p16 | bad | sleep_h_lag1 below 6 | 0.79 vs 0.21 | 0.73 vs 0.23 (n_in 11) | tak |
| p16 | good | steps_avg3 above 3000 | 0.64 vs 0.21 | 0.56 vs 0.20 (n_in 9) | tak |

## Wstrzyknięty efekt

Reguła „sen < 6 h → zły dzień z p=0,7 (inaczej 0,2)” na prawdziwych cechach, 160 przebiegów: silnik znajduje istotny wzorzec snu w 72%, z progiem w odległości ≤ 0,5 h od 6 h w 72%.
