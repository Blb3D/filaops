import { useState, useEffect } from 'react';

/**
 * Parse datetime string, ensuring UTC interpretation
 * Backend sends UTC times without 'Z' suffix
 */
function parseDateTime(datetime) {
  if (!datetime) return null;
  if (datetime instanceof Date) return datetime;

  // If string doesn't have timezone info, assume UTC and add 'Z'
  let dateStr = datetime;
  if (typeof dateStr === 'string' && !dateStr.endsWith('Z') && !dateStr.includes('+') && !dateStr.includes('-', 10)) {
    dateStr = dateStr + 'Z';
  }
  return new Date(dateStr);
}

/**
 * ElapsedTimer - Live timer showing elapsed time since start
 *
 * Updates every second while mounted.
 */
export default function ElapsedTimer({ startTime, className = '' }) {
  const [elapsed, setElapsed] = useState('');

  useEffect(() => {
    if (!startTime) return;

    const updateElapsed = () => {
      const start = parseDateTime(startTime);
      const now = new Date();
      const diffMs = now.getTime() - start.getTime();

      if (diffMs < 0) {
        setElapsed('--:--:--');
        return;
      }

      const totalSeconds = Math.floor(diffMs / 1000);
      const hours = Math.floor(totalSeconds / 3600);
      const minutes = Math.floor((totalSeconds % 3600) / 60);
      const seconds = totalSeconds % 60;

      const hh = String(hours).padStart(2, '0');
      const mm = String(minutes).padStart(2, '0');
      const ss = String(seconds).padStart(2, '0');

      setElapsed(`${hh}:${mm}:${ss}`);
    };

    // Update immediately
    updateElapsed();

    // Then update every second
    const interval = setInterval(updateElapsed, 1000);

    return () => clearInterval(interval);
  }, [startTime]);

  if (!startTime) return null;

  return (
    <span className={`font-mono tabular-nums ${className}`}>
      {elapsed}
    </span>
  );
}
