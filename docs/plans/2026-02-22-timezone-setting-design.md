# Timezone Setting Design

**Date:** 2026-02-22
**Status:** Approved

## Overview

Add a timezone preference to the Settings page. All timestamps displayed in the app reflect the chosen timezone. Default is browser local time (no override).

## Timezone Options

| Label | IANA Value |
|---|---|
| Browser local time (default) | `null` / empty |
| UTC | `UTC` |
| Eastern (ET) | `America/New_York` |
| Central (CT) | `America/Chicago` |
| Mountain (MT) | `America/Denver` |
| Pacific (PT) | `America/Los_Angeles` |

## Backend Changes (`main.py`)

- Add `timezone: str | None` to `SettingsResponse`
- Add `timezone: str | None = None` to `SettingsUpdateRequest`
- `GET /api/settings` returns stored timezone (default `null`)
- `PUT /api/settings` stores via `db.set_setting("timezone", tz)`

## Frontend — `utils/dates.js`

Core change. Add module-level singleton:

```js
let _timezone = null;
export function setTimezone(tz) { _timezone = tz || null; }
```

Update/add formatters using `Intl.DateTimeFormat` with `timeZone: _timezone ?? undefined`:

- `formatDate(dateInput)` — date + time (e.g. "Jan 15, 2024, 2:30 PM ET")
- `formatDateOnly(dateInput)` — date only (e.g. "Jan 15, 2024")
- `formatTime(dateInput)` — time only (e.g. "2:30 PM ET")

When `_timezone` is `null`, `timeZone: undefined` means browser local — matching the default.

## Frontend — `App.jsx`

After loading settings from `/api/settings`, call `setTimezone(data.timezone)`.

## Frontend — `Settings.jsx`

- Add `timezone` state initialized from `settings.timezone`
- Add timezone dropdown (6 options above)
- Include `timezone` in the `PUT /api/settings` body alongside `course_id`

## Frontend — Replace inline formatters

Replace all scattered inline date/time formatting with calls to `utils/dates.js`:

| File | What to replace |
|---|---|
| `EnhancedTADashboard.jsx` | Hardcoded `America/New_York` / "EST" in `formatLastUpdated` |
| `EnrollmentTracking.jsx` | Local `formatDate`, `formatDateTime`, inline `toLocaleDateString()` |
| `LateDaysTracking.jsx` | Inline `toLocaleTimeString()`, `toLocaleDateString()`, `toLocaleString()` |
| `PeerReviewTracking.jsx` | Local `formatDateTime` |
| `Settings.jsx` | Inline `toLocaleString()` in sync history |
| `AssignmentStatusBreakdown.jsx` | Local `formatDate` |

## Data Flow

```
App.jsx loads /api/settings
  → calls setTimezone(data.timezone)
  → module variable _timezone is set

User navigates to any page
  → page renders, calls formatDate() / formatDateOnly() / formatTime()
  → Intl.DateTimeFormat uses _timezone
  → times shown in correct zone

User changes timezone in Settings
  → PUT /api/settings saves new value
  → App.jsx reloads settings (existing behavior on navigate away from /settings)
  → setTimezone() called again with new value
  → next render shows updated times
```
