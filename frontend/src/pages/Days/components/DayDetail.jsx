import { AnimatePresence, motion } from "motion/react";
import { CHECK_IN_METRICS, useAppStore } from "../../../store/useAppStore.js";
import NormBar from "./NormBar.jsx";
import styles from "./DayDetail.module.scss";

const LABEL_TEXT = { good: "Good day", neutral: "Typical day", bad: "Lower day" };
const WHEN_TEXT = { last_night: "last night", day_before: "day before" };

function formatDate(date) {
  const [y, m, d] = date.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString("en-US", { weekday: "long", month: "short", day: "numeric" });
}

function DayDetail({ date, day, today, reference, isLoading, error }) {
  if (!day) {
    return (
      <section className={styles.card}>
        <div className={styles.head}>
          <div>
            <p className={styles.eyebrow}>{date === today ? "Today" : "Day view"}</p>
            <h2 className={styles.title}>{formatDate(date)}</h2>
          </div>
        </div>
        <p className={styles.noCheckIn}>
          {isLoading ? "Loading…" : (error ?? "No watch data or check-in for this day.")}
        </p>
      </section>
    );
  }

  return (
    <AnimatePresence mode="wait" initial={false}>
      <motion.section
        key={day.date}
        className={styles.card}
        initial={{ opacity: 0, y: 14 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -8 }}
        transition={{ duration: 0.22, ease: "easeOut" }}
      >
        <div className={styles.head}>
          <div>
            <p className={styles.eyebrow}>{day.date === today ? "Today" : "Day view"}</p>
            <h2 className={styles.title}>{formatDate(day.date)}</h2>
          </div>
          <span className={`${styles.pill} ${styles[day.label ?? "empty"]}`}>
            {LABEL_TEXT[day.label] ?? (day.date === today ? "Check-in pending" : "No check-in")}
          </span>
        </div>

        <Summary day={day} />
        <CheckIn day={day} today={today} />

        <div className={styles.section}>
          <p className={styles.sectionLabel}>vs {reference}</p>
          <ul className={styles.features}>
            {day.features.map((f, i) => (
              <motion.li
                key={f.feature}
                className={styles.feature}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.05 + i * 0.04 }}
              >
                <div className={styles.featureTop}>
                  <div>
                    <p className={styles.featureLabel}>{f.label}</p>
                    <p className={styles.when}>{WHEN_TEXT[f.when]}</p>
                  </div>
                  <div className={styles.featureValues}>
                    <p className={styles.value}>{f.display}</p>
                    <p className={`${styles.diff} ${styles[`leans_${f.leans}`] ?? ""}`}>
                      {f.difference_text}
                    </p>
                  </div>
                </div>
                <NormBar value={f.value} norm={f.norm} leans={f.leans} />
              </motion.li>
            ))}
          </ul>
          <div className={styles.key}>
            <span>
              <i className={styles.keyBad} /> toward your lower days
            </span>
            <span>
              <i className={styles.keyGood} /> toward your good days
            </span>
            <span>
              <i className={styles.keyBand} /> your usual range
            </span>
          </div>
        </div>
      </motion.section>
    </AnimatePresence>
  );
}

/** Possible reason > biggest difference > neutral text, as in backend `headline`. */
function Summary({ day }) {
  if (day.reasons.length) {
    const reason = day.reasons[0];
    return (
      <div className={`${styles.summary} ${styles.summaryReason}`}>
        <p className={styles.summaryEyebrow}>Possible reason</p>
        <p className={styles.summaryText}>{reason.text.replace("Possible reason: ", "")}</p>
        <p className={styles.summaryNote}>{reason.pattern_text}</p>
      </div>
    );
  }
  if (day.deviations.length) {
    return (
      <div className={styles.summary}>
        <p className={styles.summaryEyebrow}>Biggest difference</p>
        <p className={styles.summaryText}>{day.deviations[0].text}</p>
        <p className={styles.summaryNote}>A difference, not necessarily a cause.</p>
      </div>
    );
  }
  return (
    <div className={styles.summary}>
      <p className={styles.summaryText}>{day.summary ?? "Typical day for you"}</p>
    </div>
  );
}

function CheckIn({ day, today }) {
  const openCheckIn = useAppStore((s) => s.openCheckIn);

  if (!day.survey) {
    return day.date === today ? (
      <button className={styles.checkInCta} onClick={openCheckIn}>
        Check in to see how today compares
      </button>
    ) : (
      <p className={styles.noCheckIn}>No check-in this day.</p>
    );
  }

  return (
    <div className={styles.section}>
      <p className={styles.sectionLabel}>Your check-in</p>
      <div className={styles.answers}>
        {CHECK_IN_METRICS.map((m) => {
          const value = day.survey[m.key];
          return (
            <div key={m.key} className={styles.answer}>
              <p className={styles.answerLabel}>{m.label}</p>
              <p className={styles.answerValue}>
                {value}
                <small>/5</small>
              </p>
              <div className={styles.dots}>
                {[1, 2, 3, 4, 5].map((n) => (
                  <span key={n} className={n <= value ? styles.dotOn : undefined} />
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default DayDetail;
