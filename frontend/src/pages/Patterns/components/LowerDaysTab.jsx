import { useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { ChevronDown } from "lucide-react";
import { useAppStore } from "../../../store/useAppStore.js";
import CountUp from "../../../components/CountUp/CountUp.jsx";
import ComparisonPanel from "./ComparisonPanel.jsx";
import { useClockText } from "../../../utils/time.js";
import styles from "./LowerDaysTab.module.scss";

function LowerDaysTab() {
  const { summary, reasons, combination, statusText } = useAppStore((s) => s.patterns);
  const [showAll, setShowAll] = useState(false);
  const clock = useClockText();

  return (
    <div className={styles.tab}>
      <dl className={styles.stats}>
        <Stat label="Days analyzed" value={summary.daysAnalyzed} />
        <Stat label="Tough days" value={summary.toughDays} />
        <Stat label="Patterns found" value={summary.patternsFound} />
      </dl>

      <section>
        <p className={styles.eyebrow}>Possible reasons</p>
        <div className={styles.sectionHead}>
          <h2 className={styles.sectionTitle}>What pulls your days down</h2>
        </div>

        {reasons.length === 0 && <p className={styles.empty}>{clock(statusText)}</p>}
        <ol className={styles.reasons}>
          {reasons.map((r, i) => (
            <li key={r.key} className={styles.reason}>
              <span className={styles.rank}>{String(i + 1).padStart(2, "0")}</span>
              <div className={styles.reasonBody}>
                <h3 className={styles.reasonTitle}>{clock(r.title)}</h3>
                <p className={styles.reasonSub}>{clock(r.frequency)}</p>
                {r.drivers && <p className={styles.reasonSub}>{r.drivers}</p>}
                <div className={styles.track}>
                  <motion.span
                    className={styles.fill}
                    initial={{ width: 0 }}
                    animate={{ width: `${r.share}%` }}
                    transition={{ duration: 0.8, delay: 0.15 + i * 0.1, ease: "easeOut" }}
                  />
                </div>
              </div>
              <span className={styles.share}>
                <CountUp value={r.share} />%
              </span>
            </li>
          ))}
        </ol>
      </section>

      {combination && (
        <article className={styles.combo}>
          <span className={styles.multiplier}>
            ×<CountUp value={combination.multiplier} decimals={1} />
          </span>
          <div>
            <p className={styles.comboEyebrow}>Strongest signal</p>
            <h3 className={styles.comboTitle}>{clock(combination.title)}</h3>
            <p className={styles.comboText}>{clock(combination.text)}</p>
          </div>
        </article>
      )}

      <button className={styles.viewAll} onClick={() => setShowAll((v) => !v)} aria-expanded={showAll}>
        {showAll ? "Hide data" : "View all data"}
        <motion.span animate={{ rotate: showAll ? 180 : 0 }} className={styles.chevron}>
          <ChevronDown size={14} strokeWidth={2.4} />
        </motion.span>
      </button>
      <AnimatePresence initial={false}>
        {showAll && (
          <motion.div
            key="comparison"
            className={styles.collapse}
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.35, ease: [0.2, 0.8, 0.2, 1] }}
          >
            <ComparisonPanel />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function Stat({ label, value }) {
  return (
    <div className={styles.stat}>
      <dt>{label}</dt>
      <dd>
        <CountUp value={value} />
      </dd>
    </div>
  );
}

export default LowerDaysTab;
