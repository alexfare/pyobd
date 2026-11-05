"""UI-independent simulated vehicle service."""

import threading

import obd
from obd_io import OBDConnection
from event_sink import AppEvent, EventChannel, EventSink
from pyobd_v3.models import (
    ConnectionState,
    ConnectionStatus,
    TelemetryReading,
    VehicleState,
)


class DemoService:
    def __init__(self, event_sink: EventSink, update_interval=0.2):
        self._event_sink = event_sink
        self._update_interval = update_interval
        self._stop_event = threading.Event()
        self._thread = None
        self._connection = None

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._connection = OBDConnection(
            "DEMO", None, "AUTO", 1.0, 1, "FAST", event_sink=self._event_sink
        )
        self._publish_identity()
        self._thread = threading.Thread(
            target=self._run,
            name="pyOBD-v3-demo",
            daemon=True,
        )
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        self._thread = None
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    def _publish_identity(self):
        self._event_sink.publish(AppEvent(
            EventChannel.CONNECTION_STATE,
            ConnectionState(
                status=ConnectionStatus.CONNECTED,
                transport="Demo",
                adapter="Simulated ELM327",
                port=self._connection.connection.port_name(),
                protocol=self._connection.connection.protocol_name(),
                voltage=str(self._connection.query(obd.commands.ELM_VOLTAGE).value),
            ),
        ))
        self._event_sink.publish(AppEvent(
            EventChannel.VEHICLE_STATE,
            VehicleState(vin="DEMO0000000000001", nickname="Demo Vehicle"),
        ))

    def _run(self):
        while not self._stop_event.wait(self._update_interval):
            rpm = self._reading(obd.commands.RPM)
            speed = self._reading(obd.commands.SPEED)
            coolant = self._reading(obd.commands.COOLANT_TEMP)
            voltage = self._reading(obd.commands.ELM_VOLTAGE)
            readings = (
                TelemetryReading(
                    "010C", "Engine RPM", f"{rpm[0]:,.0f}", rpm[1] or "RPM",
                    progress=max(0.0, min(1.0, rpm[0] / 8000)),
                ),
                TelemetryReading(
                    "010D", "Vehicle Speed", f"{speed[0]:.0f}", speed[1] or "mph",
                    progress=max(0.0, min(1.0, speed[0] / 140)),
                ),
                TelemetryReading(
                    "0105", "Coolant", f"{coolant[0]:.0f}", coolant[1] or "°C",
                    "#25a96b", 0.72,
                ),
                TelemetryReading(
                    "ATRV", "Voltage", f"{voltage[0]:.1f}", voltage[1] or "V",
                    "#25a96b", 0.78,
                ),
            )
            self._event_sink.publish(AppEvent(EventChannel.TELEMETRY, readings))

    def _reading(self, command):
        response = self._connection.query(command)
        value = response.value
        magnitude = getattr(value, "magnitude", value)
        unit = str(getattr(value, "unit", ""))
        try:
            magnitude = float(magnitude)
        except (TypeError, ValueError):
            magnitude = 0.0
        return magnitude, unit
