# pyOBD v2.5 Plan

## Advanced read-only diagnostics

- [ ] Add UDS sessions, timing, tester-present messages, and negative-response decoding.
- [ ] Discover available modules and display their addresses and identities.
- [ ] Read enhanced module DTCs, status information, and available snapshots.
- [ ] Read manufacturer-specific identifiers and sensor values through vehicle profiles.
- [ ] Expand Mode 06 beyond misfire results.
- [ ] Add guided read-only tests that record data at a requested operating condition.

## Deferred vehicle and session improvements

- [ ] Save preferred adapter settings and PID presets per vehicle.
- [ ] Add scan, DTC, and connection history.

## Experimental bidirectional diagnostics

- [ ] Keep manufacturer-specific commands outside the core transport layer.
- [ ] Require explicit vehicle profiles and supported-adapter checks.
- [ ] Add preconditions, confirmations, time limits, cancellation, and activity logs.
- [ ] Begin with one vehicle family and low-risk actuator tests.
- [ ] Do not add automatic throttle or engine-rev control.
