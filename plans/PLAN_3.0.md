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
- [ ] Add framework-neutral connection and vehicle-state models.
- [ ] Replace direct `wx.PostEvent` calls behind a UI-neutral event sink.
- [ ] Add a v3 Demo service that uses the existing simulated OBD behavior.

### Phase 2 — Core diagnostics

- [ ] Add Connection configuration and status.
- [ ] Add Live Data with search, favorites, and supported-PID filtering.
- [ ] Add stored, pending, and permanent DTCs with descriptions.
- [ ] Add Readiness and Freeze Frame screens.
- [ ] Add vehicle profiles and default-dashboard selection.

### Phase 3 — Visualization

- [ ] Add responsive live graphs.
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
3. Live Data
4. Diagnostics and readiness
5. Graphs
6. Dashboard
7. Settings and secondary dialogs

## v3.0 release gate

- No wxPython imports in the v3 package or core OBD services.
- No UI work occurs on the OBD worker thread.
- Disconnect and shutdown complete without background-thread exceptions.
- Feature parity with v2.6 on all supported desktop systems.
- Demo mode and recorded-response tests work without an adapter.
