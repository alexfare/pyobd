"""JSON persistence for v3 UI preferences."""

import json
from pathlib import Path


DEFAULT_WIDGETS = [
    {"id": "rpm", "pid": "010C", "title": "Engine RPM", "size": "small"},
    {"id": "speed", "pid": "010D", "title": "Vehicle Speed", "size": "small"},
    {"id": "coolant", "pid": "0105", "title": "Coolant", "size": "small"},
    {"id": "voltage", "pid": "ATRV", "title": "Voltage", "size": "small"},
]


class SettingsStore:
    def __init__(self, path=None):
        self.path = Path(path) if path else Path.home() / ".pyobd" / "v3-settings.json"
        self._data = self._load()

    def _load(self):
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else {}
        except (OSError, ValueError):
            return {}

    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(self._data, indent=2), encoding="utf-8")
        temporary.replace(self.path)

    def overview_widgets(self, vin="", vehicle_specific=False):
        key = vin.strip().upper() if vehicle_specific and vin else "global"
        layouts = self._data.get("overview_layouts", {})
        widgets = layouts.get(key, DEFAULT_WIDGETS)
        return [dict(widget) for widget in widgets]

    def save_overview_widgets(self, widgets, vin="", vehicle_specific=False):
        key = vin.strip().upper() if vehicle_specific and vin else "global"
        self._data.setdefault("overview_layouts", {})[key] = list(widgets)
        self._save()

    def vehicle_layout_enabled(self, vin):
        return vin.strip().upper() in self._data.get("vehicle_layout_vins", [])

    def set_vehicle_layout_enabled(self, vin, enabled):
        normalized = vin.strip().upper()
        values = set(self._data.get("vehicle_layout_vins", []))
        if enabled and normalized:
            values.add(normalized)
        else:
            values.discard(normalized)
        self._data["vehicle_layout_vins"] = sorted(values)
        self._save()

    def favorites(self):
        return set(self._data.get("favorites", []))

    def save_favorites(self, favorites):
        self._data["favorites"] = sorted(favorites)
        self._save()

    def profiles(self):
        return list(self._data.get("vehicle_profiles", []))

    def save_profiles(self, profiles):
        self._data["vehicle_profiles"] = list(profiles)
        self._save()

    def connection(self):
        return dict(self._data.get("connection", {}))

    def save_connection(self, values):
        self._data["connection"] = dict(values)
        self._save()
