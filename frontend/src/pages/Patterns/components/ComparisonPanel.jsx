import { Info } from "lucide-react";
import { useAppStore } from "../../../store/useAppStore.js";
import styles from "./ComparisonPanel.module.scss";

const STRENGTH_LABEL = {
  strong: "strong pattern",
  medium: "medium pattern",
  early: "early signal",
};

function ComparisonPanel() {
  const { weeks, updated, signals } = useAppStore((s) => s.patterns.comparison);

  return (
    <section className={styles.panel}>
      <div className={styles.head}>
        <p className={styles.eyebrow}>Full comparison</p>
        <span className={styles.updated}>{updated}</span>
      </div>
      <h2 className={styles.title}>Your signals across {weeks} weeks</h2>

      <div className={styles.columns}>
        <span>Signal</span>
        <span>Good days</span>
        <span>Lower days</span>
      </div>
      <ul className={styles.table}>
        {signals.map((s) => (
          <li key={s.name} className={styles.row}>
            <div>
              <p className={styles.name}>{s.name}</p>
              <span className={`${styles.badge} ${styles[s.strength]}`}>{STRENGTH_LABEL[s.strength]}</span>
            </div>
            <span className={styles.good}>{s.good}</span>
            <div className={styles.lower}>
              <span className={styles.lowerValue}>{s.lower}</span>
              <span className={styles.delta}>{s.delta}</span>
            </div>
          </li>
        ))}
      </ul>

      <div className={styles.note}>
        <Info size={18} className={styles.noteIcon} fill="currentColor" stroke="#d9d0d3" />
        <div>
          <p className={styles.noteTitle}>How to read this</p>
          <p className={styles.noteText}>
            Patterns compare you only with yourself. “Strong” means a signal appears consistently across most of
            your lower days.
          </p>
        </div>
      </div>
    </section>
  );
}

export default ComparisonPanel;
