import { motion } from "motion/react";
import logo from "../../assets/logo.svg";
import { useAppStore } from "../../store/useAppStore.js";
import styles from "./StatusScreen.module.scss";

function StatusScreen() {
  const status = useAppStore((s) => s.status);
  const error = useAppStore((s) => s.error);
  const init = useAppStore((s) => s.init);

  return (
    <section className={styles.screen}>
      <motion.img
        src={logo}
        alt="why."
        className={styles.logo}
        animate={status === "loading" ? { scale: [1, 1.08, 1] } : { scale: 1 }}
        transition={{ duration: 1.2, repeat: status === "loading" ? Infinity : 0, ease: "easeInOut" }}
      />
      {status === "error" ? (
        <>
          <p className={styles.title}>Couldn’t load your days.</p>
          <p className={styles.text}>{error}</p>
          <p className={styles.hint}>Is the backend running on localhost:8000?</p>
          <button className={styles.retry} onClick={init}>
            Try again
          </button>
        </>
      ) : (
        <p className={styles.text}>Loading your days…</p>
      )}
    </section>
  );
}

export default StatusScreen;
