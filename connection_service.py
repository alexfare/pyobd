"""State-driven ownership of the active OBD adapter connection."""

from enum import Enum
import threading

import obd
import obd_io
from obd.utils import OBDStatus


class ConnectionState(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    INITIALIZING = "initializing"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"


class ConnectionService:
    _RETRY_DELAYS = (0.25, 0.5, 1.0, 2.0, 3.0)

    def __init__(
        self, target, notify_window, baudrate, timeout, attempts, fast,
        attempt_callback=None,
    ):
        self.target = target
        self.notify_window = notify_window
        self.baudrate_setting = baudrate
        self.timeout = timeout
        self.attempts = max(1, int(attempts))
        self.fast = fast
        self.attempt_callback = attempt_callback
        self.state = ConnectionState.DISCONNECTED
        self.failure_reason = None
        self._adapter = None
        self._lock = threading.RLock()
        self._cancel_event = threading.Event()

    @staticmethod
    def _connected_status(status):
        return status in ("Car Connected", OBDStatus.CAR_CONNECTED)

    @property
    def connection(self):
        return self._adapter.connection if self._adapter is not None else None

    @property
    def transport(self):
        return self._adapter.transport if self._adapter is not None else None

    def connect(self, reconnecting=False):
        self._close_adapter()
        self.failure_reason = None
        state = (
            ConnectionState.RECONNECTING
            if reconnecting else ConnectionState.CONNECTING
        )

        for attempt in range(1, self.attempts + 1):
            if self._cancelled():
                self.state = ConnectionState.DISCONNECTED
                return False

            self.state = state
            if self.attempt_callback:
                self.attempt_callback(state, attempt, self.attempts)

            try:
                adapter = obd_io.OBDConnection(
                    self.target,
                    self.notify_window,
                    self.baudrate_setting,
                    self.timeout,
                    1,
                    self.fast,
                    cancel_check=self._cancelled,
                )
            except Exception as ex:
                self.failure_reason = str(ex) or "Unable to open adapter"
                if attempt < self.attempts:
                    delay = self._RETRY_DELAYS[
                        min(attempt - 1, len(self._RETRY_DELAYS) - 1)
                    ]
                    if self._cancel_event.wait(delay):
                        self.state = ConnectionState.DISCONNECTED
                        return False
                continue
            if self._cancelled():
                adapter.close()
                self.state = ConnectionState.DISCONNECTED
                return False

            if self._connected_status(adapter.connection.status()):
                with self._lock:
                    self.state = ConnectionState.INITIALIZING
                    self._adapter = adapter
                    self.state = ConnectionState.CONNECTED
                    self.failure_reason = None
                return True

            self.failure_reason = (
                adapter.failure_reason
                or self._adapter_failure_reason(adapter)
                or "Vehicle connection unavailable"
            )
            adapter.close()
            if attempt < self.attempts:
                delay = self._RETRY_DELAYS[min(attempt - 1, len(self._RETRY_DELAYS) - 1)]
                if self._cancel_event.wait(delay):
                    self.state = ConnectionState.DISCONNECTED
                    return False

        self.state = ConnectionState.FAILED
        return False

    def is_connected(self):
        with self._lock:
            if self.state != ConnectionState.CONNECTED or self._adapter is None:
                return False
            if self._connected_status(self._adapter.connection.status()):
                return True
            self.failure_reason = (
                self._adapter_failure_reason(self._adapter)
                or "Adapter transport disconnected"
            )
            self.state = ConnectionState.DISCONNECTED
            return False

    def query(self, command, force=False):
        with self._lock:
            if not self.is_connected():
                return obd.OBDResponse(command)
            adapter = self._adapter

        try:
            response = adapter.query(command, force=force)
        except Exception as ex:
            with self._lock:
                if adapter is self._adapter:
                    self.failure_reason = str(ex) or "Adapter query failed"
                    self.state = ConnectionState.DISCONNECTED
            return obd.OBDResponse(command)

        with self._lock:
            if (
                adapter is self._adapter
                and not self._connected_status(adapter.connection.status())
            ):
                self.failure_reason = (
                    self._adapter_failure_reason(adapter)
                    or "Adapter transport disconnected"
                )
                self.state = ConnectionState.DISCONNECTED
        return response

    def supports(self, command):
        with self._lock:
            adapter = self._adapter
        if adapter is None:
            return False
        try:
            return adapter.supports(command)
        except Exception:
            return False

    def protocol_name(self):
        return self.connection.protocol_name() if self.connection is not None else ""

    def port_name(self):
        return self.connection.port_name() if self.connection is not None else ""

    def baudrate(self):
        connection = self.connection
        if connection is None or getattr(connection, "interface", None) is None:
            return self.baudrate_setting
        return connection.interface.baudrate()

    def close(self):
        self._cancel_event.set()
        self._close_adapter()
        self.state = ConnectionState.DISCONNECTED

    def _cancelled(self):
        return self._cancel_event.is_set()

    @staticmethod
    def _adapter_failure_reason(adapter):
        connection = getattr(adapter, "connection", None)
        reason = getattr(connection, "last_error", None)
        if reason:
            return str(reason)
        interface = getattr(connection, "interface", None)
        if interface is not None and hasattr(interface, "last_error"):
            return interface.last_error()
        return None

    def _close_adapter(self):
        with self._lock:
            adapter = self._adapter
            self._adapter = None
        if adapter is not None:
            try:
                adapter.close()
            except Exception:
                pass

