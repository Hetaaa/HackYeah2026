import styles from "./Placeholder.module.scss";

function Placeholder({ title }) {
  return (
    <section className={styles.page}>
      <h1 className={styles.title}>{title}</h1>
      <p className={styles.text}>Coming soon.</p>
    </section>
  );
}

export default Placeholder;
