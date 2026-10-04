import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import confetti from "canvas-confetti";
import { X } from "lucide-react";
import { fromApiAnswers } from "../../api/adapters.js";
import { CHECK_IN_METRICS, useAppStore } from "../../store/useAppStore.js";
import styles from "./CheckInSheet.module.scss";

const CONFETTI_COLORS = ["#ff6a1a", "#ffb21a", "#7b4fc9", "#d8c7f1", "#d84a4a"];
const CLOSE_AFTER_SUCCESS_MS = 1900;

function CheckInSheet() {
  const isOpen = useAppStore((s) => s.isCheckInOpen);
  const close = useAppStore((s) => s.closeCheckIn);
  const canvasRef = useRef(null);
  const confettiRef = useRef(null);

  // Confetti draws on our own canvas so it stays inside the phone screen.
  useEffect(() => {
    confettiRef.current = confetti.create(canvasRef.current, {
      resize: true,
      disableForReducedMotion: true,
    });
    return () => confettiRef.current.reset();
  }, []);

  const celebrate = () => {
    const fire = (opts) =>
      confettiRef.current({
        particleCount: 70,
        spread: 65,
        startVelocity: 48,
        ticks: 220,
        scalar: 0.9,
        colors: CONFETTI_COLORS,
        ...opts,
      });
    fire({ angle: 60, origin: { x: 0, y: 0.75 } });
    fire({ angle: 120, origin: { x: 1, y: 0.75 } });
    setTimeout(() => fire({ particleCount: 50, spread: 110, origin: { x: 0.5, y: 0.45 } }), 250);
  };

  return (
    <div className={styles.root}>
      <AnimatePresence>
        {isOpen && (
          <>
            <motion.div
              key="backdrop"
              className={styles.backdrop}
              onClick={close}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            />
            <motion.div
              key="sheet"
              className={styles.sheet}
              role="dialog"
              aria-label="Daily check-in"
              initial={{ y: "100%" }}
              animate={{ y: 0 }}
              exit={{ y: "100%" }}
              transition={{ type: "spring", damping: 30, stiffness: 300 }}
              drag="y"
              dragConstraints={{ top: 0, bottom: 0 }}
              dragElastic={{ top: 0, bottom: 0.6 }}
              onDragEnd={(_, info) => info.offset.y > 120 && close()}
            >
              <SheetBody onSaved={celebrate} />
            </motion.div>
          </>
        )}
      </AnimatePresence>
      <canvas ref={canvasRef} className={styles.confetti} />
    </div>
  );
}

/** Mounted fresh on every open, so the draft always starts from the last saved answers. */
function SheetBody({ onSaved }) {
  const saved = useAppStore((s) => s.checkIn);
  const saveCheckIn = useAppStore((s) => s.saveCheckIn);
  const close = useAppStore((s) => s.closeCheckIn);
  const persona = useAppStore((s) => s.persona);
  const [draft, setDraft] = useState(saved ?? {});
  const [isDone, setIsDone] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState(null);
  const closeTimer = useRef(null);

  useEffect(() => () => clearTimeout(closeTimer.current), []);

  const isComplete = CHECK_IN_METRICS.every((m) => draft[m.key]);
  const demoAnswers = fromApiAnswers(persona.demo_answers);

  const handleSave = async () => {
    setIsSaving(true);
    setError(null);
    try {
      await saveCheckIn(draft);
      setIsDone(true);
      onSaved();
      closeTimer.current = setTimeout(close, CLOSE_AFTER_SUCCESS_MS);
    } catch (e) {
      setError(e.message);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <>
      <span className={styles.grabber} />
      <AnimatePresence mode="wait" initial={false}>
        {isDone ? (
          <Success key="success" />
        ) : (
          <motion.div key="form" exit={{ opacity: 0, scale: 0.96 }} transition={{ duration: 0.2 }}>
            <div className={styles.header}>
              <p className={styles.eyebrow}>Daily check-in</p>
              <button className={styles.close} onClick={close} aria-label="Close">
                <X size={18} />
              </button>
            </div>
            <h2 className={styles.title}>
              How do you <strong>feel today?</strong>
            </h2>

            <div className={styles.metrics}>
              {CHECK_IN_METRICS.map((metric, i) => (
                <motion.div
                  key={metric.key}
                  initial={{ opacity: 0, y: 16 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.08 + i * 0.06 }}
                >
                  <ScaleRow
                    metric={metric}
                    value={draft[metric.key]}
                    onChange={(v) => setDraft((d) => ({ ...d, [metric.key]: v }))}
                  />
                </motion.div>
              ))}
            </div>

            {demoAnswers && (
              <button className={styles.demo} onClick={() => setDraft(demoAnswers)}>
                Fill in {persona.name}’s real answers
              </button>
            )}
            {error && <p className={styles.error}>{error}</p>}

            <motion.button
              className={styles.save}
              disabled={!isComplete || isSaving}
              onClick={handleSave}
              animate={{ opacity: isComplete && !isSaving ? 1 : 0.45 }}
            >
              {isSaving ? "Saving…" : "Save check-in"}
            </motion.button>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}

function ScaleRow({ metric, value, onChange }) {
  return (
    <fieldset className={styles.row}>
      <legend className={styles.label}>{metric.label}</legend>
      <div className={styles.scale}>
        {[1, 2, 3, 4, 5].map((n) => (
          <motion.button
            key={n}
            type="button"
            className={`${styles.option} ${value === n ? styles.selected : ""}`}
            onClick={() => onChange(n)}
            whileTap={{ scale: 0.9 }}
            aria-pressed={value === n}
          >
            {value === n && (
              <motion.span
                layoutId={`pill-${metric.key}`}
                className={styles.pill}
                transition={{ type: "spring", stiffness: 500, damping: 35 }}
              />
            )}
            <span className={styles.number}>{n}</span>
          </motion.button>
        ))}
      </div>
      <div className={styles.ends}>
        <span>{metric.low}</span>
        <span>{metric.high}</span>
      </div>
    </fieldset>
  );
}

function Success() {
  return (
    <motion.div
      className={styles.success}
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ type: "spring", stiffness: 260, damping: 20 }}
    >
      <motion.div
        className={styles.badge}
        initial={{ scale: 0 }}
        animate={{ scale: 1 }}
        transition={{ type: "spring", stiffness: 300, damping: 14, delay: 0.05 }}
      >
        <svg viewBox="0 0 24 24" width="44" height="44" fill="none" aria-hidden="true">
          <motion.path
            d="M5 12.5l4.5 4.5L19 7.5"
            stroke="#fff"
            strokeWidth="2.6"
            strokeLinecap="round"
            strokeLinejoin="round"
            initial={{ pathLength: 0 }}
            animate={{ pathLength: 1 }}
            transition={{ duration: 0.45, delay: 0.25, ease: "easeOut" }}
          />
        </svg>
      </motion.div>
      <h2 className={styles.title}>
        Thanks, <strong>you're checked in!</strong>
      </h2>
      <p className={styles.hint}>Every check-in sharpens your patterns.</p>
    </motion.div>
  );
}

export default CheckInSheet;
