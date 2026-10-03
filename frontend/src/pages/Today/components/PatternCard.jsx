import { Link } from "react-router";
import { ChartColumn, Moon } from "lucide-react";
import WalkIcon from "../../../components/icons/WalkIcon.jsx";
import styles from "./PatternCard.module.scss";

const KINDS = {
  sleep: { Icon: Moon, className: styles.sleep },
  steps: { Icon: WalkIcon, className: styles.steps },
  stress: { Icon: ChartColumn, className: styles.stress },
};

function PatternCard({ pattern, className = "" }) {
  const { Icon, className: kindClass } = KINDS[pattern.kind];

  return (
    <Link to="/patterns" className={`${styles.card} ${className}`}>
      <div className={styles.head}>
        <span className={`${styles.icon} ${kindClass}`}>
          <Icon size={20} strokeWidth={2} />
        </span>
        <div>
          <p className={styles.rank}>#{pattern.rank} pattern</p>
          <h3 className={styles.title}>{pattern.title}</h3>
        </div>
      </div>
      <p className={styles.subtitle}>{pattern.subtitle}</p>
      <p className={styles.frequency}>{pattern.frequency}</p>
    </Link>
  );
}

export default PatternCard;
