import { useMemo, useState } from "react";
import { useSearchParams } from "react-router";
import PageHeader from "../../components/PageHeader/PageHeader.jsx";
import Disclaimer from "../../components/Disclaimer/Disclaimer.jsx";
import { getDay, isAvailable, listDays, TODAY } from "../../mocks/days.js";
import { useAppStore } from "../../store/useAppStore.js";
import MonthCalendar from "./components/MonthCalendar.jsx";
import DayDetail from "./components/DayDetail.jsx";
import styles from "./Days.module.scss";

const lastDayOfMonth = (month) => {
  const [y, m] = month.split("-").map(Number);
  return `${month}-${String(new Date(y, m, 0).getDate()).padStart(2, "0")}`;
};

function Days() {
  // Selected day lives in the URL (?date=2024-10-19) so other screens can deep-link to a day.
  const [params, setParams] = useSearchParams();
  const requested = params.get("date");
  const selected = requested && isAvailable(requested) ? requested : TODAY;
  const [month, setMonth] = useState(selected.slice(0, 7));
  const checkIn = useAppStore((s) => s.checkIn);

  // Mock "GET /days?from&to" and "GET /days/{date}"; checkIn colours today once it's filled in.
  const days = useMemo(() => listDays(`${month}-01`, lastDayOfMonth(month), checkIn), [month, checkIn]);
  const day = useMemo(() => getDay(selected, checkIn), [selected, checkIn]);

  return (
    <div className={styles.page}>
      <PageHeader
        eyebrow="Your days"
        title="Every day,"
        subtitle="in context."
        description="Each day compared with your average good day."
      />
      <MonthCalendar
        month={month}
        days={days}
        selected={selected}
        onMonthChange={setMonth}
        onSelect={(date) => setParams({ date }, { replace: true })}
      />
      <DayDetail day={day} />
      <Disclaimer />
    </div>
  );
}

export default Days;
