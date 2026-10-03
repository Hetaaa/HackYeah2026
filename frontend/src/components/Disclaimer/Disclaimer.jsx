import { Info } from "lucide-react";
import styles from "./Disclaimer.module.scss";

/** Shown at the bottom of every screen: the app describes personal data, it doesn't give medical advice. */
function Disclaimer() {
  return (
    <aside className={styles.note}>
      <Info size={14} className={styles.icon} />
      <p>
        <strong>Not medical advice.</strong> why. shows patterns in your own data. It doesn’t diagnose or treat any
        condition, and a pattern isn’t proof of a cause. If you feel unwell, talk to a doctor.
      </p>
    </aside>
  );
}

export default Disclaimer;
