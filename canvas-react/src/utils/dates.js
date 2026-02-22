/**
 * Shared date formatting utilities.
 * Call setTimezone(tz) once on app load (e.g. from App.jsx after loading settings).
 * All formatters use the stored timezone; null = browser local time.
 */

let _timezone = null;

/**
 * Set the active display timezone for all formatters.
 * @param {string | null} tz - IANA timezone string (e.g. 'America/New_York') or null for browser local.
 */
export function setTimezone(tz) {
  _timezone = tz || null;
}

function toDate(input) {
  if (!input) return null;
  const d = typeof input === 'string' ? new Date(input) : input;
  return isNaN(d.getTime()) ? null : d;
}

/**
 * Format as date + time. e.g. "Jun 15, 2024, 2:30 PM"
 */
export function formatDate(dateInput) {
  const d = toDate(dateInput);
  if (!d && dateInput == null) return 'N/A';
  if (!d) return 'Invalid Date';
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    timeZone: _timezone ?? undefined,
  }).format(d);
}

/**
 * Format as date only. e.g. "Jun 15, 2024"
 */
export function formatDateOnly(dateInput) {
  const d = toDate(dateInput);
  if (!d && dateInput == null) return 'N/A';
  if (!d) return 'Invalid Date';
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    timeZone: _timezone ?? undefined,
  }).format(d);
}

/**
 * Format as time only. e.g. "2:30 PM"
 */
export function formatTime(dateInput) {
  const d = toDate(dateInput);
  if (!d && dateInput == null) return 'N/A';
  if (!d) return 'Invalid Date';
  return new Intl.DateTimeFormat('en-US', {
    hour: 'numeric',
    minute: '2-digit',
    timeZone: _timezone ?? undefined,
  }).format(d);
}

/**
 * @deprecated Use formatDateOnly instead.
 */
export function formatDateShort(dateInput) {
  return formatDateOnly(dateInput);
}
