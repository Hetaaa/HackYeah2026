import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion, useSpring, useTransform } from "motion/react";
import confetti from "canvas-confetti";
import { RotateCcw, X } from "lucide-react";
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
      <GooFilter />
    </div>
  );
}

/** Mounted fresh on every open, so the draft always starts from the last saved answers. */
function SheetBody({ onSaved }) {
  const saved = useAppStore((s) => s.checkIn);
  const saveCheckIn = useAppStore((s) => s.saveCheckIn);
  const resetCheckIn = useAppStore((s) => s.resetCheckIn);
  const close = useAppStore((s) => s.closeCheckIn);
  const [draft, setDraft] = useState(saved ?? {});
  const [isDone, setIsDone] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState(null);
  const closeTimer = useRef(null);

  useEffect(() => () => clearTimeout(closeTimer.current), []);

  const isComplete = CHECK_IN_METRICS.every((m) => draft[m.key]);

  const hasAnswers = saved !== null || Object.keys(draft).length > 0;

  // Saved check-in: delete it on the backend. Unsaved answers: just clear the form.
  const handleReset = async () => {
    setError(null);
    if (saved === null) {
      setDraft({});
      return;
    }
    setIsSaving(true);
    try {
      await resetCheckIn();
      setDraft({});
    } catch (e) {
      setError(e.message);
    } finally {
      setIsSaving(false);
    }
  };

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

            {error && <p className={styles.error}>{error}</p>}

            <motion.button
              className={styles.save}
              disabled={!isComplete || isSaving}
              onClick={handleSave}
              animate={{ opacity: isComplete && !isSaving ? 1 : 0.45 }}
            >
              {isSaving ? "Saving…" : "Save check-in"}
            </motion.button>
            {hasAnswers && (
              <button className={styles.reset} onClick={handleReset} disabled={isSaving}>
                <RotateCcw size={14} strokeWidth={2.2} />
                {saved !== null ? "Reset today’s check-in" : "Clear answers"}
              </button>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}

// One button (38px) + gap (8px): how far the blob moves per step.
const STEP = 46;

const R = 19; // button radius
const SCALE_WIDTH = 5 * 38 + 4 * 8;

/** Teardrop outline: hull of a full circle at the head and a smaller one at the tail,
 *  joined by their outer tangent lines (no neck, so it never pinches or breaks). */
function teardropPath(head, tail) {
  const d = Math.abs(head - tail);
  const R1 = R - Math.min(d / 40, 2); // head thins slightly while stretched
  const r = Math.max(R1 - d * 0.17, 5); // tail shrinks the longer the drop
  if (d < R1 - r + 0.5) {
    return `M ${head - R1} ${R} a ${R1} ${R1} 0 1 0 ${2 * R1} 0 a ${R1} ${R1} 0 1 0 ${-2 * R1} 0 Z`;
  }
  const dir = Math.sign(head - tail); // drop points the way it moves
  const cos = (R1 - r) / d;
  const sin = Math.sqrt(1 - cos * cos);
  const hx = head + dir * R1 * cos;
  const tx = tail + dir * r * cos;
  const sweep = dir > 0 ? 1 : 0;
  return [
    `M ${tx} ${R - r * sin}`,
    `L ${hx} ${R - R1 * sin}`,
    `A ${R1} ${R1} 0 0 ${sweep} ${hx} ${R + R1 * sin}`,
    `L ${tx} ${R + r * sin}`,
    `A ${r} ${r} 0 1 ${sweep} ${tx} ${R - r * sin}`,
    "Z",
  ].join(" ");
}

/** The selection drop: the head springs ahead, the tail follows slower, so the shape
 *  stretches into a teardrop on start and pulls itself back into a circle at the end. */
function GooBlob({ value }) {
  const target = R + (value - 1) * STEP;
  const head = useSpring(target, { stiffness: 520, damping: 40 });
  const tail = useSpring(target, { stiffness: 220, damping: 30 });

  useEffect(() => {
    head.set(target);
    tail.set(target);
  }, [target, head, tail]);

  const path = useTransform(() => teardropPath(head.get(), tail.get()));

  return (
    <motion.div
      className={styles.goo}
      aria-hidden="true"
      initial={{ opacity: 0, scale: 0.6 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.4, transition: { duration: 0.2 } }}
      style={{ transformOrigin: `${target}px 50%` }}
    >
      <svg className={styles.dropSvg} width={SCALE_WIDTH} height={2 * R}>
        <motion.path d={path} />
      </svg>
    </motion.div>
  );
}

function ScaleRow({ metric, value, onChange }) {
  return (
    <fieldset className={styles.row}>
      <legend className={styles.label}>{metric.label}</legend>
      <div className={styles.scaleLine}>
        <span className={styles.endLow}>{metric.low}</span>
        <div className={styles.scale}>
          {/* Layers: grey circles, then the orange goo, then the (transparent) buttons with numbers.
              Buttons stay on top even while pressed (a pressed button gets a transform). */}
          <div className={styles.track} aria-hidden="true">
            {[1, 2, 3, 4, 5].map((n) => (
              <span key={n} />
            ))}
          </div>
          <AnimatePresence>{value && <GooBlob key="goo" value={value} />}</AnimatePresence>
          {[1, 2, 3, 4, 5].map((n) => (
            <motion.button
              key={n}
              type="button"
              className={`${styles.option} ${value === n ? styles.selected : ""}`}
              onClick={() => onChange(n)}
              whileTap={{ scale: 0.9 }}
              aria-pressed={value === n}
              aria-label={`${metric.label} ${n}`}
            >
              <span className={styles.number}>{n}</span>
            </motion.button>
          ))}
        </div>
        <span className={styles.endHigh}>{metric.high}</span>
      </div>
    </fieldset>
  );
}

/** Gooey filter: blur merges the blobs, the alpha matrix sharpens the merged edge back. */
function GooFilter() {
  return (
    <svg width="0" height="0" className={styles.svgDefs} aria-hidden="true">
      <filter id="goo" x="-20%" y="-60%" width="140%" height="220%">
        <feGaussianBlur in="SourceGraphic" stdDeviation="6" result="blur" />
        <feColorMatrix
          in="blur"
          values="1 0 0 0 0  0 1 0 0 0  0 0 1 0 0  0 0 0 22 -9"
          result="goo"
        />
        <feComposite in="SourceGraphic" in2="goo" operator="atop" />
      </filter>
    </svg>
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
