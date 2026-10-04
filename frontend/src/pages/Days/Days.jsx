import { useEffect, useState } from "react";
import { useSearchParams } from "react-router";
import PageHeader from "../../components/PageHeader/PageHeader.jsx";
import Disclaimer from "../../components/Disclaimer/Disclaimer.jsx";
import { api } from "../../api/client.js";
import { buildDay } from "../../api/adapters.js";
import { useAppStore } from "../../store/useAppStore.js";
import MonthCalendar from "./components/MonthCalendar.jsx";
import DayDetail from "./components/DayDetail.jsx";
import styles from "./Days.module.scss";

const lastDayOfMonth = (month) => {
  const [y, m] = month.split("-").map(Number);
  return `${month}-${String(new Date(y, m, 0).getDate()).padStart(2, "0")}`;
};

function Days() {
  const persona = useAppStore((s) => s.persona);
  return <DaysView key={persona.id} persona={persona} />;
}

function DaysView({ persona }) {
  const today = persona.today;
  const firstDate = persona.first_date ?? today;
  const isAvailable = (date) => date >= firstDate && date <= today;
  const reference = persona.norm_reference === "all_days" ? "your average day" : "your average good day";

  // Selected day lives in the URL (?date=2020-02-14) so other screens can deep-link to a day.
  const [params, setParams] = useSearchParams();
  const requested = params.get("date");
  const selected = requested && isAvailable(requested) ? requested : today;
  const [month, setMonth] = useState(selected.slice(0, 7));
  const checkIn = useAppStore((s) => s.checkIn);

  const [days, setDays] = useState([]);
  const [detail, setDetail] = useState({ date: null, data: null, error: null });

  useEffect(() => {
    let active = true;
    api.days(persona.id, `${month}-01`, lastDayOfMonth(month)).then(
      (data) => active && setDays(data),
      () => active && setDays([]),
    );
    return () => {
      active = false;
    };
  }, [persona.id, month, checkIn]);

  useEffect(() => {
    let active = true;
    api.day(persona.id, selected).then(
      (data) => active && setDetail({ date: selected, data, error: null }),
      (error) => active && setDetail({ date: selected, data: null, error: error.message }),
    );
    return () => {
      active = false;
    };
  }, [persona.id, selected, checkIn]);

  const isLoaded = detail.date === selected;

  return (
    <div className={styles.page}>
      <PageHeader
        eyebrow="Your days"
        title="Every day,"
        subtitle="in context."
        description={`Each day compared with ${reference}.`}
      />
      <MonthCalendar
        month={month}
        days={days}
        selected={selected}
        firstMonth={firstDate.slice(0, 7)}
        today={today}
        onMonthChange={setMonth}
        onSelect={(date) => setParams({ date }, { replace: true })}
      />
      <DayDetail
        date={selected}
        today={today}
        reference={reference}
        day={isLoaded ? buildDay(detail.data) : null}
        isLoading={!isLoaded}
        error={detail.error}
      />
      <Disclaimer />
    </div>
  );
}

export default Days;
