# pyOBD v3 Build Checklist

## Foundation

- [x] `pyobd_v3` package created.
- [x] PySide6 is the primary desktop UI dependency.
- [x] Qt/QML shell created.
- [x] Initial visual theme created.
- [x] Overview prototype created with Demo data.
- [x] Framework-neutral application models created.
- [x] UI-neutral event sink replaces direct wx event posting.
- [x] Connection and polling services run without a UI.
- [x] Demo mode supplies the same models as a real connection.

## Screen migration

- [x] Overview customization completed.
- [x] Connection configuration completed.
- [x] Live Data completed.
- [x] Diagnostics and DTC lookup completed.
- [x] Readiness completed.
- [x] Mode 06 misfire results completed.
- [x] Freeze Frame completed.
- [x] Graphs completed.
- [x] Dashboard completed.
- [x] Vehicle profiles completed.
- [x] Recorded sessions and replay completed.
- [x] Trace/log viewer completed.
- [x] Settings, updates, About, and support completed.
- [x] DTC lookup and category summaries completed.
- [x] Graph presets, pause, and combined/separate views completed.

## Behavior parity

- [ ] Serial/USB connection matches v2.6.
- [ ] Wi-Fi connection matches v2.6.
- [ ] Supported Bluetooth connection matches v2.6.
- [ ] Demo mode matches v2.6.
- [ ] Reconnect and connection-loss behavior verified.
- [ ] Supported PID discovery verified.
- [ ] Stored, pending, and permanent DTC behavior verified.
- [ ] Clear-code confirmation and readiness warning verified.
- [ ] Dashboard layout import/export verified.
- [ ] Vehicle-specific defaults verified.

## Quality

- [x] No OBD or transport service imports wxPython or PySide6.
- [x] No blocking adapter work runs on the UI thread.
- [ ] Repeated page changes remain responsive while connected.
- [ ] Disconnect and shutdown leave no worker running.
- [ ] Light, dark, and high-contrast appearances are usable.
- [ ] Keyboard navigation and screen-reader labels are present.
- [ ] Common display scaling and window sizes do not clip controls.

## Platform validation

| Platform | Demo | USB | Wi-Fi | Bluetooth | Vehicle | Package |
| --- | --- | --- | --- | --- | --- | --- |
| macOS Apple Silicon | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| Windows 10/11 x64 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| Ubuntu/Debian x64 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |

## Release gate

- [x] v2.6 feature parity documented.
- [x] Accepted differences documented.
- [ ] Real-vehicle regression checklist completed.
- [ ] Installers launch without requiring Python or pip.
- [x] v3 becomes the default application entry point.
- [x] wxPython is retired from the main branch.
