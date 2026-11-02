"""Qt adapter for framework-neutral v3 application state."""

from collections import defaultdict, deque
import json
from pathlib import Path
from uuid import uuid4

from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot

from event_sink import AppEvent, CallbackEventSink, EventChannel
from pyobd_v3.dashboard_model import DashboardListModel
from pyobd_v3.live_data_model import LiveDataListModel
from pyobd_v3.models import ConnectionConfig, ConnectionState, VehicleState
from pyobd_v3.services import SettingsStore, VehicleService, bluetooth_adapters
from pyobd_v3.services.settings import DEFAULT_DASHBOARD_WIDGETS, DEFAULT_WIDGETS


class AppModel(QObject):
    pageChanged = Signal()
    stateChanged = Signal()
    graphChanged = Signal()
    serviceEvent = Signal(object)

    def __init__(self):
        super().__init__()
        self._page = "Overview"
        self._connection = ConnectionState()
        self._vehicle = VehicleState()
        self._supported_pids = []
        self._readings = {}
        self._history = defaultdict(lambda: deque(maxlen=300))
        self._live_data = []
        self._live_data_model = LiveDataListModel(self)
        self._live_search = ""
        self._favorites_only = False
        self._diagnostic_codes = []
        self._readiness = []
        self._freeze_frame = []
        self._operation_error = ""
        self._bluetooth_adapters = bluetooth_adapters()
        self._store = SettingsStore()
        self._favorites = self._store.favorites()
        self._profiles = self._store.profiles()
        self._active_profile_id = ""
        self._vehicle_layout_enabled = False
        self._overview_widgets = self._store.overview_widgets()
        try:
            self._dashboard_widgets = [
                self._normalized_dashboard_widget(item)
                for item in self._store.dashboard_widgets()
            ]
        except (TypeError, ValueError):
            self._dashboard_widgets = [
                self._normalized_dashboard_widget(item)
                for item in DEFAULT_DASHBOARD_WIDGETS
            ]
        self._dashboard_model = DashboardListModel(self)
        self._dashboard_message = ""
        self._event_sink = CallbackEventSink()
        self._event_sink.subscribe(self.serviceEvent.emit)
        self.serviceEvent.connect(self._apply_event)
        self._vehicle_service = VehicleService(self._event_sink)
        self._refresh_dashboard_model()

    @Property(str, notify=pageChanged)
    def page(self):
        return self._page

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
        return [item for item in self.widgetCatalog if item.get("type") == "pid"]

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

    @Property("QVariantList", notify=stateChanged)
    def liveData(self):
        return self._live_data

    @Property(QObject, constant=True)
    def liveDataModel(self):
        return self._live_data_model

    @Property("QVariantList", notify=stateChanged)
    def diagnosticCodes(self):
        return self._diagnostic_codes

    @Property("QVariantList", notify=stateChanged)
    def readinessResults(self):
        return self._readiness

    @Property("QVariantList", notify=stateChanged)
    def freezeFrameResults(self):
        return self._freeze_frame

    @Property("QVariantList", notify=stateChanged)
    def vehicleProfiles(self):
        return list(self._profiles)

    @Property(str, notify=stateChanged)
    def activeVehicleProfileID(self):
        return self._active_profile_id

    @Property(bool, notify=stateChanged)
    def vehicleLayoutEnabled(self):
        return self._vehicle_layout_enabled

    @Property("QVariantList", notify=stateChanged)
    def bluetoothAdapters(self):
        selected = self._connection.adapter if self._connection.connected else ""
        return [dict(item, connected=item.get("target") == selected) for item in self._bluetooth_adapters]

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
        self.pageChanged.emit()

    @Slot(str, str, str, str)
    def connect_vehicle(self, transport, address, port, baudrate):
        self._operation_error = ""
        self._vehicle_service.stop()
        self._vehicle_service = VehicleService(self._event_sink)
        config = ConnectionConfig(
            transport=transport,
            address=address,
            port=port,
            baudrate=baudrate or "AUTO",
        )
        self._store.save_connection({
            "transport": transport, "address": address,
            "port": port, "baudrate": baudrate or "AUTO",
        })
        self._vehicle_service.start(config)

    @Slot()
    def disconnect_vehicle(self):
        self._vehicle_service.stop()

    @Slot(result="QVariantMap")
    def saved_connection(self):
        values = self._store.connection()
        return {
            "transport": values.get("transport", "Wi-Fi"),
            "address": values.get("address", "192.168.0.10"),
            "port": values.get("port", "35000"),
            "baudrate": values.get("baudrate", "AUTO"),
        }

    @Slot()
    def refresh_bluetooth_adapters(self):
        self._bluetooth_adapters = bluetooth_adapters()
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
            "title": catalog_item.get("name", pid),
            "style": "combined",
            "minimum": 0.0,
            "maximum": self._default_dashboard_maximum(pid),
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
        widget["width"] = max(220.0, width)
        widget["height"] = max(170.0, height)
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

    @Slot()
    def restore_dashboard(self):
        self._dashboard_widgets = [dict(widget) for widget in DEFAULT_DASHBOARD_WIDGETS]
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
                "format": "pyOBD-dashboard",
                "version": 1,
                "widgets": self._dashboard_widgets,
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
            widgets = payload.get("widgets") if isinstance(payload, dict) else None
            if not isinstance(widgets, list):
                raise ValueError("Invalid dashboard layout")
            self._dashboard_widgets = [self._normalized_dashboard_widget(item) for item in widgets]
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
        self.stateChanged.emit()

    @Slot()
    def refresh_diagnostics(self):
        self._vehicle_service.request_diagnostics()

    @Slot()
    def clear_diagnostics(self):
        self._vehicle_service.clear_diagnostics()

    @Slot()
    def refresh_readiness(self):
        self._vehicle_service.request_readiness()

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
            "default_dashboard": default_dashboard or "Overview",
        }
        self._profiles.append(profile)
        self._profiles.sort(key=lambda item: item["nickname"].lower())
        self._active_profile_id = profile["profile_id"]
        self._store.save_profiles(self._profiles)
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
        destination = profile.get("default_dashboard", "Overview")
        if destination in ("Overview", "Dashboard"):
            self._page = destination
            self.pageChanged.emit()
        self.stateChanged.emit()

    @Slot(object)
    def _apply_event(self, event: AppEvent):
        if event.channel == EventChannel.CONNECTION_STATE:
            self._connection = event.payload
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
                self._freeze_frame = []
                self._vehicle = VehicleState()
                self._active_profile_id = ""
                self._vehicle_layout_enabled = False
                self._overview_widgets = self._store.overview_widgets()
        elif event.channel == EventChannel.VEHICLE_STATE:
            self._vehicle = event.payload
            self._activate_matching_profile()
            self._vehicle_layout_enabled = self._store.vehicle_layout_enabled(self._vehicle.vin)
            self._overview_widgets = self._store.overview_widgets(
                self._vehicle.vin, self._vehicle_layout_enabled
            )
        elif event.channel == EventChannel.TELEMETRY:
            self._readings = {
                reading.pid: reading.as_mapping() for reading in event.payload
            }
            for reading in event.payload:
                numeric = self._numeric_value(reading.value)
                if numeric is not None:
                    self._history[reading.pid].append(numeric)
            self._rebuild_live_data()
            self._refresh_dashboard_model()
            self.graphChanged.emit()
        elif event.channel == EventChannel.SUPPORTED_PIDS:
            self._supported_pids = [item.as_mapping() for item in event.payload]
            self._rebuild_live_data()
        elif event.channel == EventChannel.DIAGNOSTIC_CODES:
            self._diagnostic_codes = [item.as_mapping() for item in event.payload]
        elif event.channel == EventChannel.READINESS:
            self._readiness = [item.as_mapping() for item in event.payload]
        elif event.channel == EventChannel.FREEZE_FRAME:
            self._freeze_frame = [item.as_mapping() for item in event.payload]
        elif event.channel == EventChannel.OPERATION_ERROR:
            self._operation_error = str(event.payload)
        else:
            return
        self.stateChanged.emit()

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
        destination = profile.get("default_dashboard", "Overview")
        if destination in ("Overview", "Dashboard"):
            self._page = destination
            self.pageChanged.emit()

    def _dashboard_widget(self, widget_id):
        return next(
            (item for item in self._dashboard_widgets if item.get("id") == widget_id),
            None,
        )

    def _save_dashboard(self):
        self._store.save_dashboard_widgets(self._dashboard_widgets)
        self._refresh_dashboard_model()
        self.stateChanged.emit()

    def _refresh_dashboard_model(self):
        rows = []
        for item in self._dashboard_rows():
            rows.append({
                "widgetId": item.get("id", ""),
                "pid": item.get("pid", ""),
                "title": item.get("title", ""),
                "style": item.get("style", "combined"),
                "minimum": item.get("minimum", 0.0),
                "maximum": item.get("maximum", 100.0),
                "xPosition": item.get("x", 0.0),
                "yPosition": item.get("y", 0.0),
                "widgetWidth": item.get("width", 320.0),
                "widgetHeight": item.get("height", 260.0),
                "layerValue": item.get("z", 0),
                "readingValue": item.get("value", "---"),
                "unit": item.get("unit", ""),
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
        style = item.get("style", "combined")
        if style not in ("digital", "dial", "combined"):
            style = "combined"
        return {
            "id": str(item.get("id") or uuid4().hex),
            "pid": pid,
            "title": str(item.get("title") or pid),
            "style": style,
            "minimum": float(item.get("minimum", 0.0)),
            "maximum": float(item.get("maximum", self._default_dashboard_maximum(pid))),
            "x": max(0.0, float(item.get("x", 30.0))),
            "y": max(0.0, float(item.get("y", 30.0))),
            "width": max(220.0, float(item.get("width", 320.0))),
            "height": max(170.0, float(item.get("height", 260.0))),
            "z": max(0, int(item.get("z", 1))),
        }

    @staticmethod
    def _local_path(url):
        if not url:
            return None
        qurl = QUrl(url)
        local = qurl.toLocalFile() if qurl.isLocalFile() else url
        return Path(local)

    @Slot()
    def shutdown(self):
        self._vehicle_service.stop()
