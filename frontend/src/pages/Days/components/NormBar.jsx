import { motion } from "motion/react";
import styles from "./NormBar.module.scss";

/** Track with the usual range (25th–75th pct of good days), the average tick and today's dot. */
function NormBar({ value, norm, leans }) {
  // Centre the scale on the average; widen it so the value and the whole band always fit.
  const reach = Math.max(Math.abs(value - norm.average), norm.high - norm.average, norm.average - norm.low) * 1.35;
  const pos = (v) => `${((v - (norm.average - reach)) / (2 * reach)) * 100}%`;

  return (
    <div className={styles.bar}>
      <span className={styles.band} style={{ left: pos(norm.low), right: `calc(100% - ${pos(norm.high)})` }} />
      <span className={styles.average} />
      <motion.span
        className={`${styles.dot} ${styles[leans] ?? ""}`}
        initial={{ left: "50%" }}
        animate={{ left: pos(value) }}
        transition={{ type: "spring", stiffness: 140, damping: 20, delay: 0.15 }}
      />
    </div>
  );
}

export default NormBar;
