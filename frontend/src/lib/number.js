/**
 * Decimal-safe parsing/formatting for quantities and prices.
 * Avoids locale pitfalls and floating drift in UI calcs.
 */

/** @param {string|number|null|undefined} v */
export function parseDecimal(v) {
  if (v === null || v === undefined) return null;
  if (typeof v === "number") return Number.isFinite(v) ? v : null;
  const s = String(v).trim();
  if (!s) return null;
  // support "1,234.56" or "1 234,56" by normalizing
  const normalized = s
    .replace(/[\s,_]/g, "")
    .replace(/(\d)[,](\d{3}\b)/g, "$1$2")
    .replace(/,/, "."); // last comma -> dot for decimals
  const n = Number(normalized);
  return Number.isFinite(n) ? n : null;
}

/** @param {number|null|undefined} n */
export function toFixedSafe(n, digits = 2) {
  if (n === null || n === undefined || !Number.isFinite(n)) return "";
  const factor = Math.pow(10, digits);
  return String(Math.round(n * factor) / factor);
}

/** @param {number|null|undefined} n */
export function formatCurrency(n, currency = "USD", locale = "en-US") {
  if (n === null || n === undefined || !Number.isFinite(n)) return "";
  return new Intl.NumberFormat(locale, {
    style: "currency",
    currency,
    maximumFractionDigits: 2,
  }).format(n);
}

