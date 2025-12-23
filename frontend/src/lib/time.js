/**
 * Centralized time math: snap, working calendar, clamp-to-now.
 * Keep UI in local time but avoid scheduling in the past or off-hours.
 */
const HOUR_MS = 60 * 60 * 1000;

/** @param {number} ms @returns {Date} */
export const startOfDay = (ms) => {
  const d = new Date(ms);
  d.setHours(0, 0, 0, 0);
  return d;
};

/** @param {number} minutes @returns {(ms:number)=>number} */
export const makeSnap = (minutes) => {
  const step = Math.max(1, minutes) * 60 * 1000;
  return (ms) => Math.round(ms / step) * step;
};

/** @typedef {{days:boolean[], start:"HH:MM", end:"HH:MM"}} WorkSchedule */
export function parseHHMM(s) {
  const m = /^([01]?\d|2[0-3]):([0-5]\d)$/.exec(String(s || "").trim());
  return m ? { h: Number(m[1]), min: Number(m[2]) } : null;
}
export const toHours = ({ h, min }) => h + min / 60;

/** @param {WorkSchedule} sched */
export function makeCalendar(sched, snapMinutes = 15) {
  const snap = makeSnap(snapMinutes);
  const workDays = new Set(
    sched.days.map((on, i) => (on ? i : null)).filter((v) => v !== null)
  );
  const startH = toHours(parseHHMM(sched.start) || { h: 8, min: 0 });
  const endH = toHours(parseHHMM(sched.end) || { h: 22, min: 0 });
  const workWindowFor = (ms) => {
    const ds = startOfDay(ms).getTime();
    return { start: ds + startH * HOUR_MS, end: ds + endH * HOUR_MS };
  };
  const nextWorkdayStart = (ms) => {
    let t = startOfDay(ms).getTime() + 24 * HOUR_MS;
    while (true) {
      if (workDays.has(new Date(t).getDay())) return t + startH * HOUR_MS;
      t += 24 * HOUR_MS;
    }
  };
  const clampToWorkingStart = (ms, nowMs) => {
    let x = Math.max(ms, nowMs);
    if (!workDays.has(new Date(x).getDay())) return nextWorkdayStart(x);
    const { start, end } = workWindowFor(x);
    if (x < start) return start;
    if (x >= end) return nextWorkdayStart(x);
    return x;
  };
  const addWorkDuration = (startMs, durationMs, nowMs) => {
    let remaining = Math.max(durationMs, 30 * 60 * 1000);
    let cursor = clampToWorkingStart(startMs, nowMs);
    while (remaining > 0) {
      const { end } = workWindowFor(cursor);
      const chunk = Math.min(remaining, end - cursor);
      if (chunk > 0) {
        cursor += chunk;
        remaining -= chunk;
      }
      if (remaining > 0) cursor = nextWorkdayStart(cursor);
    }
    return cursor;
  };
  const scheduleWithinCalendar = (startMs, durationMs, nowMs) => {
    const s = clampToWorkingStart(snap(startMs), nowMs);
    const e = addWorkDuration(s, durationMs, nowMs);
    return { startMs: s, endMs: e };
  };
  return {
    snap,
    workDays,
    workWindowFor,
    nextWorkdayStart,
    clampToWorkingStart,
    addWorkDuration,
    scheduleWithinCalendar,
  };
}

export const fmtTime = (ms) =>
  new Date(ms).toLocaleTimeString("en-US", {
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  });
export const fmtDate = (ms) =>
  new Date(ms).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  });

