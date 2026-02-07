/**
 * Shared date formatting utilities
 */

/**
 * Format date to full locale string
 * @param {string | Date} dateInput - Date string or Date object
 * @returns {string} - Formatted date (e.g., "January 15, 2024, 2:30 PM")
 */
export function formatDate(dateInput) {
  if (!dateInput) return 'N/A';
  try {
    const date = typeof dateInput === 'string' ? new Date(dateInput) : dateInput;
    return date.toLocaleString();
  } catch {
    return 'Invalid Date';
  }
}

/**
 * Format date to short locale string (date only)
 * @param {string | Date} dateInput - Date string or Date object
 * @returns {string} - Formatted date (e.g., "1/15/2024")
 */
export function formatDateShort(dateInput) {
  if (!dateInput) return 'N/A';
  try {
    const date = typeof dateInput === 'string' ? new Date(dateInput) : dateInput;
    return date.toLocaleDateString();
  } catch {
    return 'Invalid Date';
  }
}
