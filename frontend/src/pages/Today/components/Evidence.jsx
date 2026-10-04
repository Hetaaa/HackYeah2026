import { Moon } from "lucide-react";
import { Link } from "react-router";
import CountUp from "../../../components/CountUp/CountUp.jsx";
import WalkIcon from "../../../components/icons/WalkIcon.jsx";
import { useAppStore } from "../../../store/useAppStore.js";
import styles from "./Evidence.module.scss";

const average = (values) => values.reduce((a, b) => a + b, 0) / values.length;

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
  const { days, sleep, movement } = useAppStore((s) => s.today.evidence);

  const avgSleepMin = Math.round(average(sleep.hours) * 60);
  const sleepDelta = formatMinutesDelta(avgSleepMin - sleep.usualHours * 60);
  const maxNight = Math.max(...sleep.hours, sleep.usualHours);
  const barHeight = (hours) => `${((hours - SLEEP_AXIS_MIN) / (maxNight - SLEEP_AXIS_MIN)) * 100}%`;

  const avgSteps = Math.round(average(movement.steps));
  const stepsDelta = formatPercentDelta(avgSteps / movement.usualSteps - 1);

  return (
    <section className={styles.section}>
      <p className={styles.eyebrow}>The evidence</p>
      <div className={styles.header}>
        <h2 className={styles.title}>Your last {days.length} days</h2>
        <Link to="/patterns" className={styles.more}>
          View patterns
        </Link>
      </div>
      <p className={styles.subtitle}>Daily averages compared with your usual days.</p>

      <div className={styles.grid}>
        <Link to="/patterns" className={`${styles.card} ${styles.sleep}`}>
          <div className={styles.cardHead}>
            <span className={styles.icon}>
              <Moon size={20} strokeWidth={1.6} />
            </span>
            <span className={styles.metric}>Avg sleep</span>
          </div>
          <p className={styles.value}>
            <CountUp value={Math.floor(avgSleepMin / 60)} />
            <small>h</small> <CountUp value={avgSleepMin % 60} />
            <small>m</small>
          </p>
          <p className={styles.delta}>
            <strong>{sleepDelta}</strong> vs your usual
          </p>
          <div className={styles.chart}>
            <div className={styles.bars}>
              {sleep.hours.map((hours, i) => (
                <span
                  key={i}
                  className={i === sleep.hours.length - 1 ? styles.barToday : styles.bar}
                  style={{ height: barHeight(hours) }}
                />
              ))}
              <span className={styles.usualLine} style={{ bottom: barHeight(sleep.usualHours) }} />
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
          <p className={styles.value}>
            <CountUp value={avgSteps} />
          </p>
          <p className={styles.delta}>
            <strong>{stepsDelta}</strong> vs your usual
          </p>
          <p className={styles.note}>{movement.note}</p>
          <span className={styles.ring} />
        </Link>
      </div>
    </section>
  );
}

export default Evidence;
