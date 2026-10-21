# pyOBD Roadmap 2.5

Status copy of the main improvement and Swift rebuild roadmap for v2.5.
Checked items are implemented in the repository. Unchecked items are incomplete,
unverified, or only partially implemented.

## Desktop pyOBD

### Beginner-friendly installation

- [x] Build a self-contained Windows x64 installer.
- [x] Add Start Menu and optional desktop shortcuts on Windows.
- [x] Build a signed and notarized macOS Apple Silicon disk image.
- [x] Build an Ubuntu/Debian package with an application-menu entry.
- [x] Retain Python source installation for contributors and unsupported systems.
- [x] Make Demo mode available without a vehicle or adapter.
- [x] Publish platform artifacts automatically when a version tag is created.
- [ ] Sign the Windows installer.
- [ ] Complete clean-install release validation on every supported platform.

**Exit condition**

- [ ] A first-time user can install one download and use Demo mode on every supported platform without development tools or a terminal.

### Automated tests and protocol fixtures

- [ ] Add active automated tests to the repository.
- [ ] Test ELM327 initialization and prompt handling.
- [ ] Test supported-PID discovery.
- [ ] Test Mode 01 live-data decoding.
- [ ] Test Mode 02 freeze-frame decoding.
- [ ] Test Mode 03 trouble-code decoding.
- [ ] Test Mode 04 clear-code behavior.
- [ ] Test unit conversion and formatting.
- [ ] Test serial, Wi-Fi, Bluetooth, custom URL, and Demo target parsing.
- [ ] Add sanitized adapter transcripts for normal and multi-ECU responses.
- [ ] Add transcript cases for `NO DATA`, `SEARCHING...`, malformed frames, timeouts, and disconnects.
- [ ] Run the tests in CI without a vehicle or adapter.

**Exit condition**

- [ ] Protocol and connection tests run in CI using fixed fixtures.

### Application structure

- [x] Extract dashboard UI and behavior from `pyobd.py`.
- [x] Extract graph UI and behavior from `pyobd.py`.
- [x] Extract session recording and replay UI from `pyobd.py`.
- [x] Extract vehicle-profile UI and persistence from `pyobd.py`.
- [x] Extract application theme and reusable button styling.
- [x] Extract shared UI event definitions.
- [x] Add a standalone read-only diagnostic transport layer.
- [x] Keep the bundled OBD protocol implementation separate from the desktop UI.
- [ ] Move application startup into a dedicated app module.
- [ ] Add shared typed models for readings, DTCs, and connection state.
- [ ] Move settings loading, validation, and saving into a dedicated module.
- [ ] Split connection, polling, and diagnostics into independent services.
- [ ] Define common serial, TCP, and Demo transport interfaces.
- [ ] Reduce `pyobd.py` to screen assembly and event handlers.
- [ ] Run the complete protocol and service layer headlessly.

**Exit condition**

- [ ] The desktop UI has no adapter framing, port-opening, or PID-decoding responsibilities.

### Worker and connection lifecycle

- [x] Stop reading the selected wx page from the background worker.
- [x] Use page-driven polling modes instead of hard-coded page indexes.
- [x] Keep one worker as the owner of the active desktop adapter connection.
- [x] Add bounded connection attempts and cancellation checks.
- [x] Stop and join the worker during normal disconnect and shutdown.
- [x] Add reconnect attempt status in the UI.
- [x] Prevent a single missed health response from forcing reconnection.
- [x] Fix the reconnect crash caused by the missing `StatusEvent` import.
- [ ] Replace numeric thread-control flags with explicit events and commands.
- [ ] Add a complete connection state machine.
- [ ] Replace broad exception handling with structured connection errors.
- [ ] Add exponential reconnect backoff.
- [x] Remove the emergency process-exit fallback.

### Product experience

- [x] Add a modern Overview screen and navigation menu.
- [x] Display connection status throughout the app.
- [x] Add searchable Live Data.
- [x] Add supported-PID round-robin polling and batched UI updates.
- [x] Add configurable graph PID presets.
- [x] Add graph play/stop, combined views, and individual views.
- [x] Add customizable dashboards with movable widgets.
- [x] Support digital, dial, and combined dashboard widgets.
- [x] Support dashboard import and export using `.pyOBD` files.
- [x] Add stored, pending, and permanent DTC categories.
- [x] Add DTC descriptions and clear-code confirmation.
- [x] Add readiness monitor results.
- [x] Add supported-cylinder Mode 06 misfire results.
- [x] Add freeze-frame display.
- [x] Add persistent vehicle profiles with automatic VIN matching.
- [x] Add a default dashboard per vehicle profile.
- [x] Add CSV Live Data recording.
- [x] Add saved-session management and replay.
- [x] Add serial, Wi-Fi, Bluetooth SPP/RFCOMM, custom URL, and Demo connection targets.
- [x] Use the shared platform-aware visual theme across the primary UI.
- [ ] Add a first-run connection wizard with adapter-specific help.
- [ ] Show specific failure reasons such as port busy, permission denied, ECU unavailable, unsupported BLE, and network timeout.
- [ ] Add a recent-adapter list with one-click reconnect.
- [ ] Add sensor favorites and configurable polling groups.
- [ ] Add JSON recording alongside CSV.
- [ ] Add graph range selection, multiple scales, and image/data export.
- [ ] Add a diagnostic support bundle with sanitized logs.
- [ ] Verify light, dark, and high-contrast presentation on all platforms.

### Performance

- [x] Replace worker-side page inspection with page-driven polling modes.
- [x] Throttle connection checks while static pages are open.
- [x] Batch Live Data UI updates.
- [x] Poll Live Data in bounded round-robin batches.
- [x] Prevent duplicate graph draw events from queuing.
- [x] Cap retained graph samples.
- [x] Throttle graph value labels and redraws.
- [x] Throttle dashboard update events.
- [x] Run readiness and Mode 06 scans only when requested.
- [x] Remove the obsolete 4-graph and 8-graph implementations.
- [x] Remove the unused NumPy dependency.
- [x] Improve real-vehicle Live Data loading with four-PID batches and a shorter yield.

### Advanced read-only diagnostics

- [x] Add a serialized transport restricted to read-only diagnostic services.
- [x] Add 11-bit and 29-bit CAN addressing models.
- [x] Decode standard UDS negative-response codes.
- [x] Record an in-memory diagnostic request activity log.
- [ ] Add UDS diagnostic-session and tester-present handling.
- [ ] Discover vehicle modules and display their addresses and identities.
- [ ] Read enhanced module DTC status and snapshots.
- [ ] Add manufacturer-specific identifiers through vehicle profiles.
- [ ] Expand Mode 06 beyond cylinder misfire results.
- [ ] Add guided read-only tests at requested operating conditions.

### Experimental bidirectional diagnostics

- [x] Keep non-read-only services blocked by the current diagnostic transport.
- [x] Explicitly prohibit automatic throttle and engine-rev control in the plan.
- [ ] Define manufacturer-specific command packages outside the core transport.
- [ ] Require explicit vehicle profiles and adapter capability checks.
- [ ] Add preconditions, confirmations, time limits, cancellation, and persistent activity logs.
- [ ] Select one vehicle family and one low-risk actuator test for initial development.

### Repeatable releases

- [x] Define Python 3.8 or newer as the source-install minimum.
- [x] Define Windows x64, macOS Apple Silicon, and Ubuntu/Debian packages.
- [x] Build Windows, macOS, and Linux artifacts in GitHub Actions.
- [x] Sign and notarize the macOS release.
- [x] Retry macOS ticket stapling after transient Apple service failures.
- [x] Publish tagged GitHub releases with generated release notes.
- [x] Use semantic application versions from `pyproject.toml`.
- [x] Collect third-party notices and licenses into packaged builds.
- [ ] Add formatting and static-analysis jobs to CI.
- [ ] Add unit and fixture tests to CI.
- [ ] Add a maintained changelog.
- [ ] Add a tested hardware compatibility list.
- [ ] Validate each release with USB, Wi-Fi, Demo, and every advertised Bluetooth path.
- [ ] Complete real-vehicle testing on Windows, macOS, and Linux.

## pyOBD Mobile Swift app

### Compatibility specification

- [x] Select iOS 17 as the current minimum deployment target.
- [x] Document practical iOS transport limitations for Wi-Fi, BLE, Bluetooth Classic, and USB.
- [x] Keep pyOBD Mobile separate from the Python desktop application inside the same repository.
- [ ] Create a complete desktop-to-mobile feature compatibility matrix.
- [ ] Select and document one supported Wi-Fi adapter model.
- [ ] Select and document one supported BLE adapter and its GATT characteristics.
- [ ] Capture sanitized real-adapter and Demo sessions.
- [ ] Record expected decoded values for every fixture.

### Swift protocol engine

- [x] Add serialized ELM327 command queuing.
- [x] Add ELM327 reset and initialization commands.
- [x] Add response buffering and prompt handling.
- [x] Add command timeouts and pending-command cleanup.
- [x] Add supported-PID discovery through Modes `0100`, `0120`, and `0140`.
- [x] Add initial Mode 01 PID definitions and decoders.
- [x] Add stored, pending, and permanent DTC decoding.
- [x] Add readiness decoding for spark- and compression-ignition vehicles.
- [x] Add VIN, protocol, and adapter-voltage requests.
- [ ] Create `PyOBDKit` as an independent Swift package.
- [ ] Add a transport protocol shared by TCP, BLE, replay, and future Mac serial connections.
- [ ] Move command sequencing into a dedicated Swift actor.
- [ ] Add Replay transport and Demo mode.
- [ ] Add Swift fixture tests and compare results with Python expectations.

### Wi-Fi MVP

- [x] Add TCP connectivity with Apple's Network framework.
- [x] Persist the Wi-Fi adapter host and port.
- [x] Enable TCP keepalive.
- [x] Add automatic foreground reconnection.
- [x] Add Overview, Connection, Live Data, Diagnostics, and Readiness tabs.
- [x] Add connection, initialization, reconnecting, failed, and connected UI states.
- [x] Show supported live PIDs only while Overview or Live Data is visible.
- [x] Add stored, pending, and permanent DTC scans.
- [x] Add clear-code confirmation and readiness-reset warning.
- [x] Add clean disconnect and command cancellation.
- [ ] Add the basic live graph screen.
- [ ] Validate complete ELM initialization and vehicle data on a physical Wi-Fi adapter.
- [ ] Validate on iPhone and iPad.
- [ ] Add a Mac target and validate Wi-Fi there.

### BLE and polished diagnostics

- [x] Add BLE discovery, remembered peripheral identifiers, and reconnect handling.
- [x] Add BLE characteristic discovery, notifications, and writes.
- [x] Guard Core Bluetooth restoration behind the required background mode.
- [x] Add readiness UI and safe clear-code confirmation.
- [x] Handle foreground/background lifecycle restoration.
- [ ] Restrict BLE discovery to documented supported adapters and services.
- [ ] Validate BLE command exchange with a selected physical adapter.
- [ ] Add mobile freeze-frame data.
- [ ] Add mobile favorites.
- [ ] Add mobile recordings and export.
- [ ] Add richer mobile graphs.

### Mobile release preparation

- [x] Add application icon assets.
- [x] Add Bluetooth and local-network privacy descriptions.
- [ ] Add accessibility labels and full Dynamic Type verification.
- [ ] Make user-facing strings localization-ready.
- [ ] Add app logging and support-bundle export.
- [ ] Add a privacy policy.
- [ ] Complete TestFlight and crash testing.
- [ ] Complete App Store review preparation.
- [ ] Collect repeatable real-vehicle evidence for every advertised transport.

## v2.5 release focus

- [x] Complete the desktop performance pass.
- [x] Fix reconnect status-event failure.
- [x] Add tolerance for transient health-check failures.
- [x] Improve real-vehicle Live Data loading.
- [x] Organize plans and application assets.
- [ ] Revalidate desktop connection, reconnect, Live Data, Graphs, Dashboard, Readiness, and DTC behavior on a real vehicle.
- [ ] Complete Windows and Linux real-vehicle validation.
- [ ] Add connection diagnostics suitable for reporting future adapter drops.
- [ ] Resolve stale README statements about NumPy, recording, and replay.
- [ ] Complete the v2.5 release checklist and publish release notes.
