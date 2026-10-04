import { withPrediction } from "../../../api/adapters.js";
import { useAppStore } from "../../../store/useAppStore.js";
import { useClockText } from "../../../utils/time.js";
import styles from "./ForecastCard.module.scss";

function ForecastCard() {
  const forecast = useAppStore((s) => s.today.forecast);
  const prediction = useAppStore((s) => s.prediction);
  const { lead, emphasis, chance, reason } = withPrediction(forecast, prediction);
  const clock = useClockText();

  return (
    <article className={styles.card}>
      <p className={styles.eyebrow}>
        <span className={styles.step}>01</span>
        Don't be caught off guard
      </p>
      <h2 className={styles.title}>
        {clock(lead)} <strong>{clock(emphasis)}</strong>
      </h2>
      {chance && <p className={styles.chance}>{clock(chance)}</p>}
      {reason && <p className={styles.reason}>{clock(reason)}</p>}
    </article>
  );
}

export default ForecastCard;
