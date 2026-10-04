import { motion } from "motion/react";
import { useAppStore } from "../../../store/useAppStore.js";
import heartBackdrop from "../../../assets/heart-backdrop.svg";
import heartBody from "../../../assets/heart-body.svg";
import PatternCard from "./PatternCard.jsx";
import styles from "./HeartHero.module.scss";

// Card positions around the heart, in pattern rank order.
const SLOTS = [styles.slot1, styles.slot2, styles.slot3];

function HeartHero() {
  const patterns = useAppStore((s) => s.today.patterns);

  return (
    <section className={styles.hero} aria-label="Top patterns">
      {/* Two layers of one Figma export: glow + shadow stay put, only the heart floats and beats. */}
      <motion.div
        className={styles.heart}
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ type: "spring", stiffness: 120, damping: 18 }}
      >
        <img src={heartBackdrop} alt="" />
        <div className={styles.floater}>
          <span className={styles.ripple} />
          <span className={`${styles.ripple} ${styles.rippleLate}`} />
          <img src={heartBody} alt="" className={styles.heartBody} />
        </div>
      </motion.div>

      {/* Cards pop in one by one after the heart; the inner card keeps its idle float.
          Only transform here, never opacity: an ancestor with opacity < 1 becomes the card's
          backdrop root, so its backdrop-filter would have nothing to blur until the fade ends. */}
      {patterns.map((p, i) => (
        <motion.div
          key={p.rank}
          className={`${styles.slot} ${SLOTS[i]}`}
          initial={{ scale: 0, y: 16 }}
          animate={{ scale: 1, y: 0 }}
          transition={{ type: "spring", stiffness: 300, damping: 22, delay: 0.35 + i * 0.15 }}
        >
          <PatternCard pattern={p} className={styles.card} />
        </motion.div>
      ))}
    </section>
  );
}

export default HeartHero;
