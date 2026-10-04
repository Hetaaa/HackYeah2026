import { useAppStore } from "../store/useAppStore.js";

// "HH:MM" clock times inside backend texts ("Asleep after 08:00", bedtime "00:20").
const CLOCK = /\b([01]\d|2[0-3]):([0-5]\d)\b/g;

/** Rewrites 24-hour clock times in a text for the chosen format ("12h": "00:20" -> "12:20 AM"). */
export function formatClockText(text, format) {
  if (format !== "12h" || typeof text !== "string") return text;
  return text.replace(CLOCK, (_, h, m) => {
    const hour = Number(h);
    return `${hour % 12 || 12}:${m} ${hour < 12 ? "AM" : "PM"}`;
  });
}

/** (text) => text in the user's clock format; re-renders when the setting changes. */
export function useClockText() {
  const format = useAppStore((s) => s.clockFormat);
  return (text) => formatClockText(text, format);
}
