"""Qt adapter for framework-neutral v3 application state."""

from collections import defaultdict, deque
import csv
import json
from pathlib import Path
import re
import threading
import time
import urllib.error
import urllib.request
from uuid import uuid4

from PySide6.QtCore import Property, QObject, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices

from event_sink import AppEvent, CallbackEventSink, EventChannel
from obd2_codes import pcodes
from pyobd_v3.app_info import (
    ADAPTER_URL, APP_VERSION, ISSUES_URL, LICENSE_URL, PROJECT_URL, RELEASE_API_URL,
    RELEASES_URL, SUPPORT_URL,
)
from pyobd_v3.dashboard_model import DashboardListModel
from pyobd_v3.live_data_model import LiveDataListModel
from pyobd_v3.models import ConnectionConfig, ConnectionState, VehicleState
from pyobd_v3.services import (
    AppLog, RecordingService, SettingsStore, VehicleService,
    bluetooth_adapters, serial_adapters,
)
from pyobd_v3.services.settings import DEFAULT_DASHBOARD_WIDGETS, DEFAULT_WIDGETS


class AppModel(QObject):
    pageChanged = Signal()
    stateChanged = Signal()
    graphChanged = Signal()
    profileChanged = Signal()
    diagnosticsChanged = Signal()
    sessionsChanged = Signal()
    traceChanged = Signal()
    dashboardChanged = Signal()
    graphSelectionChanged = Signal()
    settingsSectionChanged = Signal()
    performanceChanged = Signal()
    serviceEvent = Signal(object)

    def __init__(self):
        super().__init__()
        self._page = "Overview"
        self._settings_section = "General"
        self._connection = ConnectionState()
        self._vehicle = VehicleState()
        self._supported_pids = []
        self._readings = {}
        self._history = defaultdict(lambda: deque(maxlen=300))
        self._live_data = []
        self._live_data_model = LiveDataListModel(self)
        self._live_search = ""
        self._favorites_only = False
        self._live_selected = set()
        self._diagnostic_codes = []
        self._readiness = []
        self._misfire_results = []
        self._freeze_frame = []
        self._operation_error = ""
        self._update_status = ""
        self._update_url = RELEASES_URL
        self._bluetooth_adapters = bluetooth_adapters()
        self._serial_adapters = serial_adapters()
        self._store = SettingsStore()
        self._preferences = self._store.preferences()
        try:
            self._poll_interval = max(
                0.03, float(self._preferences.get("poll_interval", 0.08))
            )
        except (TypeError, ValueError):
            self._poll_interval = 0.08
        self._log = AppLog()
        self._trace_lines = self._log.tail()
        self._recording = RecordingService()
        self._recording_status = ""
        self._recorded_sessions = self._recording.sessions()
        self._replay_rows = []
        self._replay_index = 0
        self._replay_started = None
        self._replay_status = ""
        self._replay_timer = QTimer(self)
        self._replay_timer.setInterval(33)
        self._replay_timer.timeout.connect(self._advance_session_replay)
        self._favorites = self._store.favorites()
        self._graph_pids = self._store.graph_pids()
        self._graph_presets = self._store.graph_presets()
        self._current_graph_preset = ""
        self._profiles = self._store.profiles()
        self._active_profile_id = ""
        self._vehicle_profile_status = ""
        self._vehicle_layout_enabled = False
        self._overview_widgets = self._store.overview_widgets()
        self._dashboard_layouts = {}
        for name, layout in self._store.dashboard_layouts().items():
            try:
                widgets = [
                    self._normalized_dashboard_widget(item)
                    for item in layout.get("widgets", [])
                ]
            except (TypeError, ValueError):
                continue
            self._dashboard_layouts[name] = {"widgets": widgets}
        if not self._dashboard_layouts:
            self._dashboard_layouts = {"Daily Driving": {"widgets": [
                self._normalized_dashboard_widget(item)
                for item in DEFAULT_DASHBOARD_WIDGETS
            ]}}
        saved_dashboard = self._store.current_dashboard()
        self._dashboard_current = (
            saved_dashboard if saved_dashboard in self._dashboard_layouts
            else next(iter(self._dashboard_layouts))
        )
        self._dashboard_widgets = [
            dict(item)
            for item in self._dashboard_layouts[self._dashboard_current]["widgets"]
        ]
        self._dashboard_model = DashboardListModel(self)
        self._dashboard_message = ""
        self._event_sink = CallbackEventSink()
        self._event_sink.subscribe(self.serviceEvent.emit)
        self.serviceEvent.connect(self._apply_event)
        self._vehicle_service = VehicleService(self._event_sink, self._poll_interval)
        self._update_poll_scope()
        self._refresh_dashboard_model()
        self._log.info("pyOBD v3 started")

    @Property(str, notify=pageChanged)
    def page(self):
        return self._page

    @Property(str, notify=settingsSectionChanged)
    def settingsSection(self):
        return self._settings_section

    @Property("QVariantList", notify=stateChanged)
    def telemetry(self):
        return list(self._readings.values())

    @Property("QVariantList", notify=stateChanged)
    def overviewWidgets(self):
        widgets = []
        for widget in self._overview_widgets:
            item = dict(widget)
            item.setdefault("type", "pid")
            reading = self._readings.get(item.get("pid", ""), {})
            item.update({
                "value": reading.get("value", "---"),
                "unit": reading.get("unit", ""),
                "progress": reading.get("progress", 0.0),
                "available": bool(reading),
            })
            if item["type"] == "health":
                count = len(self._diagnostic_codes)
                item.update(value="No trouble codes" if count == 0 else "{} codes".format(count), unit="", available=self.connected)
            elif item["type"] == "readiness":
                supported = [row for row in self._readiness if row.get("supported")]
                ready = sum(row.get("status") == "Ready" for row in supported)
                item.update(value="{} / {} ready".format(ready, len(supported)), unit="", available=bool(self._readiness))
            elif item["type"] == "connection":
                item.update(value=self.connectionStatus, unit=self.protocol if self.connected else "", available=True)
            elif item["type"] == "vehicle":
                profile = next((row for row in self._profiles if row.get("profile_id") == self._active_profile_id), None)
                item.update(value=(profile or {}).get("nickname") or self.vin, unit="", available=self.vin != "----")
            elif item["type"] == "shortcut":
                item.update(value=item.get("destination", "Dashboard"), unit="", available=True)
            widgets.append(item)
        return widgets

    @Property("QVariantList", notify=stateChanged)
    def widgetCatalog(self):
        catalog = [dict(item, type="pid") for item in self._supported_pids]
        if not any(item.get("pid") == "ATRV" for item in catalog):
            catalog.append({"pid": "ATRV", "name": "Adapter Voltage", "type": "pid"})
        catalog.extend([
            {"pid": "@graph", "sourcePid": "010C", "name": "Engine RPM Graph", "type": "graph"},
            {"pid": "@health", "name": "Vehicle Health", "type": "health"},
            {"pid": "@readiness", "name": "Readiness Summary", "type": "readiness"},
            {"pid": "@connection", "name": "Connection Details", "type": "connection"},
            {"pid": "@vehicle", "name": "Vehicle Profile", "type": "vehicle"},
            {"pid": "@shortcut", "name": "Dashboard Shortcut", "type": "shortcut"},
        ])
        return catalog

    @Property("QVariantList", notify=stateChanged)
    def dashboardCatalog(self):
        catalog = [item for item in self.widgetCatalog if item.get("type") == "pid"]
        known = {item.get("pid") for item in catalog}
        for widget in self._dashboard_widgets:
            for pid in (widget.get("pid"), widget.get("center_pid")):
                if pid and pid not in known:
                    catalog.append({
                        "pid": pid,
                        "name": widget.get("title", pid) if pid == widget.get("pid") else pid,
                        "type": "pid",
                    })
                    known.add(pid)
        return catalog

    @Property("QVariantList", notify=stateChanged)
    def dashboardWidgets(self):
        return self._dashboard_rows()

    def _dashboard_rows(self):
        widgets = []
        for widget in self._dashboard_widgets:
            item = dict(widget)
            reading = self._readings.get(item.get("pid", ""), {})
            item.update({
                "value": reading.get("value", "---"),
                "unit": reading.get("unit", ""),
                "numericValue": self._numeric_value(reading.get("value")),
            })
            widgets.append(item)
        return widgets

    @Property(QObject, constant=True)
    def dashboardModel(self):
        return self._dashboard_model

    @Property(str, notify=stateChanged)
    def dashboardMessage(self):
        return self._dashboard_message

    @Property("QStringList", notify=dashboardChanged)
    def dashboardNames(self):
        return sorted(self._dashboard_layouts, key=str.casefold)

    @Property(str, notify=dashboardChanged)
    def currentDashboard(self):
        return self._dashboard_current

    @Property("QVariantList", notify=stateChanged)
    def liveData(self):
        return self._live_data

    @Property(QObject, constant=True)
    def liveDataModel(self):
        return self._live_data_model

    @Property("QVariantList", notify=diagnosticsChanged)
    def diagnosticCodes(self):
        return self._diagnostic_codes

    @Property("QVariantList", notify=diagnosticsChanged)
    def readinessResults(self):
        return self._readiness

    @Property("QVariantList", notify=diagnosticsChanged)
    def misfireResults(self):
        return self._misfire_results

    @Property("QVariantList", notify=diagnosticsChanged)
    def freezeFrameResults(self):
        return self._freeze_frame

    @Property("QVariantList", notify=profileChanged)
    def vehicleProfiles(self):
        return [dict(item, display_name=self._profile_name(item)) for item in self._profiles]

    @Property(str, notify=profileChanged)
    def activeVehicleProfileID(self):
        return self._active_profile_id

    @Property("QVariantMap", notify=profileChanged)
    def activeVehicleProfile(self):
        profile = next(
            (item for item in self._profiles if item.get("profile_id") == self._active_profile_id),
            {},
        )
        return dict(profile)

    @Property(str, notify=profileChanged)
    def vehicleProfileStatus(self):
        return self._vehicle_profile_status

    @Property(str, notify=profileChanged)
    def activeVehicleName(self):
        if self._connection.transport == "Demo" and self.connected:
            return "DEMO MODE"
        profile = next(
            (item for item in self._profiles if item.get("profile_id") == self._active_profile_id),
            None,
        )
        return self._profile_name(profile) if profile else ""

    @Property(bool, notify=stateChanged)
    def vehicleLayoutEnabled(self):
        return self._vehicle_layout_enabled

    @Property("QVariantList", notify=stateChanged)
    def bluetoothAdapters(self):
        selected = self._connection.adapter if self._connection.connected else ""
        return [dict(item, connected=item.get("target") == selected) for item in self._bluetooth_adapters]

    @Property("QVariantList", notify=stateChanged)
    def serialAdapters(self):
        selected = self._connection.adapter if self._connection.connected else ""
        return [dict(item, connected=item.get("target") == selected) for item in self._serial_adapters]

    @Property(int, notify=stateChanged)
    def selectedLiveCount(self):
        return len(self._live_selected)

    @Property(bool, notify=stateChanged)
    def recordingActive(self):
        return self._recording.active

    @Property(str, notify=stateChanged)
    def recordingStatus(self):
        return self._recording_status

    @Property("QVariantList", notify=sessionsChanged)
    def recordedSessions(self):
        return list(self._recorded_sessions)

    @Property(bool, notify=sessionsChanged)
    def replayActive(self):
        return self._replay_timer.isActive()

    @Property(str, notify=sessionsChanged)
    def replayStatus(self):
        return self._replay_status

    @Property(str, constant=True)
    def appVersion(self):
        return APP_VERSION

    @Property(str, notify=stateChanged)
    def updateStatus(self):
        return self._update_status

    @Property(str, constant=True)
    def logPath(self):
        return str(self._log.path)

    @Property("QStringList", notify=traceChanged)
    def traceLines(self):
        return list(self._trace_lines)

    @Property(str, constant=True)
    def recordingsPath(self):
        return str(self._recording.directory)

    @Property(float, notify=stateChanged)
    def pollInterval(self):
        return self._poll_interval

    @Property(str, notify=performanceChanged)
    def pollingStatus(self):
        requested = self._vehicle_service.requested_pids
        if requested is None:
            return "All supported PIDs"
        if not requested:
            return "Paused"
        return "{} PID{}".format(len(requested), "" if len(requested) == 1 else "s")

    @Property(str, notify=stateChanged)
    def workerStatus(self):
        return "Running" if self._vehicle_service.running else "Stopped"

    @Property(str, notify=stateChanged)
    def connectionStatus(self):
        return self._connection.status.value

    @Property(bool, notify=stateChanged)
    def connected(self):
        return self._connection.connected

    @Property(str, notify=stateChanged)
    def connectionError(self):
        return self._connection.error or self._operation_error

    @Property(str, notify=stateChanged)
    def connectionTransport(self):
        return self._connection.transport

    @Property(str, notify=stateChanged)
    def protocol(self):
        return self._connection.protocol

    @Property(str, notify=stateChanged)
    def adapter(self):
        return self._connection.adapter

    @Property(str, notify=stateChanged)
    def port(self):
        return self._connection.port

    @Property(str, notify=stateChanged)
    def voltage(self):
        return self._connection.voltage

    @Property(str, notify=stateChanged)
    def vin(self):
        return self._vehicle.vin

    @Slot(str)
    def select_page(self, page):
        if page == self._page:
            return
        self._page = page
        self._update_poll_scope()
        if page == "Live Data":
            self._rebuild_live_data()
        elif page == "Dashboard":
            self._refresh_dashboard_model()
        self.pageChanged.emit()

    @Slot(str)
    def open_settings(self, section):
        if section not in ("Connection", "General", "Trace", "About"):
            section = "General"
        if section != self._settings_section:
            self._settings_section = section
            self.settingsSectionChanged.emit()
        self.select_page("Settings")

    @Slot(str, str, str, str, str, str, str, str)
    def connect_vehicle(
        self, transport, address, port, baudrate, timeout, retries,
        send_mode, measurement_system,
    ):
        self._operation_error = ""
        if not self._vehicle_service.stop():
            self._operation_error = "Previous connection is still shutting down"
            self.stateChanged.emit()
            return
        self._vehicle_service = VehicleService(self._event_sink, self._poll_interval)
        self._update_poll_scope()
        try:
            timeout_value = max(0.5, float(timeout))
            retry_value = max(1, min(10, int(retries)))
        except (TypeError, ValueError):
            timeout_value, retry_value = 1.0, 5
        config = ConnectionConfig(
            transport=transport,
            address=address,
            port=port,
            baudrate=baudrate or "AUTO",
            timeout=timeout_value,
            retries=retry_value,
            send_mode=send_mode if send_mode in ("FAST", "NORMAL") else "NORMAL",
            measurement_system=(
                measurement_system
                if measurement_system in ("IMPERIAL", "METRIC") else "IMPERIAL"
            ),
        )
        self._store.save_connection({
            "transport": transport, "address": address,
            "port": port, "baudrate": baudrate or "AUTO",
            "timeout": timeout_value, "retries": retry_value,
            "send_mode": config.send_mode,
            "measurement_system": config.measurement_system,
        })
        self._vehicle_service.start(config)

    @Slot()
    def disconnect_vehicle(self):
        if not self._vehicle_service.stop():
            self._operation_error = "Connection is still shutting down"
            self.stateChanged.emit()

    @Slot()
    def quick_connect(self):
        if self.connected:
            self.disconnect_vehicle()
            return
        if self.connectionStatus in ("Connecting", "Reconnecting"):
            return
        saved = self.saved_connection()
        self.connect_vehicle(
            saved["transport"], saved["address"], saved["port"],
            saved["baudrate"], saved["timeout"], saved["retries"],
            saved["send_mode"], saved["measurement_system"],
        )

    @Slot(str, str, str, str, str, str, str, str)
    def save_connection_settings(
        self, transport, address, port, baudrate, timeout, retries,
        send_mode, measurement_system,
    ):
        try:
            timeout_value = max(0.5, float(timeout))
            retry_value = max(1, min(10, int(retries)))
        except (TypeError, ValueError):
            timeout_value, retry_value = 1.0, 5
        self._store.save_connection({
            "transport": transport,
            "address": address,
            "port": port,
            "baudrate": baudrate or "AUTO",
            "timeout": timeout_value,
            "retries": retry_value,
            "send_mode": send_mode if send_mode in ("FAST", "NORMAL") else "NORMAL",
            "measurement_system": (
                measurement_system
                if measurement_system in ("IMPERIAL", "METRIC") else "IMPERIAL"
            ),
        })

    @Slot(result="QVariantMap")
    def saved_connection(self):
        values = self._store.connection()
        return {
            "transport": values.get("transport", "Auto detect"),
            "address": values.get("address", "192.168.0.10"),
            "port": values.get("port", "35000"),
            "baudrate": values.get("baudrate", "AUTO"),
            "timeout": str(values.get("timeout", 1.0)),
            "retries": str(values.get("retries", 5)),
            "send_mode": values.get("send_mode", "NORMAL"),
            "measurement_system": values.get("measurement_system", "IMPERIAL"),
        }

    @Slot()
    def refresh_bluetooth_adapters(self):
        self._bluetooth_adapters = bluetooth_adapters()
        self._serial_adapters = serial_adapters()
        self.stateChanged.emit()

    @Slot()
    def refresh_serial_adapters(self):
        self._serial_adapters = serial_adapters()
        self.stateChanged.emit()

    @Slot(str, bool)
    def set_live_filter(self, query, favorites_only):
        self._live_search = query.strip().lower()
        self._favorites_only = favorites_only
        self._rebuild_live_data()
        self.stateChanged.emit()

    @Slot(str)
    def toggle_favorite(self, pid):
        if pid in self._favorites:
            self._favorites.remove(pid)
        else:
            self._favorites.add(pid)
        self._store.save_favorites(self._favorites)
        self._rebuild_live_data()
        self.stateChanged.emit()

    @Slot(str)
    def toggle_live_selection(self, pid):
        if pid in self._live_selected:
            self._live_selected.remove(pid)
        else:
            self._live_selected.add(pid)
        self._rebuild_live_data()
        self.stateChanged.emit()

    @Slot()
    def clear_live_selection(self):
        self._live_selected.clear()
        self._rebuild_live_data()
        self.stateChanged.emit()

    @Slot(str)
    def start_recording(self, name):
        if not self._live_selected:
            self._recording_status = "Select at least one PID"
            self.stateChanged.emit()
            return
        try:
            path = self._recording.start(
                name.strip() or "Live Data",
                self._live_selected,
                self.vin if self.vin != "----" else "Unassigned",
            )
            self._recording_status = "Recording to " + path.name
            self._log.info(self._recording_status)
            self._update_poll_scope()
        except OSError as error:
            self._recording_status = str(error)
            self._log.error(error)
        self.stateChanged.emit()

    @Slot()
    def stop_recording(self):
        try:
            result = self._recording.stop()
            if result:
                self._recording_status = "Saved {} samples".format(result["samples"])
                self._log.info(self._recording_status)
                self.refresh_sessions()
            self._update_poll_scope()
        except OSError as error:
            self._recording_status = str(error)
            self._log.error(error)
        self.stateChanged.emit()

    @Slot()
    def refresh_sessions(self):
        self._recorded_sessions = self._recording.sessions()
        self.sessionsChanged.emit()

    @Slot(str, str)
    def rename_session(self, csv_path, name):
        name = name.strip()
        if not name:
            return
        try:
            self._recording.rename_session(csv_path, name)
            self._replay_status = "Session renamed"
        except OSError as error:
            self._replay_status = str(error)
        self.refresh_sessions()

    @Slot(str)
    def delete_session(self, csv_path):
        if self._replay_timer.isActive():
            self.stop_session_replay()
        self._recording.delete_session(csv_path)
        self._replay_status = "Session deleted"
        self.refresh_sessions()

    @Slot(str, str)
    def export_session(self, csv_path, url):
        destination = self._local_path(url)
        if destination is None:
            return
        try:
            self._recording.export_session(csv_path, destination)
            self._replay_status = "Session exported"
        except OSError as error:
            self._replay_status = str(error)
        self.sessionsChanged.emit()

    @Slot(str)
    def start_session_replay(self, csv_path):
        if self.connected:
            self._replay_status = "Disconnect from the vehicle before replaying a session"
            self.sessionsChanged.emit()
            return
        rows = []
        try:
            with Path(csv_path).open("r", newline="", encoding="utf-8") as replay_file:
                for row in csv.DictReader(replay_file):
                    try:
                        elapsed = float(row.get("Elapsed Seconds", ""))
                    except (TypeError, ValueError):
                        continue
                    pid_match = re.search(r"[0-9A-F]{4,8}|ATRV", row.get("PID", "").upper())
                    value_text = row.get("Value", "").strip()
                    value_match = re.search(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)", value_text)
                    if not pid_match or not value_match:
                        continue
                    rows.append({
                        "elapsed": max(0.0, elapsed),
                        "pid": pid_match.group(),
                        "sensor": row.get("Sensor", "").strip() or pid_match.group(),
                        "value": value_match.group(),
                        "number": float(value_match.group()),
                        "unit": value_text[value_match.end():].strip(),
                    })
        except OSError as error:
            self._replay_status = str(error)
            self.sessionsChanged.emit()
            return
        if not rows:
            self._replay_status = "This session has no replayable PID data"
            self.sessionsChanged.emit()
            return
        rows.sort(key=lambda item: item["elapsed"])
        first = rows[0]["elapsed"]
        for row in rows:
            row["elapsed"] -= first
        self._replay_rows = rows
        self._replay_index = 0
        self._replay_started = time.monotonic()
        self._readings = {}
        self._history.clear()
        pids = list(dict.fromkeys(row["pid"] for row in rows))
        names = {row["pid"]: row["sensor"] for row in rows}
        self._supported_pids = [
            {"pid": pid, "name": names[pid]} for pid in pids
        ]
        self._graph_pids = pids
        self._store.save_graph_pids(pids)
        self.graphSelectionChanged.emit()
        self._replay_status = "Replaying session"
        self._replay_timer.start()
        self.select_page("Graphs")
        self.sessionsChanged.emit()
        self.stateChanged.emit()

    @Slot()
    def stop_session_replay(self):
        self._replay_timer.stop()
        self._replay_status = "Replay stopped"
        self.sessionsChanged.emit()

    @Slot()
    def _advance_session_replay(self):
        if not self._replay_rows or self._replay_started is None:
            self.stop_session_replay()
            return
        elapsed = time.monotonic() - self._replay_started
        while self._replay_index < len(self._replay_rows):
            row = self._replay_rows[self._replay_index]
            if row["elapsed"] > elapsed:
                break
            self._replay_index += 1
            self._readings[row["pid"]] = {
                "pid": row["pid"], "label": row["sensor"],
                "value": row["value"], "unit": row["unit"],
                "progress": 0.0,
            }
            self._history[row["pid"]].append(row["number"])
        self._rebuild_live_data()
        self._refresh_dashboard_model()
        self.graphChanged.emit()
        self.stateChanged.emit()
        if self._replay_index >= len(self._replay_rows):
            self._replay_timer.stop()
            self._replay_status = "Replay complete"
            self.sessionsChanged.emit()

    @Slot(str)
    def save_poll_interval(self, milliseconds):
        try:
            interval = max(30, min(1000, int(milliseconds))) / 1000.0
        except (TypeError, ValueError):
            return
        self._poll_interval = interval
        self._preferences["poll_interval"] = interval
        self._store.save_preferences(self._preferences)
        self.stateChanged.emit()

    @Slot(str)
    def open_url(self, url):
        if url:
            QDesktopServices.openUrl(QUrl(url))

    @Slot()
    def refresh_trace(self):
        self._trace_lines = self._log.tail()
        self.traceChanged.emit()

    @Slot(str)
    def open_app_link(self, name):
        if name == "recordings":
            self._recording.directory.mkdir(parents=True, exist_ok=True)
        urls = {
            "project": PROJECT_URL, "releases": RELEASES_URL,
            "issues": ISSUES_URL, "support": SUPPORT_URL,
            "license": LICENSE_URL, "logs": self._log.path.parent.as_uri(),
            "recordings": self._recording.directory.as_uri(),
            "adapter": ADAPTER_URL,
        }
        self.open_url(str(urls.get(name, "")))

    @Slot()
    def check_for_updates(self):
        if self._update_status == "Checking for updates…":
            return
        self._update_status = "Checking for updates…"
        self.stateChanged.emit()

        def check():
            try:
                request = urllib.request.Request(
                    RELEASE_API_URL,
                    headers={"Accept": "application/vnd.github+json", "User-Agent": "pyOBD"},
                )
                with urllib.request.urlopen(request, timeout=8) as response:
                    release = json.loads(response.read().decode("utf-8"))
                latest = release.get("tag_name", "")
                url = release.get("html_url", RELEASES_URL)
                payload = (latest, url, "")
            except (OSError, ValueError, urllib.error.URLError) as error:
                payload = ("", RELEASES_URL, str(error))
            self._event_sink.publish(AppEvent(EventChannel.UPDATE_STATUS, payload))

        threading.Thread(target=check, name="pyOBD-v3-update", daemon=True).start()

    @Slot(str)
    def add_overview_widget(self, selection):
        catalog_item = next(
            (item for item in self.widgetCatalog if item.get("pid") == selection),
            None,
        )
        if catalog_item is None:
            return
        widget_type = catalog_item.get("type", "pid")
        pid = catalog_item.get("sourcePid", selection if widget_type == "pid" else "")
        if any(
            widget.get("type", "pid") == widget_type and widget.get("pid", "") == pid
            for widget in self._overview_widgets
        ):
            return
        widget = {
            "id": uuid4().hex,
            "type": widget_type,
            "pid": pid,
            "title": catalog_item.get("name", selection),
            "size": "wide" if widget_type == "graph" else "small",
        }
        if widget_type == "shortcut":
            widget["destination"] = "Dashboard"
        self._overview_widgets.append(widget)
        self._save_overview()

    @Slot(str, result="QVariantList")
    def graph_points(self, pid):
        return list(self._history.get(pid, ()))

    @Property("QStringList", notify=graphSelectionChanged)
    def graphPids(self):
        return list(self._graph_pids)

    @Property("QStringList", notify=graphSelectionChanged)
    def graphPresetNames(self):
        return sorted(self._graph_presets, key=str.casefold)

    @Property(str, notify=graphSelectionChanged)
    def currentGraphPreset(self):
        return self._current_graph_preset

    @Slot(str)
    def add_graph_pid(self, pid):
        if pid and pid not in self._graph_pids:
            self._graph_pids.append(pid)
            self._current_graph_preset = ""
            self._store.save_graph_pids(self._graph_pids)
            self._update_poll_scope()
            self.graphSelectionChanged.emit()

    @Slot(int)
    def remove_graph_pid(self, index):
        if 0 <= index < len(self._graph_pids):
            self._graph_pids.pop(index)
            self._current_graph_preset = ""
            self._store.save_graph_pids(self._graph_pids)
            self._update_poll_scope()
            self.graphSelectionChanged.emit()

    @Slot(str)
    def select_graph_preset(self, name):
        if name not in self._graph_presets:
            return
        self._current_graph_preset = name
        self._graph_pids = list(dict.fromkeys(self._graph_presets[name]))
        self._store.save_graph_pids(self._graph_pids)
        self._update_poll_scope()
        self.graphSelectionChanged.emit()

    @Slot(str)
    def save_graph_preset(self, name):
        name = name.strip()
        if not name or not self._graph_pids:
            return
        self._graph_presets[name] = list(self._graph_pids)
        self._current_graph_preset = name
        self._store.save_graph_presets(self._graph_presets)
        self.graphSelectionChanged.emit()

    @Slot(str)
    def rename_graph_preset(self, name):
        name = name.strip()
        old_name = self._current_graph_preset
        if not old_name or not name or (name != old_name and name in self._graph_presets):
            return
        self._graph_presets[name] = self._graph_presets.pop(old_name)
        self._current_graph_preset = name
        self._store.save_graph_presets(self._graph_presets)
        self.graphSelectionChanged.emit()

    @Slot()
    def delete_graph_preset(self):
        if self._current_graph_preset not in self._graph_presets:
            return
        del self._graph_presets[self._current_graph_preset]
        self._current_graph_preset = ""
        self._store.save_graph_presets(self._graph_presets)
        self.graphSelectionChanged.emit()

    @Slot()
    def add_selected_to_graphs(self):
        changed = False
        for pid in sorted(self._live_selected):
            if pid not in self._graph_pids:
                self._graph_pids.append(pid)
                changed = True
        if changed:
            self._current_graph_preset = ""
            self._store.save_graph_pids(self._graph_pids)
            self._update_poll_scope()
            self.graphSelectionChanged.emit()
        self.select_page("Graphs")

    @Slot(str, result="QVariantMap")
    def reading_for_pid(self, pid):
        return dict(self._readings.get(pid, {
            "pid": pid, "label": pid, "value": "---", "unit": "",
        }))

    @Slot(str)
    def open_shortcut(self, destination):
        self.select_page(destination)

    @Slot(int)
    def remove_overview_widget(self, index):
        if 0 <= index < len(self._overview_widgets):
            self._overview_widgets.pop(index)
            self._save_overview()

    @Slot(int, int)
    def move_overview_widget(self, index, direction):
        target = index + direction
        if 0 <= index < len(self._overview_widgets) and 0 <= target < len(self._overview_widgets):
            self._overview_widgets[index], self._overview_widgets[target] = (
                self._overview_widgets[target], self._overview_widgets[index]
            )
            self._save_overview()

    @Slot(int)
    def toggle_overview_widget_size(self, index):
        if 0 <= index < len(self._overview_widgets):
            widget = self._overview_widgets[index]
            widget["size"] = "wide" if widget.get("size") == "small" else "small"
            self._save_overview()

    @Slot()
    def restore_overview(self):
        self._overview_widgets = [dict(widget) for widget in DEFAULT_WIDGETS]
        self._save_overview()

    @Slot(str)
    def add_dashboard_widget(self, pid):
        catalog_item = next(
            (item for item in self.dashboardCatalog if item.get("pid") == pid),
            None,
        )
        if catalog_item is None:
            return
        offset = 30.0 + (len(self._dashboard_widgets) % 6) * 36.0
        highest = max([item.get("z", 0) for item in self._dashboard_widgets] or [0])
        self._dashboard_widgets.append({
            "id": uuid4().hex,
            "pid": pid,
            "center_pid": "",
            "title": catalog_item.get("name", pid),
            "style": "combined",
            "shape": "rounded",
            "colour": "blue",
            "minimum": 0.0,
            "maximum": self._default_dashboard_maximum(pid),
            "divisions": 10,
            "x": offset,
            "y": offset,
            "width": 320.0,
            "height": 280.0,
            "z": highest + 1,
        })
        self._save_dashboard()

    @Slot(str)
    def remove_dashboard_widget(self, widget_id):
        self._dashboard_widgets = [
            item for item in self._dashboard_widgets if item.get("id") != widget_id
        ]
        self._save_dashboard()

    @Slot()
    def clear_dashboard(self):
        self._dashboard_widgets = []
        self._save_dashboard()

    @Slot(str, float, float)
    def move_dashboard_widget(self, widget_id, x, y):
        widget = self._dashboard_widget(widget_id)
        if widget is None:
            return
        widget["x"] = max(0.0, x)
        widget["y"] = max(0.0, y)
        self._save_dashboard()

    @Slot(str, float, float)
    def resize_dashboard_widget(self, widget_id, width, height):
        widget = self._dashboard_widget(widget_id)
        if widget is None:
            return
        is_dial = widget.get("style") in ("dial", "combined")
        width = max(240.0 if is_dial else 120.0, width)
        height = max(240.0 if is_dial else 100.0, height)
        if widget.get("shape") == "circle":
            width = height = max(width, height)
        widget["width"] = width
        widget["height"] = height
        self._save_dashboard()

    @Slot(str, float, float, float, float)
    def set_dashboard_geometry(self, widget_id, x, y, width, height):
        widget = self._dashboard_widget(widget_id)
        if widget is None:
            return
        is_dial = widget.get("style") in ("dial", "combined")
        width = max(240.0 if is_dial else 120.0, width)
        height = max(240.0 if is_dial else 100.0, height)
        if widget.get("shape") == "circle":
            width = height = max(width, height)
        widget.update({
            "x": max(0.0, x), "y": max(0.0, y),
            "width": width, "height": height,
        })
        self._save_dashboard()

    @Slot(str, str, str, str, str, str, str, str, str, int)
    def update_dashboard_properties(
        self, widget_id, pid, center_pid, title, style, shape, colour,
        minimum, maximum, divisions,
    ):
        widget = self._dashboard_widget(widget_id)
        if widget is None or style not in ("digital", "dial", "combined"):
            return
        if shape not in ("rounded", "circle", "rectangle"):
            return
        if colour not in ("blue", "green", "orange", "red", "purple", "cyan"):
            return
        try:
            lower = float(minimum)
            upper = float(maximum)
        except (TypeError, ValueError):
            return
        if upper <= lower:
            return
        widget.update({
            "pid": pid,
            "center_pid": center_pid if style == "combined" else "",
            "title": title.strip() or pid,
            "style": style,
            "shape": shape,
            "colour": colour,
            "minimum": lower,
            "maximum": upper,
            "divisions": max(2, min(20, divisions)),
        })
        if style in ("dial", "combined"):
            widget["width"] = max(240.0, widget["width"])
            widget["height"] = max(240.0, widget["height"])
        if shape == "circle":
            widget["width"] = widget["height"] = max(widget["width"], widget["height"])
        self._save_dashboard()

    @Slot(str, str)
    def set_dashboard_style(self, widget_id, style):
        if style not in ("digital", "dial", "combined"):
            return
        widget = self._dashboard_widget(widget_id)
        if widget is not None:
            widget["style"] = style
            self._save_dashboard()

    @Slot(str, str, str)
    def set_dashboard_range(self, widget_id, minimum, maximum):
        widget = self._dashboard_widget(widget_id)
        if widget is None:
            return
        try:
            lower = float(minimum)
            upper = float(maximum)
        except (TypeError, ValueError):
            return
        if upper <= lower:
            return
        widget["minimum"] = lower
        widget["maximum"] = upper
        self._save_dashboard()

    @Slot(str, int)
    def change_dashboard_layer(self, widget_id, direction):
        widget = self._dashboard_widget(widget_id)
        if widget is None:
            return
        widget["z"] = max(0, int(widget.get("z", 0)) + direction)
        self._save_dashboard()

    @Slot(str, bool)
    def set_dashboard_layer_edge(self, widget_id, front):
        widget = self._dashboard_widget(widget_id)
        if widget is None:
            return
        if front:
            widget["z"] = max(
                [int(item.get("z", 0)) for item in self._dashboard_widgets] or [0]
            ) + 1
        else:
            widget["z"] = 0
            for item in self._dashboard_widgets:
                if item is not widget:
                    item["z"] = max(1, int(item.get("z", 0)))
        self._save_dashboard()

    @Slot()
    def restore_dashboard(self):
        self._dashboard_widgets = [dict(widget) for widget in DEFAULT_DASHBOARD_WIDGETS]
        self._save_dashboard()

    @Slot(str)
    def select_dashboard(self, name):
        if name not in self._dashboard_layouts or name == self._dashboard_current:
            return
        self._dashboard_current = name
        self._dashboard_widgets = [
            dict(item) for item in self._dashboard_layouts[name]["widgets"]
        ]
        self._store.save_dashboard_layouts(
            self._dashboard_layouts, self._dashboard_current
        )
        self._refresh_dashboard_model()
        self._update_poll_scope()
        self.dashboardChanged.emit()
        self.stateChanged.emit()

    @Slot(str)
    def create_dashboard(self, name):
        name = name.strip()
        if not name or name in self._dashboard_layouts:
            self._dashboard_message = "Dashboard name already exists"
            self.stateChanged.emit()
            return
        self._dashboard_layouts[name] = {"widgets": []}
        self._dashboard_current = name
        self._dashboard_widgets = []
        self._save_dashboard()

    @Slot(str)
    def rename_dashboard(self, name):
        name = name.strip()
        old_name = self._dashboard_current
        if not name or (name != old_name and name in self._dashboard_layouts):
            self._dashboard_message = "Dashboard name already exists"
            self.stateChanged.emit()
            return
        if name == old_name:
            return
        self._dashboard_layouts[name] = self._dashboard_layouts.pop(old_name)
        self._dashboard_current = name
        for profile in self._profiles:
            if profile.get("default_dashboard") == old_name:
                profile["default_dashboard"] = name
        self._store.save_profiles(self._profiles)
        self._save_dashboard()

    @Slot()
    def delete_dashboard(self):
        if len(self._dashboard_layouts) <= 1:
            self._dashboard_message = "At least one dashboard is required"
            self.stateChanged.emit()
            return
        removed = self._dashboard_current
        del self._dashboard_layouts[removed]
        self._dashboard_current = next(iter(self._dashboard_layouts))
        self._dashboard_widgets = [
            dict(item)
            for item in self._dashboard_layouts[self._dashboard_current]["widgets"]
        ]
        for profile in self._profiles:
            if profile.get("default_dashboard") == removed:
                profile["default_dashboard"] = ""
        self._store.save_profiles(self._profiles)
        self._save_dashboard()

    @Slot(str)
    def export_dashboard(self, url):
        path = self._local_path(url)
        if path is None:
            return
        if path.suffix.lower() != ".pyobd":
            path = path.with_suffix(".pyOBD")
        try:
            path.write_text(json.dumps({
                "format": "pyobd-dashboard-layouts",
                "version": 1,
                "current": self._dashboard_current,
                "layouts": {
                    self._dashboard_current: {
                        "widgets": self._dashboard_widgets
                    }
                },
            }, indent=2), encoding="utf-8")
            self._dashboard_message = "Dashboard exported"
        except OSError as error:
            self._dashboard_message = str(error)
        self.stateChanged.emit()

    @Slot(str)
    def import_dashboard(self, url):
        path = self._local_path(url)
        if path is None:
            return
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("Invalid dashboard layout")
            layouts = payload.get("layouts")
            if isinstance(layouts, dict):
                imported = {}
                for name, layout in layouts.items():
                    if not isinstance(layout, dict) or not isinstance(layout.get("widgets"), list):
                        continue
                    imported[str(name)] = {"widgets": [
                        self._normalized_dashboard_widget(item)
                        for item in layout["widgets"]
                    ]}
                if not imported:
                    raise ValueError("Invalid dashboard layout")
                for name, layout in imported.items():
                    unique_name = name
                    suffix = 2
                    while unique_name in self._dashboard_layouts:
                        unique_name = "{} ({})".format(name, suffix)
                        suffix += 1
                    self._dashboard_layouts[unique_name] = layout
                    self._dashboard_current = unique_name
                self._dashboard_widgets = [
                    dict(item)
                    for item in self._dashboard_layouts[self._dashboard_current]["widgets"]
                ]
            else:
                widgets = payload.get("widgets")
                if not isinstance(widgets, list):
                    raise ValueError("Invalid dashboard layout")
                self._dashboard_widgets = [
                    self._normalized_dashboard_widget(item) for item in widgets
                ]
            self._dashboard_message = "Dashboard imported"
            self._save_dashboard()
        except (OSError, ValueError, TypeError) as error:
            self._dashboard_message = str(error)
            self.stateChanged.emit()

    @Slot(bool)
    def set_vehicle_layout_enabled(self, enabled):
        vin = self._vehicle.vin
        if not vin or vin == "----":
            return
        self._vehicle_layout_enabled = enabled
        self._store.set_vehicle_layout_enabled(vin, enabled)
        self._overview_widgets = self._store.overview_widgets(vin, enabled)
        self._update_poll_scope()
        self.stateChanged.emit()

    @Slot()
    def refresh_diagnostics(self):
        self._vehicle_service.request_diagnostics()

    @Slot(str, result="QVariantList")
    def lookup_diagnostic_codes(self, query):
        query = query.strip().casefold()
        return [
            {"code": code, "description": description}
            for code, description in sorted(pcodes.items())
            if not query or query in code.casefold() or query in description.casefold()
        ]

    @Slot()
    def clear_diagnostics(self):
        self._vehicle_service.clear_diagnostics()

    @Slot()
    def refresh_readiness(self):
        self._vehicle_service.request_readiness()

    @Slot()
    def refresh_misfire(self):
        self._vehicle_service.request_misfire()

    @Slot()
    def refresh_freeze_frame(self):
        self._vehicle_service.request_freeze_frame()

    @Slot(str, str, str)
    def add_vehicle_profile(self, nickname, vin, default_dashboard):
        nickname = nickname.strip()
        vin = vin.strip().upper()
        if not nickname:
            return
        profile = {
            "profile_id": uuid4().hex,
            "nickname": nickname,
            "vin": vin,
            "year": "",
            "make": "",
            "model": "",
            "notes": "",
            "default_dashboard": default_dashboard or "Overview",
        }
        self._profiles.append(profile)
        self._profiles.sort(key=lambda item: item["nickname"].lower())
        self._active_profile_id = profile["profile_id"]
        self._store.save_profiles(self._profiles)
        self._vehicle_profile_status = "Vehicle profile added"
        self.profileChanged.emit()
        self.stateChanged.emit()

    @Slot()
    def create_vehicle_profile(self):
        profile = {
            "profile_id": uuid4().hex,
            "vin": "" if self.vin == "----" else self.vin,
            "nickname": "",
            "year": "",
            "make": "",
            "model": "",
            "notes": "",
            "default_dashboard": "",
        }
        self._profiles.append(profile)
        self._active_profile_id = profile["profile_id"]
        self._store.save_profiles(self._profiles)
        self._vehicle_profile_status = "New profile"
        self.profileChanged.emit()
        self.stateChanged.emit()

    @Slot(str, str, str, str, str, str, str, str)
    def save_vehicle_profile(
        self, profile_id, vin, nickname, year, make, model, notes,
        default_dashboard,
    ):
        profile = next(
            (item for item in self._profiles if item.get("profile_id") == profile_id),
            None,
        )
        if profile is None:
            return
        vin = re.sub(r"[^A-Za-z0-9]", "", vin).upper()[:17]
        year = year.strip()
        if year and (not year.isdigit() or len(year) != 4):
            self._vehicle_profile_status = "Enter a four-digit year or leave it blank"
            self.stateChanged.emit()
            return
        profile.update({
            "vin": vin,
            "nickname": nickname.strip(),
            "year": year,
            "make": make.strip(),
            "model": model.strip(),
            "notes": notes.strip(),
            "default_dashboard": (
                default_dashboard if default_dashboard in self._dashboard_layouts else ""
            ),
        })
        self._profiles.sort(key=lambda item: self._profile_name(item).casefold())
        self._store.save_profiles(self._profiles)
        self._vehicle_profile_status = "Vehicle profile saved"
        self._apply_profile_dashboard(profile)
        self.profileChanged.emit()
        self.stateChanged.emit()

    @Slot(str)
    def delete_vehicle_profile(self, profile_id):
        self._profiles = [
            profile for profile in self._profiles
            if profile.get("profile_id") != profile_id
        ]
        if self._active_profile_id == profile_id:
            self._active_profile_id = ""
        self._store.save_profiles(self._profiles)
        self._vehicle_profile_status = "Vehicle profile deleted"
        self.profileChanged.emit()
        self.stateChanged.emit()

    @Slot(str)
    def select_vehicle_profile(self, profile_id):
        profile = next(
            (item for item in self._profiles if item.get("profile_id") == profile_id),
            None,
        )
        if profile is None:
            return
        self._active_profile_id = profile_id
        self._apply_profile_dashboard(profile)
        self.profileChanged.emit()
        self.stateChanged.emit()

    @Slot(object)
    def _apply_event(self, event: AppEvent):
        emit_state = True
        if event.channel == EventChannel.CONNECTION_STATE:
            self._connection = event.payload
            self._log.info(
                "Connection {}{}".format(
                    self._connection.status.value,
                    (": " + self._connection.error) if self._connection.error else "",
                )
            )
            if not self._connection.connected:
                self._operation_error = ""
                self._readings = {}
                self._history.clear()
                self._refresh_dashboard_model()
                self.graphChanged.emit()
                self._supported_pids = []
                self._live_data = []
                self._live_data_model.update_rows([])
                self._diagnostic_codes = []
                self._readiness = []
                self._misfire_results = []
                self._freeze_frame = []
                self.diagnosticsChanged.emit()
                self._vehicle = VehicleState()
                self._active_profile_id = ""
                self._vehicle_layout_enabled = False
                self._overview_widgets = self._store.overview_widgets()
                if self._connection.status.value == "Disconnected":
                    self.stop_recording()
                    self._live_selected.clear()
                self.profileChanged.emit()
        elif event.channel == EventChannel.VEHICLE_STATE:
            self._vehicle = event.payload
            self._activate_matching_profile()
            self._vehicle_layout_enabled = self._store.vehicle_layout_enabled(self._vehicle.vin)
            self._overview_widgets = self._store.overview_widgets(
                self._vehicle.vin, self._vehicle_layout_enabled
            )
            self._update_poll_scope()
            self.profileChanged.emit()
        elif event.channel == EventChannel.TELEMETRY:
            self._readings.update({
                reading.pid: reading.as_mapping() for reading in event.payload
            })
            try:
                self._recording.write(event.payload)
                if self._recording.active:
                    self._recording_status = "Recording · {} samples".format(
                        self._recording.samples
                    )
            except OSError as error:
                self._recording_status = str(error)
                self._recording.stop()
                self._update_poll_scope()
            for reading in event.payload:
                numeric = self._numeric_value(reading.value)
                if numeric is not None:
                    self._history[reading.pid].append(numeric)
            if self._page == "Live Data":
                self._rebuild_live_data()
            elif self._page == "Dashboard":
                self._refresh_dashboard_model()
            if self._page in ("Graphs", "Overview"):
                self.graphChanged.emit()
            emit_state = self._page == "Overview" or (
                self._page == "Live Data" and self._recording.active
            )
        elif event.channel == EventChannel.SUPPORTED_PIDS:
            self._supported_pids = [item.as_mapping() for item in event.payload]
            self._live_selected.intersection_update(
                item.get("pid", "") for item in self._supported_pids
            )
            if self._page == "Live Data":
                self._rebuild_live_data()
        elif event.channel == EventChannel.DIAGNOSTIC_CODES:
            self._diagnostic_codes = [item.as_mapping() for item in event.payload]
            self.diagnosticsChanged.emit()
        elif event.channel == EventChannel.READINESS:
            self._readiness = [item.as_mapping() for item in event.payload]
            self.diagnosticsChanged.emit()
        elif event.channel == EventChannel.MISFIRE:
            self._misfire_results = [item.as_mapping() for item in event.payload]
            self.diagnosticsChanged.emit()
        elif event.channel == EventChannel.FREEZE_FRAME:
            self._freeze_frame = [item.as_mapping() for item in event.payload]
            self.diagnosticsChanged.emit()
        elif event.channel == EventChannel.OPERATION_ERROR:
            self._operation_error = str(event.payload)
            self._log.error(event.payload)
        elif event.channel == EventChannel.DEBUG:
            payload = event.payload
            message = payload[-1] if isinstance(payload, (list, tuple)) else payload
            self._log.info(message)
            self._trace_lines.append(str(message))
            self._trace_lines = self._trace_lines[-500:]
            self.traceChanged.emit()
        elif event.channel == EventChannel.UPDATE_STATUS:
            latest, self._update_url, error = event.payload
            if error:
                self._update_status = "Update check failed: " + error
            elif not latest:
                self._update_status = "No published release found"
            elif self._version_numbers(latest) > self._version_numbers(APP_VERSION):
                self._update_status = "pyOBD {} is available".format(latest)
            else:
                self._update_status = "pyOBD {} is up to date".format(APP_VERSION)
        else:
            return
        if emit_state:
            self.stateChanged.emit()

    def _update_poll_scope(self):
        service = getattr(self, "_vehicle_service", None)
        if service is None:
            return
        if self._page == "Live Data":
            pids = None
        elif self._page == "Dashboard":
            pids = {
                pid
                for widget in self._dashboard_widgets
                for pid in (widget.get("pid"), widget.get("center_pid"))
                if pid
            }
        elif self._page == "Graphs":
            pids = set(self._graph_pids)
        elif self._page == "Overview":
            pids = {
                widget.get("pid")
                for widget in self._overview_widgets
                if widget.get("type", "pid") in ("pid", "graph")
                and widget.get("pid")
            }
        else:
            pids = set()
        if self._recording.active and pids is not None:
            pids.update(self._recording.selected_pids)
        service.set_poll_pids(pids)
        self.performanceChanged.emit()

    def _rebuild_live_data(self):
        rows = []
        for pid in self._supported_pids:
            number = pid.get("pid", "")
            name = pid.get("name", number)
            if self._live_search and self._live_search not in (name + " " + number).lower():
                continue
            favorite = number in self._favorites
            if self._favorites_only and not favorite:
                continue
            reading = self._readings.get(number, {})
            rows.append({
                "pid": number, "name": name,
                "value": reading.get("value", "---"),
                "unit": reading.get("unit", ""),
                "favorite": favorite,
                "selected": number in self._live_selected,
            })
        rows.sort(key=lambda item: (not item["favorite"], item["pid"]))
        self._live_data = rows
        self._live_data_model.update_rows(rows)

    def _save_overview(self):
        self._store.save_overview_widgets(
            self._overview_widgets,
            self._vehicle.vin,
            self._vehicle_layout_enabled,
        )
        self._update_poll_scope()
        self.stateChanged.emit()

    def _activate_matching_profile(self):
        vin = self._vehicle.vin.strip().upper()
        profile = next(
            (item for item in self._profiles if item.get("vin", "").upper() == vin),
            None,
        )
        if profile is None:
            return
        self._active_profile_id = profile.get("profile_id", "")
        self._vehicle_profile_status = "Selected automatically from the connected VIN"
        self._apply_profile_dashboard(profile)

    def _apply_profile_dashboard(self, profile):
        dashboard = str(profile.get("default_dashboard", ""))
        if dashboard in self._dashboard_layouts:
            self.select_dashboard(dashboard)
            if self._page != "Dashboard":
                self._page = "Dashboard"
                self._update_poll_scope()
                self.pageChanged.emit()

    @staticmethod
    def _profile_name(profile):
        nickname = str(profile.get("nickname", "")).strip()
        if nickname:
            return nickname
        description = " ".join(
            str(profile.get(field, "")).strip()
            for field in ("year", "make", "model")
        ).strip()
        return description or str(profile.get("vin", "")).strip() or "Untitled vehicle"

    def _dashboard_widget(self, widget_id):
        return next(
            (item for item in self._dashboard_widgets if item.get("id") == widget_id),
            None,
        )

    def _save_dashboard(self):
        self._dashboard_layouts[self._dashboard_current] = {
            "widgets": [dict(item) for item in self._dashboard_widgets]
        }
        self._store.save_dashboard_layouts(
            self._dashboard_layouts, self._dashboard_current
        )
        self._refresh_dashboard_model()
        self._update_poll_scope()
        self.dashboardChanged.emit()
        self.stateChanged.emit()

    def _refresh_dashboard_model(self):
        rows = []
        for item in self._dashboard_rows():
            rows.append({
                "widgetId": item.get("id", ""),
                "pid": item.get("pid", ""),
                "centerPid": item.get("center_pid", ""),
                "title": item.get("title", ""),
                "style": item.get("style", "combined"),
                "shape": item.get("shape", "rounded"),
                "colour": item.get("colour", "blue"),
                "minimum": item.get("minimum", 0.0),
                "maximum": item.get("maximum", 100.0),
                "divisions": item.get("divisions", 10),
                "xPosition": item.get("x", 0.0),
                "yPosition": item.get("y", 0.0),
                "widgetWidth": item.get("width", 320.0),
                "widgetHeight": item.get("height", 260.0),
                "layerValue": item.get("z", 0),
                "readingValue": item.get("value", "---"),
                "centerReadingValue": self._readings.get(
                    item.get("center_pid") or item.get("pid", ""), {}
                ).get("value", "---"),
                "unit": item.get("unit", ""),
                "centerUnit": self._readings.get(
                    item.get("center_pid") or item.get("pid", ""), {}
                ).get("unit", ""),
                "numericValue": item.get("numericValue") or 0.0,
            })
        self._dashboard_model.update_rows(rows)

    @staticmethod
    def _numeric_value(value):
        if value is None:
            return None
        try:
            return float(str(value).replace(",", ""))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _default_dashboard_maximum(pid):
        return {
            "010C": 8000.0,
            "010D": 140.0,
            "0105": 260.0,
            "0104": 100.0,
            "0111": 100.0,
            "012F": 100.0,
            "ATRV": 16.0,
        }.get(pid, 100.0)

    def _normalized_dashboard_widget(self, item):
        if not isinstance(item, dict):
            raise ValueError("Invalid dashboard widget")
        pid = str(item.get("pid", "")).upper()
        if not pid:
            raise ValueError("Dashboard widget is missing a PID")
        style = str(item.get("style", item.get("type", "combined"))).lower()
        if style not in ("digital", "dial", "combined"):
            style = "combined"
        shape = str(item.get("shape", "rounded")).lower()
        if shape not in ("rounded", "circle", "rectangle"):
            shape = "rounded"
        colour = str(item.get("colour", "blue")).lower()
        if colour not in ("blue", "green", "orange", "red", "purple", "cyan"):
            colour = "blue"
        return {
            "id": str(item.get("id") or uuid4().hex),
            "pid": pid,
            "center_pid": str(item.get("center_pid", "")).upper(),
            "title": str(item.get("title") or pid),
            "style": style,
            "shape": shape,
            "colour": colour,
            "minimum": float(item.get("minimum", 0.0)),
            "maximum": float(item.get("maximum", self._default_dashboard_maximum(pid))),
            "divisions": max(2, min(20, int(item.get("divisions", 10)))),
            "x": max(0.0, float(item.get("x", 30.0))),
            "y": max(0.0, float(item.get("y", 30.0))),
            "width": max(120.0, float(item.get("width", 320.0))),
            "height": max(100.0, float(item.get("height", 260.0))),
            "z": max(0, int(item.get("z", 1))),
        }

    @staticmethod
    def _local_path(url):
        if not url:
            return None
        qurl = QUrl(url)
        local = qurl.toLocalFile() if qurl.isLocalFile() else url
        return Path(local)

    @staticmethod
    def _version_numbers(version):
        numbers = [int(value) for value in re.findall(r"\d+", str(version))[:3]]
        return tuple((numbers + [0, 0, 0])[:3])

    @Slot()
    def shutdown(self):
        self.stop_session_replay()
        self.stop_recording()
        self._vehicle_service.stop()
        self._log.info("pyOBD v3 stopped")
