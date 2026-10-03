import PageHeader from "../../components/PageHeader/PageHeader.jsx";
import Disclaimer from "../../components/Disclaimer/Disclaimer.jsx";
import { useAppStore } from "../../store/useAppStore.js";
import HeartHero from "./components/HeartHero.jsx";
import ForecastCard from "./components/ForecastCard.jsx";
import CheckInButton from "./components/CheckInButton.jsx";
import RecipeCard from "./components/RecipeCard.jsx";
import Evidence from "./components/Evidence.jsx";
import styles from "./Today.module.scss";

function Today() {
  const date = useAppStore((s) => s.today.date);

  return (
    <div className={styles.page}>
      <PageHeader
        eyebrow={date}
        title="Feeling off today?"
        subtitle="Here’s what may be behind it."
      />
      <HeartHero />
      <div className={styles.cards}>
        <ForecastCard />
        <CheckInButton />
        <RecipeCard />
      </div>
      <Evidence />
      <Disclaimer />
    </div>
  );
}

export default Today;
