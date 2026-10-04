import { create } from "zustand";
import { api } from "../api/client.js";
import { buildPatterns, buildToday, fromApiAnswers, initialsOf, lastDays, toApiAnswers } from "../api/adapters.js";

// Daily check-in: four 1–5 scales. low/high describe what 1 and 5 mean.
export const CHECK_IN_METRICS = [
  { key: "mood", label: "Mood", low: "Awful", high: "Great" },
  { key: "fatigue", label: "Fatigue", low: "Exhausted", high: "Rested" },
  { key: "sleepQuality", label: "Sleep quality", low: "Poor", high: "Great" },
  { key: "stress", label: "Stress", low: "Very high", high: "Calm" },
];

const MOCK_PROFILE = {
  email: "alex.morgan@example.com",
  memberSince: "Aug 2024",
  stats: { daysTracked: 81, checkIns: 76, streak: 12 },
};

const userOf = (persona) => ({
  ...MOCK_PROFILE,
  firstName: persona.name,
  lastName: persona.last_name,
  initials: initialsOf(`${persona.name} ${persona.last_name}`),
});

const PERSONA_KEY = "why.persona";
const EVIDENCE_DAYS = 7;

function readSavedPersona() {
  try {
    return localStorage.getItem(PERSONA_KEY);
  } catch {
    return null;
  }
}

function savePersona(id) {
  try {
    localStorage.setItem(PERSONA_KEY, id);
    return true;
  } catch {
    return false;
  }
}

async function loadPersona(persona) {
  const id = persona.id;
  const dates = lastDays(persona.today, EVIDENCE_DAYS);
  const [today, patterns, recipe, stats, ...days] = await Promise.all([
    api.today(id),
    api.patterns(id),
    api.recipe(id),
    api.stats(id),
    ...dates.map((date) => api.day(id, date)),
  ]);
  const raw = { today, patterns, recipe, stats, dates, days };
  return {
    today: buildToday(persona, raw),
    patterns: buildPatterns(raw),
    checkIn: fromApiAnswers(today.survey),
  };
}

export const useAppStore = create((set, get) => ({
  status: "loading",
  error: null,
  users: [],
  persona: null,
  user: { ...MOCK_PROFILE, firstName: "", lastName: "", initials: "" },
  today: null,
  patterns: null,
  checkIn: null,
  prediction: null,
  isCheckInOpen: false,

  init: async () => {
    set({ status: "loading", error: null });
    try {
      const users = await api.users();
      if (!users.length) throw new Error("No personas found. Run scripts.reset_db in the backend.");
      const saved = users.find((u) => u.id === readSavedPersona());
      set({ users });
      await get().selectUser((saved ?? users[0]).id);
    } catch (error) {
      set({ status: "error", error: error.message });
    }
  },

  selectUser: async (id) => {
    const persona = get().users.find((u) => u.id === id);
    if (!persona) return;
    savePersona(id);
    set({ persona, user: userOf(persona), prediction: null });
    try {
      const data = await loadPersona(persona);
      if (get().persona?.id !== id) return;
      set({ ...data, status: "ready", error: null });
    } catch (error) {
      if (get().persona?.id === id) set({ status: "error", error: error.message });
      return;
    }
    const prediction = await api.prediction(id);
    if (get().persona?.id === id) set({ prediction });
  },

  refresh: () => get().selectUser(get().persona.id),

  openCheckIn: () => set({ isCheckInOpen: true }),
  closeCheckIn: () => set({ isCheckInOpen: false }),

  saveCheckIn: async (answers) => {
    const { persona } = get();
    await api.saveSurvey(persona.id, persona.today, toApiAnswers(answers));
    set({ checkIn: answers });
    await get().refresh();
  },

  resetCheckIn: async () => {
    const { persona } = get();
    await api.deleteSurvey(persona.id, persona.today);
    set({ checkIn: null });
    await get().refresh();
  },

  // Mock Apple Health sync: nothing is fetched, only the "last synced" label changes.
  lastHealthSync: "Today, 07:42",
  markHealthSynced: () => set({ lastHealthSync: "Just now" }),
}));
