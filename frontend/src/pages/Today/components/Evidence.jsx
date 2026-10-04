import { Moon } from "lucide-react";
import { Link } from "react-router";
import CountUp from "../../../components/CountUp/CountUp.jsx";
import WalkIcon from "../../../components/icons/WalkIcon.jsx";
import { useAppStore } from "../../../store/useAppStore.js";
import styles from "./Evidence.module.scss";

const present = (values) => values.filter((v) => v !== null);
const average = (values) => {
  const known = present(values);
  return known.length ? known.reduce((a, b) => a + b, 0) / known.length : null;
};

// Bars start at 4h, not 0, so a 45-minute gap is actually visible.
const SLEEP_AXIS_MIN = 4;

/** Signed minutes as "−43m" / "+1h 05m" (real minus sign). */
function formatMinutesDelta(minutes) {
  const sign = minutes < 0 ? "−" : "+";
  const abs = Math.abs(Math.round(minutes));
  const h = Math.floor(abs / 60);
  const m = abs % 60;
  return `${sign}${h ? `${h}h ${String(m).padStart(2, "0")}m` : `${m}m`}`;
}

function formatPercentDelta(ratio) {
  const pct = Math.round(ratio * 100);
  return `${pct < 0 ? "−" : "+"}${Math.abs(pct)}%`;
}

function Evidence() {
  const { days, reference, sleep, movement } = useAppStore((s) => s.today.evidence);

  const avgSleep = average(sleep.hours);
  const avgSleepMin = avgSleep === null ? null : Math.round(avgSleep * 60);
  const sleepDelta =
    avgSleepMin !== null && sleep.usualHours !== null
      ? formatMinutesDelta(avgSleepMin - sleep.usualHours * 60)
      : null;
  const maxNight = Math.max(...present(sleep.hours), sleep.usualHours ?? 0, SLEEP_AXIS_MIN + 1);
  const barHeight = (hours) => `${(Math.max(hours - SLEEP_AXIS_MIN, 0) / (maxNight - SLEEP_AXIS_MIN)) * 100}%`;

  const avgStepsRaw = average(movement.steps);
  const avgSteps = avgStepsRaw === null ? null : Math.round(avgStepsRaw);
  const stepsDelta =
    avgSteps !== null && movement.usualSteps ? formatPercentDelta(avgSteps / movement.usualSteps - 1) : null;

  return (
    <section className={styles.section}>
      <p className={styles.eyebrow}>The evidence</p>
      <div className={styles.header}>
        <h2 className={styles.title}>Your last {days.length} days</h2>
        <Link to="/patterns" className={styles.more}>
          View patterns
        </Link>
      </div>
      <p className={styles.subtitle}>Daily averages compared with {reference}.</p>

      <div className={styles.grid}>
        <Link to="/patterns" className={`${styles.card} ${styles.sleep}`}>
          <div className={styles.cardHead}>
            <span className={styles.icon}>
              <Moon size={20} strokeWidth={1.6} />
            </span>
            <span className={styles.metric}>Avg sleep</span>
          </div>
          <p className={styles.value}>
            {avgSleepMin === null ? (
              "–"
            ) : (
              <>
                <CountUp value={Math.floor(avgSleepMin / 60)} />
                <small>h</small> <CountUp value={avgSleepMin % 60} />
                <small>m</small>
              </>
            )}
          </p>
          {sleepDelta && (
            <p className={styles.delta}>
              <strong>{sleepDelta}</strong> vs {reference}
            </p>
          )}
          <div className={styles.chart}>
            <div className={styles.bars}>
              {sleep.hours.map((hours, i) => (
                <span
                  key={i}
                  className={i === sleep.hours.length - 1 ? styles.barToday : styles.bar}
                  style={{ height: hours === null ? 0 : barHeight(hours) }}
                />
              ))}
              {sleep.usualHours !== null && (
                <span className={styles.usualLine} style={{ bottom: barHeight(sleep.usualHours) }} />
              )}
            </div>
            <div className={styles.days}>
              {days.map((day, i) => (
                <span key={i} className={i === days.length - 1 ? styles.dayToday : undefined}>
                  {day}
                </span>
              ))}
            </div>
          </div>
        </Link>

        <Link to="/patterns" className={`${styles.card} ${styles.movement}`}>
          <div className={styles.cardHead}>
            <span className={styles.icon}>
              <WalkIcon size={20} strokeWidth={1.6} />
            </span>
            <span className={styles.metric}>Avg steps</span>
          </div>
          <p className={styles.value}>{avgSteps === null ? "–" : <CountUp value={avgSteps} />}</p>
          {stepsDelta && (
            <p className={styles.delta}>
              <strong>{stepsDelta}</strong> vs {reference}
            </p>
          )}
          <span className={styles.ring} />
        </Link>
      </div>
    </section>
  );
}

export default Evidence;
