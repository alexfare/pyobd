"""CSV live-data recording independent of the UI framework."""

import csv
import datetime
import json
from pathlib import Path
import re
import time


class RecordingService:
    def __init__(self, directory=None):
        self.directory = Path(directory) if directory else Path.home() / ".pyobd" / "sessions"
        self._file = None
        self._writer = None
        self._started = None
        self._metadata = None
        self.selected_pids = set()
        self.samples = 0

    @property
    def active(self):
        return self._file is not None

    def start(self, name, selected_pids, vehicle="Unassigned"):
        self.stop()
        self.directory.mkdir(parents=True, exist_ok=True)
        stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        safe_name = re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip("-.") or "session"
        csv_path = self.directory / "{}-{}.csv".format(stamp, safe_name)
        self._file = csv_path.open("w", newline="", encoding="utf-8")
        self._writer = csv.writer(self._file)
        self._writer.writerow(["Timestamp", "Elapsed Seconds", "PID", "Sensor", "Value"])
        self._started = time.monotonic()
        self.selected_pids = set(selected_pids)
        self.samples = 0
        self._metadata = {
            "name": name,
            "file": csv_path.name,
            "started_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
            "ended_at": "",
            "vehicle": vehicle,
            "samples": 0,
            "duration_seconds": 0,
            "metadata_path": csv_path.with_suffix(".json"),
        }
        try:
            self._write_metadata()
        except OSError:
            self._file.close()
            self._file = None
            self._writer = None
            self._metadata = None
            self.selected_pids.clear()
            raise
        return csv_path

    def write(self, readings):
        if not self.active:
            return
        for reading in readings:
            if reading.pid not in self.selected_pids:
                continue
            value = reading.value + ((" " + reading.unit) if reading.unit else "")
            self._writer.writerow([
                datetime.datetime.now().astimezone().isoformat(timespec="milliseconds"),
                "{:.3f}".format(time.monotonic() - self._started),
                reading.pid, reading.label, value,
            ])
            self.samples += 1
        if self.samples and self.samples % 25 == 0:
            self._file.flush()

    def stop(self):
        if not self.active:
            return None
        duration = max(0.0, time.monotonic() - self._started)
        self._file.flush()
        self._file.close()
        self._file = None
        self._writer = None
        self._metadata.update({
            "ended_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
            "samples": self.samples,
            "duration_seconds": round(duration, 3),
        })
        self._write_metadata()
        result = dict(self._metadata)
        self._metadata = None
        self._started = None
        self.selected_pids.clear()
        return result

    def _write_metadata(self):
        path = self._metadata["metadata_path"]
        data = {key: value for key, value in self._metadata.items() if key != "metadata_path"}
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

