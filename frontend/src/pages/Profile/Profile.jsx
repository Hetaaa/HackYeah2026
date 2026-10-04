import { useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { Bell, ChevronRight, Clock, Heart, Lock, LogOut, RefreshCw, Watch } from "lucide-react";
import PageHeader from "../../components/PageHeader/PageHeader.jsx";
import Disclaimer from "../../components/Disclaimer/Disclaimer.jsx";
import { useAppStore } from "../../store/useAppStore.js";
import { useClockText } from "../../utils/time.js";
import styles from "./Profile.module.scss";

// Mostly a mock: no real integration. Working settings: 24-hour format (stored in the browser)
// and the privacy sheet.
const HEALTH_DATA = ["Sleep", "steps", "heart rate", "workouts"];
const OTHER_SOURCES = [
  { name: "Fitbit", note: "Sleep stages, heart rate" },
  { name: "Garmin Connect", note: "Activity, stress" },
  { name: "Oura", note: "Sleep, readiness" },
];
const SYNC_MS = 1800;

function Profile() {
  const user = useAppStore((s) => s.user);
  const clockFormat = useAppStore((s) => s.clockFormat);
  const setClockFormat = useAppStore((s) => s.setClockFormat);
  const openPrivacy = useAppStore((s) => s.openPrivacy);
  const clock = useClockText();

  return (
    <div className={styles.page}>
      <PageHeader eyebrow="Your profile" title={`Hi, ${user.firstName}.`} subtitle="Here’s your setup." />

      <section className={styles.userCard}>
        <span className={styles.bigAvatar}>{user.initials}</span>
        <div>
          <h2 className={styles.userName}>
            {user.firstName} {user.lastName}
          </h2>
          <p className={styles.userMeta}>{user.email}</p>
          <p className={styles.userMeta}>Member since {user.memberSince}</p>
        </div>
      </section>

      <dl className={styles.stats}>
        <Stat label="Days tracked" value={user.stats.daysTracked} />
        <Stat label="Check-ins" value={user.stats.checkIns} />
        <Stat label="Day streak" value={user.stats.streak} />
      </dl>

      <HealthSync />

      <section>
        <p className={styles.sectionLabel}>Other sources</p>
        <ul className={styles.list}>
          {OTHER_SOURCES.map((s) => (
            <li key={s.name} className={styles.row}>
              <span className={styles.rowIcon}>
                <Watch size={18} />
              </span>
              <div className={styles.rowText}>
                <p className={styles.rowTitle}>{s.name}</p>
                <p className={styles.rowNote}>{s.note}</p>
              </div>
              <span className={styles.soon}>Soon</span>
            </li>
          ))}
        </ul>
      </section>

      <section>
        <p className={styles.sectionLabel}>Settings</p>
        <ul className={styles.list}>
          <ToggleRow icon={Bell} title="Daily check-in reminder" note={`Every day at ${clock("08:00")}`} defaultOn />
          <ToggleRow icon={RefreshCw} title="Weekly summary" note="Sunday evening" defaultOn={false} />
          <ToggleRow
            icon={Clock}
            title="24-hour format"
            note={`Bedtime ${clock("00:20")}`}
            on={clockFormat === "24h"}
            onChange={(on) => setClockFormat(on ? "24h" : "12h")}
          />
          <li className={styles.row}>
            <button className={styles.rowButton} onClick={openPrivacy}>
              <span className={styles.rowIcon}>
                <Lock size={18} />
              </span>
              <div className={styles.rowText}>
                <p className={styles.rowTitle}>Privacy</p>
                <p className={styles.rowNote}>Patterns use only your own data</p>
              </div>
              <ChevronRight size={18} className={styles.chevron} />
            </button>
          </li>
        </ul>
      </section>

      <Disclaimer />

      <button className={styles.signOut}>
        <LogOut size={16} /> Sign out
      </button>
      <p className={styles.version}>why. · v0.1 · HackYeah 2026</p>
    </div>
  );
}

function Stat({ label, value }) {
  return (
    <div className={styles.stat}>
      <dd>{value}</dd>
      <dt>{label}</dt>
    </div>
  );
}

function HealthSync() {
  const lastSync = useAppStore((s) => s.lastHealthSync);
  const clock = useClockText();
  const markSynced = useAppStore((s) => s.markHealthSynced);
  const [isSyncing, setIsSyncing] = useState(false);

  const sync = () => {
    setIsSyncing(true);
    setTimeout(() => {
      setIsSyncing(false);
      markSynced();
    }, SYNC_MS);
  };

  return (
    <section className={styles.health}>
      <div className={styles.healthHead}>
        <span className={styles.healthIcon}>
          <Heart size={20} strokeWidth={1.8} />
        </span>
        <div className={styles.rowText}>
          <p className={styles.healthTitle}>Apple Health</p>
          <p className={styles.rowNote}>{HEALTH_DATA.join(", ")}</p>
        </div>
        <span className={styles.connected}>Connected</span>
      </div>

      <div className={styles.syncRow}>
        <span>Last synced</span>
        <strong>{clock(lastSync)}</strong>
      </div>

      <button className={styles.syncButton} onClick={sync} disabled={isSyncing}>
        <motion.span
          className={styles.syncIcon}
          animate={isSyncing ? { rotate: 360 } : { rotate: 0 }}
          transition={isSyncing ? { repeat: Infinity, duration: 0.9, ease: "linear" } : { duration: 0 }}
        >
          <RefreshCw size={16} strokeWidth={2.4} />
        </motion.span>
        <AnimatePresence mode="wait" initial={false}>
          <motion.span
            key={isSyncing ? "syncing" : "idle"}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.15 }}
          >
            {isSyncing ? "Syncing…" : "Sync now"}
          </motion.span>
        </AnimatePresence>
        {isSyncing && (
          <motion.span
            className={styles.progress}
            initial={{ scaleX: 0 }}
            animate={{ scaleX: 1 }}
            transition={{ duration: SYNC_MS / 1000, ease: "easeInOut" }}
          />
        )}
      </button>
    </section>
  );
}

/** Uncontrolled (defaultOn, local state) unless `on` + `onChange` are given. */
function ToggleRow({ icon: Icon, title, note, defaultOn, on: controlledOn, onChange }) {
  const [localOn, setLocalOn] = useState(defaultOn);
  const on = controlledOn ?? localOn;
  const toggle = () => (onChange ? onChange(!on) : setLocalOn(!on));

  return (
    <li className={styles.row}>
      <span className={styles.rowIcon}>
        <Icon size={18} />
      </span>
      <div className={styles.rowText}>
        <p className={styles.rowTitle}>{title}</p>
        <p className={styles.rowNote}>{note}</p>
      </div>
      <button
        className={`${styles.toggle} ${on ? styles.toggleOn : ""}`}
        onClick={toggle}
        role="switch"
        aria-checked={on}
        aria-label={title}
      >
        <motion.span className={styles.knob} layout transition={{ type: "spring", stiffness: 600, damping: 35 }} />
      </button>
    </li>
  );
}

export default Profile;
