"""Qt adapter for framework-neutral v3 application state."""

from PySide6.QtCore import Property, QObject, Signal, Slot

from event_sink import AppEvent, CallbackEventSink, EventChannel
from pyobd_v3.models import ConnectionState, VehicleState
from pyobd_v3.services import DemoService


class AppModel(QObject):
    pageChanged = Signal()
    stateChanged = Signal()
    serviceEvent = Signal(object)

    def __init__(self):
        super().__init__()
        self._page = "Overview"
        self._connection = ConnectionState()
        self._vehicle = VehicleState()
        self._telemetry = []
        self._event_sink = CallbackEventSink()
        self._event_sink.subscribe(self.serviceEvent.emit)
        self.serviceEvent.connect(self._apply_event)
        self._demo_service = DemoService(self._event_sink)
        self._demo_service.start()

    @Property(str, notify=pageChanged)
    def page(self):
        return self._page

    @Property("QVariantList", notify=stateChanged)
    def telemetry(self):
        return self._telemetry

    @Property(str, notify=stateChanged)
    def connectionStatus(self):
        return self._connection.status.value

    @Property(bool, notify=stateChanged)
    def connected(self):
        return self._connection.connected

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

    @Slot(object)
    def _apply_event(self, event: AppEvent):
        if event.channel == EventChannel.CONNECTION_STATE:
            self._connection = event.payload
        elif event.channel == EventChannel.VEHICLE_STATE:
            self._vehicle = event.payload
        elif event.channel == EventChannel.TELEMETRY:
            self._telemetry = [reading.as_mapping() for reading in event.payload]
        else:
            return
        self.stateChanged.emit()

    @Slot()
    def shutdown(self):
        self._demo_service.stop()
