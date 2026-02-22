import { describe, it, expect, beforeEach } from 'vitest';
import { setTimezone, formatDate, formatDateOnly, formatTime, formatDateShort } from './dates';

const ISO = '2024-06-15T18:30:00.000Z'; // 2:30 PM ET, 1:30 PM CT, 12:30 PM MT, 11:30 AM PT

describe('setTimezone + formatDate', () => {
  beforeEach(() => setTimezone(null));

  it('formats with explicit ET timezone', () => {
    setTimezone('America/New_York');
    const result = formatDate(ISO);
    expect(result).toContain('2:30');
    expect(result).toMatch(/Jun|June/);
    expect(result).toContain('2024');
  });

  it('formats with explicit PT timezone', () => {
    setTimezone('America/Los_Angeles');
    const result = formatDate(ISO);
    expect(result).toContain('11:30');
  });

  it('formats with UTC', () => {
    setTimezone('UTC');
    const result = formatDate(ISO);
    expect(result).toContain('6:30');
  });

  it('returns N/A for null input', () => {
    expect(formatDate(null)).toBe('N/A');
  });

  it('returns Invalid Date for garbage input', () => {
    expect(formatDate('not-a-date')).toBe('Invalid Date');
  });
});

describe('formatDateOnly', () => {
  it('returns date without time', () => {
    setTimezone('UTC');
    const result = formatDateOnly(ISO);
    expect(result).toContain('Jun');
    expect(result).toContain('15');
    expect(result).not.toMatch(/\d+:\d+/); // no time portion
  });

  it('returns N/A for null', () => {
    expect(formatDateOnly(null)).toBe('N/A');
  });
});

describe('formatTime', () => {
  it('returns time only', () => {
    setTimezone('UTC');
    const result = formatTime(ISO);
    expect(result).toMatch(/\d+:\d+/);
    expect(result).not.toMatch(/Jun/); // no date portion
  });
});

describe('formatDateShort (legacy compat)', () => {
  it('still works after refactor', () => {
    setTimezone('UTC');
    expect(formatDateShort(ISO)).toBe(formatDateOnly(ISO));
  });
});
