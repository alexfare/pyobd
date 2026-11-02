"""Framework-neutral connection and vehicle state."""

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Dict


class ConnectionStatus(str, Enum):
    DISCONNECTED = "Disconnected"
    CONNECTING = "Connecting"
    CONNECTED = "Connected"
    RECONNECTING = "Reconnecting"
    FAILED = "Failed"


@dataclass(frozen=True)
class ConnectionConfig:
    transport: str = "Wi-Fi"
    address: str = "192.168.0.10"
    port: str = "35000"
    baudrate: str = "AUTO"
    timeout: float = 2.0
    retries: int = 3
    send_mode: str = "FAST"
    measurement_system: str = "IMPERIAL"

    def adapter_target(self) -> str:
        if self.transport == "Auto detect":
            return "AUTO"
        if self.transport == "Demo":
            return "DEMO"
        if self.transport == "Wi-Fi":
            address = self.address.strip()
            if not address:
                return ""
            if "://" in address:
                return address
            if address.upper().startswith("WIFI:"):
                address = address[5:]
            if ":" not in address:
                address = "{}:{}".format(address, self.port.strip() or "35000")
            return "WIFI:" + address
        if self.transport == "Bluetooth":
            return "BT:" + self.address.strip()
        if self.transport == "USB / Serial" and not self.address.strip():
            return "AUTO"
        return self.address.strip()


@dataclass(frozen=True)
class ConnectionState:
    status: ConnectionStatus = ConnectionStatus.DISCONNECTED
    transport: str = "Wi-Fi"
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


@dataclass(frozen=True)
class SupportedPID:
    pid: str
    name: str

    def as_mapping(self) -> Dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class DiagnosticCode:
    code: str
    category: str
    description: str

    def as_mapping(self) -> Dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class ReadinessMonitor:
    name: str
    status: str
    supported: bool

    def as_mapping(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MisfireResult:
    cylinder: int
    result: str
    count: int

    def as_mapping(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FreezeFrameReading:
    pid: str
    name: str
    value: str

    def as_mapping(self) -> Dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class VehicleProfile:
    profile_id: str
    nickname: str
    vin: str
    default_dashboard: str = "Overview"

    def as_mapping(self) -> Dict[str, str]:
        return asdict(self)
