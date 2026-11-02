"""Cross-platform serial adapter discovery."""

from serial.tools import list_ports


def bluetooth_adapters():
    detected = []
    fallback = []
    try:
        ports = sorted(list_ports.comports(), key=lambda item: item.device or "")
    except Exception:
        return []
    for port in ports:
        target = (port.device or "").strip()
        if not target:
            continue
        name = (
            port.description
            or getattr(port, "product", "")
            or getattr(port, "manufacturer", "")
            or "Bluetooth adapter"
        ).strip()
        label = "{} ({})".format(name, target)
        entry = {"label": label, "target": target}
        fallback.append(entry)
        searchable = " ".join((
            label,
            port.hwid or "",
            getattr(port, "manufacturer", "") or "",
        )).lower()
        if any(word in searchable for word in ("bluetooth", "rfcomm", "obd", "elm327")):
            detected.append(entry)
    return detected or fallback
