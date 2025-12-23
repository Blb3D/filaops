/**
 * Tiny global event bus for app-wide notifications (API errors, etc).
 */
const listeners = new Map();

export function on(event, cb) {
  if (!listeners.has(event)) listeners.set(event, new Set());
  listeners.get(event).add(cb);
  return () => off(event, cb);
}

export function off(event, cb) {
  listeners.get(event)?.delete(cb);
}

export function emit(event, payload) {
  const set = listeners.get(event);
  if (!set) return;
  for (const cb of set) {
    try {
      cb(payload);
    } catch (e) {
      /* ignore */
    }
  }
}

