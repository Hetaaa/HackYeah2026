import { useAppStore } from "../../../store/useAppStore.js";
import styles from "./ForecastCard.module.scss";

function ForecastCard() {
  const { lead, emphasis, reason } = useAppStore((s) => s.today.forecast);

  return (
    <article className={styles.card}>
      <p className={styles.eyebrow}>
        <span className={styles.step}>01</span>
        Don't be caught off guard
      </p>
      <h2 className={styles.title}>
        {lead} <strong>{emphasis}</strong>
      </h2>
      {reason && <p className={styles.reason}>{reason}</p>}
    </article>
  );
}

export default ForecastCard;
