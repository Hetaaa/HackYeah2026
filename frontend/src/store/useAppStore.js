import { create } from "zustand";

// Mock data shaped like the Figma screens. Swap for /api calls later.
const user = {
  firstName: "Alex",
  lastName: "Morgan",
  initials: "AM",
  email: "alex.morgan@example.com",
  memberSince: "Aug 2024",
  stats: { daysTracked: 81, checkIns: 76, streak: 12 },
};

const today = {
  date: "Sunday, Oct 20",
  patterns: [
    {
      rank: 1,
      kind: "sleep",
      title: "Under 7h sleep",
      subtitle: "Your clearest warning sign",
      frequency: "1 in 2 tough days",
    },
    {
      rank: 2,
      kind: "steps",
      title: "Under 4k steps",
      subtitle: "A repeating pattern",
      frequency: "1 in 4 tough days",
    },
    {
      rank: 3,
      kind: "stress",
      title: "Stress at 4–5",
      subtitle: "Often part of a mix",
      frequency: "1 in 5 tough days",
    },
  ],
  forecast: {
    lead: "Today you may feel a little",
    emphasis: "under the weather.",
    reason: "Your last two days you did not sleep well. Try getting more sleep",
  },
  recipe: {
    items: [
      { value: "7h+", label: "sleep" },
      { value: "6k", label: "steps" },
      { value: "Low", label: "evening stress" },
    ],
    goodDayRate: 82,
  },
  // Last 7 days, oldest first; the final entry is today. `usual` = the user's typical day.
  evidence: {
    days: ["M", "T", "W", "T", "F", "S", "S"],
    sleep: {
      hours: [5.6, 6.6, 5.9, 7.4, 6.1, 6.7, 6.8],
      usualHours: 7.2,
    },
    movement: {
      steps: [4100, 3200, 5200, 2900, 3600, 2700, 1840],
      usualSteps: 6100,
      note: "A short walk could lift your day",
    },
  },
};

const patterns = {
  summary: { daysAnalyzed: 123, toughDays: 45, patternsFound: 8 },
  reasons: [
    { title: "Less than 7h sleep", frequency: "1 in 2 tough days", share: 50 },
    { title: "Under 4k steps", frequency: "1 in 4 tough days", share: 25 },
    { title: "Stress at 4–5", frequency: "1 in 5 tough days", share: 20 },
  ],
  comparison: {
    weeks: 8,
    updated: "Updated today",
    // strength: "strong" | "medium" | "early"
    signals: [
      { name: "Sleep duration", strength: "strong", good: "7h 24m", lower: "6h 21m", delta: "−1h 03m" },
      { name: "Daily movement", strength: "strong", good: "7,210", lower: "3,280", delta: "−55%" },
      { name: "Resting heart rate", strength: "medium", good: "61 bpm", lower: "65 bpm", delta: "+4 bpm" },
      { name: "Evening stress", strength: "strong", good: "1.8 / 5", lower: "3.4 / 5", delta: "+1.6" },
      { name: "Active minutes", strength: "medium", good: "42 min", lower: "24 min", delta: "−18 min" },
      { name: "Sleep consistency", strength: "early", good: "± 32m", lower: "± 1h 12m", delta: "+40 min" },
    ],
  },
  combination: {
    multiplier: 3.1,
    title: "Short sleep + low movement",
    text: "When both happen, a lower day is 3.1× more likely for you.",
  },
  recipe: {
    goodDayRate: 82,
    items: [
      { area: "Sleep", title: "Protect 7+ hours", note: "Your strongest signal", score: 92 },
      { area: "Movement", title: "Move 6–9k steps", note: "A comfortable range", score: 76 },
      { area: "Evening stress", title: "Wind down calmly", note: "Low after 8pm", score: 68 },
    ],
    tryToday: {
      title: "Take a 20-minute walk before lunch.",
      text: "It’s the easiest part of your recipe to influence right now.",
    },
  },
};

// Daily check-in: four 1–5 scales. low/high describe what 1 and 5 mean.
export const CHECK_IN_METRICS = [
  { key: "mood", label: "Mood", low: "Awful", high: "Great" },
  { key: "fatigue", label: "Fatigue", low: "Fresh", high: "Exhausted" },
  { key: "sleepQuality", label: "Sleep quality", low: "Poor", high: "Great" },
  { key: "stress", label: "Stress", low: "Calm", high: "Very high" },
];

export const useAppStore = create((set) => ({
  user,
  today,
  patterns,
  checkIn: null, // { mood, fatigue, sleepQuality, stress } once saved
  isCheckInOpen: false,
  openCheckIn: () => set({ isCheckInOpen: true }),
  closeCheckIn: () => set({ isCheckInOpen: false }),
  saveCheckIn: (checkIn) => set({ checkIn }),
  // Mock Apple Health sync: nothing is fetched, only the "last synced" label changes.
  lastHealthSync: "Today, 07:42",
  markHealthSynced: () => set({ lastHealthSync: "Just now" }),
}));
