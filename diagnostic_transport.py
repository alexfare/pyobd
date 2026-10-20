"""Serialized, read-only diagnostic transport for CAN-based requests."""

import datetime
import threading
from collections import deque
from dataclasses import dataclass

from obd import ECU, OBDCommand


READ_ONLY_SERVICES = frozenset({0x01, 0x02, 0x03, 0x06, 0x07, 0x09, 0x0A, 0x19, 0x22})
NEGATIVE_RESPONSE_CODES = {
    0x10: "General reject",
    0x11: "Service not supported",
    0x12: "Sub-function not supported",
    0x13: "Incorrect message length or format",
    0x21: "Busy; repeat request",
    0x22: "Conditions not correct",
    0x31: "Request out of range",
    0x33: "Security access denied",
    0x78: "Response pending",
}


class DiagnosticTransportError(Exception):
    pass


@dataclass(frozen=True)
class DiagnosticAddress:
    request_id: int
    response_id: int = None
    id_bits: int = 11
    functional: bool = False

    def __post_init__(self):
        if self.id_bits not in (11, 29):
            raise ValueError("CAN identifiers must be 11-bit or 29-bit")
        maximum = 0x7FF if self.id_bits == 11 else 0x1FFFFFFF
        if not 0 <= self.request_id <= maximum:
            raise ValueError("Request CAN identifier is out of range")
        if self.response_id is not None and not 0 <= self.response_id <= maximum:
            raise ValueError("Response CAN identifier is out of range")

    @property
    def header(self):
        width = 3 if self.id_bits == 11 else 8
        return f"{self.request_id:0{width}X}".encode("ascii")


@dataclass(frozen=True)
class DiagnosticResponse:
    source_id: int
    payload: bytes
    raw: str
    negative_response_code: int = None

    @property
    def successful(self):
        return self.negative_response_code is None

    @property
    def negative_response(self):
        if self.negative_response_code is None:
            return ""
        return NEGATIVE_RESPONSE_CODES.get(
            self.negative_response_code,
            f"Unknown negative response 0x{self.negative_response_code:02X}",
        )


class ReadOnlyDiagnosticTransport:
    def __init__(self, connection, request_lock=None):
        self.connection = connection
        self.request_lock = request_lock or threading.RLock()
        self.activity = deque(maxlen=500)

    def capabilities(self):
        protocol_id = ""
        protocol_name = ""
        try:
            protocol_id = str(self.connection.connection.protocol_id()).upper()
            protocol_name = str(self.connection.connection.protocol_name())
        except (AttributeError, RuntimeError):
            pass
        return {
            "protocol_id": protocol_id,
            "protocol_name": protocol_name,
            "can": protocol_id in {"6", "7", "8", "9", "A", "B", "C"},
            "11_bit": protocol_id in {"6", "8"},
            "29_bit": protocol_id in {"7", "9", "A", "B", "C"},
            "iso_tp": protocol_id in {"6", "7", "8", "9"},
        }

    @staticmethod
    def _message_source_id(message, id_bits):
        try:
            raw = message.frames[0].raw.replace(" ", "")
            width = 3 if id_bits == 11 else 8
            return int(raw[:width], 16)
        except (AttributeError, IndexError, TypeError, ValueError):
            return message.tx_id

    def request(self, address, payload):
        payload = bytes(payload)
        if not payload:
            raise DiagnosticTransportError("Diagnostic request cannot be empty")
        if payload[0] not in READ_ONLY_SERVICES:
            raise DiagnosticTransportError(
                f"Service 0x{payload[0]:02X} is not allowed by the read-only transport"
            )
        command = OBDCommand(
            "READ_ONLY_DIAGNOSTIC",
            "Read-only diagnostic request",
            payload.hex().upper().encode("ascii"),
            0,
            lambda messages: messages,
            ECU.ALL,
            False,
            address.header,
        )
        started_at = datetime.datetime.now().astimezone().isoformat(timespec="milliseconds")
        with self.request_lock:
            response = self.connection.query(command, force=True)
        results = []
        for message in response.value or []:
            response_payload = bytes(message.data)
            if not response_payload:
                continue
            source_id = self._message_source_id(message, address.id_bits)
            if address.response_id is not None and source_id != address.response_id:
                continue
            negative_code = (
                response_payload[2]
                if len(response_payload) >= 3 and response_payload[0] == 0x7F
                else None
            )
            results.append(DiagnosticResponse(
                source_id=source_id,
                payload=response_payload,
                raw=message.raw(),
                negative_response_code=negative_code,
            ))
        self.activity.append({
            "timestamp": started_at,
            "request_id": address.request_id,
            "id_bits": address.id_bits,
            "functional": address.functional,
            "request": payload.hex().upper(),
            "responses": [result.raw for result in results],
        })
        return results
