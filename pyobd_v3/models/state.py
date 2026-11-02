"""Framework-neutral connection and vehicle state."""

from dataclasses import asdict, dataclass
from enum import Enum


class ConnectionStatus(str, Enum):
    DISCONNECTED = "Disconnected"
    CONNECTING = "Connecting"
    CONNECTED = "Connected"
    RECONNECTING = "Reconnecting"
    FAILED = "Failed"


@dataclass(frozen=True)
class ConnectionState:
    status: ConnectionStatus = ConnectionStatus.DISCONNECTED
    transport: str = "Demo"
    adapter: str = "----"
    port: str = "----"
    protocol: str = "----"
    voltage: str = "----"
    error: str = ""

    @property
    def connected(self) -> bool:
        return self.status == ConnectionStatus.CONNECTED


@dataclass(frozen=True)
class VehicleState:
    vin: str = "----"
    nickname: str = ""


@dataclass(frozen=True)
class TelemetryReading:
    pid: str
    label: str
    value: str
    unit: str
    accent: str = "#2878f0"
    progress: float = 0.0

    def as_mapping(self):
        return asdict(self)
