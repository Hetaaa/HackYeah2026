import { AnimatePresence, motion } from "motion/react";
import { Check, ChevronRight } from "lucide-react";
import { useAppStore } from "../../../store/useAppStore.js";
import styles from "./CheckInButton.module.scss";

function CheckInButton() {
  const isCheckedIn = useAppStore((s) => s.checkIn !== null);
  const openCheckIn = useAppStore((s) => s.openCheckIn);

  return (
    <motion.button
      className={`${styles.button} ${isCheckedIn ? styles.done : ""}`}
      onClick={openCheckIn}
    >
      <AnimatePresence mode="wait" initial={false}>
        <motion.span
          key={isCheckedIn ? "done" : "todo"}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          transition={{ duration: 0.2 }}
        >
          {isCheckedIn ? "Checked in for today" : "Tell us how you feel today"}
        </motion.span>
      </AnimatePresence>
      <span className={styles.arrow}>
        {isCheckedIn ? (
          <Check size={18} strokeWidth={2.5} />
        ) : (
          <ChevronRight size={18} strokeWidth={2.5} />
        )}
      </span>
    </motion.button>
  );
}

export default CheckInButton;
