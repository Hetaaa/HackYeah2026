import { Signal, Wifi, BatteryFull } from "lucide-react";
import styles from "./PhoneFrame.module.scss";

/**
 * Desktop: renders children inside an iPhone mockup.
 * Phone-sized viewport: the frame disappears and the app goes full screen.
 * `transform` on .screen makes `position: fixed` children stick to the screen, not the window.
 */
function PhoneFrame({ children }) {
  return (
    <div className={styles.stage}>
      <div className={styles.device}>
        <div className={styles.screen}>
          <div className={styles.statusBar}>
            <span className={styles.time}>9:41</span>
            <span className={styles.island} />
            <span className={styles.statusIcons}>
              <Signal size={16} strokeWidth={2.5} />
              <Wifi size={16} strokeWidth={2.5} />
              <BatteryFull size={22} strokeWidth={2} />
            </span>
          </div>
          {children}
        </div>
      </div>
    </div>
  );
}

export default PhoneFrame;
