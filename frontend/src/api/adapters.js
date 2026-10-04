const toDate = (iso) => new Date(`${iso}T00:00:00Z`);
const toIso = (date) => date.toISOString().slice(0, 10);

export const formatLongDate = (iso) =>
  toDate(iso).toLocaleDateString("en-US", { weekday: "long", month: "short", day: "numeric", timeZone: "UTC" });

const weekdayInitial = (iso) => toDate(iso).toLocaleDateString("en-US", { weekday: "narrow", timeZone: "UTC" });

export function lastDays(iso, count) {
  return Array.from({ length: count }, (_, i) => {
    const date = toDate(iso);
    date.setUTCDate(date.getUTCDate() - (count - 1 - i));
    return toIso(date);
  });
}

const daysBetween = (from, to) => (from && to ? (toDate(to) - toDate(from)) / 86_400_000 + 1 : 0);

export const initialsOf = (name) =>
  name
    .split(/\s+/)
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

export function toApiAnswers(ui) {
  return { mood: ui.mood, fatigue: 6 - ui.fatigue, sleep_quality: ui.sleepQuality, stress: 6 - ui.stress };
}

export function fromApiAnswers(answers) {
  if (!answers) return null;
  return {
    mood: answers.mood,
    fatigue: 6 - answers.fatigue,
    sleepQuality: answers.sleep_quality,
    stress: 6 - answers.stress,
  };
}

const hasList = (report) => report.status === "ok" || report.status === "preliminary";
const percent = (rate) => Math.round(rate * 100);
const kindOf = (when) => (when === "last_night" || when === "last_3_nights" ? "sleep" : "steps");
const daysText = (p, tone) =>
  `${p.target_days_in_condition} of ${p.days_in_condition} days ${tone === "good" ? "felt good" : "were tough"}`;

function heroPatterns(patterns, recipe) {
  const bad = hasList(patterns) ? patterns.patterns.map((p) => ({ ...p, tone: "bad" })) : [];
  const good = hasList(recipe) ? recipe.ingredients.map((p) => ({ ...p, tone: "good" })) : [];
  return [...bad, ...good].slice(0, 3).map((p, i) => ({
    rank: i + 1,
    kind: kindOf(p.when),
    title: p.condition,
    subtitle:
      p.tone === "good"
        ? "Part of your good days"
        : p.level === "preliminary"
          ? "An early signal"
          : i === 0
            ? "Your clearest warning sign"
            : "A repeating pattern",
    frequency: daysText(p, p.tone),
  }));
}

const OUTLOOK = {
  tough: ["Today you may feel a little", "under the weather."],
  promising: ["Today looks", "promising."],
  mixed: ["Today brings", "mixed signals."],
  neutral: ["Nothing stands out", "today."],
  unknown: ["No watch data", "for today yet."],
};

const PREDICTED = {
  bad: ["Today you may feel a little", "under the weather."],
  neutral: ["Today looks like", "a typical day."],
  good: ["Today looks", "promising."],
};

const UNSURE = ["It's gonna be", "normal today."];
const SURE_ENOUGH = 0.55;

const CHECKED_IN = {
  good: ["You’re having", "a good day."],
  neutral: ["Looks like", "a typical day."],
  bad: ["Today feels like", "a tougher day."],
};

function forecast(today) {
  if (today.survey?.label) {
    const [lead, emphasis] = CHECKED_IN[today.survey.label];
    return { lead, emphasis, reason: today.summary, checkedIn: true };
  }
  const [lead, emphasis] = OUTLOOK[today.outlook];
  const signals = [...today.heads_up, ...today.good_signs];
  const reason = signals.length
    ? signals.map((s) => s.text).join(" · ")
    : today.deviations.map((d) => d.text).join(" · ");
  const agreeing = {
    bad: today.heads_up.map((s) => s.text).join(" · "),
    good: today.good_signs.map((s) => s.text).join(" · "),
    neutral: "",
  };
  return { lead, emphasis, reason, agreeing, checkedIn: false };
}

export function withPrediction(forecast, prediction) {
  if (forecast.checkedIn || prediction?.status !== "ok") return forecast;
  const sure = prediction[`p_${prediction.pred}`] >= SURE_ENOUGH;
  const [lead, emphasis] = sure ? PREDICTED[prediction.pred] : UNSURE;
  return { ...forecast, lead, emphasis, chance: prediction.text, reason: forecast.agreeing[prediction.pred] };
}

function recipeCard(recipe) {
  const items = hasList(recipe) ? recipe.ingredients.slice(0, 3) : [];
  return {
    statusText: recipe.summary,
    items: items.map((i) => ({
      key: i.feature,
      value: i.op === "above" ? `${i.display_threshold}+` : `<${i.display_threshold}`,
      label: i.label.toLowerCase(),
    })),
    goodDayRate: items.length ? percent(items[0].rate_in) : null,
  };
}

function evidence(persona, raw) {
  const valueOf = (day, name) => day?.features.find((f) => f.feature === name)?.value ?? null;
  const usualOf = (name) => raw.today.features.find((f) => f.feature === name)?.norm?.average ?? null;
  return {
    days: raw.dates.map(weekdayInitial),
    reference: persona.norm_reference === "all_days" ? "your average day" : "your good days",
    sleep: { hours: raw.days.map((d) => valueOf(d, "sleep_h")), usualHours: usualOf("sleep_h") },
    movement: { steps: raw.days.map((d) => valueOf(d, "steps")), usualSteps: usualOf("steps") },
  };
}

function strengthOf(feature, patterns) {
  const pattern = patterns.find((p) => p.feature === feature);
  if (!pattern) return null;
  return pattern.level === "significant" ? "strong" : "early";
}

function combination(patterns) {
  const top = patterns[0];
  if (!top || top.rate_out <= 0) return null;
  const multiplier = Math.round((top.rate_in / top.rate_out) * 10) / 10;
  return {
    multiplier,
    title: top.condition,
    text: `When this happens, a tougher day is ${multiplier}× more likely for you.`,
  };
}

export function buildToday(persona, raw) {
  return {
    date: formatLongDate(persona.today),
    patterns: heroPatterns(raw.patterns, raw.recipe),
    forecast: forecast(raw.today),
    recipe: recipeCard(raw.recipe),
    evidence: evidence(persona, raw),
  };
}

export function buildPatterns(raw) {
  const bad = hasList(raw.patterns) ? raw.patterns.patterns : [];
  const ingredients = hasList(raw.recipe) ? raw.recipe.ingredients : [];
  const weeks = Math.round(daysBetween(raw.stats.date_from, raw.stats.date_to) / 7);
  return {
    statusText: raw.patterns.summary,
    summary: {
      daysAnalyzed: raw.stats.analysed_days,
      toughDays: raw.stats.bad_days_count,
      patternsFound: bad.length,
    },
    reasons: bad.map((p) => ({
      key: p.feature,
      title: p.condition,
      frequency: `${daysText(p, "bad")}${p.level === "preliminary" ? " · early signal" : ""}`,
      drivers: p.drivers_text,
      share: percent(p.rate_in),
    })),
    comparison: {
      weeks,
      updated: `Based on ${raw.stats.analysed_days} days`,
      signals: [...raw.stats.features]
        .filter((f) => f.good.display || f.bad.display)
        .sort((a, b) => Number(b.in_patterns) - Number(a.in_patterns))
        .map((f) => ({
          name: f.label,
          strength: strengthOf(f.feature, bad),
          good: f.good.display ?? "–",
          lower: f.bad.display ?? "–",
          delta: f.difference_display ?? "",
        })),
    },
    combination: combination(bad),
    recipe: {
      statusText: raw.recipe.summary,
      goodDayRate: ingredients.length ? percent(ingredients[0].rate_in) : null,
      items: ingredients.map((i) => ({
        key: i.feature,
        area: i.label,
        title: i.condition,
        note: i.drivers_text ?? daysText(i, "good"),
        score: percent(i.rate_in),
      })),
    },
  };
}

export function buildDay(detail) {
  if (!detail) return null;
  return {
    date: detail.date,
    label: detail.label,
    summary: detail.summary,
    survey: fromApiAnswers(detail.survey),
    reasons: detail.reasons,
    deviations: detail.deviations,
    features: detail.features.filter((f) => f.in_patterns && f.value !== null && f.norm),
  };
}
