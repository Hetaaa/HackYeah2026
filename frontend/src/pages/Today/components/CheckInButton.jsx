import { AnimatePresence, motion } from "motion/react";
import { ChevronRight, Pencil } from "lucide-react";
import { useAppStore } from "../../../store/useAppStore.js";
import MoodFace from "./MoodFace.jsx";
import styles from "./CheckInButton.module.scss";

const SUMMARY = {
  good: "You’re feeling generally okay",
  neutral: "A pretty normal day for you",
  low: "You’re feeling a bit low today",
};

/** Average of the four answers; every scale is "higher = better". */
function feelingOf(c) {
  const avg = (c.mood + c.sleepQuality + c.fatigue + c.stress) / 4;
  if (avg > 3.25) return "good";
  if (avg < 2.75) return "low";
  return "neutral";
}

function CheckInButton() {
  const checkIn = useAppStore((s) => s.checkIn);
  const openCheckIn = useAppStore((s) => s.openCheckIn);
  const feeling = checkIn ? feelingOf(checkIn) : null;

  return (
    <motion.button
      className={`${styles.button} ${feeling ? styles.done : ""}`}
      onClick={openCheckIn}
      initial="rest"
      whileHover="hover"
      animate="rest"
    >
      <AnimatePresence mode="wait" initial={false}>
        {feeling ? (
          <motion.span
            key={feeling}
            className={styles.content}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.2 }}
          >
            <MoodFace feeling={feeling} />
            <span className={styles.texts}>
              <span className={styles.eyebrow}>Today’s check-in</span>
              <span className={styles.summary}>{SUMMARY[feeling]}</span>
            </span>
          </motion.span>
        ) : (
          <motion.span
            key="todo"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.2 }}
          >
            Tell us how you feel today
          </motion.span>
        )}
      </AnimatePresence>
      <span className={styles.arrow} aria-label={feeling ? "Edit check-in" : undefined}>
        {feeling ? <Pencil size={16} strokeWidth={2.2} /> : <ChevronRight size={18} strokeWidth={2.5} />}
      </span>
    </motion.button>
  );
}

export default CheckInButton;
