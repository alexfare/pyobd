# pyOBD v3.0 Plan

## Goal

Replace wxPython with a modern PySide6 and Qt/QML interface while preserving the
working Python OBD engine and all supported desktop platforms.

The v2.6 application remains available and unchanged until v3 reaches feature
parity.

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

- [ ] Add responsive live graphs.
- [ ] Add PID value, graph, vehicle health, readiness, connection, and shortcut Overview widgets.
- [ ] Rebuild the customizable dashboard.
- [ ] Support dial, digital, and combined widgets.
- [ ] Support free positioning, resizing, layering, and layout import/export.

### Phase 4 — Migration

- [ ] Port settings, logging, recording, updates, and support information.
- [ ] Match serial, Wi-Fi, Bluetooth, custom URL, and Demo behavior.
- [ ] Remove all Qt-to-wx compatibility code.
- [ ] Reach feature parity with v2.6.

### Phase 5 — Release

- [ ] Validate macOS, Windows, and Linux packages.
- [ ] Validate USB, Wi-Fi, Bluetooth, and Demo connections.
- [ ] Complete real-vehicle regression testing.
- [ ] Make the Qt application the default desktop entry point.
- [ ] Retire wxPython after the final compatibility release.

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
