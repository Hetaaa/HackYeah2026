import { ArrowRight } from "lucide-react";
import { Link } from "react-router";
import { useAppStore } from "../../../store/useAppStore.js";
import CountUp from "../../../components/CountUp/CountUp.jsx";
import styles from "./RecipeCard.module.scss";

function RecipeCard() {
  const { items, goodDayRate, statusText } = useAppStore((s) => s.today.recipe);

  return (
    <article className={styles.card}>
      <p className={styles.eyebrow}>
        <span className={styles.step}>02</span>
        What helps you feel good
      </p>
      <h2 className={styles.title}>Your personal good-day recipe</h2>
      {items.length > 0 ? (
        <>
          <ul className={styles.tiles}>
            {items.map((item) => (
              <li key={item.key} className={styles.tile}>
                <span className={styles.value}>{item.value}</span>
                <span className={styles.label}>{item.label}</span>
              </li>
            ))}
          </ul>
          <p className={styles.summary}>
            On days with your top ingredient, you report feeling good <strong>
              <CountUp value={goodDayRate} />% of the time.
            </strong>
          </p>
        </>
      ) : (
        <p className={styles.summary}>{statusText}</p>
      )}
      <Link to="/patterns?tab=recipe" className={styles.link}>
        See your full recipe <ArrowRight size={16} strokeWidth={1.8} />
      </Link>
    </article>
  );
}

export default RecipeCard;
