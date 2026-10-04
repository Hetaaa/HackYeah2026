import { useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { Check, ChevronRight } from "lucide-react";
import { Link } from "react-router";
import logo from "../../assets/logo.svg";
import { initialsOf } from "../../api/adapters.js";
import { useAppStore } from "../../store/useAppStore.js";
import styles from "./PageHeader.module.scss";

/** Logo + avatar bar and the two-tone page title shared by all tabs. */
function PageHeader({ eyebrow, title, subtitle, description }) {
  return (
    <header className={styles.header}>
      <div className={styles.topBar}>
        <img src={logo} alt="why." className={styles.logo} />
        <PersonaSwitcher />
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

function PersonaSwitcher() {
  const user = useAppStore((s) => s.user);
  const users = useAppStore((s) => s.users);
  const current = useAppStore((s) => s.persona?.id);
  const selectUser = useAppStore((s) => s.selectUser);
  const [isOpen, setIsOpen] = useState(false);

  const choose = (id) => {
    setIsOpen(false);
    if (id !== current) selectUser(id);
  };

  return (
    <div className={styles.switcher}>
      <button
        className={styles.profile}
        aria-label="Switch person"
        aria-expanded={isOpen}
        onClick={() => setIsOpen((v) => !v)}
      >
        <span className={styles.name}>
          {user.firstName} {user.lastName}
        </span>
        <span className={styles.avatar}>{user.initials}</span>
      </button>
      <AnimatePresence>
        {isOpen && (
          <>
            <div className={styles.backdrop} onClick={() => setIsOpen(false)} />
            <motion.ul
              className={styles.menu}
              initial={{ opacity: 0, y: -6, scale: 0.97 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -6, scale: 0.97 }}
              transition={{ duration: 0.16 }}
            >
              {users.map((u) => (
                <li key={u.id}>
                  <button
                    className={`${styles.person} ${u.id === current ? styles.current : ""}`}
                    onClick={() => choose(u.id)}
                  >
                    <span className={styles.personAvatar}>{initialsOf(`${u.name} ${u.last_name}`)}</span>
                    <span className={styles.personText}>
                      <strong>
                        {u.name} {u.last_name}
                      </strong>
                      {u.description && <small>{u.description}</small>}
                    </span>
                    {u.id === current && <Check size={16} strokeWidth={2.5} className={styles.check} />}
                  </button>
                </li>
              ))}
              <li className={styles.menuFooter}>
                <Link to="/you" className={styles.profileLink} onClick={() => setIsOpen(false)}>
                  Your profile
                  <ChevronRight size={16} strokeWidth={2} />
                </Link>
              </li>
            </motion.ul>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}

export default PageHeader;
