# pyOBD v3 Customizable Overview Checklist

## Widget catalog

- [ ] PID value card.
- [ ] Compact PID graph.
- [ ] Vehicle health and DTC summary.
- [ ] Readiness summary.
- [ ] Connection details.
- [ ] Vehicle profile summary.
- [ ] Navigation shortcut.
- [ ] Empty-state guidance when disconnected.

## Editing

- [ ] Add an explicit Edit Overview mode.
- [ ] Add widgets from a searchable catalog.
- [ ] Remove widgets without deleting their saved settings immediately.
- [ ] Drag widgets between grid positions.
- [ ] Resize widgets using supported grid sizes.
- [ ] Configure PID, units, title, color, and display style where applicable.
- [ ] Preview changes before leaving edit mode.
- [ ] Undo the current edit session.
- [ ] Restore the default Overview.

## Layout rules

- [ ] Use a structured responsive grid rather than free overlap.
- [ ] Reflow widgets safely when the window becomes narrow.
- [ ] Prevent widgets from becoming too small to read.
- [ ] Preserve logical keyboard and screen-reader order after rearranging.
- [ ] Keep connection status and Configure available regardless of layout.
- [ ] Show unavailable PIDs without breaking the layout.

## Persistence

- [ ] Save layouts automatically after confirmed edits.
- [ ] Maintain one global default layout.
- [ ] Allow an optional layout per vehicle profile.
- [ ] Load the vehicle layout after VIN/profile matching.
- [ ] Version the saved layout format for future migrations.
- [ ] Recover from missing, corrupt, or outdated layout data.
- [ ] Export and import Overview layouts.

## Performance and validation

- [ ] Update values without rebuilding the widget tree.
- [ ] Pause hidden widget subscriptions where practical.
- [ ] Keep editing responsive while Demo or live polling is active.
- [ ] Verify layouts at minimum, default, and maximized window sizes.
- [ ] Verify macOS, Windows, and Linux scaling behavior.
- [ ] Verify layouts with Demo mode and a real vehicle.
