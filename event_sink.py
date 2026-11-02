"""Framework-neutral application event boundary."""

from dataclasses import dataclass
from enum import Enum
from threading import RLock
from typing import Any, Callable, List, Protocol


class EventChannel(str, Enum):
    RESULT = "result"
    DTC = "dtc"
    STATUS = "status"
    TEST = "test"
    GRAPH = "graph"
    GRAPH_VALUE = "graph_value"
    CLOSE = "close"
    INSERT_FREEZE_FRAME_ROW = "insert_freeze_frame_row"
    FREEZE_FRAME_RESULT = "freeze_frame_result"
    DASHBOARD_VALUES = "dashboard_values"
    DEBUG = "debug"
    CONNECTION_STATE = "connection_state"
    VEHICLE_STATE = "vehicle_state"
    TELEMETRY = "telemetry"
    SUPPORTED_PIDS = "supported_pids"
    DIAGNOSTIC_CODES = "diagnostic_codes"
    READINESS = "readiness"
    FREEZE_FRAME = "freeze_frame"
    OPERATION_ERROR = "operation_error"


@dataclass(frozen=True)
class AppEvent:
    channel: EventChannel
    payload: Any = None


class EventSink(Protocol):
    def publish(self, event: AppEvent) -> None:
        """Publish an application event."""


class NullEventSink:
    def publish(self, event: AppEvent) -> None:
        pass


class CallbackEventSink:
    def __init__(self):
        self._callbacks: List[Callable[[AppEvent], None]] = []
        self._lock = RLock()

    def subscribe(self, callback: Callable[[AppEvent], None]) -> Callable[[], None]:
        with self._lock:
            self._callbacks.append(callback)

        def unsubscribe():
            with self._lock:
                if callback in self._callbacks:
                    self._callbacks.remove(callback)

        return unsubscribe

    def publish(self, event: AppEvent) -> None:
        with self._lock:
            callbacks = tuple(self._callbacks)
        for callback in callbacks:
            callback(event)
