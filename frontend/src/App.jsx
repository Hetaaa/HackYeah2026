import { useEffect, useRef } from "react";
import { AnimatePresence, motion } from "motion/react";
import { Navigate, Route, Routes, useLocation } from "react-router";
import PhoneFrame from "./components/PhoneFrame/PhoneFrame.jsx";
import BottomNav from "./components/BottomNav/BottomNav.jsx";
import CheckInSheet from "./components/CheckInSheet/CheckInSheet.jsx";
import PrivacySheet from "./components/PrivacySheet/PrivacySheet.jsx";
import Today from "./pages/Today/Today.jsx";
import Patterns from "./pages/Patterns/Patterns.jsx";
import Days from "./pages/Days/Days.jsx";
import Profile from "./pages/Profile/Profile.jsx";
import StatusScreen from "./components/StatusScreen/StatusScreen.jsx";
import { useAppStore } from "./store/useAppStore.js";
import styles from "./App.module.scss";

function App() {
  const location = useLocation();
  const scrollRef = useRef(null);
  const status = useAppStore((s) => s.status);
  const init = useAppStore((s) => s.init);
  const switching = useAppStore((s) => s.switching);

  useEffect(() => {
    init();
  }, [init]);

  if (status !== "ready") {
    return (
      <PhoneFrame>
        <StatusScreen />
      </PhoneFrame>
    );
  }

  return (
    <PhoneFrame>
      <main ref={scrollRef} className={styles.scroll}>
        {/* Keyed by pathname only, so ?tab= changes inside a page don't replay the transition.
            Scroll resets after the old page has faded out, not mid-animation. */}
        <AnimatePresence
          mode="wait"
          initial={false}
          onExitComplete={() => scrollRef.current?.scrollTo(0, 0)}
        >
          <motion.div
            key={location.pathname}
            initial={{ opacity: 0, y: 12 }}
            animate={{
              opacity: 1,
              y: 0,
              transition: { duration: 0.28, ease: "easeOut" },
            }}
            exit={{
              opacity: 0,
              y: -6,
              transition: { duration: 0.15, ease: "easeIn" },
            }}
          >
            <Routes location={location}>
              <Route path="/" element={<Today />} />
              <Route path="/days" element={<Days />} />
              <Route path="/patterns" element={<Patterns />} />
              <Route path="/you" element={<Profile />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </motion.div>
        </AnimatePresence>
      </main>
      <BottomNav />
      <CheckInSheet />
      <AnimatePresence>
        {switching && (
          <motion.div
            className={styles.switching}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1, transition: { duration: 0.2 } }}
            exit={{ opacity: 0, transition: { duration: 0.2 } }}
          >
            <span className={styles.spinner} />
          </motion.div>
        )}
      </AnimatePresence>
    </PhoneFrame>
  );
}

export default App;
