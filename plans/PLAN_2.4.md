# pyOBD v2.4 Plan

## Vehicle profiles and sessions

- [x] Save VIN, nickname, year, make, model, and notes.
- [x] Automatically select a vehicle profile by VIN.
- [x] Save and automatically select a default dashboard per vehicle.
- [x] Add recent-session history for Live Data recordings.
- [x] Browse, rename, export, and remove saved sessions.
- [x] Replay recorded CSV sessions through Graphs and Dashboard.

## Advanced diagnostics

- [x] Add a serialized read-only transport layer for physical and functional ECU addressing.
- [x] Support 11-bit and 29-bit CAN identifiers.
- [x] Use the adapter's ISO-TP multi-frame request and response handling.
- [x] Serialize diagnostic requests so they cannot collide with Live Data polling.
- [x] Add adapter capability detection and raw communication logging.
