import { useRef } from "react";
import { AnimatePresence, motion } from "motion/react";
import { Navigate, Route, Routes, useLocation } from "react-router";
import PhoneFrame from "./components/PhoneFrame/PhoneFrame.jsx";
import BottomNav from "./components/BottomNav/BottomNav.jsx";
import CheckInSheet from "./components/CheckInSheet/CheckInSheet.jsx";
import Today from "./pages/Today/Today.jsx";
import Patterns from "./pages/Patterns/Patterns.jsx";
import Placeholder from "./pages/Placeholder/Placeholder.jsx";
import styles from "./App.module.scss";

function App() {
  const location = useLocation();
  const scrollRef = useRef(null);

  return (
    <PhoneFrame>
      <main ref={scrollRef} className={styles.scroll}>
        {/* Keyed by pathname only, so ?tab= changes inside a page don't replay the transition.
            Scroll resets after the old page has faded out, not mid-animation. */}
        <AnimatePresence mode="wait" initial={false} onExitComplete={() => scrollRef.current?.scrollTo(0, 0)}>
          <motion.div
            key={location.pathname}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0, transition: { duration: 0.28, ease: "easeOut" } }}
            exit={{ opacity: 0, y: -6, transition: { duration: 0.15, ease: "easeIn" } }}
          >
            <Routes location={location}>
              <Route path="/" element={<Today />} />
              <Route path="/days" element={<Placeholder title="Days" />} />
              <Route path="/patterns" element={<Patterns />} />
              <Route path="/you" element={<Placeholder title="You" />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </motion.div>
        </AnimatePresence>
      </main>
      <BottomNav />
      <CheckInSheet />
    </PhoneFrame>
  );
}

export default App;
