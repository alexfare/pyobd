"""Qt adapter for framework-neutral v3 application state."""

from uuid import uuid4

from PySide6.QtCore import Property, QObject, Signal, Slot

from event_sink import AppEvent, CallbackEventSink, EventChannel
from pyobd_v3.models import ConnectionConfig, ConnectionState, VehicleState
from pyobd_v3.services import SettingsStore, VehicleService, bluetooth_adapters
from pyobd_v3.services.settings import DEFAULT_WIDGETS


class AppModel(QObject):
    pageChanged = Signal()
    stateChanged = Signal()
    serviceEvent = Signal(object)

    def __init__(self):
        super().__init__()
        self._page = "Overview"
        self._connection = ConnectionState()
        self._vehicle = VehicleState()
        self._supported_pids = []
        self._readings = {}
        self._live_data = []
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
        self._event_sink = CallbackEventSink()
        self._event_sink.subscribe(self.serviceEvent.emit)
        self.serviceEvent.connect(self._apply_event)
        self._vehicle_service = VehicleService(self._event_sink)

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
            reading = self._readings.get(item.get("pid", ""), {})
            item.update({
                "value": reading.get("value", "---"),
                "unit": reading.get("unit", ""),
                "progress": reading.get("progress", 0.0),
                "available": bool(reading),
            })
            widgets.append(item)
        return widgets

    @Property("QVariantList", notify=stateChanged)
    def widgetCatalog(self):
        catalog = list(self._supported_pids)
        if not any(item.get("pid") == "ATRV" for item in catalog):
            catalog.append({"pid": "ATRV", "name": "Adapter Voltage"})
        return catalog

    @Property("QVariantList", notify=stateChanged)
    def liveData(self):
        return self._live_data

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
    def add_overview_widget(self, pid):
        if any(widget.get("pid") == pid for widget in self._overview_widgets):
            return
        name = next(
            (item.get("name") for item in self.widgetCatalog if item.get("pid") == pid),
            pid,
        )
        self._overview_widgets.append({
            "id": uuid4().hex, "pid": pid, "title": name, "size": "small",
        })
        self._save_overview()

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
                self._supported_pids = []
                self._live_data = []
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
            self._rebuild_live_data()
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

    @Slot()
    def shutdown(self):
        self._vehicle_service.stop()
