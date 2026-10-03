import { AnimatePresence, motion } from "motion/react";
import { useSearchParams } from "react-router";
import PageHeader from "../../components/PageHeader/PageHeader.jsx";
import SegmentedControl from "../../components/SegmentedControl/SegmentedControl.jsx";
import LowerDaysTab from "./components/LowerDaysTab.jsx";
import RecipeTab from "./components/RecipeTab.jsx";
import styles from "./Patterns.module.scss";

// `dir` comes from AnimatePresence `custom`, so the exiting tab also gets the current direction.
const slide = {
  enter: (dir) => ({ opacity: 0, x: 24 * dir }),
  center: { opacity: 1, x: 0 },
  exit: (dir) => ({ opacity: 0, x: -24 * dir }),
};

const TABS = [
  { value: "lower", label: "Lower days" },
  { value: "recipe", label: "Good-day recipe" },
];

function Patterns() {
  // Tab lives in the URL so Today can link straight to /patterns?tab=recipe.
  const [params, setParams] = useSearchParams();
  const tab = params.get("tab") === "recipe" ? "recipe" : "lower";
  const direction = tab === "recipe" ? 1 : -1;

  return (
    <div className={styles.page}>
      <PageHeader
        eyebrow="Your patterns"
        title="What shapes"
        subtitle="how you feel."
        description="Built only from your own days — never population averages."
      />
      <div className={styles.tabs}>
        <SegmentedControl
          id="patterns"
          options={TABS}
          value={tab}
          onChange={(value) => setParams({ tab: value }, { replace: true })}
        />
      </div>
      <AnimatePresence mode="wait" initial={false} custom={direction}>
        <motion.div
          key={tab}
          custom={direction}
          variants={slide}
          initial="enter"
          animate="center"
          exit="exit"
          transition={{ duration: 0.22, ease: "easeOut" }}
        >
          {tab === "recipe" ? <RecipeTab /> : <LowerDaysTab />}
        </motion.div>
      </AnimatePresence>
    </div>
  );
}

export default Patterns;
