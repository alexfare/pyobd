# pyOBD v2.3 Plan

v2.2 release validation remains on the v2.2 branch. v2.3 development assumes the existing desktop features are working.

## Current focus

- [x] Record selected Live Data PIDs with timestamps.
- [x] Export recorded sessions to CSV.
- [x] Show recording state, elapsed time, and sample count.
- [x] Stop and save recordings cleanly during disconnect or shutdown.
- [x] Support recording in Demo mode.

## Next

- [x] Save named PID and graph presets.
- [x] Restore a preset without duplicating graph entries.
- [x] Improve connection-loss detection and recovery.
- [x] Add customizable named dashboards with movable and configurable PID widgets.
- [ ] Add vehicle profiles and recent-session history.
- [ ] Complete another cross-platform interface consistency pass.

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
