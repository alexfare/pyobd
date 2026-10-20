"""Background vehicle polling worker for pyOBD."""

from collections import deque
import threading
import time
import traceback

import wx

import obd
import obd_io
from app_events import *
from debugEvent import DebugEvent
from obd.utils import OBDStatus

READINESS_MONITORS = (
    "MISFIRE_MONITORING", "FUEL_SYSTEM_MONITORING", "COMPONENT_MONITORING",
    "CATALYST_MONITORING", "HEATED_CATALYST_MONITORING",
    "EVAPORATIVE_SYSTEM_MONITORING", "SECONDARY_AIR_SYSTEM_MONITORING",
    "OXYGEN_SENSOR_MONITORING", "OXYGEN_SENSOR_HEATER_MONITORING",
    "EGR_VVT_SYSTEM_MONITORING", "NMHC_CATALYST_MONITORING",
    "NOX_SCR_AFTERTREATMENT_MONITORING", "BOOST_PRESSURE_MONITORING",
    "EXHAUST_GAS_SENSOR_MONITORING", "PM_FILTER_MONITORING",
)

DTC_CATEGORIES = (
    ("Stored", obd.commands.GET_DTC),
    ("Pending", obd.commands.GET_CURRENT_DTC),
    ("Permanent", obd.commands.GET_PERMANENT_DTC),
)


class SensorProducer(threading.Thread):
    @staticmethod
    def _target_loop_interval(demo_mode):
        return (1.0 / 30.0) if demo_mode else (1.0 / 12.0)

    @staticmethod
    def _graph_commands_to_poll(commands, isolated_key):
        if isolated_key is None:
            return list(commands)
        return [command for command in commands if command.command == isolated_key]

    def _post_graph_event(self, data):
        if getattr(self._notify_window, "graph_event_pending", False):
            return False
        self._notify_window.graph_event_pending = True
        wx.PostEvent(self._notify_window, GraphEvent(data))
        return True

    @staticmethod
    def _readiness_results(status_value):
        counts = {"ready": 0, "not_ready": 0, "unsupported": 0}
        results = []
        for index, name in enumerate(READINESS_MONITORS):
            monitor = getattr(status_value, name, None) if status_value is not None else None
            supported = bool(monitor and monitor.available)
            if not supported:
                status = "Unsupported"
                counts["unsupported"] += 1
            elif monitor.complete:
                status = "Ready"
                counts["ready"] += 1
            else:
                status = "Not ready"
                counts["not_ready"] += 1
            results.append({
                "kind": "readiness", "index": index,
                "supported": supported, "status": status,
            })
        return results, counts

    @staticmethod
    def _misfire_result(value):
        if value is None:
            return "Unsupported"
        return f"{value.MISFIRE_COUNT} misfires"

    @staticmethod
    def _collect_dtc_results(connection):
        rows = []
        counts = {category: 0 for category, _command in DTC_CATEGORIES}
        for category, command in DTC_CATEGORIES:
            response = connection.query(command)
            if response.value is None:
                continue
            for code, description in response.value:
                rows.append((code, category, description))
                counts[category] += 1
        return rows, counts

    def __init__(self, _notify_window, portName, SERTIMEOUT, RECONNATTEMPTS, BAUDRATE, FAST):
        #from queue import Queue
        self.portName = portName
        self.RECONNATTEMPTS = RECONNATTEMPTS
        self.SERTIMEOUT = SERTIMEOUT
        self.port = None
        self._notify_window = _notify_window
        self.baudrate = BAUDRATE
        self.FAST = FAST
        self.demo_mode = str(portName).upper() == "DEMO"
        threading.Thread.__init__(self)
        self.state = "started"
        self.disconnect_status = "Disconnected"
        self._stop_notified = False
        self._wake_event = threading.Event()

    def wake(self):
        self._wake_event.set()

    @staticmethod
    def _is_connected_status(status):
        return status in ("Car Connected", OBDStatus.CAR_CONNECTED)

    def initCommunication(self, reconnecting=False):
        try:
            self.connection.close()
        except:
            pass
        status_text = "Reconnecting..." if reconnecting else "Connecting..."
        wx.PostEvent(self._notify_window, StatusEvent([0, 1, status_text]))
        self.connection = obd_io.OBDConnection(
            self.portName,
            self._notify_window,
            self.baudrate,
            self.SERTIMEOUT,
            self.RECONNATTEMPTS,
            self.FAST,
            attempt_status="Reconnecting" if reconnecting else None,
            cancel_check=lambda: self._notify_window.ThreadControl == 666,
        )
        if self._notify_window.ThreadControl == 666:
            try:
                self.connection.close()
            except Exception:
                pass
            return None
        current_status = self.connection.connection.status()
        if not self._is_connected_status(current_status):  # Cant open serial port
            print(current_status)
            #wx.PostEvent(self._notify_window, StatusEvent([666]))  # signal apl, that communication was disconnected
            #wx.PostEvent(self._notify_window, StatusEvent([0, 1, "Error cant connect..."]))
            #self.state="finished"
            return None
        elif self._is_connected_status(current_status):
            wx.PostEvent(self._notify_window, DebugEvent([1, "Communication initialized..."]))
            wx.PostEvent(self._notify_window, StatusEvent([0, 1, "Car connected!"]))

            r = self.connection.query(obd.commands.ELM_VERSION)
            self.ELMver = str(r.value)
            r = self.connection.query(obd.commands.ELM_VOLTAGE)
            self.ELMvoltage = str(r.value)
            wx.PostEvent(self._notify_window, StatusEvent([5, 1, str(self.ELMvoltage)]))
            self.protocol = self.connection.connection.protocol_name()

            wx.PostEvent(self._notify_window, StatusEvent([2, 1, str(self.ELMver)]))
            wx.PostEvent(self._notify_window, StatusEvent([1, 1, str(self.protocol)]))
            wx.PostEvent(self._notify_window, StatusEvent([3, 1, str(self.connection.connection.port_name())]))
            try:
                r = self.connection.query(obd.commands.VIN)
                if r.value != None:
                    self.VIN = r.value.decode()
                    wx.PostEvent(self._notify_window, StatusEvent([4, 1, str(self.VIN)]))
            except:
                pass
                #traceback.print_exc()

            return "OK"


    @staticmethod
    def _live_value_text(command, value, formatter):
        if command.command in (b"0101", b"0141"):
            return (
                f"MIL ON: {value.MIL}, DTC Count: {value.DTC_count}, "
                f"Ignition type: {value.ignition_type}, Misfire monitoring complete: "
                f"{value.MISFIRE_MONITORING.complete}"
            )
        if command.command == b"0113":
            return (
                f"Bank1S1: {value[1][0]}, Bank1S2: {value[1][1]}, "
                f"Bank1S3: {value[1][2]}, Bank1S4: {value[1][3]} "
                f"Bank2S1: {value[2][0]}, Bank2S2: {value[2][1]}, "
                f"Bank2S3: {value[2][2]}, Bank2S4: {value[2][3]}"
            )
        if command.command == b"0103" and isinstance(value, (list, tuple)):
            return str(value[0]) if value else ""
        return formatter(value)

    def run(self):
        if self.initCommunication() != "OK":
            self._notify_window.ThreadControl = 666
            self.state = "finished"
            self.stop("Connection failed")
            return

        self.baudrate = self.connection.connection.interface.baudrate()
        self.portName = self.connection.connection.port_name()
        sensor_commands = None
        sensor_index = 0
        freeze_commands = None
        freeze_index = 0
        previous_page = None
        graph_series = {}
        graph_counter = 0
        graph_last_draw_at = 0.0
        graph_last_value_at = 0.0
        graph_was_streaming = False
        dashboard_last_emit_at = 0.0
        next_health_at = time.monotonic() + 1.0

        def reconnect():
            self.disconnect_status = "Connection lost"
            wx.PostEvent(self._notify_window, StatusEvent([0, 1, "Connection lost"]))
            if self.initCommunication(reconnecting=True) != "OK":
                self._notify_window.ThreadControl = 666
                return False
            self.disconnect_status = "Disconnected"
            return True

        def health_check(now):
            nonlocal next_health_at
            if now < next_health_at:
                return True
            next_health_at = now + 1.0
            return self.connection.query(obd.commands.RPM).value is not None

        while self._notify_window.ThreadControl != 666:
            if not self._is_connected_status(self.connection.connection.status()):
                if not reconnect():
                    break
                sensor_commands = None
                freeze_commands = None
                previous_page = None

            page = getattr(self._notify_window, "active_polling_page", "idle")
            page_changed = page != previous_page
            now = time.monotonic()

            if page != "graph" and graph_was_streaming:
                graph_series.clear()
                graph_counter = 0
                graph_was_streaming = False
                self._post_graph_event([[], 0, True])

            if page == "status":
                if now >= next_health_at:
                    rpm = self.connection.query(obd.commands.RPM)
                    if rpm.value is None:
                        if not reconnect():
                            break
                        previous_page = None
                        continue
                    voltage = self.connection.query(obd.commands.ELM_VOLTAGE)
                    wx.PostEvent(self._notify_window, StatusEvent([5, 1, str(voltage.value)]))
                    next_health_at = now + 1.0

            elif page == "tests":
                if page_changed or self._notify_window.tests_refresh_requested:
                    self._notify_window.tests_refresh_requested = False
                    try:
                        if self._notify_window.tests_active_section == "readiness":
                            response = self.connection.query(obd.commands[1][1])
                            readiness, counts = self._readiness_results(response.value)
                            for result in readiness:
                                wx.PostEvent(self._notify_window, TestEvent(result))
                            wx.PostEvent(self._notify_window, TestEvent({"kind": "complete", **counts}))
                        else:
                            commands = [
                                (cylinder, getattr(obd.commands, f"MONITOR_MISFIRE_CYLINDER_{cylinder}"))
                                for cylinder in range(1, 13)
                                if self.connection.supports(getattr(
                                    obd.commands, f"MONITOR_MISFIRE_CYLINDER_{cylinder}"
                                ))
                            ]
                            wx.PostEvent(self._notify_window, TestEvent({
                                "kind": "misfire_reset",
                                "cylinders": [cylinder for cylinder, _command in commands],
                            }))
                            for index, (_cylinder, command) in enumerate(commands):
                                if self._notify_window.tests_poll_cancelled:
                                    break
                                response = self.connection.query(command)
                                wx.PostEvent(self._notify_window, TestEvent({
                                    "kind": "misfire", "index": index,
                                    "result": self._misfire_result(response.value),
                                }))
                            wx.PostEvent(self._notify_window, TestEvent({
                                "kind": "misfire_complete", "count": len(commands),
                            }))
                    except Exception:
                        wx.PostEvent(self._notify_window, TestEvent({"kind": "error"}))
                        traceback.print_exc()

            elif page == "sensors":
                if sensor_commands is None:
                    excluded = {b"0100", b"0120", b"0140"}
                    candidates = [
                        command for command in obd.commands[1]
                        if command and command.command not in excluded
                    ]
                    supported = [command for command in candidates if self.connection.supports(command)]
                    sensor_commands = supported or candidates
                    sensor_index = 0
                    catalog_updates = []
                    for index, command in enumerate(sensor_commands):
                        catalog_updates.extend([
                            [index, 0, command.command],
                            [index, 1, command.desc],
                            [index, 2, "---"],
                        ])
                    if catalog_updates:
                        wx.PostEvent(self._notify_window, ResultEvent(catalog_updates))

                updates = []
                batch_size = 4 if self.demo_mode else 1
                for _ in range(min(batch_size, len(sensor_commands))):
                    index = sensor_index % len(sensor_commands)
                    command = sensor_commands[index]
                    response = self.connection.query(command)
                    if response.value is not None:
                        updates.append([
                            index, 2, self._live_value_text(
                                command, response.value,
                                self._notify_window.format_measurement_value,
                            ),
                        ])
                    sensor_index = (sensor_index + 1) % len(sensor_commands)
                if updates:
                    wx.PostEvent(self._notify_window, ResultEvent(updates))

            elif page == "dtc":
                if self._notify_window.ThreadControl == 1:
                    self.connection.query(obd.commands["CLEAR_DTC"])
                    if self._notify_window.ThreadControl != 666:
                        self._notify_window.ThreadControl = 0
                    page_changed = True
                if self._notify_window.ThreadControl == 2:
                    self._notify_window.ThreadControl = 0
                    page_changed = True
                if page_changed:
                    wx.PostEvent(self._notify_window, DTCEvent(0))
                    codes, counts = self._collect_dtc_results(self.connection)
                    for code in codes:
                        wx.PostEvent(self._notify_window, DTCEvent(code))
                    wx.PostEvent(self._notify_window, DTCEvent({"counts": counts}))

            elif page == "freeze_frame":
                if freeze_commands is None:
                    excluded = {
                        b"0200", b"0201", b"0220", b"0240", b"0203",
                        b"0202", b"021C", b"0213", b"0241", b"0251",
                    }
                    freeze_commands = [
                        command for command in obd.commands[2]
                        if command and command.command not in excluded
                    ]
                    freeze_index = 0
                    for index, command in enumerate(freeze_commands):
                        wx.PostEvent(self._notify_window, InsertFreezeframeRowEvent(index))
                        wx.PostEvent(self._notify_window, FreezeframeResultEvent([index, 0, command.command]))
                        wx.PostEvent(self._notify_window, FreezeframeResultEvent([index, 1, command.desc]))
                if freeze_commands:
                    index = freeze_index % len(freeze_commands)
                    response = self.connection.query(freeze_commands[index])
                    if response.value is not None:
                        wx.PostEvent(self._notify_window, FreezeframeResultEvent([
                            index, 2,
                            self._notify_window.format_measurement_value(response.value),
                        ]))
                    freeze_index = (freeze_index + 1) % len(freeze_commands)

            elif page == "graph":
                if self._notify_window.graph_interaction_paused:
                    pass
                elif not self._notify_window.graph_streaming_enabled:
                    if graph_was_streaming:
                        graph_series.clear()
                        graph_counter = 0
                        self._post_graph_event([[], 0, True])
                    graph_was_streaming = False
                else:
                    graph_was_streaming = True
                    commands = self._graph_commands_to_poll(
                        list(self._notify_window.selected_graph_commands),
                        getattr(self._notify_window, "isolated_graph_command_key", None),
                    )
                    selected_keys = {command.command for command in commands}
                    for key in tuple(graph_series):
                        if key not in selected_keys:
                            del graph_series[key]
                    plot_series = []
                    emit_values = now - graph_last_value_at >= 0.2
                    successful_query = False
                    for command in commands:
                        response = self.connection.query(command)
                        if response.value is None:
                            if emit_values:
                                wx.PostEvent(self._notify_window, GraphValueEvent([
                                    command.command, 2, "No data"
                                ]))
                            continue
                        successful_query = True
                        magnitude, unit, text = self._notify_window.get_measurement_components(
                            response.value
                        )
                        series = graph_series.setdefault(command.command, {
                            "x": deque(maxlen=450), "y": deque(maxlen=450),
                            "unit": "value", "desc": command.desc,
                        })
                        series["x"].append(graph_counter)
                        try:
                            series["y"].append(float(magnitude))
                        except (AttributeError, TypeError, ValueError):
                            series["y"].append(0.0)
                        series["unit"] = unit or "value"
                        if emit_values:
                            wx.PostEvent(self._notify_window, GraphValueEvent([
                                command.command, 2, text
                            ]))
                        plot_series.append((
                            series["x"], series["y"], series["unit"],
                            series["desc"], command.command,
                        ))
                    if emit_values:
                        graph_last_value_at = now
                    if commands and not successful_query and not health_check(now):
                        if not reconnect():
                            break
                        previous_page = None
                        continue
                    if now - graph_last_draw_at >= 0.25:
                        snapshot = [
                            (tuple(item[0]), tuple(item[1]), item[2], item[3], item[4])
                            for item in plot_series
                        ]
                        if self._post_graph_event([snapshot, graph_counter, graph_counter == 0]):
                            graph_last_draw_at = now
                    graph_counter += 1

            elif page == "dashboard":
                if (
                    now - dashboard_last_emit_at >= 0.2
                    and not self._notify_window.dashboard_event_pending
                ):
                    values = []
                    for command in list(self._notify_window.dashboard_poll_commands):
                        response = self.connection.query(command)
                        if response.value is None:
                            continue
                        magnitude, unit, text = self._notify_window.get_measurement_components(
                            response.value
                        )
                        values.append({
                            "pid": command.command.decode(errors="ignore").upper(),
                            "magnitude": magnitude, "unit": unit, "text": text,
                        })
                    self._notify_window.dashboard_event_pending = True
                    wx.PostEvent(self._notify_window, DashboardValuesEvent(values))
                    dashboard_last_emit_at = now

            elif not health_check(now):
                if not reconnect():
                    break
                sensor_commands = None
                freeze_commands = None
                previous_page = None
                continue

            previous_page = page
            self._wake_event.wait(self._target_loop_interval(self.demo_mode))
            self._wake_event.clear()

        self.state = "finished"
        self.stop(self.disconnect_status)

    def stop(self, status_text="Disconnected"):
        self.disconnect_status = status_text
        self._notify_window.ThreadControl = 666

        try: # if stop is called before any connection port is not defined (and not connected )
            self.connection.connection.close()
        except Exception as e:\
            print(e)

        #if self.port != None: #if stop is called before any connection port is not defined (and not connected )
        #  self.port.close()
        if (
            not self._stop_notified
            and not getattr(self._notify_window, "_shutdown_started", False)
        ):
            self._stop_notified = True
            wx.PostEvent(self._notify_window, StatusEvent([0, 1, status_text]))
            wx.PostEvent(self._notify_window, StatusEvent([1, 1, "----"]))
            wx.PostEvent(self._notify_window, StatusEvent([2, 1, "----"]))
            wx.PostEvent(self._notify_window, StatusEvent([3, 1, "----"]))
            wx.PostEvent(self._notify_window, StatusEvent([4, 1, "----"]))
            wx.PostEvent(self._notify_window, StatusEvent([5, 1, "----"]))
            wx.PostEvent(self._notify_window, CloseEvent([]))
        print("Sensor producer has stopped.")

# class producer end

