// Mock of GET /api/users/{id}/days and /days/{date}. Field names follow backend/app/schemas.py
// (DaySummary, DayDetail, FeatureValue, Deviation) so swapping in real fetches is mechanical.
// Logic mirrors backend/app/insights/calendar.py in a simplified form.

export const TODAY = "2024-10-20";
const FIRST_DAY = "2024-08-01";

// Norm = the user's average good day (NormRange: average + 25th–75th percentile).
// badWhen: which direction this user's lower days lean (stands in for backend `leans` stats).
const FEATURES = [
  { feature: "sleep_h", label: "Sleep", unit: "h", when: "last_night", norm: { average: 7.4, low: 7.0, high: 7.9 }, sd: 0.55, badWhen: "lower" },
  { feature: "bedtime_h", label: "Bedtime", unit: "clock", when: "last_night", norm: { average: 5.1, low: 4.8, high: 5.5 }, sd: 0.5, badWhen: "higher" },
  { feature: "wake_pct", label: "Awake at night", unit: "%", when: "last_night", norm: { average: 8.4, low: 7.1, high: 9.6 }, sd: 1.8, badWhen: "higher" },
  { feature: "rhr_night", label: "Resting heart rate", unit: "bpm", when: "last_night", norm: { average: 61, low: 59, high: 63 }, sd: 2.2, badWhen: "higher" },
  { feature: "steps", label: "Steps", unit: "steps", when: "day_before", norm: { average: 7200, low: 6100, high: 8400 }, sd: 1500, badWhen: "lower" },
  { feature: "mvpa", label: "Brisk activity", unit: "min", when: "day_before", norm: { average: 38, low: 27, high: 49 }, sd: 12, badWhen: "lower" },
];

// The user's significant bad-day patterns (see Patterns screen); a day's possible reason
// is one whose condition held that day, as in calendar.day_reasons.
const PATTERNS = [
  { feature: "sleep_h", holds: (v) => v < 7, pattern_text: "Under 7h sleep: 1 in 2 lower days" },
  { feature: "steps", holds: (v) => v < 4000, pattern_text: "Under 4k steps: 1 in 4 lower days" },
];

// Last week matches the Today screen (Evidence card + "two short nights" forecast).
const PINNED = {
  "2024-10-14": { sleep_h: 5.6, steps: 4100 },
  "2024-10-15": { sleep_h: 6.6, steps: 3200 },
  "2024-10-16": { sleep_h: 5.9, steps: 5200 },
  "2024-10-17": { sleep_h: 7.4, steps: 2900 },
  "2024-10-18": { sleep_h: 6.1, steps: 3600 },
  "2024-10-19": { sleep_h: 6.7, steps: 2700 },
  "2024-10-20": { sleep_h: 6.8, steps: 1840 },
};

// ---------- formatting (like backend texts.fmt / compare_text) ----------

function hm(hours) {
  const total = Math.round(Math.abs(hours) * 60);
  const h = Math.floor(total / 60);
  const m = total % 60;
  return h ? `${h}h ${String(m).padStart(2, "0")}m` : `${m} min`;
}

export function formatValue(unit, v) {
  if (unit === "h") return hm(v);
  if (unit === "clock") {
    const total = Math.round((18 + v) * 60) % (24 * 60); // hours since 18:00 the evening before
    return `${String(Math.floor(total / 60)).padStart(2, "0")}:${String(total % 60).padStart(2, "0")}`;
  }
  if (unit === "%") return `${v.toFixed(1)}%`;
  if (unit === "steps") return Math.round(v).toLocaleString("en-US");
  if (unit === "bpm") return `${Math.round(v)} bpm`;
  return `${Math.round(v)} min`;
}

export function formatDiff(unit, d) {
  const sign = d > 0 ? "+" : "−";
  if (unit === "clock") return `${hm(d)} ${d > 0 ? "later" : "earlier"}`;
  if (unit === "h") return `${sign}${hm(d)}`;
  if (unit === "%") return `${sign}${Math.abs(d).toFixed(1)}%`;
  if (unit === "steps") return `${sign}${Math.round(Math.abs(d)).toLocaleString("en-US")}`;
  if (unit === "bpm") return `${sign}${Math.round(Math.abs(d))} bpm`;
  return `${sign}${Math.round(Math.abs(d))} min`;
}

// ---------- deterministic generation ----------

const iso = (d) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
const parse = (s) => {
  const [y, m, d] = s.split("-").map(Number);
  return new Date(y, m - 1, d);
};

/** Small seeded PRNG so every date always gets the same mock values. */
function random(seed) {
  let t = seed + 0x6d2b79f5;
  return () => {
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const gauss = (rnd) => (rnd() + rnd() + rnd() - 1.5) * 1.4;
const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));

function leans(f, diff) {
  if (Math.abs(diff) < f.sd * 0.25) return null; // too close to call
  return (diff < 0) === (f.badWhen === "lower") ? "bad" : "good";
}

/** Check-in score like backend absolute mode: 0 = typical, negative = worse. */
function scoreOf(s) {
  return (s.mood + s.sleep_quality + (6 - s.fatigue) + (6 - s.stress)) / 4 - 3;
}

function labelOf(score) {
  if (score >= 0.6) return "good";
  if (score <= -0.6) return "bad";
  return "neutral";
}

function buildDay(date, todayCheckIn) {
  const rnd = random(Number(date.replaceAll("-", "")));
  const pinned = PINNED[date] ?? {};

  // A "rough streak" factor makes bad days cluster a bit, like real data.
  const rough = gauss(rnd);
  const features = FEATURES.map((f) => {
    const towardBad = f.badWhen === "lower" ? -1 : 1;
    const raw = pinned[f.feature] ?? f.norm.average + (gauss(rnd) * 0.9 + rough * 0.5 * towardBad) * f.sd;
    const value = f.unit === "steps" ? Math.round(clamp(raw, 900, 16000)) : clamp(raw, 0, 99);
    const diff = value - f.norm.average;
    return {
      feature: f.feature,
      label: f.label,
      unit: f.unit,
      when: f.when,
      value,
      display: formatValue(f.unit, value),
      norm: f.norm,
      difference: diff,
      z: diff / f.sd,
      direction: diff > 0 ? "higher" : "lower",
      leans: leans(f, diff),
      text: `${f.label} ${formatDiff(f.unit, diff)} vs good days`,
    };
  });

  // Survey: today's comes from the live check-in; ~8% of past days have none.
  let survey = null;
  if (date === TODAY) {
    survey = todayCheckIn
      ? {
          mood: todayCheckIn.mood,
          fatigue: todayCheckIn.fatigue,
          sleep_quality: todayCheckIn.sleepQuality,
          stress: todayCheckIn.stress,
        }
      : null;
  } else if (rnd() > 0.08) {
    const badness = features.reduce((sum, f) => sum + (f.leans === "bad" ? Math.min(Math.abs(f.z), 2) : 0), 0);
    const base = 3.6 - badness * 0.35 + gauss(rnd) * 0.5;
    const answer = (offset) => clamp(Math.round(base + offset + gauss(rnd) * 0.6), 1, 5);
    survey = { mood: answer(0), fatigue: 6 - answer(0), sleep_quality: answer(0.2), stress: 6 - answer(-0.2) };
  }

  const score = survey ? scoreOf(survey) : null;
  const label = survey ? labelOf(score) : null;

  const reasons =
    label === "bad"
      ? PATTERNS.flatMap((p) => {
          const f = features.find((x) => x.feature === p.feature);
          return p.holds(f.value)
            ? [{ feature: f.feature, label: f.label, value: f.value, display: f.display, text: `Possible reason: ${f.display} ${f.label.toLowerCase()}`, pattern_text: p.pattern_text }]
            : [];
        }).slice(0, 2)
      : [];

  const deviations = features
    .filter((f) => Math.abs(f.z) >= 1)
    .sort((a, b) => Math.abs(b.z) - Math.abs(a.z))
    .slice(0, 2);

  let headline = null;
  if (reasons.length) headline = reasons[0].text;
  else if (deviations.length) headline = deviations[0].text;
  else if (label === "good" || label === "bad") headline = "No clear reason";

  return { date, label, score, survey, features, deviations, reasons, headline, has_reason: reasons.length > 0 };
}

// ---------- "endpoints" ----------

export const isAvailable = (date) => date >= FIRST_DAY && date <= TODAY;
export const FIRST_MONTH = FIRST_DAY.slice(0, 7);

/** Like GET /days?from&to: one DaySummary per date with data. */
export function listDays(from, to, todayCheckIn) {
  const out = [];
  for (let d = parse(from); iso(d) <= to; d.setDate(d.getDate() + 1)) {
    const date = iso(d);
    if (!isAvailable(date)) continue;
    const day = buildDay(date, todayCheckIn);
    out.push({
      date,
      label: day.label,
      score: day.score,
      has_reason: day.has_reason,
      headline: day.headline,
      top_deviations: day.deviations,
    });
  }
  return out;
}

/** Like GET /days/{date}: full DayDetail, or null outside the data range (backend 404). */
export function getDay(date, todayCheckIn) {
  return isAvailable(date) ? buildDay(date, todayCheckIn) : null;
}
