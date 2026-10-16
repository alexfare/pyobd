# pyOBD v2.2 Release Checklist

Release owner: ____________________  Target date: ____________________

## Release blockers

- [ ] No crashes, freezes, or deleted-object tracebacks during normal use or shutdown.
- [ ] Windows, macOS Apple Silicon, and Linux pass clean-install testing.
- [ ] Windows, macOS Apple Silicon, and Linux pass real-vehicle testing.
- [ ] Installer artifacts report version `2.2.0` consistently.
- [ ] No known issue can clear codes or change vehicle state without confirmation.

## Version and release metadata

- [ ] Change `pyproject.toml` from `1.17` to `2.2.0`.
- [ ] Decide whether `obd/__version__.py` remains the bundled library version (`0.7.3`) or should match the app version.
- [ ] Confirm the window title shows `pyOBD v2.2 - Modified by Fare Brothers`.
- [ ] Confirm Windows installer, macOS DMG, Linux package, Git tag, and GitHub release all show `2.2.0`.
- [ ] Prepare release notes covering the new interface, installers, performance improvements, DTC categories, Readiness, and Mode 06 results.
- [ ] Document supported platforms and known limitations, including no Intel macOS release and no BLE-only adapter support.

## Platform sign-off

| Platform | Clean install | Demo mode | Real vehicle | Installer | Sign-off |
| --- | --- | --- | --- | --- | --- |
| macOS Apple Silicon | [ ] | [ ] | [ ] | [ ] | __________ |
| Windows 10/11 x64 | [ ] | [ ] | [ ] | [ ] | __________ |
| Ubuntu/Debian x64 | [ ] | [ ] | [ ] | [ ] | __________ |

### Validation notes

- [x] Linux: application launches and runs normally in initial desktop testing.
- [ ] Linux: real-vehicle connection and diagnostics remain untested.

## Clean-install checks — each platform

- [ ] Install on a machine without the development environment.
- [ ] Launch from the normal application shortcut or launcher without a terminal.
- [ ] Confirm the icon, application name, version, and publisher information.
- [ ] Confirm no Python, pip, or dependency setup is requested.
- [ ] Open every page and verify controls fit without clipped labels.
- [ ] Verify button colors, hover states, disabled states, keyboard focus, and text contrast.
- [ ] Verify light and dark system themes where available.
- [ ] Verify common display scaling settings do not clip the header, navigation, dialogs, or bottom status bar.
- [ ] Close from the window control and menu without a traceback or remaining background process.
- [ ] Reopen after closing and confirm saved settings load correctly.
- [ ] Uninstall cleanly.

## Demo-mode checks — each platform

- [ ] Connect using Demo mode.
- [ ] Disconnect and reconnect several times.
- [ ] Toggle the hamburger navigation open and closed.
- [ ] Visit every page repeatedly while connected.
- [ ] Filter Live Data rapidly without freezing.
- [ ] Select one and multiple PIDs and add them to Graphs.
- [ ] Add and remove graph PIDs without lag.
- [ ] Start and stop graph playback; verify combined and individual graph views.
- [ ] Scan codes and verify Stored, Pending, and Permanent categories and totals.
- [ ] Verify code lookup opens normally.
- [ ] Refresh Readiness and verify Ready, Not ready, and Unsupported presentation.
- [ ] Verify Mode 06 misfire results remain separate from Readiness.
- [ ] Leave the app running for at least 15 minutes and switch pages during graph playback.
- [ ] Close while connected and confirm a clean shutdown.

## Real-vehicle setup

- [ ] Use the same known-good ELM327-compatible adapter and vehicle for the first pass on all three platforms.
- [ ] Record vehicle year, make, model, engine, adapter model, connection type, and protocol.
- [ ] Keep the vehicle parked in a safe, ventilated location with stable battery voltage.
- [ ] Capture existing codes and readiness state before any clear-code test.
- [ ] Do not create faults, command actuators, or perform road testing solely for release validation.

## Real-vehicle checks — each platform

- [ ] Adapter is listed clearly in Configure.
- [ ] Connect succeeds without repeated attempts or UI freezing.
- [ ] Header and bottom status bar show the correct connection state.
- [ ] Protocol, adapter, port, VIN, and voltage populate where supported.
- [ ] Disconnect and reconnect without restarting the app.
- [ ] Live Data loads supported PIDs and updates smoothly.
- [ ] Live Data search remains responsive while values update.
- [ ] Add selected Live Data PIDs to Graphs.
- [ ] Graph multiple PIDs for at least five minutes without lag or stale values.
- [ ] Remove graph PIDs and switch graph views while connected.
- [ ] Stored, Pending, and Permanent DTC requests complete without errors.
- [ ] DTC category totals match the displayed rows.
- [ ] Freeze Frame loads when supported and handles unsupported data cleanly.
- [ ] Readiness results match a trusted comparison scanner.
- [ ] Mode 06 misfire results display when supported and show Unsupported otherwise.
- [ ] Clearing codes requires confirmation and explains that readiness will reset.
- [ ] If clearing is approved for the test vehicle, Stored and Pending codes clear while Permanent codes follow ECU behavior.
- [ ] Connection loss or adapter removal returns the UI to Disconnected without a crash.
- [ ] Closing while connected produces no traceback and leaves no active process.

## Platform-specific installer checks

### macOS Apple Silicon

- [ ] DMG opens, application copies to Applications, and the application launches normally.
- [ ] Developer ID signature verifies.
- [ ] Notarization and stapling verify.
- [ ] Gatekeeper does not show the malware/unverified-developer warning.
- [ ] Serial/USB permission behavior is understandable.

### Windows

- [ ] Installer works for a standard non-admin user.
- [ ] Start menu and optional desktop shortcuts launch the application.
- [ ] Publisher/version details are correct.
- [ ] Required adapter driver and COM port appear correctly.
- [ ] Uninstaller removes application files and shortcuts.

### Linux

- [ ] DEB installs through the graphical package manager and command-line package tools.
- [ ] Application menu entry and icon appear correctly.
- [ ] Launcher starts the bundled application without a terminal.
- [ ] Missing serial-group permission produces a useful failure instead of a crash.
- [ ] Package removes cleanly.

## Final release gate

- [ ] Review all failures and document accepted known issues.
- [ ] Repeat any failed test after its fix on the affected platform.
- [ ] Confirm the repository is clean and the release commit is identified.
- [ ] Trigger the installer workflow from the release commit.
- [ ] Verify all three artifact names and versions.
- [ ] Install and launch the exact generated artifacts once more.
- [ ] Create tag `v2.2.0` and publish the GitHub release.
- [ ] Confirm the release page includes Windows, macOS Apple Silicon, and Linux downloads.
