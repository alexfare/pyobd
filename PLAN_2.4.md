# pyOBD v2.4 Plan

## Vehicle profiles and sessions

- [x] Save VIN, nickname, year, make, model, and notes.
- [ ] Automatically select a vehicle profile by VIN.
- [ ] Save preferred adapter settings, dashboards, and PID presets per vehicle.
- [ ] Add recent-session history for recordings, scans, DTCs, and connection dates.
- [ ] Browse, rename, export, and remove saved sessions.
- [ ] Replay recorded CSV sessions through Graphs and Dashboard.

## Advanced diagnostics

- [ ] Add a transport layer for physical and functional ECU addressing.
- [ ] Support 11-bit and 29-bit CAN identifiers.
- [ ] Add ISO-TP multi-frame request and response handling.
- [ ] Add UDS sessions, timing, tester-present messages, and negative-response decoding.
- [ ] Serialize diagnostic requests so they cannot collide with Live Data polling.
- [ ] Add adapter capability detection and raw communication logging.
- [ ] Discover available modules and display their addresses and identities.
- [ ] Read enhanced module DTCs, status information, and available snapshots.
- [ ] Read manufacturer-specific identifiers and sensor values through vehicle profiles.
- [ ] Expand Mode 06 beyond misfire results.
- [ ] Add guided read-only tests that record data at a requested operating condition.

## Experimental bidirectional diagnostics

- [ ] Keep manufacturer-specific commands outside the core transport layer.
- [ ] Require explicit vehicle profiles and supported-adapter checks.
- [ ] Add preconditions, confirmations, time limits, cancellation, and activity logs.
- [ ] Begin with one vehicle family and low-risk actuator tests.
- [ ] Do not add automatic throttle or engine-rev control.
