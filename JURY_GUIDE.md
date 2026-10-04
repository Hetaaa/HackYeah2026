# why. — 2-minute guide for the jury

**Open:** <https://hack-yeah2026.vercel.app>

> **Before you start**
> - **Real people, real data.** The four users (Sam, Kim, Robin, Alex) are real, anonymous
>   participants of the public research dataset
>   [PMData](https://datasets.simula.no/pmdata/): Fitbit watch data + a daily wellness check-in,
>   recorded in 2019–2020. Each user's **"today"** is a day from that recording.
> - **Switching users is a demo-only feature.** Tap the **name in the top-right corner** to switch
>   at any time. It exists only so you can compare people; a real user sees only their own data.
> - **Fullscreen works best** (`F11`, or `Ctrl`+`Cmd`+`F` on Mac). If something is too small, zoom in
>   with `Ctrl` + `+` (`Cmd` + `+` on Mac), and `Ctrl` + `0` to reset.
> - The very first load can take up to a minute (the free server wakes up). After that it is fast.

## The main catch

Your watch counts your sleep and steps, but nobody tells you **why** you feel bad. **why.** learns
from **your own** days which watch signals come before **your** tough days. It warns you in the
morning, before you even say how you feel, and explains each day afterwards. No averages from
other people, no generic advice.

## 1. Sam: the morning warning (≈ 45 s)

First tap the name in the top-right corner → **Sam Carter**.

| Click | Notice |
| --- | --- |
| **Today** (start screen) | Sam's top 3 personal patterns around the heart, e.g. **"Awake over 12% of night: 15 of 27 days were tough"**. |
| Scroll to the dark card | **"Today you may feel a little under the weather"** plus **"Heads-up: awake 12.5% of night"**. This is a warning **before** the check-in, from last night's watch data only. |
| **Tell us how you feel today** → **Mood 3, Fatigue 1, Sleep quality 2, Stress 2** → **Save check-in** | The day is confirmed as tougher, with **"Possible reason: awake 12.5% of night"**. The morning warning was right, and the reason is Sam's own pattern. |

## 2. Sam: why we believe it (≈ 30 s)

| Click | Notice |
| --- | --- |
| **Patterns** (bottom bar) | **Strongest signal ×4.3**: after a restless night, a tough day is 4.3× more likely **for Sam**. |
| Under each pattern | **"Mostly: more tired, lower mood, more stressed"** shows what actually changes on those days. |
| **View all data** (under Strongest signal) | Every watch signal, Sam's good days vs lower days, side by side. |
| **Good-day recipe** tab | What Sam's good days share, e.g. **over 5h20 of light activity the day before**. |

## 3. Every day explained (≈ 20 s)

| Click | Notice |
| --- | --- |
| **Days** (bottom bar) | Calendar coloured by how Sam felt. |
| Tap **Feb 3** | A tough day with **"Possible reason: awake 15.2% of night"**. Below it, every signal compared with Sam's **average good day**, coloured toward lower / good days. |
| Tap a day **without** a reason | The app shows only the biggest difference and says it is **"not necessarily a cause"**. It does not invent reasons. |

## 4. Different person, different reason (≈ 25 s)

| Click | Notice |
| --- | --- |
| Name (top right) → **Kim Lee** → **Patterns** | Kim's tough days follow **short sleep: "Under 6h sleep: 10 of 13 days were tough", ×4**, and very late sleep (Kim is a night owl). Same app, completely different story. |
| Name → **Robin Hayes** → **Patterns** | After hard training Robin is **"Mostly: more tired"**, not in a worse mood. That is recovery, so the app does not say "stop training". The **Good-day recipe** tab is empty: with only 3 good days, the app says so instead of guessing. |

## What to look for

- **Personal, not generic:** every number comes from the user's own history.
- **Warns before, explains after:** a morning heads-up from watch data, and a "possible reason" after
  the check-in.
- **Honest:** patterns are tested against shuffled data (about 5% false alarms). Where there is no
  clear pattern, the app says so. A pattern is a correlation, not medical advice.

Optional, under **You**: **24-hour format** switch (all times become AM/PM) and **Privacy**
(what data is used and how).
