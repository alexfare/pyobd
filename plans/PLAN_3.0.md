# pyOBD v3.0 Plan

## Goal

Replace wxPython with a modern PySide6 and Qt/QML interface while preserving the
working Python OBD engine and all supported desktop platforms.

Version 3 is the primary desktop application. The retired wxPython interface
remains available through earlier release tags.

## Architecture

```text
pyobd_v3/
  app.py                 Qt application startup
  models/                framework-neutral application state
  services/              connection, polling, diagnostics, recording
  ui/                    QML screens and reusable controls

obd/                     existing protocol and command implementation
```

The OBD engine must not import PySide6 or wxPython. UI updates flow through
typed state and callbacks so the same services can support Qt, tests, and
headless diagnostics.

## Delivery phases

### Phase 1 — Foundation

- [x] Create the parallel `pyobd_v3` application package.
- [x] Create the Qt/QML application shell and visual theme.
- [x] Create the first Overview screen using Demo data.
- [x] Add framework-neutral connection and vehicle-state models.
- [x] Replace direct `wx.PostEvent` calls behind a UI-neutral event sink.
- [x] Add a v3 Demo service that uses the existing simulated OBD behavior.

### Phase 2 — Core diagnostics

- [x] Add Connection configuration and status.
- [x] Make Overview a customizable, responsive widget grid.
- [x] Allow users to add, remove, reorder, and resize Overview widgets.
- [x] Save a global Overview layout and optional per-vehicle layouts.
- [x] Add Live Data with search, favorites, and supported-PID filtering.
- [x] Add stored, pending, and permanent DTCs with descriptions.
- [x] Add Readiness and Freeze Frame screens.
- [x] Add vehicle profiles and default-dashboard selection.

### Phase 3 — Visualization

- [x] Add responsive live graphs.
- [x] Add PID value, graph, vehicle health, readiness, connection, and shortcut Overview widgets.
- [x] Rebuild the customizable dashboard.
- [x] Support dial, digital, and combined widgets.
- [x] Support free positioning, resizing, layering, and layout import/export.

### Phase 4 — Migration

- [x] Port settings, logging, recording, updates, and support information.
- [x] Match serial, Wi-Fi, Bluetooth, custom URL, and Demo behavior.
- [x] Remove all Qt-to-wx compatibility code.
- [x] Reach feature parity with v2.6.

### Phase 5 — Release

- [ ] Validate macOS, Windows, and Linux packages.
- [ ] Validate USB, Wi-Fi, Bluetooth, and Demo connections.
- [ ] Complete real-vehicle regression testing.
- [x] Make the Qt application the default desktop entry point.
- [x] Retire wxPython after the final compatibility release.

### Phase 7 — v2.6 parity audit

- [x] Inventory every v2.6 page, action, setting, and persisted data type.
- [x] Restore DTC category summaries and searchable code lookup.
- [x] Restore graph presets, pause/resume, and combined/separate views.
- [x] Match connection defaults and advanced configuration fields.
- [x] Confirm vehicle profiles, dashboard layouts, recordings, replay, Mode 06,
  freeze frame, readiness, updates, support, and activity logs are represented.
- [x] Document intentional Qt UX differences.
- [ ] Complete connected-vehicle and cross-platform parity validation.

## First migration order

1. Application state and event boundary
2. Connection lifecycle
3. Customizable Overview
4. Live Data
5. Diagnostics and readiness
6. Graphs
7. Dashboard
8. Settings and secondary dialogs

## v3.0 release gate

- No wxPython imports in the v3 package or core OBD services.
- No UI work occurs on the OBD worker thread.
- Disconnect and shutdown complete without background-thread exceptions.
- Feature parity with v2.6 on all supported desktop systems.
- Demo mode and recorded-response tests work without an adapter.
- Overview layouts persist, recover safely, and remain usable at supported window sizes.
