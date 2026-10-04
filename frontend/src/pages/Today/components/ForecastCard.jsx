import { withPrediction } from "../../../api/adapters.js";
import { useAppStore } from "../../../store/useAppStore.js";
import styles from "./ForecastCard.module.scss";

function ForecastCard() {
  const forecast = useAppStore((s) => s.today.forecast);
  const prediction = useAppStore((s) => s.prediction);
  const { lead, emphasis, chance, reason } = withPrediction(forecast, prediction);

  return (
    <article className={styles.card}>
      <p className={styles.eyebrow}>
        <span className={styles.step}>01</span>
        Don't be caught off guard
      </p>
      <h2 className={styles.title}>
        {lead} <strong>{emphasis}</strong>
      </h2>
      {chance && <p className={styles.chance}>{chance}</p>}
      {reason && <p className={styles.reason}>{reason}</p>}
    </article>
  );
}

export default ForecastCard;
