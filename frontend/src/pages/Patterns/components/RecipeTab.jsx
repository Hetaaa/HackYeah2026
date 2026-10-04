import { motion } from "motion/react";
import { useAppStore } from "../../../store/useAppStore.js";
import CountUp from "../../../components/CountUp/CountUp.jsx";
import { useClockText } from "../../../utils/time.js";
import styles from "./RecipeTab.module.scss";

function RecipeTab() {
  const { goodDayRate, items, statusText } = useAppStore((s) => s.patterns.recipe);
  const clock = useClockText();

  return (
    <div className={styles.tab}>
      <article className={styles.formula}>
        <p className={styles.eyebrow}>Your personal formula</p>
        <h2 className={styles.formulaTitle}>{clock(statusText)}</h2>
        {goodDayRate !== null && (
          <p className={styles.rate}>
            <strong>
              <CountUp value={goodDayRate} />
              <small>%</small>
            </strong>
            <span>of days with your top ingredient feel good</span>
          </p>
        )}
        <span className={styles.ring} />
      </article>

      <ol className={styles.items}>
        {items.map((item, i) => (
          <motion.li
            key={item.key}
            className={styles.item}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 + i * 0.07 }}
          >
            <span className={styles.rank}>{String(i + 1).padStart(2, "0")}</span>
            <div className={styles.itemBody}>
              <p className={styles.area}>{item.area}</p>
              <h3 className={styles.itemTitle}>{clock(item.title)}</h3>
              <p className={styles.itemNote}>{clock(item.note)}</p>
            </div>
            <ScoreRing score={item.score} delay={0.3 + i * 0.1} />
          </motion.li>
        ))}
      </ol>

    </div>
  );
}

function ScoreRing({ score, delay }) {
  return (
    <span className={styles.score}>
      <svg viewBox="0 0 52 52" aria-hidden="true">
        <circle cx="26" cy="26" r="24" className={styles.scoreTrack} />
        <motion.circle
          cx="26"
          cy="26"
          r="24"
          className={styles.scoreFill}
          initial={{ pathLength: 0 }}
          animate={{ pathLength: score / 100 }}
          transition={{ duration: 0.9, delay, ease: "easeOut" }}
        />
      </svg>
      <CountUp value={score} />
    </span>
  );
}

export default RecipeTab;
