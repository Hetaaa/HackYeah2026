import { NavLink } from "react-router";
import { motion } from "motion/react";
import { Calendar, ChartNoAxesColumn, House, User } from "lucide-react";
import styles from "./BottomNav.module.scss";

const TABS = [
  { to: "/", label: "Today", Icon: House },
  { to: "/days", label: "Days", Icon: Calendar },
  { to: "/patterns", label: "Patterns", Icon: ChartNoAxesColumn },
  { to: "/you", label: "You", Icon: User },
];

function BottomNav() {
  return (
    <nav className={styles.nav}>
      {TABS.map(({ to, label, Icon }) => (
        <NavLink
          key={to}
          to={to}
          end={to === "/"}
          className={({ isActive }) => (isActive ? `${styles.tab} ${styles.active}` : styles.tab)}
        >
          {({ isActive }) => (
            <>
              <span className={styles.icon}>
                {/* One shared layoutId: the dark square slides to the active tab. */}
                {isActive && (
                  <motion.span
                    layoutId="nav-pill"
                    className={styles.pill}
                    transition={{ type: "spring", stiffness: 420, damping: 34 }}
                  />
                )}
                <motion.span
                  className={styles.glyph}
                  animate={isActive ? { y: [0, -4, 0], scale: [1, 1.12, 1] } : { y: 0, scale: 1 }}
                  transition={{ duration: 0.4, ease: "easeOut" }}
                >
                  <Icon size={22} strokeWidth={1.6} />
                </motion.span>
              </span>
              {label}
            </>
          )}
        </NavLink>
      ))}
    </nav>
  );
}

export default BottomNav;
