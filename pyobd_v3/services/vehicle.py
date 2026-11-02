"""Headless connection, polling, and diagnostic service for v3."""

from queue import Empty, Queue
import threading
import time

import obd
from obd_io import OBDConnection
from obd.utils import OBDStatus
from event_sink import AppEvent, EventChannel, EventSink
from pyobd_v3.models import (
    ConnectionConfig,
    ConnectionState,
    ConnectionStatus,
    DiagnosticCode,
    FreezeFrameReading,
    ReadinessMonitor,
    SupportedPID,
    TelemetryReading,
    VehicleState,
)


READINESS_MONITORS = (
    ("MISFIRE_MONITORING", "Misfire monitoring"),
    ("FUEL_SYSTEM_MONITORING", "Fuel system"),
    ("COMPONENT_MONITORING", "Comprehensive components"),
    ("CATALYST_MONITORING", "Catalyst"),
    ("HEATED_CATALYST_MONITORING", "Heated catalyst"),
    ("EVAPORATIVE_SYSTEM_MONITORING", "Evaporative system"),
    ("SECONDARY_AIR_SYSTEM_MONITORING", "Secondary air system"),
    ("OXYGEN_SENSOR_MONITORING", "Oxygen sensors"),
    ("OXYGEN_SENSOR_HEATER_MONITORING", "Oxygen sensor heater"),
    ("EGR_VVT_SYSTEM_MONITORING", "EGR/VVT system"),
    ("NMHC_CATALYST_MONITORING", "NMHC catalyst"),
    ("NOX_SCR_AFTERTREATMENT_MONITORING", "NOx/SCR aftertreatment"),
    ("BOOST_PRESSURE_MONITORING", "Boost pressure"),
    ("EXHAUST_GAS_SENSOR_MONITORING", "Exhaust gas sensor"),
    ("PM_FILTER_MONITORING", "Particulate matter filter"),
)

DEFAULT_LIVE_COMMANDS = (
    "ENGINE_LOAD", "COOLANT_TEMP", "SHORT_FUEL_TRIM_1", "LONG_FUEL_TRIM_1",
    "RPM", "SPEED", "INTAKE_TEMP", "MAF", "THROTTLE_POS", "FUEL_LEVEL",
    "BAROMETRIC_PRESSURE", "CONTROL_MODULE_VOLTAGE",
)


class VehicleService:
    def __init__(self, event_sink: EventSink, update_interval=0.08):
        self._event_sink = event_sink
        self._update_interval = update_interval
        self._stop_event = threading.Event()
        self._operations = Queue()
        self._thread = None
        self._connection = None
        self._config = ConnectionConfig()
        self._live_commands = []
        self._live_index = 0
        self._readings = {}

    @property
    def running(self):
        return bool(self._thread and self._thread.is_alive())

    def start(self, config: ConnectionConfig):
        if self.running:
            return False
        self._config = config
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="pyOBD-v3-vehicle",
            daemon=True,
        )
        self._thread.start()
        return True

    def stop(self):
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3.0)
        self._thread = None
        self._publish_connection(ConnectionStatus.DISCONNECTED)
        self._event_sink.publish(AppEvent(EventChannel.VEHICLE_STATE, VehicleState()))
        self._event_sink.publish(AppEvent(EventChannel.SUPPORTED_PIDS, ()))
        self._event_sink.publish(AppEvent(EventChannel.TELEMETRY, ()))
        self._event_sink.publish(AppEvent(EventChannel.DIAGNOSTIC_CODES, ()))
        self._event_sink.publish(AppEvent(EventChannel.READINESS, ()))
        self._event_sink.publish(AppEvent(EventChannel.FREEZE_FRAME, ()))

    def request_diagnostics(self):
        self._operations.put("diagnostics")

    def clear_diagnostics(self):
        self._operations.put("clear_diagnostics")

    def request_readiness(self):
        self._operations.put("readiness")

    def request_freeze_frame(self):
        self._operations.put("freeze_frame")

    def _run(self):
        target = self._config.adapter_target()
        if not target:
            self._publish_connection(ConnectionStatus.FAILED, "Adapter target is required")
            return
        reconnects = 0
        connected_once = False
        while not self._stop_event.is_set():
            self._publish_connection(
                ConnectionStatus.RECONNECTING if connected_once else ConnectionStatus.CONNECTING
            )
            try:
                self._connection = OBDConnection(
                    target,
                    None,
                    self._config.baudrate,
                    self._config.timeout,
                    self._config.retries,
                    "FAST",
                    attempt_status="Reconnecting" if connected_once else None,
                    event_sink=self._event_sink,
                    cancel_check=self._stop_event.is_set,
                )
                if self._stop_event.is_set():
                    break
                if self._connection.connection.status() not in (
                    "Car Connected", OBDStatus.CAR_CONNECTED
                ):
                    reason = self._connection.failure_reason or "No vehicle connection"
                    self._publish_connection(ConnectionStatus.FAILED, reason)
                    break
                connected_once = True
                reconnects = 0
                self._readings.clear()
                self._live_commands = []
                self._live_index = 0
                self._publish_identity()
                self._discover_supported_pids()
                self._publish_readiness()
                while not self._stop_event.is_set():
                    status = self._connection.connection.status()
                    if status not in ("Car Connected", OBDStatus.CAR_CONNECTED):
                        raise ConnectionError("Vehicle connection lost")
                    self._process_operation()
                    self._poll_next_reading()
                    self._stop_event.wait(self._update_interval)
            except Exception as error:
                if self._stop_event.is_set():
                    break
                reconnects += 1
                self._event_sink.publish(AppEvent(EventChannel.OPERATION_ERROR, str(error)))
                if not connected_once or reconnects > self._config.retries:
                    self._publish_connection(ConnectionStatus.FAILED, str(error))
                    break
                self._publish_connection(ConnectionStatus.RECONNECTING, str(error))
                self._stop_event.wait(1.0)
            finally:
                if self._connection is not None:
                    try:
                        self._connection.close()
                    except Exception:
                        pass
                self._connection = None

    def _publish_connection(self, status, error=""):
        if self._stop_event.is_set() and status != ConnectionStatus.DISCONNECTED:
            return
        connection = getattr(self._connection, "connection", None)
        connected = status == ConnectionStatus.CONNECTED and connection is not None
        disconnected = status == ConnectionStatus.DISCONNECTED
        self._event_sink.publish(AppEvent(EventChannel.CONNECTION_STATE, ConnectionState(
            status=status,
            transport=self._config.transport,
            adapter=(
                "----" if disconnected
                else "Simulated ELM327" if self._config.transport == "Demo"
                else self._config.address or "----"
            ),
            port=(
                "----" if disconnected
                else connection.port_name() if connected
                else self._config.adapter_target() or "----"
            ),
            protocol=(connection.protocol_name() if connected else "----"),
            voltage=self._voltage() if connected else "----",
            error=error,
        )))

    def _publish_identity(self):
        self._publish_connection(ConnectionStatus.CONNECTED)
        vin = "----"
        try:
            value = self._connection.query(obd.commands.VIN).value
            if isinstance(value, bytes):
                value = value.decode(errors="ignore")
            if value:
                vin = str(value)
        except Exception:
            pass
        if self._stop_event.is_set():
            return
        self._event_sink.publish(AppEvent(
            EventChannel.VEHICLE_STATE, VehicleState(vin=vin)
        ))

    def _discover_supported_pids(self):
        commands = []
        supported = []
        excluded = {b"0100", b"0120", b"0140", b"0160", b"0180", b"01A0", b"01C0"}
        for command in obd.commands[1]:
            if not command or command.command in excluded:
                continue
            if self._connection.supports(command):
                commands.append(command)
                supported.append(SupportedPID(
                    command.command.decode(errors="ignore").upper(), command.desc
                ))
        if not commands:
            commands = [getattr(obd.commands, name) for name in DEFAULT_LIVE_COMMANDS]
            supported = [SupportedPID(
                command.command.decode(errors="ignore").upper(), command.desc
            ) for command in commands]
        preferred = [
            getattr(obd.commands, name) for name in DEFAULT_LIVE_COMMANDS
            if getattr(obd.commands, name) in commands
        ]
        remaining = [command for command in commands if command not in preferred]
        self._live_commands = preferred + remaining + [obd.commands.ELM_VOLTAGE]
        supported.append(SupportedPID("ATRV", "Adapter Voltage"))
        if self._stop_event.is_set():
            return
        self._event_sink.publish(AppEvent(EventChannel.SUPPORTED_PIDS, tuple(supported)))

    def _poll_next_reading(self):
        if not self._live_commands:
            return
        command = self._live_commands[self._live_index % len(self._live_commands)]
        self._live_index += 1
        response = self._connection.query(command)
        if self._stop_event.is_set() or response.value is None:
            return
        pid = command.command.decode(errors="ignore").upper()
        magnitude, unit, text = self._format_value(response.value)
        self._readings[pid] = TelemetryReading(
            pid, command.desc, text, unit,
            progress=self._progress(command.name, magnitude),
        )
        self._event_sink.publish(AppEvent(EventChannel.TELEMETRY, (
            self._readings[pid],
        )))

    def _process_operation(self):
        try:
            operation = self._operations.get_nowait()
        except Empty:
            return
        try:
            if operation == "diagnostics":
                self._publish_diagnostics()
            elif operation == "clear_diagnostics":
                self._connection.query(obd.commands.CLEAR_DTC)
                self._publish_diagnostics()
                self._publish_readiness()
            elif operation == "readiness":
                self._publish_readiness()
            elif operation == "freeze_frame":
                self._publish_freeze_frame()
        except Exception as error:
            self._event_sink.publish(AppEvent(EventChannel.OPERATION_ERROR, str(error)))

    def _publish_diagnostics(self):
        rows = []
        for category, command in (
            ("Stored", obd.commands.GET_DTC),
            ("Pending", obd.commands.GET_CURRENT_DTC),
            ("Permanent", obd.commands.GET_PERMANENT_DTC),
        ):
            response = self._connection.query(command)
            for code, description in response.value or []:
                rows.append(DiagnosticCode(str(code), category, str(description)))
        if self._stop_event.is_set():
            return
        self._event_sink.publish(AppEvent(EventChannel.DIAGNOSTIC_CODES, tuple(rows)))

    def _publish_readiness(self):
        response = self._connection.query(obd.commands.STATUS)
        value = response.value
        rows = []
        for attribute, name in READINESS_MONITORS:
            monitor = getattr(value, attribute, None) if value is not None else None
            supported = bool(monitor and monitor.available)
            status = "Unsupported" if not supported else "Ready" if monitor.complete else "Not ready"
            rows.append(ReadinessMonitor(name, status, supported))
        if self._stop_event.is_set():
            return
        self._event_sink.publish(AppEvent(EventChannel.READINESS, tuple(rows)))

    def _publish_freeze_frame(self):
        rows = []
        excluded = {b"0200", b"0220", b"0240", b"0260", b"0280", b"02A0", b"02C0"}
        for command in obd.commands[2]:
            if not command or command.command in excluded:
                continue
            response = self._connection.query(command)
            if response.value is not None:
                rows.append(FreezeFrameReading(
                    command.command.decode(errors="ignore").upper(),
                    command.desc,
                    self._format_value(response.value)[2],
                ))
        if self._stop_event.is_set():
            return
        self._event_sink.publish(AppEvent(EventChannel.FREEZE_FRAME, tuple(rows)))

    def _voltage(self):
        try:
            return str(self._connection.query(obd.commands.ELM_VOLTAGE).value)
        except Exception:
            return "----"

    @staticmethod
    def _format_value(value):
        magnitude = getattr(value, "magnitude", None)
        unit = str(getattr(value, "unit", ""))
        if magnitude is not None:
            try:
                numeric = float(magnitude)
                return numeric, unit, "{:.2f}".format(numeric).rstrip("0").rstrip(".")
            except (TypeError, ValueError):
                pass
        if isinstance(value, bytes):
            value = value.decode(errors="ignore")
        return 0.0, unit, str(value)

    @staticmethod
    def _progress(name, value):
        maximums = {
            "RPM": 8000.0, "SPEED": 140.0, "COOLANT_TEMP": 120.0,
            "ENGINE_LOAD": 100.0, "THROTTLE_POS": 100.0, "FUEL_LEVEL": 100.0,
            "CONTROL_MODULE_VOLTAGE": 16.0,
        }
        maximum = maximums.get(name, 100.0)
        return max(0.0, min(1.0, value / maximum))
