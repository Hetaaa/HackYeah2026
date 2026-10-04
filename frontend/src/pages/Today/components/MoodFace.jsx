import { motion } from "motion/react";
import styles from "./MoodFace.module.scss";

// Body gradient per feeling: logo orange, calendar lavender, calendar copper.
const BODY = {
  good: ["#ffb21a", "#ff5a1a"],
  neutral: ["#e9defb", "#b79ce6"],
  low: ["#e8977a", "#c4573a"],
};

const MOUTH = {
  good: "M14.5 25.5 Q22 33 29.5 25.5",
  neutral: "M16 28 L28 28",
  low: "M16 30.5 Q22 25 28 30.5",
};

// Hover wiggle (driven by the parent button's `whileHover="hover"`).
const wiggle = {
  rest: { rotate: 0, scale: 1 },
  hover: { rotate: [0, -12, 9, -5, 0], scale: 1.12, transition: { duration: 0.6 } },
};

/** Small round face in the app's style; pops in when the feeling changes. */
function MoodFace({ feeling }) {
  const [from, to] = BODY[feeling];
  const id = `mood-${feeling}`;

  return (
    <motion.span
      className={styles.face}
      initial={{ scale: 0, rotate: -40 }}
      animate={{ scale: 1, rotate: 0 }}
      transition={{ type: "spring", stiffness: 380, damping: 14 }}
    >
      <motion.svg viewBox="0 0 44 44" width="44" height="44" variants={wiggle} aria-hidden="true">
        <defs>
          <radialGradient id={id} cx="0.35" cy="0.3" r="0.8">
            <stop offset="0" stopColor={from} />
            <stop offset="1" stopColor={to} />
          </radialGradient>
        </defs>
        <circle cx="22" cy="22" r="20" fill={`url(#${id})`} />
        <ellipse cx="15" cy="12" rx="6" ry="3.5" fill="#fff" opacity="0.35" transform="rotate(-25 15 12)" />

        {feeling === "good" && (
          <g fill="#ff7a8a" opacity="0.45">
            <ellipse cx="11.5" cy="24" rx="3" ry="2" />
            <ellipse cx="32.5" cy="24" rx="3" ry="2" />
          </g>
        )}

        {/* Eyes blink every few seconds. */}
        <motion.g
          className={styles.eyes}
          animate={{ scaleY: [1, 1, 0.1, 1] }}
          transition={{ duration: 4, times: [0, 0.9, 0.95, 1], repeat: Infinity, delay: 1 }}
        >
          {feeling === "good" ? (
            <path d="M12.5 19 Q15.5 15.5 18.5 19 M25.5 19 Q28.5 15.5 31.5 19" className={styles.line} />
          ) : (
            <>
              <circle cx="15.5" cy="18.5" r="2.2" />
              <circle cx="28.5" cy="18.5" r="2.2" />
            </>
          )}
        </motion.g>

        <motion.path
          d={MOUTH[feeling]}
          className={styles.line}
          initial={{ pathLength: 0 }}
          animate={{ pathLength: 1 }}
          transition={{ duration: 0.4, delay: 0.25 }}
        />
      </motion.svg>
    </motion.span>
  );
}

export default MoodFace;
