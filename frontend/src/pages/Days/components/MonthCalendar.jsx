import { AnimatePresence, motion } from "motion/react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { FIRST_MONTH, TODAY } from "../../../mocks/days.js";
import styles from "./MonthCalendar.module.scss";

const WEEKDAYS = ["M", "T", "W", "T", "F", "S", "S"];

const LEGEND = [
  { label: "good", text: "Good" },
  { label: "neutral", text: "Typical" },
  { label: "bad", text: "Lower" },
  { label: null, text: "No check-in" },
];

function shiftMonth(month, delta) {
  const [y, m] = month.split("-").map(Number);
  const d = new Date(y, m - 1 + delta, 1);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

function monthTitle(month) {
  const [y, m] = month.split("-").map(Number);
  return new Date(y, m - 1, 1).toLocaleDateString("en-US", { month: "long", year: "numeric" });
}

/** Grid cells for a month, Monday first: null = padding before the 1st. */
function monthCells(month) {
  const [y, m] = month.split("-").map(Number);
  const offset = (new Date(y, m - 1, 1).getDay() + 6) % 7;
  const count = new Date(y, m, 0).getDate();
  return [
    ...Array(offset).fill(null),
    ...Array.from({ length: count }, (_, i) => `${month}-${String(i + 1).padStart(2, "0")}`),
  ];
}

function MonthCalendar({ month, days, selected, onMonthChange, onSelect }) {
  const byDate = Object.fromEntries(days.map((d) => [d.date, d]));
  const canPrev = month > FIRST_MONTH;
  const canNext = month < TODAY.slice(0, 7);

  const counts = days.reduce((acc, d) => ({ ...acc, [d.label]: (acc[d.label] ?? 0) + 1 }), {});

  return (
    <section className={styles.card}>
      <div className={styles.head}>
        <h2 className={styles.title}>{monthTitle(month)}</h2>
        <div className={styles.nav}>
          <button disabled={!canPrev} onClick={() => onMonthChange(shiftMonth(month, -1))} aria-label="Previous month">
            <ChevronLeft size={18} />
          </button>
          <button disabled={!canNext} onClick={() => onMonthChange(shiftMonth(month, 1))} aria-label="Next month">
            <ChevronRight size={18} />
          </button>
        </div>
      </div>

      <ul className={styles.legend}>
        {LEGEND.map((l) => (
          <li key={l.text}>
            <span className={`${styles.swatch} ${styles[l.label ?? "empty"]}`} />
            {l.text}
            <strong>{counts[l.label] ?? 0}</strong>
          </li>
        ))}
        <li>
          <span className={styles.legendDot} />
          Possible reason
        </li>
      </ul>

      <div className={styles.weekdays}>
        {WEEKDAYS.map((w, i) => (
          <span key={i}>{w}</span>
        ))}
      </div>

      <AnimatePresence mode="wait" initial={false}>
        <motion.div
          key={month}
          className={styles.grid}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          transition={{ duration: 0.2 }}
        >
          {monthCells(month).map((date, i) => {
            if (!date) return <span key={`pad-${i}`} />;
            const day = byDate[date];
            const isSelected = date === selected;
            const tone = day ? (day.label ?? "empty") : "future";
            return (
              <button
                key={date}
                className={`${styles.tile} ${styles[tone]} ${date === TODAY ? styles.today : ""}`}
                disabled={!day}
                onClick={() => onSelect(date)}
                aria-pressed={isSelected}
                aria-label={day?.headline ? `${date}: ${day.headline}` : date}
              >
                {isSelected && (
                  <motion.span
                    layoutId="day-ring"
                    className={styles.ring}
                    transition={{ type: "spring", stiffness: 500, damping: 38 }}
                  />
                )}
                {Number(date.slice(8))}
                {day?.has_reason && <span className={styles.reasonDot} />}
              </button>
            );
          })}
        </motion.div>
      </AnimatePresence>
    </section>
  );
}

export default MonthCalendar;
