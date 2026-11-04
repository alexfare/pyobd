# pyOBD v3 Feature Parity Audit

Compared against the v2.6 wx application.

| Area | v3 status | Notes |
| --- | --- | --- |
| Overview | Complete | Qt uses customizable cards instead of the fixed six-button home grid. |
| Connection configuration | Complete | Auto, Demo, serial, Wi-Fi, Bluetooth, custom URL, baud, timeout, retries, send mode, and units are present. |
| Connection lifecycle | Complete | Connect, disconnect, reconnect, cleared identity/status, and shared ELM engine are present. |
| Live Data | Complete | Supported PIDs, search, selection, favorites, CSV recording, and Add to Graphs are present. |
| Diagnostics | Complete | Stored, pending, permanent, category summaries, descriptions, lookup, and clear warning are present. |
| Readiness | Complete | Summary and individual monitor states are present. |
| Mode 06 misfire | Complete | Only supported cylinder monitors are requested and displayed. |
| Freeze Frame | Complete | Mode 02 results are displayed. |
| Graphs | Complete | Multiple PIDs, values, presets, pause/resume, combined/separate views, and removal are present. |
| Dashboard | Complete | Named layouts, PID selection, dial/digital/combined gauges, center PID, ranges, divisions, names, colours, shapes, drag, resize, overlap, layering, reset, import, and export are present. |
| Vehicle profiles | Complete | VIN, nickname, year, make, model, notes, automatic VIN matching, and default dashboard are present. |
| Sessions | Complete | Named recordings, metadata, browse, replay, rename, export, delete, and recordings folder access are present. |
| Activity log | Complete | Qt uses a rotating chronological application log rather than the wx two-column event list. |
| Updates and support | Complete | Update check, releases, issue reporting, support, source, license, and adapter links are present. |
| Read-only diagnostic transport | Complete | v3 uses the same serialized `OBDConnection` and read-only diagnostic transport as v2.6. |

## Intentional differences

- The removed connection/status page remains replaced by the persistent header and footer status.
- Qt navigation replaces the wx menu bar; the same user actions remain available on pages.
- Graph PID removal is per graph card instead of wx multi-row selection.
- Settings and favorites are v3 additions.
- Overview is more configurable than v2.6 and does not copy its fixed tile layout.

## Remaining release validation

- Physical USB, Wi-Fi, and supported Bluetooth adapters.
- Connection loss and reconnect behavior.
- Real-vehicle PID discovery, DTCs, clearing, readiness, Mode 06, and freeze frame.
- Dashboard import/export and per-vehicle defaults using existing v2.6 data.
- macOS, Windows, and Linux packaging, scaling, keyboard navigation, and shutdown.
