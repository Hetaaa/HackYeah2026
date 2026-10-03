import { motion } from "motion/react";
import styles from "./SegmentedControl.module.scss";

/** iOS-style tabs; the white pill slides between options. options: [{ value, label }] */
function SegmentedControl({ options, value, onChange, id }) {
  return (
    <div className={styles.control} role="tablist">
      {options.map((o) => (
        <button
          key={o.value}
          role="tab"
          aria-selected={o.value === value}
          className={`${styles.option} ${o.value === value ? styles.active : ""}`}
          onClick={() => onChange(o.value)}
        >
          {o.value === value && (
            <motion.span
              layoutId={`segment-${id}`}
              className={styles.pill}
              transition={{ type: "spring", stiffness: 450, damping: 38 }}
            />
          )}
          <span className={styles.label}>{o.label}</span>
        </button>
      ))}
    </div>
  );
}

export default SegmentedControl;
