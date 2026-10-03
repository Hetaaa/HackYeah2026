import { Link } from "react-router";
import logo from "../../assets/logo.svg";
import { useAppStore } from "../../store/useAppStore.js";
import styles from "./PageHeader.module.scss";

/** Logo + avatar bar and the two-tone page title shared by all tabs. */
function PageHeader({ eyebrow, title, subtitle, description }) {
  const user = useAppStore((s) => s.user);

  return (
    <header className={styles.header}>
      <div className={styles.topBar}>
        <img src={logo} alt="why." className={styles.logo} />
        <Link to="/you" className={styles.profile} aria-label="Profile">
          <span className={styles.name}>
            {user.firstName} {user.lastName}
          </span>
          <span className={styles.avatar}>{user.initials}</span>
        </Link>
      </div>
      <p className={styles.eyebrow}>{eyebrow}</p>
      <h1 className={styles.title}>
        {title}
        <span className={styles.subtitle}> {subtitle}</span>
      </h1>
      {description && <p className={styles.description}>{description}</p>}
    </header>
  );
}

export default PageHeader;
