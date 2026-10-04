import { AnimatePresence, motion } from "motion/react";
import { Database, Info, Server, Sparkles, UserRound, X } from "lucide-react";
import { useAppStore } from "../../store/useAppStore.js";
import styles from "./PrivacySheet.module.scss";

// Keep these true to the backend: patterns use one person's data only, the forecast model is
// trained on all users' past days (backend/app/services/predictions.py), the demo DB resets.
const SECTIONS = [
  {
    icon: Database,
    title: "What we use",
    text: "Sleep, heart rate, steps and activity from your watch, plus your daily check-in: mood, fatigue, sleep quality and stress.",
  },
  {
    icon: UserRound,
    title: "Only you",
    text: "Patterns, possible reasons and your good-day recipe compare you only with yourself. Nobody else’s days are mixed in.",
  },
  {
    icon: Sparkles,
    title: "The daily forecast",
    text: "The forecast model also learns from past days of all users. It never sees your answers for today.",
  },
  {
    icon: Server,
    title: "Demo app",
    text: "Data is kept on our demo server and reset regularly. Please don’t enter real personal information.",
  },
  {
    icon: Info,
    title: "Not medical advice",
    text: "why. shows correlations in your own data, not diagnoses, and a pattern isn’t proof of a cause. If you feel unwell for a while, talk to a doctor.",
  },
];

function PrivacySheet() {
  const isOpen = useAppStore((s) => s.isPrivacyOpen);
  const close = useAppStore((s) => s.closePrivacy);

  return (
    <div className={styles.root}>
      <AnimatePresence>
        {isOpen && (
          <>
            <motion.div
              key="backdrop"
              className={styles.backdrop}
              onClick={close}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            />
            <motion.div
              key="sheet"
              className={styles.sheet}
              role="dialog"
              aria-label="Privacy"
              initial={{ y: "100%" }}
              animate={{ y: 0 }}
              exit={{ y: "100%" }}
              transition={{ type: "spring", damping: 30, stiffness: 300 }}
              drag="y"
              dragConstraints={{ top: 0, bottom: 0 }}
              dragElastic={{ top: 0, bottom: 0.6 }}
              onDragEnd={(_, info) => info.offset.y > 120 && close()}
            >
              <span className={styles.grabber} />
              <div className={styles.header}>
                <p className={styles.eyebrow}>Privacy</p>
                <button className={styles.close} onClick={close} aria-label="Close">
                  <X size={18} />
                </button>
              </div>
              <h2 className={styles.title}>
                Your data, <strong>your patterns</strong>
              </h2>
              <ul className={styles.sections}>
                {SECTIONS.map(({ icon: Icon, title, text }) => (
                  <li key={title} className={styles.section}>
                    <span className={styles.icon}>
                      <Icon size={18} />
                    </span>
                    <div>
                      <p className={styles.sectionTitle}>{title}</p>
                      <p className={styles.sectionText}>{text}</p>
                    </div>
                  </li>
                ))}
              </ul>
              <button className={styles.done} onClick={close}>
                Got it
              </button>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}

export default PrivacySheet;
