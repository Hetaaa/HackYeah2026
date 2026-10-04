import { useEffect, useRef } from "react";
import { animate, motion, useInView, useMotionValue, useReducedMotion, useTransform } from "motion/react";

/** Counts from 0 to `value` the first time it scrolls into view. */
function CountUp({ value, decimals = 0, duration = 1.2 }) {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, amount: 0.5 });
  const reduceMotion = useReducedMotion();
  const count = useMotionValue(reduceMotion ? value : 0);
  const text = useTransform(count, (n) =>
    n.toLocaleString("en-US", { minimumFractionDigits: decimals, maximumFractionDigits: decimals }),
  );

  useEffect(() => {
    if (!isInView) return;
    const controls = animate(count, value, { duration, ease: [0.16, 1, 0.3, 1] });
    return () => controls.stop();
  }, [isInView, value, duration, count]);

  // tabular-nums keeps the width steady while digits change
  return (
    <motion.span ref={ref} style={{ fontVariantNumeric: "tabular-nums" }}>
      {text}
    </motion.span>
  );
}

export default CountUp;
