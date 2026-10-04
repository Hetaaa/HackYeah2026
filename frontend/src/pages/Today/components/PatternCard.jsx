import { Link } from "react-router";
import {
  Armchair,
  BedDouble,
  Brain,
  Eye,
  Flame,
  Footprints,
  Gauge,
  Heart,
  HeartPulse,
  Moon,
  Star,
  Waves,
  Zap,
} from "lucide-react";
import WalkIcon from "../../../components/icons/WalkIcon.jsx";
import styles from "./PatternCard.module.scss";

// Icon per backend feature id (GET /api/features); falls back to sleep / activity by `kind`.
const FEATURE_ICONS = {
  sleep_h: Moon,
  time_in_bed_h: BedDouble,
  bedtime_h: BedDouble,
  wake_pct: Eye,
  wake_min: Eye,
  rem_pct: Brain,
  deep_pct: Waves,
  sleep_eff: Gauge,
  ss_overall: Star,
  hr_sleep_mean: HeartPulse,
  rhr_night: Heart,
  steps: WalkIcon,
  lightly: Footprints,
  mvpa: Zap,
  z_cardio_peak: Flame,
  sedentary: Armchair,
};
const KIND_ICONS = { sleep: Moon, steps: WalkIcon };

// Colour belongs to the slot (#1, #2, #3), not to the feature, so the hero always has all three.
const RANK_COLORS = [styles.rank1, styles.rank2, styles.rank3];

function PatternCard({ pattern, className = "" }) {
  const Icon = FEATURE_ICONS[pattern.feature] ?? KIND_ICONS[pattern.kind] ?? Moon;

  return (
    <Link to="/patterns" className={`${styles.card} ${className}`}>
      <div className={styles.head}>
        <span className={`${styles.icon} ${RANK_COLORS[pattern.rank - 1] ?? ""}`}>
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
