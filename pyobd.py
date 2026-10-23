#!/usr/bin/env python
############################################################################
#
# wxgui.py
#
# Copyright 2004 Donour Sizemore (donour@uchicago.edu)
# Copyright 2009 Secons Ltd. (www.obdtester.com)
# Copyright 2021 Jure Poljsak (https://github.com/barracuda-fsh/pyobd) 
# Modified by FareBrothers, LLC.
# Modifications made from 2026-04-05 through 2026-10-20.
#
# This file is part of pyOBD.
#
# pyOBD is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# pyOBD is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyOBD; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
############################################################################

import traceback
import wx
import obd_io  # OBD2 funcs
import os  # os.environ
import datetime
import threading
import sys
import serial
import re
import json
import subprocess
import urllib.error
import urllib.request
from serial.tools import list_ports
import time
import configparser  # safe application configuration
import webbrowser  # open browser from python
import csv

from about_ui import APP_VERSION, ABOUT_DIALOG_TEXT, build_about_page
from app_events import *
from debugEvent import *
from dashboard_ui import DashboardUIMixin
from graph_ui import GraphUIMixin
from session_ui import SessionUIMixin
from sensor_worker import SensorProducer
from obd2_codes import pcodes
from ui_theme import ActionCard, AppTheme, ModernButton
from vehicle_profiles import VehicleProfilesMixin

from wx.lib.mixins.listctrl import ListCtrlAutoWidthMixin
import obd

from obd.utils import OBDStatus




ID_ABOUT = 101
ID_EXIT = 110
ID_CONFIG = 500
ID_CLEAR = 501
ID_GETC = 502
ID_RESET = 503
ID_LOOK = 504
ALL_ON = 505
ALL_OFF = 506

ID_DISCONNECT = 507
ID_HELP_ABOUT = 508
ID_HELP_VISIT = 509
ID_HELP_ORDER = 510

RELEASE_API_URL = "https://api.github.com/repos/alexfare/pyobd/releases/latest"
RELEASES_URL = "https://github.com/alexfare/pyobd/releases/latest"

lock = threading.Lock()

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)


def user_config_path():
    if sys.platform == "win32":
        config_dir = os.path.join(
            os.environ.get("APPDATA", os.path.expanduser("~")),
            "pyOBD",
        )
        os.makedirs(config_dir, exist_ok=True)
        return os.path.join(config_dir, "pyobd.ini")
    return os.path.join(os.path.expanduser("~"), ".pyobdrc")

TESTS = ["MISFIRE_MONITORING",
    "FUEL_SYSTEM_MONITORING",
    "COMPONENT_MONITORING",
    "CATALYST_MONITORING",
    "HEATED_CATALYST_MONITORING",
    "EVAPORATIVE_SYSTEM_MONITORING",
    "SECONDARY_AIR_SYSTEM_MONITORING",
    "OXYGEN_SENSOR_MONITORING",
    "OXYGEN_SENSOR_HEATER_MONITORING",
    "EGR_VVT_SYSTEM_MONITORING",
    "NMHC_CATALYST_MONITORING",
    "NOX_SCR_AFTERTREATMENT_MONITORING",
    "BOOST_PRESSURE_MONITORING",
    "EXHAUST_GAS_SENSOR_MONITORING",
    "PM_FILTER_MONITORING"]

TEST_LABELS = [
    "Misfire monitoring",
    "Fuel system monitoring",
    "Component monitoring",
    "Catalyst monitoring",
    "Heated catalyst monitoring",
    "Evaporative system monitoring",
    "Secondary air system monitoring",
    "Oxygen sensor monitoring",
    "Oxygen sensor heater monitoring",
    "EGR / VVT system monitoring",
    "NMHC catalyst monitoring",
    "NOx / SCR aftertreatment monitoring",
    "Boost pressure monitoring",
    "Exhaust gas sensor monitoring",
    "Particulate filter monitoring",
]



class MyApp(SessionUIMixin, VehicleProfilesMixin, DashboardUIMixin, GraphUIMixin, wx.App):
    # A listctrl which auto-resizes the column boxes to fill
    class MyListCtrl(wx.ListCtrl, ListCtrlAutoWidthMixin):
        def __init__(self, parent, id, pos=wx.DefaultPosition,
                     size=wx.DefaultSize, style=0):
            wx.ListCtrl.__init__(self, parent, id, pos, size, style)
            ListCtrlAutoWidthMixin.__init__(self)

    STATUS_TOOLBAR_MAP = {
        0: "link",
        1: "protocol",
        2: "adapter",
        3: "port",
        4: "vin",
        5: "voltage",
    }

    def _build_bottom_status_toolbar(self):
        self.bottom_toolbar = wx.Panel(self.content_panel, -1)
        self.bottom_toolbar.SetBackgroundColour(self.theme.sidebar)
        self.bottom_toolbar_values = {}

        toolbar_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.bottom_toolbar.SetSizer(toolbar_sizer)
        self.bottom_toolbar.SetMinSize((-1, 52))

        toolbar_fields = [
            ("link", "Link", "Disconnected"),
            ("protocol", "Protocol", "----"),
            ("adapter", "Adapter", "----"),
            ("port", "Port", "----"),
            ("vin", "VIN", "----"),
            ("voltage", "Voltage", "----"),
        ]

        for index, (key, label, value) in enumerate(toolbar_fields):
            field_sizer = wx.BoxSizer(wx.VERTICAL)

            title = wx.StaticText(self.bottom_toolbar, -1, label.upper())
            title.SetForegroundColour(self.theme.sidebar_muted)
            title.SetFont(wx.Font(7, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))

            value_widget = wx.StaticText(self.bottom_toolbar, -1, value)
            value_widget.SetForegroundColour(self.theme.sidebar_text)
            value_widget.SetFont(wx.Font(10, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))

            self.bottom_toolbar_values[key] = value_widget

            field_sizer.Add(title, 0, wx.BOTTOM, 2)
            field_sizer.Add(value_widget, 0)
            toolbar_sizer.Add(field_sizer, 1, wx.ALIGN_CENTER_VERTICAL | wx.LEFT | wx.RIGHT, 10)

            if index < len(toolbar_fields) - 1:
                toolbar_sizer.Add(wx.StaticLine(self.bottom_toolbar, style=wx.LI_VERTICAL), 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 8)

    def _set_bottom_status_defaults(self):
        defaults = {
            "link": "Disconnected",
            "protocol": "----",
            "adapter": "----",
            "port": "----",
            "vin": "----",
            "voltage": "----",
        }
        for key, value in defaults.items():
            if key in self.bottom_toolbar_values:
                self.bottom_toolbar_values[key].SetLabel(value)
        self.bottom_toolbar.Layout()
        self._update_connection_visuals("Disconnected")

    def _update_bottom_status(self, status_index, value):
        status_key = self.STATUS_TOOLBAR_MAP.get(status_index)
        if status_key and status_key in self.bottom_toolbar_values:
            self.bottom_toolbar_values[status_key].SetLabel(str(value))
            self.bottom_toolbar.Layout()

    def _update_connection_visuals(self, state_text):
        state = str(state_text).strip()
        normalized = state.lower()
        if "connected" in normalized and "disconnected" not in normalized:
            label = "●  Connected"
            colour = self.theme.success
        elif "disconnecting" in normalized:
            label = "●  Disconnecting"
            colour = self.theme.warning
        elif "reconnecting" in normalized:
            label = "●  Reconnecting"
            colour = self.theme.warning
        elif "connecting" in normalized:
            label = "●  Connecting"
            colour = self.theme.warning
        elif "lost" in normalized:
            label = "●  Connection lost"
            colour = self.theme.danger
        elif "fail" in normalized or "error" in normalized:
            label = "●  Connection failed"
            colour = self.theme.danger
        else:
            label = "●  Disconnected"
            colour = self.theme.muted

        for control_name in ("header_connection_status", "home_connection_status"):
            control = getattr(self, control_name, None)
            if control is not None:
                control.SetLabel(label)
                control.SetForegroundColour(colour)
                control.SetToolTip(state)

        if hasattr(self, "header_connect_button"):
            active = label in (
                "●  Connected", "●  Connecting", "●  Reconnecting", "●  Disconnecting"
            )
            self.header_connect_button.SetLabel(
                "Disconnect" if label == "●  Connected" else "Cancel" if active else "Connect"
            )
            self.header_connect_button.SetVariant("danger" if active else "primary")

    def sensor_control_reconnecting(self):
        self._stop_sensor_recording()
        self._set_graph_streaming(False)
        self._set_graph_connection_state(False)
        self._reset_dashboard_values()
        self.settingmenu.Enable(ID_CONFIG, False)
        self.settingmenu.Enable(ID_RESET, False)
        self.settingmenu.Enable(ID_DISCONNECT, True)
        self.dtcmenu.Enable(ID_GETC, False)
        self.dtcmenu.Enable(ID_CLEAR, False)
        self.GetDTCButton.Enable(False)
        self.ClearDTCButton.Enable(False)
        self.RefreshTestsButton.Enable(False)
        self.sensor_record_button.Enable(False)

    def _build_content_header(self):
        self.content_header = wx.Panel(self.content_panel)
        self.content_header.SetBackgroundColour(self.theme.surface)
        self.content_header.SetMinSize((-1, 64))
        header_sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.header_menu_button = ModernButton(
            self.content_header, "☰", self.theme, variant="ghost", size=(44, 38)
        )
        self.header_menu_button.SetMinSize((44, 38))
        self.header_menu_button.SetFont(self.theme.font(16))
        self.header_menu_button.SetToolTip("Open navigation")
        self.header_menu_button.Bind(wx.EVT_BUTTON, self._toggle_sidebar)

        self.page_title = wx.StaticText(self.content_header, label="Overview")
        self.page_title.SetForegroundColour(self.theme.text)
        self.page_title.SetFont(self.theme.font(20, bold=True))

        self.header_connection_status = wx.StaticText(self.content_header, label="●  Disconnected")
        self.header_connection_status.SetForegroundColour(self.theme.muted)
        self.header_connection_status.SetFont(self.theme.font(10, bold=True))

        self.header_vehicle_profile = wx.StaticText(
            self.content_header,
            label="No vehicle profile",
            style=wx.ST_ELLIPSIZE_END,
        )
        self.header_vehicle_profile.SetMaxSize((180, -1))
        self.header_vehicle_profile.SetForegroundColour(self.theme.muted)
        self.header_vehicle_profile.SetFont(self.theme.font(10))

        self.header_connect_button = ModernButton(
            self.content_header, "Connect", self.theme, variant="primary"
        )
        self.header_connect_button.SetMinSize((110, 38))
        self.header_connect_button.Bind(wx.EVT_BUTTON, self._on_header_connection_action)

        self.header_configure_button = ModernButton(
            self.content_header, "Configure", self.theme, variant="secondary"
        )
        self.header_configure_button.SetMinSize((110, 38))
        self.header_configure_button.Bind(wx.EVT_BUTTON, self.Configure)

        header_sizer.Add(self.header_menu_button, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 16)
        header_sizer.Add(self.page_title, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 12)
        header_sizer.AddStretchSpacer()
        header_sizer.Add(self.header_vehicle_profile, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 16)
        header_sizer.Add(self.header_connection_status, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 16)
        header_sizer.Add(self.header_configure_button, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        header_sizer.Add(self.header_connect_button, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 16)
        self.content_header.SetSizer(header_sizer)
        self._update_active_vehicle_header()

    def _toggle_sidebar(self, event=None):
        self._sidebar_open = not self._sidebar_open
        self.sidebar_panel.Show(self._sidebar_open)
        self.header_menu_button.SetToolTip(
            "Close navigation" if self._sidebar_open else "Open navigation"
        )
        self.shell_panel.Layout()

    def _on_header_connection_action(self, event):
        if self.senprod and self.senprod.is_alive():
            self.OnDisconnect(event)
        else:
            self.OpenPort(event)

    def _build_sidebar(self):
        self.sidebar_panel = wx.Panel(self.shell_panel)
        self.sidebar_panel.SetBackgroundColour(self.theme.sidebar)
        self.sidebar_panel.SetMinSize((220, -1))
        sidebar_sizer = wx.BoxSizer(wx.VERTICAL)

        brand = wx.StaticText(self.sidebar_panel, label="pyOBD")
        brand.SetForegroundColour(self.theme.sidebar_text)
        brand.SetFont(self.theme.font(21, bold=True))
        subtitle = wx.StaticText(self.sidebar_panel, label="VEHICLE DIAGNOSTICS")
        subtitle.SetForegroundColour(self.theme.sidebar_muted)
        subtitle.SetFont(self.theme.font(8, bold=True))
        sidebar_sizer.Add(brand, 0, wx.LEFT | wx.RIGHT | wx.TOP, 22)
        sidebar_sizer.Add(subtitle, 0, wx.LEFT | wx.RIGHT | wx.TOP | wx.BOTTOM, 22)

        primary_groups = [
            ("MONITOR", [
                ("Overview", self.home_panel),
                ("Dashboard", self.dashboard_panel),
                ("Live Data", self.sensors_panel),
                ("Graphs", self.graph_panel),
            ]),
            ("DIAGNOSE", [
                ("Diagnostics", self.DTCpanel),
                ("Readiness", self.tests_panel),
                ("Freeze Frame", self.freezeframe),
            ]),
            ("MANAGE", [
                ("Vehicles", self.vehicle_profiles_panel),
                ("Sessions", self.sessions_panel),
            ]),
        ]
        self.sidebar_buttons = {}

        def add_item(label, page):
            button = ModernButton(
                self.sidebar_panel,
                label,
                self.theme,
                variant="sidebar",
                align="left",
            )
            button.SetMinSize((-1, 44))
            button.SetFont(self.theme.font(11, bold=label == "Overview"))
            button.Bind(wx.EVT_BUTTON, lambda _event, target=page, title=label: self._go_to_page(target, title))
            sidebar_sizer.Add(button, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)
            self.sidebar_buttons[page] = button

        for group_label, items in primary_groups:
            group = wx.StaticText(self.sidebar_panel, label=group_label)
            group.SetForegroundColour(self.theme.sidebar_muted)
            group.SetFont(self.theme.font(8, bold=True))
            sidebar_sizer.Add(group, 0, wx.LEFT | wx.RIGHT | wx.TOP, 22)
            for label, page in items:
                add_item(label, page)
        sidebar_sizer.AddStretchSpacer()
        add_item("Activity Log", self.trace)
        self.sidebar_update_button = ModernButton(
            self.sidebar_panel,
            "Update",
            self.theme,
            variant="sidebar",
            align="left",
        )
        self.sidebar_update_button.SetMinSize((-1, 44))
        self.sidebar_update_button.SetFont(self.theme.font(11))
        self.sidebar_update_button.Bind(wx.EVT_BUTTON, self.OnHomeUpdate)
        sidebar_sizer.Add(
            self.sidebar_update_button,
            0,
            wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM,
            10,
        )
        add_item("About", self.about_panel)
        sidebar_sizer.AddSpacer(12)
        self.sidebar_panel.SetSizer(sidebar_sizer)

    def _refresh_sidebar_selection(self, selected_page):
        for page, button in getattr(self, "sidebar_buttons", {}).items():
            selected = page is selected_page
            button.SetVariant("sidebar_active" if selected else "sidebar")
            button.SetFont(self.theme.font(11, bold=selected))
            button.Refresh()

    def _apply_touch_friendly_style(self):
        self.touch_font = wx.Font(11, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        self.touch_font_bold = wx.Font(11, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        self.home_title_font = wx.Font(17, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        self.home_tile_font = wx.Font(14, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        # Keep native tabs and their labels on the same system theme, including
        # dark themes where a fixed light background hides the tab text.
        self.frame.SetBackgroundColour(self.theme.window)
        self.nb.SetBackgroundColour(self.theme.window)
        self.nb.SetForegroundColour(self.theme.text)
        self.frame.SetFont(self.touch_font)

        try:
            self.nb.SetPadding(wx.Size(20, 10))
        except Exception:
            pass
        self.nb.SetFont(self.touch_font_bold)

        controls = [
            self.status,
            self.OBDTests,
            self.misfire_tests,
            self.sensors,
            self.freezeframe,
            self.dtc,
            self.trace,
            self.graph_list_ctrl,
        ]
        for control in controls:
            control.SetFont(self.touch_font)
            self.theme.style_list(control)

        self.GetDTCButton.SetMinSize((140, 40))
        self.GetDTCButton.SetFont(self.touch_font_bold)
        self.ClearDTCButton.SetMinSize((140, 40))
        self.ClearDTCButton.SetFont(self.touch_font_bold)
        self.LookupDTCButton.SetMinSize((140, 40))
        self.LookupDTCButton.SetFont(self.touch_font_bold)

        if hasattr(self, "add_graph_pid_button"):
            self.add_graph_pid_button.SetFont(self.touch_font_bold)
            self.remove_graph_pid_button.SetFont(self.touch_font_bold)
            self.graph_play_button.SetFont(self.touch_font_bold)
            self.graph_list_ctrl.SetFont(self.touch_font)

        if hasattr(self, "home_title"):
            self.home_title.SetFont(self.home_title_font)

        if hasattr(self, "home_scan_button"):
            self.home_scan_button.SetFont(self.home_tile_font)
            self.home_services_button.SetFont(self.home_tile_font)
            self.home_graphs_button.SetFont(self.home_tile_font)

    def _go_to_page(self, page, title=None):
        self.tests_poll_cancelled = page is not self.tests_panel
        if page is getattr(self, "vehicle_profiles_panel", None):
            self._refresh_vehicle_profile_list(self.active_vehicle_profile)
        elif page is getattr(self, "sessions_panel", None):
            self._refresh_session_list()
        page_index = wx.NOT_FOUND
        for i in range(self.nb.GetPageCount()):
            if self.nb.GetPage(i) is page:
                page_index = i
                break

        if page_index != wx.NOT_FOUND:
            self.nb.SetSelection(page_index)
            self.active_polling_page = {
                self.status: "status",
                self.tests_panel: "tests",
                self.sensors_panel: "sensors",
                self.DTCpanel: "dtc",
                self.freezeframe: "freeze_frame",
                self.graph_panel: "graph",
                self.home_panel: "overview",
                self.dashboard_panel: "dashboard",
            }.get(page, "idle")
            if self.senprod and self.senprod.is_alive():
                self.senprod.wake()
            if title is None:
                title = {
                    self.home_panel: "Overview",
                    self.dashboard_panel: "Dashboard",
                    self.sensors_panel: "Live Data",
                    self.DTCpanel: "Diagnostics",
                    self.tests_panel: "Readiness",
                    self.freezeframe: "Freeze Frame",
                    self.graph_panel: "Graphs",
                    self.vehicle_profiles_panel: "Vehicles",
                    self.sessions_panel: "Sessions",
                    self.status: "Connection",
                    self.trace: "Activity Log",
                    self.about_panel: "About",
                }.get(page, "pyOBD")
            if hasattr(self, "page_title"):
                self.page_title.SetLabel(title)
            self._refresh_sidebar_selection(page)

    def _create_home_tile(self, parent, label, description, colour, hover_colour, handler, icon):
        return ActionCard(
            parent,
            self.theme,
            label,
            description,
            colour,
            hover_colour,
            handler,
            icon,
        )

    def build_home_page(self):
        self.home_panel = wx.Panel(self.nb, -1)
        self.home_panel.SetBackgroundColour(self.theme.window)
        self.home_panel.SetForegroundColour(self.theme.text)

        root_sizer = wx.BoxSizer(wx.VERTICAL)
        actions = wx.GridBagSizer(12, 12)

        self.home_scan_button = self._create_home_tile(
            self.home_panel,
            "Dashboard",
            "",
            self.theme.accent,
            self.theme.accent_hover,
            self.OnHomeDashboard,
            "dashboard",
        )
        self.home_services_button = self._create_home_tile(
            self.home_panel,
            "Live Data",
            "",
            self.theme.success,
            self.theme.success_hover,
            self.OnHomeSensors,
            "live",
        )
        self.home_graphs_button = self._create_home_tile(
            self.home_panel,
            "Graphs",
            "",
            self.theme.info,
            self.theme.info_hover,
            self.OnHomeGraphs,
            "graphs",
        )
        self.home_readiness_button = self._create_home_tile(
            self.home_panel,
            "Readiness",
            "",
            self.theme.warning,
            self.theme.warning.ChangeLightness(85),
            self.OnHomeReadiness,
            "readiness",
        )
        self.home_diagnostics_button = self._create_home_tile(
            self.home_panel,
            "Diagnostics",
            "",
            self.theme.danger,
            self.theme.danger.ChangeLightness(85),
            self.OnHomeDiagnostics,
            "diagnostics",
        )
        vehicle_colour = wx.Colour(126, 34, 206)
        self.home_vehicle_button = self._create_home_tile(
            self.home_panel,
            "Vehicles",
            "",
            vehicle_colour,
            vehicle_colour.ChangeLightness(85),
            self.OnHomeVehicles,
            "vehicles",
        )
        actions.Add(self.home_scan_button, pos=(0, 0), flag=wx.EXPAND)
        actions.Add(self.home_services_button, pos=(0, 1), flag=wx.EXPAND)
        actions.Add(self.home_graphs_button, pos=(0, 2), flag=wx.EXPAND)
        actions.Add(self.home_readiness_button, pos=(1, 0), flag=wx.EXPAND)
        actions.Add(self.home_diagnostics_button, pos=(1, 1), flag=wx.EXPAND)
        actions.Add(self.home_vehicle_button, pos=(1, 2), flag=wx.EXPAND)
        actions.AddGrowableCol(0, 1)
        actions.AddGrowableCol(1, 1)
        actions.AddGrowableCol(2, 1)
        actions.AddGrowableRow(0, 1)
        actions.AddGrowableRow(1, 1)

        root_sizer.Add(actions, 1, wx.EXPAND | wx.ALL, 28)
        self.home_panel.SetSizer(root_sizer)

        self.nb.AddPage(self.home_panel, "Home")

    def OnHomeScan(self, event):
        self.GetDTC(None)

    def OnHomeDashboard(self, event):
        self._go_to_page(self.dashboard_panel)

    def OnHomeServices(self, event):
        self._go_to_page(self.status)

    def OnHomeSensors(self, event):
        self._go_to_page(self.sensors_panel)

    def OnHomeGraphs(self, event):
        self._go_to_page(self.graph_panel)

    def OnHomeReadiness(self, event):
        self._go_to_page(self.tests_panel)

    def OnHomeDiagnostics(self, event):
        self._go_to_page(self.DTCpanel)

    def OnHomeVehicles(self, event):
        self._go_to_page(self.vehicle_profiles_panel)

    def OnHomeUpdate(self, event):
        if getattr(self, "update_check_in_progress", False):
            return
        self.update_check_in_progress = True
        self.sidebar_update_button.SetLabel("Checking…")

        def check_release():
            try:
                request = urllib.request.Request(
                    RELEASE_API_URL,
                    headers={"Accept": "application/vnd.github+json", "User-Agent": "pyOBD"},
                )
                with urllib.request.urlopen(request, timeout=8) as response:
                    release = json.loads(response.read().decode("utf-8"))
                wx.CallAfter(
                    self._finish_update_check,
                    release.get("tag_name", ""),
                    release.get("html_url", RELEASES_URL),
                    None,
                )
            except (OSError, ValueError, urllib.error.URLError) as error:
                wx.CallAfter(self._finish_update_check, "", RELEASES_URL, str(error))

        threading.Thread(target=check_release, daemon=True).start()

    @staticmethod
    def _version_numbers(version):
        numbers = [int(value) for value in re.findall(r"\d+", str(version))[:3]]
        return tuple((numbers + [0, 0, 0])[:3])

    def _finish_update_check(self, latest_version, release_url, error):
        try:
            if not self.frame or self.frame.IsBeingDeleted():
                return
        except RuntimeError:
            return
        self.update_check_in_progress = False
        self.sidebar_update_button.SetLabel("Update")
        if error:
            wx.MessageBox(
                f"Unable to check for updates.\n\n{error}",
                "pyOBD Update", wx.OK | wx.ICON_ERROR,
            )
            return
        if not latest_version:
            wx.MessageBox(
                "No published release was found.",
                "pyOBD Update", wx.OK | wx.ICON_INFORMATION,
            )
            return
        if self._version_numbers(latest_version) > self._version_numbers(APP_VERSION):
            if wx.MessageBox(
                f"pyOBD {latest_version} is available. Open the download page?",
                "Update Available", wx.YES_NO | wx.ICON_INFORMATION,
            ) == wx.YES:
                webbrowser.open(release_url)
            return
        wx.MessageBox(
            f"pyOBD {APP_VERSION} is up to date.",
            "pyOBD Update", wx.OK | wx.ICON_INFORMATION,
        )

    def RefreshTests(self, event=None):
        self.tests_active_section = (
            "misfire" if self.tests_notebook.GetSelection() == 1 else "readiness"
        )
        self.tests_poll_cancelled = False
        self.tests_refresh_requested = True
        self.tests_status_label.SetLabel(
            "Reading misfire results…"
            if self.tests_active_section == "misfire"
            else "Reading monitor status…"
        )
        self.tests_status_label.SetForegroundColour(self.theme.warning)
        if self.tests_active_section == "readiness":
            for count in self.tests_summary_labels.values():
                count.SetLabel("…")
        self.RefreshTestsButton.Enable(False)
        if self.senprod and self.senprod.is_alive():
            self.senprod.wake()

    def OnTestsPageChanged(self, event):
        self.tests_active_section = "misfire" if event.GetSelection() == 1 else "readiness"
        is_readiness = self.tests_active_section == "readiness"
        self.tests_summary_panel.Show(is_readiness)
        self.tests_help_label.SetLabel(
            "Readiness shows which emissions monitors have completed. Clearing codes resets readiness."
            if is_readiness
            else "Mode 06 misfire results are shown only for cylinder monitors supported by the vehicle."
        )
        self.tests_panel.Layout()
        if self.senprod and self.senprod.is_alive():
            self.RefreshTests()
        event.Skip()


    def sensor_control_on(self):  # after connection enable few buttons
        self.settingmenu.Enable(ID_CONFIG, False)
        self.settingmenu.Enable(ID_RESET, False)
        self.settingmenu.Enable(ID_DISCONNECT, True)
        self.dtcmenu.Enable(ID_GETC, True)
        self.dtcmenu.Enable(ID_CLEAR, True)
        self.GetDTCButton.Enable(True)
        self.ClearDTCButton.Enable(True)
        self.RefreshTestsButton.Enable(True)
        self.sensor_record_button.Enable(True)
        self.tests_status_label.SetLabel("Ready to check monitors")
        self.tests_status_label.SetForegroundColour(self.theme.muted)
        self._set_graph_connection_state(True)
        if self.dtc.GetItemCount() == 0:
            self.dtc_status_label.SetLabel("Ready to scan")
            self.dtc_empty_label.SetLabel("No scan results yet.")
            self.dtc_empty_label.Show()
        else:
            self.dtc_empty_label.Hide()
        self._update_sensor_selection_ui(connected=True)
        self.DTCpanel.Layout()
        self.tests_panel.Layout()

    def sensor_control_off(self):  # after disconnect disable few buttons
        self._stop_sensor_recording()
        self._reset_dashboard_values()
        self.dtcmenu.Enable(ID_GETC, False)
        self.dtcmenu.Enable(ID_CLEAR, False)
        self.settingmenu.Enable(ID_DISCONNECT, False)
        self.settingmenu.Enable(ID_CONFIG, True)
        self.settingmenu.Enable(ID_RESET, True)
        self.GetDTCButton.Enable(False)
        self.ClearDTCButton.Enable(False)
        self.dtc_status_label.SetLabel("Connect to scan vehicle")
        self.dtc_empty_label.SetLabel(
            "Disconnected — displayed diagnostic results may be out of date."
        )
        self.dtc_empty_label.Show()
        self.RefreshTestsButton.Enable(False)
        self.sensor_record_button.Enable(False)
        self.tests_status_label.SetLabel("Connect to check monitors")
        self.tests_status_label.SetForegroundColour(self.theme.muted)
        for count in self.tests_summary_labels.values():
            count.SetLabel("—")
        self._set_graph_connection_state(False)
        self._update_sensor_selection_ui(connected=False)
        self.DTCpanel.Layout()
        self.tests_panel.Layout()
        # http://pyserial.sourceforge.net/                                                    empty function
        # EVT_LIST_ITEM_ACTIVATED(self.sensors,self.sensor_id, lambda : None)




    def build_sensor_page(self):
        tID = wx.NewIdRef(count=1)
        self.sensor_id = tID
        self.sensor_rows = []
        self.sensor_visible_indices = []
        self.sensor_view_by_source = {}
        self.sensor_selected_sources = set()
        self._rebuilding_sensor_list = False
        self.sensor_filter_timer = None
        self.sensor_record_file = None
        self.sensor_record_writer = None
        self.sensor_record_sources = set()
        self.sensor_record_started_at = None
        self.sensor_record_sample_count = 0
        self.sensor_record_flush_count = 0
        self.sensor_record_session = None

        self.sensors_panel = wx.Panel(self.nb)
        self.sensors_panel.SetBackgroundColour(self.theme.window)

        toolbar_panel = wx.Panel(self.sensors_panel)
        toolbar_panel.SetBackgroundColour(self.theme.surface)
        toolbar_root = wx.BoxSizer(wx.VERTICAL)
        status_row = wx.BoxSizer(wx.HORIZONTAL)
        toolbar = wx.BoxSizer(wx.HORIZONTAL)

        guidance = wx.StaticText(
            toolbar_panel,
            label="Select one or more PIDs to record or add to a graph.",
        )
        guidance.SetForegroundColour(self.theme.muted)
        self.sensor_count_label = wx.StaticText(toolbar_panel, label="Waiting for vehicle data")
        self.sensor_count_label.SetForegroundColour(self.theme.muted)
        self.sensor_selection_label = wx.StaticText(toolbar_panel, label="0 selected")
        self.sensor_selection_label.SetForegroundColour(self.theme.accent)
        self.sensor_selection_label.SetFont(self.theme.font(10, bold=True))
        self.sensor_record_status_label = wx.StaticText(toolbar_panel, label="")
        self.sensor_record_status_label.SetForegroundColour(self.theme.muted)
        self.sensor_record_status_label.Hide()

        status_row.Add(guidance, 1, wx.ALIGN_CENTER_VERTICAL)
        status_row.Add(self.sensor_count_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 16)
        status_row.Add(self.sensor_selection_label, 0, wx.ALIGN_CENTER_VERTICAL)

        self.sensor_search = wx.SearchCtrl(toolbar_panel, style=wx.TE_PROCESS_ENTER)
        self.sensor_search.SetDescriptiveText("Search PID or sensor")
        self.sensor_search.ShowCancelButton(True)
        self.sensor_search.SetMinSize((280, 36))
        self.sensor_clear_button = ModernButton(
            toolbar_panel, "Clear Selection", self.theme, variant="ghost", size=(120, 36)
        )
        self.sensor_add_graph_button = ModernButton(
            toolbar_panel, "Add to Graph", self.theme, variant="primary", size=(118, 36)
        )
        self.sensor_add_graph_button.SetToolTip("Add selected PIDs to Graphs")
        self.sensor_record_button = ModernButton(
            toolbar_panel, "Record Selected", self.theme, variant="success", size=(126, 36)
        )
        self.sensor_record_button.SetToolTip("Record selected PIDs to CSV")

        toolbar.Add(self.sensor_search, 1, wx.RIGHT, 12)
        toolbar.Add(self.sensor_record_status_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 12)
        toolbar.Add(self.sensor_clear_button, 0, wx.RIGHT, 8)
        toolbar.Add(self.sensor_record_button, 0, wx.RIGHT, 8)
        toolbar.Add(self.sensor_add_graph_button, 0)
        toolbar_root.Add(status_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 10)
        toolbar_root.Add(toolbar, 0, wx.EXPAND | wx.ALL, 10)
        toolbar_panel.SetSizer(toolbar_root)

        self.sensor_empty_label = wx.StaticText(
            self.sensors_panel,
            label="Connect to a vehicle to view supported live data.",
        )
        self.sensor_empty_label.SetForegroundColour(self.theme.muted)
        self.sensor_empty_label.SetFont(self.theme.font(11))

        self.sensors = self.MyListCtrl(
            self.sensors_panel,
            tID,
            style=wx.LC_REPORT | wx.BORDER_NONE | wx.LC_HRULES,
        )
        self.sensors.InsertColumn(0, "PID", width=100)
        self.sensors.InsertColumn(1, "Sensor", format=wx.LIST_FORMAT_LEFT, width=420)
        self.sensors.InsertColumn(2, "Value", format=wx.LIST_FORMAT_RIGHT, width=220)

        root = wx.BoxSizer(wx.VERTICAL)
        root.AddSpacer(8)
        root.Add(toolbar_panel, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 20)
        root.Add(self.sensor_empty_label, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 20)
        root.Add(self.sensors, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 20)
        self.sensors_panel.SetSizer(root)

        self.sensor_search.Bind(wx.EVT_TEXT, self._schedule_sensor_filter)
        self.sensor_clear_button.Bind(wx.EVT_BUTTON, self._clear_sensor_selection)
        self.sensor_add_graph_button.Bind(wx.EVT_BUTTON, self._add_selected_sensors_to_graph)
        self.sensor_record_button.Bind(wx.EVT_BUTTON, self._toggle_sensor_recording)
        self.sensors.Bind(wx.EVT_LIST_ITEM_SELECTED, self._on_sensor_selected)
        self.sensors.Bind(wx.EVT_LIST_ITEM_DESELECTED, self._on_sensor_deselected)
        self.sensor_record_timer = wx.Timer(self.sensors_panel)
        self.sensors_panel.Bind(
            wx.EVT_TIMER, self._update_sensor_recording_status, self.sensor_record_timer
        )
        self._update_sensor_selection_ui()
        self.nb.AddPage(self.sensors_panel, "Sensors")

    def _toggle_sensor_recording(self, event=None):
        if self.sensor_record_file:
            self._stop_sensor_recording()
            return

        self._capture_sensor_selection()
        selected_sources = {
            source_index
            for source_index in self.sensor_selected_sources
            if 0 <= source_index < len(self.sensor_rows)
        }
        if not selected_sources:
            wx.MessageBox(
                "Select one or more PIDs first.",
                "Live Data Recording",
                wx.OK | wx.ICON_INFORMATION,
            )
            return

        default_name = datetime.datetime.now().strftime("Session %b %d, %Y %I-%M %p")
        dialog = wx.TextEntryDialog(
            self.frame,
            "Name this Live Data recording.",
            "New recorded session",
            default_name,
        )
        try:
            if dialog.ShowModal() != wx.ID_OK or not dialog.GetValue().strip():
                return
            session_name = dialog.GetValue().strip()
        finally:
            dialog.Destroy()

        try:
            path, self.sensor_record_session = self._begin_recording_session(session_name)
            self.sensor_record_file = open(path, "w", newline="", encoding="utf-8")
            self.sensor_record_writer = csv.writer(self.sensor_record_file)
            self.sensor_record_writer.writerow(
                ["Timestamp", "Elapsed Seconds", "PID", "Sensor", "Value"]
            )
        except OSError as error:
            if self.sensor_record_file:
                self.sensor_record_file.close()
            self.sensor_record_file = None
            self.sensor_record_writer = None
            self._discard_recording_session(self.sensor_record_session)
            self.sensor_record_session = None
            wx.MessageBox(
                f"Unable to create the recording file.\n\n{error}",
                "Live Data Recording",
                wx.OK | wx.ICON_ERROR,
            )
            return

        self.sensor_record_sources = selected_sources
        self.sensor_record_started_at = time.monotonic()
        self.sensor_record_sample_count = 0
        self.sensor_record_flush_count = 0
        self.sensor_record_button.SetLabel("Stop Recording")
        self.sensor_record_button.SetVariant("danger")
        self.sensor_record_button.SetToolTip("Stop and save recording")
        self.sensor_record_status_label.Show()
        self.sensor_record_timer.Start(500)
        self._update_sensor_recording_status()

    def _update_sensor_recording_status(self, event=None):
        if not self.sensor_record_file or self.sensor_record_started_at is None:
            return
        elapsed = max(0, int(time.monotonic() - self.sensor_record_started_at))
        hours, remainder = divmod(elapsed, 3600)
        minutes, seconds = divmod(remainder, 60)
        elapsed_text = (
            f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            if hours
            else f"{minutes:02d}:{seconds:02d}"
        )
        self.sensor_record_status_label.SetLabel(
            f"{elapsed_text}  •  {self.sensor_record_sample_count} samples"
        )
        self.sensors_panel.Layout()

    def _record_sensor_value(self, source_index):
        if (
            not self.sensor_record_writer
            or source_index not in self.sensor_record_sources
            or not 0 <= source_index < len(self.sensor_rows)
        ):
            return
        row = self.sensor_rows[source_index]
        try:
            self.sensor_record_writer.writerow([
                datetime.datetime.now().astimezone().isoformat(timespec="milliseconds"),
                f"{time.monotonic() - self.sensor_record_started_at:.3f}",
                row[0],
                row[1],
                row[2],
            ])
            self.sensor_record_sample_count += 1
            self.sensor_record_flush_count += 1
            if self.sensor_record_flush_count >= 25:
                self.sensor_record_file.flush()
                self.sensor_record_flush_count = 0
        except (OSError, ValueError) as error:
            self._stop_sensor_recording("Recording stopped: unable to write file")
            wx.MessageBox(
                f"Unable to continue the recording.\n\n{error}",
                "Live Data Recording",
                wx.OK | wx.ICON_ERROR,
            )

    def _stop_sensor_recording(self, status=None):
        if not self.sensor_record_file:
            return
        if self.sensor_record_timer.IsRunning():
            self.sensor_record_timer.Stop()
        recorded_file = self.sensor_record_file
        sample_count = self.sensor_record_sample_count
        duration_seconds = max(0, time.monotonic() - self.sensor_record_started_at)
        try:
            recorded_file.flush()
            recorded_file.close()
        except OSError:
            pass
        self.sensor_record_file = None
        self.sensor_record_writer = None
        self.sensor_record_sources.clear()
        self._finish_recording_session(
            self.sensor_record_session, sample_count, duration_seconds
        )
        self.sensor_record_session = None
        self.sensor_record_started_at = None
        self.sensor_record_flush_count = 0
        self.sensor_record_button.SetLabel("Record Selected")
        self.sensor_record_button.SetVariant("success")
        self.sensor_record_button.SetToolTip("Record selected PIDs to CSV")
        self.sensor_record_status_label.Show()
        self.sensor_record_status_label.SetLabel(
            status or f"Saved {sample_count} samples"
        )
        self._update_sensor_selection_ui()
        self.sensors_panel.Layout()

    def _schedule_sensor_filter(self, event=None):
        if self._shutdown_started:
            return
        if self.sensor_filter_timer and self.sensor_filter_timer.IsRunning():
            self.sensor_filter_timer.Stop()
        self.sensor_filter_timer = wx.CallLater(150, self._apply_sensor_filter)

    def _apply_sensor_filter(self):
        self.sensor_filter_timer = None
        if self._shutdown_started:
            return
        query = self.sensor_search.GetValue().strip().lower()
        self._capture_sensor_selection()

        self._rebuilding_sensor_list = True
        self.sensors.Freeze()
        self.sensors.DeleteAllItems()
        self.sensor_visible_indices = []
        self.sensor_view_by_source = {}
        for source_index, row in enumerate(self.sensor_rows):
            searchable = f"{row[0]} {row[1]}".lower()
            if query and query not in searchable:
                continue
            view_index = self.sensors.InsertItem(self.sensors.GetItemCount(), row[0])
            self.sensors.SetItem(view_index, 1, row[1])
            self.sensors.SetItem(view_index, 2, row[2])
            self.sensor_visible_indices.append(source_index)
            self.sensor_view_by_source[source_index] = view_index
        self.sensor_selected_sources.intersection_update(self.sensor_visible_indices)
        for view_index, source_index in enumerate(self.sensor_visible_indices):
            if source_index in self.sensor_selected_sources:
                self.sensors.Select(view_index)
        self.sensors.Thaw()
        self._rebuilding_sensor_list = False

        visible = len(self.sensor_visible_indices)
        total = len(self.sensor_rows)
        self.sensor_count_label.SetLabel(f"{visible} of {total} PIDs" if total else "Waiting for vehicle data")
        self._update_sensor_selection_ui()

    def _selected_sensor_rows(self):
        selected = []
        index = self.sensors.GetFirstSelected()
        while index != wx.NOT_FOUND:
            selected.append(index)
            index = self.sensors.GetNextSelected(index)
        return selected

    def _capture_sensor_selection(self):
        for view_index in self._selected_sensor_rows():
            if 0 <= view_index < len(self.sensor_visible_indices):
                self.sensor_selected_sources.add(self.sensor_visible_indices[view_index])

    def _clear_sensor_selection(self, event=None):
        self._rebuilding_sensor_list = True
        try:
            for view_index in self._selected_sensor_rows():
                self.sensors.Select(view_index, False)
            self.sensor_selected_sources.clear()
        finally:
            self._rebuilding_sensor_list = False
        self._update_sensor_selection_ui()

    def _update_sensor_selection_ui(self, connected=None):
        selected = len(self.sensor_selected_sources)
        if connected is None:
            connected = bool(self.senprod and self.senprod.is_alive())
        visible = len(self.sensor_visible_indices)
        total = len(self.sensor_rows)

        self.sensor_selection_label.SetLabel(
            f"{selected} selected" if selected != 1 else "1 selected"
        )
        self.sensor_clear_button.Enable(selected > 0)
        self.sensor_add_graph_button.Enable(selected > 0)
        if not self.sensor_record_file:
            self.sensor_record_button.Enable(connected and selected > 0)

        if not connected:
            self.sensor_empty_label.SetLabel("Disconnected — displayed values are not updating.")
            self.sensor_empty_label.Show()
        elif total and not visible:
            self.sensor_empty_label.SetLabel("No PIDs match the current search.")
            self.sensor_empty_label.Show()
        elif not total:
            self.sensor_empty_label.SetLabel(
                "Waiting for supported PIDs…"
                if connected
                else "Connect to a vehicle to view supported live data."
            )
            self.sensor_empty_label.Show()
        else:
            self.sensor_empty_label.Hide()
        self.sensors_panel.Layout()

    def _on_sensor_selected(self, event):
        if not self._rebuilding_sensor_list:
            view_index = event.GetIndex()
            if 0 <= view_index < len(self.sensor_visible_indices):
                self.sensor_selected_sources.add(self.sensor_visible_indices[view_index])
            self._update_sensor_selection_ui()
        event.Skip()

    def _on_sensor_deselected(self, event):
        if not self._rebuilding_sensor_list:
            view_index = event.GetIndex()
            if 0 <= view_index < len(self.sensor_visible_indices):
                self.sensor_selected_sources.discard(self.sensor_visible_indices[view_index])
            self._update_sensor_selection_ui()
        event.Skip()

    def _add_selected_sensors_to_graph(self, event=None):
        self._capture_sensor_selection()
        selected_sources = {
            source_index
            for source_index in self.sensor_selected_sources
            if 0 <= source_index < len(self.sensor_rows)
        }
        if not selected_sources:
            wx.MessageBox(
                "Select one or more PIDs first.",
                "Live Data",
                wx.OK | wx.ICON_INFORMATION,
            )
            return

        selected_pids = {
            self.sensor_rows[source_index][0].strip().upper()
            for source_index in selected_sources
        }

        catalog_indices = [
            index
            for index, command in enumerate(self.graph_command_catalog)
            if command.command.decode(errors="ignore").upper() in selected_pids
        ]
        if not catalog_indices:
            wx.MessageBox(
                "The selected PID does not provide graph-compatible numeric data.",
                "Live Data",
                wx.OK | wx.ICON_INFORMATION,
            )
            return
        self._add_graph_commands_by_catalog_indices(catalog_indices)

        """
        HOFFSET_LIST = 0
        # tID = wx.NewId()
        tID = wx.NewIdRef(count=1)
        self.sensor_id = tID

        self.sensors_panel = wx.Panel(self.nb, -1)

        self.sensors = self.MyListCtrl(self.sensors_panel, tID, pos=wx.Point(0, HOFFSET_LIST),
                                     style=
                                     wx.LC_REPORT |
                                     wx.SUNKEN_BORDER |
                                     wx.LC_HRULES |
                                     wx.LC_SINGLE_SEL)

        self.sensors.InsertColumn(0, "PID", width=70)
        self.sensors.InsertColumn(1, "Sensor", format=wx.LIST_FORMAT_LEFT, width=320)
        self.sensors.InsertColumn(2, "Value")
        #self.sensors.SetSize(0, 0, 800, 1500)
        """
        """
        ####################################################################
        # This little bit of magic keeps the list the same size as the frame
        def OnPSize(e, win=panel):
            self.sensors_panel.SetSize(e.GetSize())
            self.sensors.SetSize(e.GetSize())

            w, h = self.frame.GetSize()

            self.sensors.SetSize(0, HOFFSET_LIST, w - 10, h - 35)

        self.sensors_panel.Bind(wx.EVT_SIZE, OnPSize)
        ####################################################################
        """
        """
        ####################################################################
        # This little bit of magic keeps the list the same size as the frame
        def OnPSize(e, win=self.sensors_panel):
            self.sensors_panel.SetSize(e.GetSize())
            self.sensors.SetSize(e.GetSize())
            w, h = self.frame.GetSize()
            # I have no idea where 70 comes from
            # self.dtc.SetDimensions(0,HOFFSET_LIST, w-16 , h - 70 )
            self.sensors.SetSize(0, HOFFSET_LIST, w - 16, h - 70)

        self.sensors_panel.Bind(wx.EVT_SIZE, OnPSize)
        ####################################################################


        self.nb.AddPage(self.sensors_panel, "Sensors")
        """
    def build_freezeframe_page(self):
        tID = wx.NewIdRef(count=1)
        self.freezeframe_id = tID
        self.freezeframe = self.MyListCtrl(self.nb, tID, style=
                                     wx.LC_REPORT |
                                     wx.BORDER_NONE |
                                     wx.LC_HRULES |
                                     wx.LC_SINGLE_SEL)
        self.freezeframe.InsertColumn(0, "PID", width=70)
        self.freezeframe.InsertColumn(1, "Sensor", format=wx.LIST_FORMAT_LEFT, width=320)
        self.freezeframe.InsertColumn(2, "Value", width=60)
        self.nb.AddPage(self.freezeframe, "Freeze frame")


        """
        """
        """
        HOFFSET_LIST = 0
        # tID = wx.NewId()
        tID = wx.NewIdRef(count=1)
        self.freezeframe_id = tID
        self.freezeframe_panel = wx.Panel(self.nb, -1)

        self.freezeframe = self.MyListCtrl(self.freezeframe_panel, tID, pos=wx.Point(0, HOFFSET_LIST),
                                       style=
                                       wx.LC_REPORT |
                                       wx.SUNKEN_BORDER |
                                       wx.LC_HRULES |
                                       wx.LC_SINGLE_SEL)

        self.freezeframe.InsertColumn(0, "PID", width=70)
        self.freezeframe.InsertColumn(1, "Sensor", format=wx.LIST_FORMAT_LEFT, width=320)
        self.freezeframe.InsertColumn(2, "Value", width=60)
        #self.freezeframe.SetSize(0, 0, 800, 1500)

        ####################################################################
        # This little bit of magic keeps the list the same size as the frame
        def OnPSize(e, win=self.freezeframe_panel):
            self.freezeframe_panel.SetSize(e.GetSize())
            self.freezeframe.SetSize(e.GetSize())

            w, h = self.frame.GetSize()

            self.freezeframe.SetSize(0, HOFFSET_LIST, w - 16, h - 70)

        self.freezeframe_panel.Bind(wx.EVT_SIZE, OnPSize)
        ####################################################################

        self.nb.AddPage(self.freezeframe_panel, "Freeze frame")
        """

    def build_DTC_page(self):
        """
        HOFFSET_LIST = 70
        tID = wx.NewIdRef(count=1)
        self.dtc = self.MyListCtrl(self.nb, tID, pos=wx.Point(0, HOFFSET_LIST), style=
        wx.LC_REPORT |
        wx.SUNKEN_BORDER |
        wx.LC_HRULES |
        wx.LC_SINGLE_SEL)
        self.dtc.InsertColumn(0, "Code", width=100)
        self.dtc.InsertColumn(1, "Status", width=100)
        self.dtc.InsertColumn(2, "Trouble code")
        self.GetDTCButton = wx.Button(self.dtc, -1, "Get DTC", wx.Point(15, 0))
        self.ClearDTCButton = wx.Button(self.dtc, -1, "Clear DTC", wx.Point(100, 0))

        # bind functions to button click action
        self.dtc.Bind(wx.EVT_BUTTON, self.GetDTC, self.GetDTCButton)
        self.dtc.Bind(wx.EVT_BUTTON, self.QueryClear, self.ClearDTCButton)
        self.nb.AddPage(self.dtc, "DTC")


        """
        
        tID = wx.NewIdRef(count=1)
        self.DTCpanel = wx.Panel(self.nb, -1)
        self.DTCpanel.SetBackgroundColour(self.theme.window)
        toolbar_panel = wx.Panel(self.DTCpanel)
        toolbar_panel.SetBackgroundColour(self.theme.surface)
        self.GetDTCButton = ModernButton(
            toolbar_panel, "Scan codes", self.theme, variant="primary"
        )
        self.ClearDTCButton = ModernButton(
            toolbar_panel, "Clear codes", self.theme, variant="danger"
        )
        self.LookupDTCButton = ModernButton(
            toolbar_panel, "Code lookup", self.theme, variant="ghost"
        )
        self.dtc_status_label = wx.StaticText(
            toolbar_panel, label="Connect to scan vehicle"
        )
        self.dtc_status_label.SetForegroundColour(self.theme.muted)

        toolbar_root = wx.BoxSizer(wx.VERTICAL)
        status_row = wx.BoxSizer(wx.HORIZONTAL)
        toolbar = wx.BoxSizer(wx.HORIZONTAL)

        guidance = wx.StaticText(
            toolbar_panel,
            label="Scan the vehicle for emissions-related diagnostic trouble codes.",
        )
        guidance.SetForegroundColour(self.theme.muted)
        status_row.Add(guidance, 1, wx.ALIGN_CENTER_VERTICAL)
        status_row.Add(self.dtc_status_label, 0, wx.ALIGN_CENTER_VERTICAL)

        self.GetDTCButton.Bind(wx.EVT_BUTTON, self.GetDTC)
        self.ClearDTCButton.Bind(wx.EVT_BUTTON, self.QueryClear)
        self.LookupDTCButton.Bind(wx.EVT_BUTTON, self.CodeLookup)

        self.dtc = self.MyListCtrl(
            self.DTCpanel,
            tID,
            style=wx.LC_REPORT | wx.BORDER_NONE | wx.LC_HRULES | wx.LC_SINGLE_SEL,
        )

        self.dtc.InsertColumn(0, "Code", width=110)
        self.dtc.InsertColumn(1, "Category", width=140)
        self.dtc.InsertColumn(2, "Description", width=520)

        toolbar.Add(self.GetDTCButton, 0, wx.RIGHT, 8)
        toolbar.Add(self.LookupDTCButton, 0, wx.RIGHT, 8)
        toolbar.AddStretchSpacer()
        toolbar.Add(self.ClearDTCButton, 0)
        toolbar_root.Add(status_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 10)
        toolbar_root.Add(toolbar, 0, wx.EXPAND | wx.ALL, 10)
        toolbar_panel.SetSizer(toolbar_root)

        summary = wx.BoxSizer(wx.HORIZONTAL)
        self.dtc_summary_labels = {}
        for category, colour in (
            ("Stored", self.theme.danger),
            ("Pending", self.theme.warning),
            ("Permanent", self.theme.accent),
        ):
            card = wx.Panel(self.DTCpanel, style=wx.BORDER_SIMPLE)
            card.SetBackgroundColour(self.theme.surface)
            card.SetMinSize((-1, 54))
            card_sizer = wx.BoxSizer(wx.HORIZONTAL)
            name = wx.StaticText(card, label=category)
            name.SetForegroundColour(self.theme.muted)
            count = wx.StaticText(card, label="0")
            count.SetForegroundColour(colour)
            count.SetFont(self.theme.font(16, bold=True))
            card_sizer.Add(name, 0, wx.ALIGN_CENTER_VERTICAL)
            card_sizer.AddStretchSpacer()
            card_sizer.Add(count, 0, wx.ALIGN_CENTER_VERTICAL)
            card.SetSizer(card_sizer)
            summary.Add(card, 1, wx.EXPAND | wx.RIGHT, 10 if category != "Permanent" else 0)
            card_sizer.AddSpacer(14)
            card_sizer.PrependSpacer(14)
            self.dtc_summary_labels[category] = count

        self.dtc_empty_label = wx.StaticText(
            self.DTCpanel,
            label="Connect to a vehicle to scan diagnostic trouble codes.",
        )
        self.dtc_empty_label.SetForegroundColour(self.theme.muted)
        self.dtc_empty_label.SetFont(self.theme.font(11))

        root = wx.BoxSizer(wx.VERTICAL)
        root.AddSpacer(8)
        root.Add(toolbar_panel, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 20)
        root.Add(summary, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 20)
        root.Add(self.dtc_empty_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 20)
        root.Add(self.dtc, 1, wx.EXPAND | wx.ALL, 20)
        self.DTCpanel.SetSizer(root)

        self.nb.AddPage(self.DTCpanel, "DTC")

    def TraceDebug(self, level, msg):
        if self.DEBUGLEVEL <= level:
            self.trace.Append([str(level), msg])

    def OnInit(self):
        self.ThreadControl = 0  # say thread what to do
        self.active_polling_page = "idle"
        self._shutdown_started = False
        self._sidebar_open = False
        self.COMPORT = 0
        self.senprod = None
        self.DEBUGLEVEL = 0  # debug everything

        # tID = wx.NewId()
        tID = wx.NewIdRef(count=1)
        self.tID = tID
        # read settings from file
        self.config = configparser.RawConfigParser()

        # print platform.system()
        # print platform.mac_ver()[]

        self.configfilepath = user_config_path()
        if self.config.read(self.configfilepath) == []:
            self.COMPORT = "AUTO"
            self.CONNECTION_TYPE = "AUTO"
            self.CONNECTION_TARGET = ""
            self.RECONNATTEMPTS = 5
            self.SERTIMEOUT = 1
            self.BAUDRATE = "AUTO"
            self.FAST = "NORMAL"
            self.MEASUREMENT_SYSTEM = "IMPERIAL"
        else:
            try:
                self.COMPORT = self.config.get("pyOBD", "COMPORT")
                self.CONNECTION_TYPE = self.config.get("pyOBD", "CONNECTION_TYPE", fallback="")
                self.CONNECTION_TARGET = self.config.get("pyOBD", "CONNECTION_TARGET", fallback="")
                self.RECONNATTEMPTS = self.config.getint("pyOBD", "RECONNATTEMPTS")
                self.SERTIMEOUT = self.config.get("pyOBD", "SERTIMEOUT")
                self.BAUDRATE = self.config.get("pyOBD", "BAUDRATE")
                self.FAST = self.config.get("pyOBD", "FAST")
                self.MEASUREMENT_SYSTEM = self.config.get("pyOBD", "MEASUREMENT_SYSTEM", fallback="IMPERIAL").upper()
            except Exception as e:
                print(e)
                self.COMPORT = "AUTO"
                self.CONNECTION_TYPE = "AUTO"
                self.CONNECTION_TARGET = ""
                self.RECONNATTEMPTS = 5
                self.SERTIMEOUT = 5
                self.BAUDRATE = "AUTO"
                self.FAST = "FAST"
                self.MEASUREMENT_SYSTEM = "IMPERIAL"

        if self.MEASUREMENT_SYSTEM not in ["IMPERIAL", "METRIC"]:
            self.MEASUREMENT_SYSTEM = "IMPERIAL"

        self.CONNECTION_TYPE, self.CONNECTION_TARGET = self._infer_connection_from_comport(
            self.CONNECTION_TYPE,
            self.CONNECTION_TARGET,
            self.COMPORT,
        )

        self.theme = AppTheme()
        self.frame = wx.Frame(None, -1, f"pyOBD v{APP_VERSION} - Modified by FareBrothers,LLC")
        ico = wx.Icon(resource_path('assets/pyobd.png'), wx.BITMAP_TYPE_PNG)
        self.frame.SetIcon(ico)

        EVT_RESULT(self, self.OnResult, EVT_RESULT_ID)
        EVT_RESULT(self, self.OnDebug, EVT_DEBUG_ID)
        EVT_RESULT(self, self.OnDtc, EVT_DTC_ID)
        EVT_RESULT(self, self.OnStatus, EVT_STATUS_ID)
        EVT_RESULT(self, self.OnTests, EVT_TESTS_ID)
        EVT_RESULT(self, self.OnGraphValue, EVT_GRAPH_VALUE_ID)
        EVT_RESULT(self, self.OnGraph, EVT_GRAPH_ID)
        EVT_RESULT(self, self.OnClose, EVT_CLOSE_ID)
        EVT_RESULT(self, self.InsertFreezeframeRow, EVT_INSERT_FREEZEFRAME_ROW_ID)
        EVT_RESULT(self, self.OnFreezeframeResult, EVT_FREEZEFRAME_RESULT_ID)
        EVT_RESULT(self, self.OnDashboardValues, EVT_DASHBOARD_VALUES_ID)

        # Main application shell and page container.
        self.shell_panel = wx.Panel(self.frame)
        self.shell_panel.SetBackgroundColour(self.theme.window)
        self.content_panel = wx.Panel(self.shell_panel)
        self.content_panel.SetBackgroundColour(self.theme.window)
        self.nb = wx.Simplebook(self.content_panel)

        self.status = self.MyListCtrl(self.nb, tID, style=wx.LC_REPORT | wx.BORDER_NONE)
        self.status.InsertColumn(0, "Description", width=200)
        self.status.InsertColumn(1, "Value")
        self.status.Append(["Link State", "Disconnnected"])
        self.status.Append(["Protocol", "----"])
        self.status.Append(["Cable version", "----"])
        self.status.Append(["COM port", "----"])
        self.status.Append(["VIN number", "----"])
        self.status.Append(["ELM voltage", "----"])

        self.nb.AddPage(self.status, "Status")

        self.tests_refresh_requested = False
        self.tests_active_section = "readiness"
        self.tests_poll_cancelled = True
        self.tests_panel = wx.Panel(self.nb)
        self.tests_panel.SetBackgroundColour(self.theme.window)
        tests_root = wx.BoxSizer(wx.VERTICAL)
        toolbar_panel = wx.Panel(self.tests_panel)
        toolbar_panel.SetBackgroundColour(self.theme.surface)
        toolbar_root = wx.BoxSizer(wx.VERTICAL)
        tests_toolbar = wx.BoxSizer(wx.HORIZONTAL)
        self.tests_status_label = wx.StaticText(
            toolbar_panel, label="Connect to check monitors"
        )
        self.tests_status_label.SetForegroundColour(self.theme.muted)
        self.RefreshTestsButton = ModernButton(
            toolbar_panel, "Refresh", self.theme, variant="primary"
        )
        self.RefreshTestsButton.Enable(False)
        self.RefreshTestsButton.Bind(wx.EVT_BUTTON, self.RefreshTests)
        tests_toolbar.Add(self.tests_status_label, 1, wx.ALIGN_CENTER_VERTICAL)
        tests_toolbar.Add(self.RefreshTestsButton, 0)
        toolbar_root.Add(tests_toolbar, 0, wx.EXPAND | wx.ALL, 10)
        toolbar_panel.SetSizer(toolbar_root)

        self.tests_summary_panel = wx.Panel(self.tests_panel)
        self.tests_summary_panel.SetBackgroundColour(self.theme.window)
        tests_summary = wx.BoxSizer(wx.HORIZONTAL)
        self.tests_summary_labels = {}
        for category, colour in (
            ("Ready", self.theme.success),
            ("Not Ready", self.theme.warning),
            ("Unsupported", self.theme.muted),
        ):
            card = wx.Panel(self.tests_summary_panel, style=wx.BORDER_SIMPLE)
            card.SetBackgroundColour(self.theme.surface)
            card.SetMinSize((-1, 54))
            card_sizer = wx.BoxSizer(wx.HORIZONTAL)
            name = wx.StaticText(card, label=category)
            name.SetForegroundColour(self.theme.muted)
            count = wx.StaticText(card, label="—")
            count.SetForegroundColour(colour)
            count.SetFont(self.theme.font(16, bold=True))
            card_sizer.AddSpacer(14)
            card_sizer.Add(name, 0, wx.ALIGN_CENTER_VERTICAL)
            card_sizer.AddStretchSpacer()
            card_sizer.Add(count, 0, wx.ALIGN_CENTER_VERTICAL)
            card_sizer.AddSpacer(14)
            card.SetSizer(card_sizer)
            tests_summary.Add(
                card,
                1,
                wx.EXPAND | wx.RIGHT,
                10 if category != "Unsupported" else 0,
            )
            self.tests_summary_labels[category] = count
        self.tests_summary_panel.SetSizer(tests_summary)

        self.tests_help_label = wx.StaticText(
            self.tests_panel,
            label=(
                "Readiness shows which emissions monitors have completed. "
                "Mode 06 shows onboard test results when supported. "
                "Clearing diagnostic codes resets readiness."
            ),
        )
        self.tests_help_label.SetForegroundColour(self.theme.muted)

        self.tests_notebook = wx.Notebook(self.tests_panel)
        self.OBDTests = self.MyListCtrl(
            self.tests_notebook, wx.NewIdRef(), style=wx.LC_REPORT | wx.BORDER_NONE
        )
        self.OBDTests.InsertColumn(0, "Monitor", width=330)
        self.OBDTests.InsertColumn(1, "Supported", width=110)
        self.OBDTests.InsertColumn(2, "Status", width=140)
        for label in TEST_LABELS:
            self.OBDTests.Append([label, "—", "—"])

        self.misfire_tests = self.MyListCtrl(
            self.tests_notebook, wx.NewIdRef(), style=wx.LC_REPORT | wx.BORDER_NONE
        )
        self.misfire_tests.InsertColumn(0, "Monitor", width=330)
        self.misfire_tests.InsertColumn(1, "Mode 06 result", width=180)
        self.misfire_tests.Append(["Refresh to detect supported cylinder monitors", "—"])

        self.tests_notebook.AddPage(self.OBDTests, "Readiness")
        self.tests_notebook.AddPage(self.misfire_tests, "Misfire Results")
        self.tests_notebook.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.OnTestsPageChanged)
        tests_root.AddSpacer(8)
        tests_root.Add(toolbar_panel, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 20)
        tests_root.Add(self.tests_summary_panel, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 20)
        tests_root.Add(self.tests_help_label, 0, wx.LEFT | wx.RIGHT | wx.TOP | wx.BOTTOM, 20)
        tests_root.Add(self.tests_notebook, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 20)
        self.tests_panel.SetSizer(tests_root)
        self.nb.AddPage(self.tests_panel, "Readiness")




        self.build_sensor_page()
        self.build_DTC_page()
        self.build_freezeframe_page()
        #self.trace.Destroy()


        self.build_graph_page()
        self.trace = self.MyListCtrl(self.nb, tID, style=wx.LC_REPORT | wx.BORDER_NONE)
        self.trace.InsertColumn(0, "Level", width=40)
        self.trace.InsertColumn(1, "Message")
        self.nb.AddPage(self.trace, "Trace")
        self.TraceDebug(1, "Application started")
        self.about_panel = build_about_page(self.nb)
        self.build_home_page()
        self.build_dashboard_page()
        self.build_vehicle_profiles_page()
        self.build_sessions_page()

        self._build_sidebar()
        self._build_content_header()
        self._build_bottom_status_toolbar()
        self._set_bottom_status_defaults()

        content_sizer = wx.BoxSizer(wx.VERTICAL)
        content_sizer.Add(self.content_header, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 20)
        content_sizer.Add(self.nb, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 20)
        content_sizer.Add(self.bottom_toolbar, 0, wx.EXPAND)
        self.content_panel.SetSizer(content_sizer)

        shell_sizer = wx.BoxSizer(wx.HORIZONTAL)
        shell_sizer.Add(self.sidebar_panel, 0, wx.EXPAND)
        shell_sizer.Add(self.content_panel, 1, wx.EXPAND)
        self.sidebar_panel.Show(self._sidebar_open)
        self.shell_panel.SetSizer(shell_sizer)

        self.main_sizer = wx.BoxSizer(wx.VERTICAL)
        self.main_sizer.Add(self.shell_panel, 1, wx.EXPAND)
        self.frame.SetSizer(self.main_sizer)

        self._apply_touch_friendly_style()




        # Setting up the menu.
        self.filemenu = wx.Menu()
        self.filemenu.Append(ID_EXIT, "E&xit", " Terminate the program")

        self.settingmenu = wx.Menu()
        self.settingmenu.Append(ID_CONFIG, "Configure", " Configure pyOBD")
        self.settingmenu.Append(ID_RESET, "Connect", " Reopen and connect to device")
        self.settingmenu.Append(ID_DISCONNECT, "Disconnect", "Close connection to device")

        self.dtcmenu = wx.Menu()
        # tady toto nastavi automaticky tab DTC a provede akci
        self.dtcmenu.Append(ID_GETC, "Get DTCs", " Get DTC Codes")
        self.dtcmenu.Append(ID_CLEAR, "Clear DTC", " Clear DTC Codes")
        self.dtcmenu.Append(ID_LOOK, "Code Lookup", " Lookup DTC Codes")

        self.helpmenu = wx.Menu()

        self.helpmenu.Append(ID_HELP_ABOUT, "About this program", " Get DTC Codes")
        self.helpmenu.Append(ID_HELP_VISIT, "Visit program homepage", " Lookup DTC Codes")
        self.helpmenu.Append(ID_HELP_ORDER, "Order OBD-II interface", " Clear DTC Codes")

        # Creating the menubar.
        self.menuBar = wx.MenuBar()
        self.menuBar.Append(self.filemenu, "&File")  # Adding the "filemenu" to the MenuBar
        self.menuBar.Append(self.settingmenu, "&OBD-II")
        self.menuBar.Append(self.dtcmenu, "&Trouble codes")
        self.menuBar.Append(self.helpmenu, "&Help")

        self.frame.SetMenuBar(self.menuBar)  # Adding the MenuBar to the Frame content.

        self.frame.Bind(wx.EVT_MENU, self.OnExitMenu, id=ID_EXIT)
        self.frame.Bind(wx.EVT_MENU, self.QueryClear, id=ID_CLEAR)
        self.frame.Bind(wx.EVT_MENU, self.Configure, id=ID_CONFIG)
        self.frame.Bind(wx.EVT_MENU, self.OpenPort, id=ID_RESET)
        self.frame.Bind(wx.EVT_MENU, self.OnDisconnect, id=ID_DISCONNECT)
        self.frame.Bind(wx.EVT_MENU, self.GetDTC, id=ID_GETC)
        self.frame.Bind(wx.EVT_MENU, self.CodeLookup, id=ID_LOOK)
        self.frame.Bind(wx.EVT_MENU, self.OnHelpAbout, id=ID_HELP_ABOUT)
        self.frame.Bind(wx.EVT_MENU, self.OnHelpVisit, id=ID_HELP_VISIT)
        self.frame.Bind(wx.EVT_MENU, self.OnHelpOrder, id=ID_HELP_ORDER)
        self.frame.Bind(wx.EVT_CLOSE, self.OnWindowClose)

        self.SetTopWindow(self.frame)

        self.frame.SetSize((1180, 900))
        self.frame.SetMinSize((960, 700))
        self.frame.Centre()
        self._go_to_page(self.home_panel)
        self.frame.Show(True)
        self.sensor_control_off() # ??? JURE POLJSAK


        return True

    def OnHelpVisit(self, event):
        webbrowser.open("https://github.com/alexfare/pyobd")

    def OnHelpOrder(self, event):
        webbrowser.open("https://www.google.com/search?q=elm327+obd2+scanner")

    def OnHelpAbout(self, event):
        Text = ABOUT_DIALOG_TEXT

        # HelpAboutDlg = wx.Dialog(self.frame, id, title="About")

        # box  = wx.BoxSizer(wx.HORIZONTAL)
        # box.Add(wx.StaticText(reconnectPanel,-1,Text,pos=(0,0),size=(200,200)))
        # box.Add(wx.Button(HelpAboutDlg,wx.ID_OK),0)
        # box.Add(wx.Button(HelpAboutDlg,wx.ID_CANCEL),1)

        # HelpAboutDlg.SetSizer(box)
        # HelpAboutDlg.SetAutoLayout(True)
        # sizer.Fit(HelpAboutDlg)
        # HelpAboutDlg.ShowModal()

        self.HelpAboutDlg = wx.MessageDialog(self.frame, Text, 'About pyOBD', wx.OK | wx.ICON_INFORMATION)
        self.HelpAboutDlg.ShowModal()
        self.HelpAboutDlg.Destroy()

    def OnResult(self, event):
        data = event.data
        updates = data if data and isinstance(data[0], (list, tuple)) else [data]
        query_active = bool(self.sensor_search.GetValue().strip())
        filter_changed = False

        self.sensors.Freeze()
        try:
            for source_index, column, value in updates:
                while len(self.sensor_rows) <= source_index:
                    self.sensor_rows.append(["", "", ""])
                if source_index not in self.sensor_view_by_source and not query_active:
                    view_index = self.sensors.InsertItem(self.sensors.GetItemCount(), "")
                    self.sensor_visible_indices.append(source_index)
                    self.sensor_view_by_source[source_index] = view_index

                if isinstance(value, bytes):
                    value = value.decode(errors="ignore")
                value = str(value)
                changed = self.sensor_rows[source_index][column] != value
                self.sensor_rows[source_index][column] = value
                if column == 2:
                    self._record_sensor_value(source_index)
                if query_active and column in (0, 1) and changed:
                    filter_changed = True
                elif changed and source_index in self.sensor_view_by_source:
                    self.sensors.SetItem(
                        self.sensor_view_by_source[source_index], column, value
                    )
        finally:
            self.sensors.Thaw()

        if filter_changed:
            self._schedule_sensor_filter()
        self.sensor_count_label.SetLabel(
            f"{len(self.sensor_visible_indices)} of {len(self.sensor_rows)} PIDs"
        )
        if not query_active and self.sensor_empty_label.IsShown() and self.sensor_rows:
            self._update_sensor_selection_ui()

    def OnFreezeframeResult(self, event):
        self.freezeframe.SetItem(event.data[0], event.data[1], event.data[2])

    def OnStatus(self, event):
        if event.data[0] == 666:  # signal, that connection falied
            self.sensor_control_off()
            self._set_bottom_status_defaults()
        else:
            self.status.SetItem(event.data[0], event.data[1], event.data[2])
            self._update_bottom_status(event.data[0], event.data[2])
            if event.data[0] == 4:
                self._activate_vehicle_profile_for_vin(event.data[2])
            # Drive UI control state from actual connection state notifications.
            if event.data[0] == 0:
                state_text = str(event.data[2])
                normalized_state = state_text.strip().lower()
                self._update_connection_visuals(state_text)
                if state_text == "Car connected!":
                    self.sensor_control_on()
                elif "reconnecting" in normalized_state or "connection lost" in normalized_state:
                    self.sensor_control_reconnecting()
                elif normalized_state == "disconnected" or normalized_state.startswith("connection failed"):
                    self.sensor_control_off()
                    self._set_graph_streaming(False)

    def OnTests(self, event):
        data = event.data
        if not isinstance(data, dict):
            self.OBDTests.SetItem(data[0], data[1], data[2])
            return
        if data["kind"] == "readiness":
            self.OBDTests.SetItem(data["index"], 1, "Yes" if data["supported"] else "No")
            self.OBDTests.SetItem(data["index"], 2, data["status"])
            colour = {
                "Ready": self.theme.success,
                "Not ready": self.theme.warning,
                "Unsupported": self.theme.muted,
            }[data["status"]]
            self.OBDTests.SetItemTextColour(data["index"], colour)
        elif data["kind"] == "misfire":
            self.misfire_tests.SetItem(data["index"], 1, data["result"])
            result = data["result"]
            colour = (
                self.theme.muted
                if result == "Unsupported"
                else self.theme.success
                if result.startswith("0 ")
                else self.theme.warning
            )
            self.misfire_tests.SetItemTextColour(data["index"], colour)
        elif data["kind"] == "misfire_reset":
            self.misfire_tests.DeleteAllItems()
            cylinders = data["cylinders"]
            if cylinders:
                for cylinder in cylinders:
                    self.misfire_tests.Append([f"Cylinder {cylinder}", "Reading…"])
            else:
                self.misfire_tests.Append(["No supported cylinder monitors", "—"])
        elif data["kind"] == "complete":
            self.tests_summary_labels["Ready"].SetLabel(str(data["ready"]))
            self.tests_summary_labels["Not Ready"].SetLabel(str(data["not_ready"]))
            self.tests_summary_labels["Unsupported"].SetLabel(str(data["unsupported"]))
            self.tests_status_label.SetLabel(
                f"{data['ready']} ready  •  {data['not_ready']} not ready  •  "
                f"{data['unsupported']} unsupported"
            )
            self.tests_status_label.SetForegroundColour(
                self.theme.warning if data["not_ready"] else self.theme.success
            )
            self.RefreshTestsButton.Enable(True)
        elif data["kind"] == "misfire_complete":
            count = data["count"]
            self.tests_status_label.SetLabel(
                f"{count} cylinder monitor{'s' if count != 1 else ''} updated"
                if count
                else "No supported per-cylinder misfire monitors"
            )
            self.tests_status_label.SetForegroundColour(
                self.theme.success if count else self.theme.muted
            )
            self.RefreshTestsButton.Enable(True)
        elif data["kind"] == "error":
            self.tests_status_label.SetLabel("Unable to read monitor status")
            self.tests_status_label.SetForegroundColour(self.theme.danger)
            self.RefreshTestsButton.Enable(True)
        self.tests_panel.Layout()

    """
    def OnCombo(self, event):
        self.curr_selection1 = self.combobox1.GetSelection()
        self.curr_selection2 = self.combobox2.GetSelection()
        self.curr_selection3 = self.combobox3.GetSelection()
        self.curr_selection4 = self.combobox4.GetSelection()
    """
    def InsertFreezeframeRow(self, event):
        counter = event.data
        self.freezeframe.InsertItem(counter, "")

    def OnClose(self, event):

        if self._shutdown_started:
            return

        #while self.senprod.state != "finished":
        #    time.sleep(0.1)
        print("on close!")

        self.sensors.DeleteAllItems()
        self.sensor_rows.clear()
        self.sensor_visible_indices.clear()
        self.sensor_view_by_source.clear()
        self.sensor_selected_sources.clear()
        self.sensor_count_label.SetLabel("Waiting for vehicle data")
        self.freezeframe.DeleteAllItems()
        for row in range(self.OBDTests.GetItemCount()):
            self.OBDTests.SetItem(row, 1, "—")
            self.OBDTests.SetItem(row, 2, "—")
        for row in range(self.misfire_tests.GetItemCount()):
            self.misfire_tests.SetItem(row, 1, "—")
        self.dtc.DeleteAllItems()

        self._set_graph_streaming(False)
        self._refresh_graph_selection_ui()
        try:
            self.ThreadControl = 666

            self.sensor_control_off()
            time.sleep(0.1)

        except:
            traceback.print_exc()

    def OnDebug(self, event):
        self.TraceDebug(event.data[0], event.data[1])

    def OnDtc(self, event):
        if event.data == 0:  # signal, that DTC was cleared
            self.dtc.DeleteAllItems()
            for count in self.dtc_summary_labels.values():
                count.SetLabel("0")
            self.dtc_status_label.SetLabel("Scanning diagnostic trouble codes…")
            self.dtc_empty_label.SetLabel("Scanning diagnostic trouble codes…")
            self.dtc_empty_label.Show()
            self.GetDTCButton.Enable(False)
        elif isinstance(event.data, dict):
            counts = event.data.get("counts", {})
            for category, count in self.dtc_summary_labels.items():
                count.SetLabel(str(counts.get(category, 0)))
            total = sum(counts.values())
            if total:
                self.dtc_status_label.SetLabel(
                    f"{counts.get('Stored', 0)} stored  •  "
                    f"{counts.get('Pending', 0)} pending  •  "
                    f"{counts.get('Permanent', 0)} permanent"
                )
                self.dtc_empty_label.Hide()
            else:
                self.dtc_status_label.SetLabel("No diagnostic trouble codes reported")
                self.dtc_empty_label.SetLabel("No diagnostic trouble codes were reported.")
                self.dtc_empty_label.Show()
            self.GetDTCButton.Enable(True)
        else:
            row = tuple(event.data)
            row_index = self.dtc.Append(row)
            category_colours = {
                "Stored": self.theme.danger,
                "Pending": self.theme.warning,
                "Permanent": self.theme.accent,
            }
            self.dtc.SetItemTextColour(
                row_index, category_colours.get(row[1], self.theme.text)
            )
            self.dtc_empty_label.Hide()
        self.DTCpanel.Layout()

    def OnDisconnect(self, event):  # disconnect connection to ECU
        self._stop_sensor_recording()
        try:
            if self.senprod and self.senprod.is_alive():
                self.senprod.stop()
            else:
                self.ThreadControl = 666

        except:
            traceback.print_exc()




    def OpenPort(self, e):
        print("Open port event.")
        if self.senprod:
            if self.senprod.is_alive():  # signal current producers to finish
                self.senprod.stop()
                self.senprod.join(timeout=2.0)
                if self.senprod.is_alive():
                    self._update_connection_visuals("Disconnecting...")
                    return
        self.ThreadControl = 0

        # Prevent reconfigure/reconnect clicks while connection attempt is in progress.
        self.settingmenu.Enable(ID_CONFIG, False)
        self.settingmenu.Enable(ID_RESET, False)
        self.settingmenu.Enable(ID_DISCONNECT, False)

        self.senprod = SensorProducer(
            self, self.COMPORT, self.SERTIMEOUT, self.RECONNATTEMPTS,
            self.BAUDRATE, self.FAST,
        )
        self.senprod.start()

    def GetDTC(self, e):
        self.dtc_status_label.SetLabel("Scanning diagnostic trouble codes…")
        self.dtc_empty_label.SetLabel("Scanning diagnostic trouble codes…")
        self.dtc_empty_label.Show()
        self.GetDTCButton.Enable(False)
        self.ThreadControl = 2
        self._go_to_page(self.DTCpanel)

    def AddDTC(self, code):
        self.dtc.InsertStringItem(0, "")
        self.dtc.SetItem(0, 0, code[0])
        self.dtc.SetItem(0, 1, code[1])

    def CodeLookup(self, e=None):
        diag = wx.Frame(
            self.frame,
            title="Diagnostic Trouble Code Lookup",
            size=(760, 620),
        )
        ico = wx.Icon(resource_path('assets/pyobd.png'), wx.BITMAP_TYPE_PNG)
        diag.SetIcon(ico)
        diag.SetBackgroundColour(self.theme.window)

        panel = wx.Panel(diag)
        panel.SetBackgroundColour(self.theme.window)
        search = wx.SearchCtrl(panel, style=wx.TE_PROCESS_ENTER)
        search.SetDescriptiveText("Search code or description")
        search.ShowCancelButton(True)
        search.SetMinSize((-1, 38))
        result_label = wx.StaticText(panel, label="")
        result_label.SetForegroundColour(self.theme.muted)

        results = self.MyListCtrl(
            panel,
            wx.NewIdRef(),
            style=wx.LC_REPORT | wx.BORDER_NONE | wx.LC_HRULES | wx.LC_SINGLE_SEL,
        )
        results.InsertColumn(0, "Code", width=120)
        results.InsertColumn(1, "Description", width=560)
        self.theme.style_list(results)

        rows = sorted(pcodes.items())
        pending_filter = {"timer": None}

        def populate():
            pending_filter["timer"] = None
            query = search.GetValue().strip().lower()
            filtered = [
                (code, description)
                for code, description in rows
                if not query or query in code.lower() or query in description.lower()
            ]
            results.Freeze()
            try:
                results.DeleteAllItems()
                for code, description in filtered:
                    results.Append([code, description])
            finally:
                results.Thaw()
            result_label.SetLabel(f"{len(filtered)} codes")
            panel.Layout()

        def schedule_filter(event):
            timer = pending_filter["timer"]
            if timer and timer.IsRunning():
                timer.Stop()
            pending_filter["timer"] = wx.CallLater(120, populate)
            event.Skip()

        def close_lookup(event):
            timer = pending_filter["timer"]
            if timer and timer.IsRunning():
                timer.Stop()
            event.Skip()

        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(search, 0, wx.EXPAND | wx.ALL, 16)
        root.Add(result_label, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 16)
        root.Add(results, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 16)
        panel.SetSizer(root)
        search.Bind(wx.EVT_TEXT, schedule_filter)
        diag.Bind(wx.EVT_CLOSE, close_lookup)
        populate()
        diag.CentreOnParent()
        diag.Show(True)

    def QueryClear(self, e):
        result = wx.MessageBox(
            "Clear stored and pending codes and freeze-frame data?\n\n"
            "Readiness monitors will reset. Permanent codes cannot be cleared by a scan tool.",
            "Clear diagnostic codes",
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING,
            self.frame,
        )
        if result == wx.YES:
            self.ClearDTC()

    def ClearDTC(self):
        self.dtc_status_label.SetLabel("Clearing diagnostic trouble codes…")
        self.ThreadControl = 1
        self._go_to_page(self.DTCpanel)
        self.senprod.wake()

    def try_port(self, portStr):
        """returns boolean for port availability"""
        try:
            s = serial.Serial(portStr)
            s.close()  # explicit close 'cause of delayed GC in java
            return True

        except serial.SerialException:
            pass
        except:
            traceback.print_exc()

        return False

    def scanSerial(self):  # NEW

        """scan for available ports. return a list of serial names"""
        available = self._get_connected_port_names()

        return available

    def _get_connected_port_infos(self):
        try:
            return sorted(list(list_ports.comports()), key=lambda p: p.device or "")
        except Exception:
            traceback.print_exc()
            return []

    def _get_connected_port_names(self):
        names = [p.device for p in self._get_connected_port_infos() if p.device]
        if "AUTO" not in names:
            names.append("AUTO")
        if not names:
            names = ["AUTO"]
        return names

    def _get_bluetooth_adapter_choices(self):
        def _windows_bt_name_by_mac():
            if os.name != "nt":
                return {}

            command = (
                "Get-PnpDevice -Class Bluetooth | "
                "Select-Object FriendlyName,InstanceId | ConvertTo-Json -Compress"
            )
            try:
                result = subprocess.run(
                    ["powershell", "-NoProfile", "-Command", command],
                    capture_output=True,
                    text=True,
                    timeout=4,
                )
            except Exception:
                return {}

            if result.returncode != 0 or result.stdout.strip() == "":
                return {}

            try:
                parsed = json.loads(result.stdout)
            except Exception:
                return {}

            entries = parsed if isinstance(parsed, list) else [parsed]
            name_by_mac = {}
            for entry in entries:
                if not isinstance(entry, dict):
                    continue

                friendly_name = str(entry.get("FriendlyName") or "").strip()
                instance_id = str(entry.get("InstanceId") or "")

                if friendly_name == "" or friendly_name.lower().startswith("standard serial over bluetooth"):
                    continue

                matches = re.findall(r"(?<![0-9A-Fa-f])[0-9A-Fa-f]{12}(?![0-9A-Fa-f])", instance_id)
                for mac12 in matches:
                    mac = ":".join(mac12[i:i + 2] for i in range(0, 12, 2)).upper()
                    name_by_mac[mac] = friendly_name

            return name_by_mac

        def _first_mac_like(text):
            if not text:
                return ""
            match = re.search(r"(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}", text)
            return match.group(0).upper() if match else ""

        def _compact_name(text):
            name = (text or "Bluetooth Adapter").strip()
            name = re.sub(r"\s*\(COM\d+\)\s*$", "", name, flags=re.IGNORECASE)
            return name or "Bluetooth Adapter"

        def _compact_label(name, adapter_id, max_len=44):
            label = f"{name} ({adapter_id})"
            if len(label) <= max_len:
                return label
            reserve = len(adapter_id) + 5
            short_name_len = max(10, max_len - reserve)
            return f"{name[:short_name_len].rstrip()}... ({adapter_id})"

        bt_name_by_mac = _windows_bt_name_by_mac()
        choices = []
        fallback_choices = []

        for port_info in self._get_connected_port_infos():
            device = (port_info.device or "").strip()
            if device == "":
                continue

            description = _compact_name(port_info.description or port_info.product or "")
            candidates = [
                getattr(port_info, "serial_number", "") or "",
                port_info.description or "",
                port_info.hwid or "",
                getattr(port_info, "location", "") or "",
                getattr(port_info, "manufacturer", "") or "",
            ]

            adapter_id = ""
            for candidate in candidates:
                adapter_id = _first_mac_like(candidate)
                if adapter_id:
                    break

            if adapter_id == "":
                adapter_id = device

            if adapter_id in bt_name_by_mac:
                description = _compact_name(bt_name_by_mac[adapter_id])

            label = _compact_label(description, adapter_id)
            lower = label.lower()

            if "bluetooth" in lower or " bt" in lower or lower.startswith("bt"):
                choices.append((label, device))
            fallback_choices.append((label, device))

        if not choices:
            choices = fallback_choices

        choices.insert(0, ("AUTO", "AUTO"))
        return choices

    def _infer_connection_from_comport(self, connection_type, connection_target, comport):
        if connection_type in ["AUTO", "SERIAL", "WIFI", "BLUETOOTH", "CUSTOM", "DEMO"]:
            return connection_type, connection_target

        if comport == "AUTO":
            return "AUTO", ""
        if comport == "DEMO":
            return "DEMO", ""

        if isinstance(comport, str):
            upper = comport.upper()
            if upper.startswith("WIFI:"):
                return "WIFI", comport[5:]
            if upper.startswith("BT:"):
                return "BLUETOOTH", comport[3:]
            if comport.startswith("socket://"):
                return "WIFI", comport[len("socket://"):]
            if comport.startswith("rfcomm://"):
                return "BLUETOOTH", comport[len("rfcomm://"):]
            if "://" in comport:
                return "CUSTOM", comport

        return "SERIAL", comport

    def _compose_comport(self, connection_type, serial_port, target):
        target = (target or "").strip()

        if connection_type == "AUTO":
            return "AUTO"
        if connection_type == "DEMO":
            return "DEMO"
        if connection_type == "SERIAL":
            return serial_port
        if connection_type == "WIFI":
            if target == "":
                target = "192.168.0.10:35000"
            return "WIFI:" + target
        if connection_type == "BLUETOOTH":
            return "BT:" + target
        return target

    @staticmethod
    def _normalize_unit_label(unit_label):
        return str(unit_label or "").strip().lower().replace(" ", "")

    @staticmethod
    def _canonical_unit_label(unit_label):
        normalized = MyApp._normalize_unit_label(unit_label)
        aliases = {
            "mph": "mph",
            "mi/h": "mph",
            "mile/hour": "mph",
            "miles/hour": "mph",
            "kph": "kph",
            "km/h": "kph",
            "kilometer/hour": "kph",
            "kilometers/hour": "kph",
            "psi": "psi",
            "kpa": "kPa",
            "kilopascal": "kPa",
            "kilopascals": "kPa",
            "c": "C",
            "degc": "C",
            "celsius": "C",
            "f": "F",
            "degf": "F",
            "fahrenheit": "F",
            "lb/min": "lb/min",
            "lbs/min": "lb/min",
            "g/s": "g/s",
            "gram/second": "g/s",
            "grams/second": "g/s",
        }
        return aliases.get(normalized, str(unit_label or "").strip())

    def _target_unit_for_measurement_system(self, unit_label):
        normalized = self._normalize_unit_label(unit_label)
        if self.MEASUREMENT_SYSTEM == "METRIC":
            metric_map = {
                "mph": "kph",
                "mi/h": "kph",
                "mile/hour": "kph",
                "miles/hour": "kph",
                "psi": "kPa",
                "f": "degC",
                "degf": "degC",
                "fahrenheit": "degC",
                "lb/min": "g/s",
                "lbs/min": "g/s",
            }
            return metric_map.get(normalized)

        imperial_map = {
            "kph": "mph",
            "km/h": "mph",
            "kilometer/hour": "mph",
            "kilometers/hour": "mph",
            "kpa": "psi",
            "kilopascal": "psi",
            "kilopascals": "psi",
            "c": "degF",
            "degc": "degF",
            "celsius": "degF",
            "g/s": "lb/min",
            "gram/second": "lb/min",
            "grams/second": "lb/min",
        }
        return imperial_map.get(normalized)

    def _manual_convert_quantity(self, magnitude, unit_label):
        normalized = self._normalize_unit_label(unit_label)
        if self.MEASUREMENT_SYSTEM == "METRIC":
            if normalized in ("mph", "mi/h", "mile/hour", "miles/hour"):
                return magnitude * 1.609344, "kph"
            if normalized == "psi":
                return magnitude * 6.894757293168361, "kPa"
            if normalized in ("f", "degf", "fahrenheit"):
                return ((magnitude - 32.0) * 5.0 / 9.0), "C"
            if normalized in ("lb/min", "lbs/min"):
                return magnitude * 7.559872833333334, "g/s"
            return magnitude, self._canonical_unit_label(unit_label)

        if normalized in ("kph", "km/h", "kilometer/hour", "kilometers/hour"):
            return magnitude * 0.621371192237334, "mph"
        if normalized in ("kpa", "kilopascal", "kilopascals"):
            return magnitude * 0.14503773773020923, "psi"
        if normalized in ("c", "degc", "celsius"):
            return ((magnitude * 9.0 / 5.0) + 32.0), "F"
        if normalized in ("g/s", "gram/second", "grams/second"):
            return magnitude * 0.13227735731092652, "lb/min"
        return magnitude, self._canonical_unit_label(unit_label)

    @staticmethod
    def _format_quantity_text(magnitude, unit_label):
        if unit_label:
            return f"{magnitude:.2f} {unit_label}"
        return f"{magnitude:.2f}"

    def get_measurement_components(self, value):
        if value is None:
            return None, "value", "No data"

        if hasattr(value, "magnitude"):
            try:
                magnitude = float(value.magnitude)
            except Exception:
                return None, "value", str(value)

            unit_obj = getattr(value, "units", None)
            unit_label = str(unit_obj) if unit_obj is not None else str(getattr(value, "unit", ""))
            target_unit = self._target_unit_for_measurement_system(unit_label)

            if target_unit and hasattr(value, "to"):
                try:
                    converted = value.to(target_unit)
                    magnitude = float(converted.magnitude)
                    unit_label = str(getattr(converted, "units", target_unit))
                except Exception:
                    magnitude, unit_label = self._manual_convert_quantity(magnitude, unit_label)
            else:
                magnitude, unit_label = self._manual_convert_quantity(magnitude, unit_label)

            display_unit = self._canonical_unit_label(unit_label)
            return magnitude, display_unit or "value", self._format_quantity_text(magnitude, display_unit)

        return None, "value", str(value)

    def format_measurement_value(self, value):
        return self.get_measurement_components(value)[2]

    def Configure(self, e=None):
        id = 0
        diag = wx.Dialog(self.frame, id, title="Configure")
        sizer = wx.BoxSizer(wx.VERTICAL)

        ports = self._get_connected_port_names()
        bt_choices = self._get_bluetooth_adapter_choices()
        bt_labels = [label for (label, _value) in bt_choices]
        bt_value_by_label = dict(bt_choices)

        connection_types = ["AUTO", "DEMO", "SERIAL", "WIFI", "BLUETOOTH", "CUSTOM"]
        baudrates = [
            "AUTO", "38400", "9600", "115200", "57600", "19200", "14400", "3000000", "2000000",
            "1000000", "250000", "230400", "128000", "500000", "460800", "576000", "921600",
            "1152000", "1500000", "2500000", "3500000", "4000000",
        ]

        connection_type, connection_target = self._infer_connection_from_comport(
            self.CONNECTION_TYPE,
            self.CONNECTION_TARGET,
            self.COMPORT,
        )

        header_box = wx.StaticBoxSizer(wx.VERTICAL, diag, "Connection")
        top_row = wx.BoxSizer(wx.HORIZONTAL)

        type_label = wx.StaticText(diag, -1, "Connection type:")
        connection_type_choice = wx.Choice(diag, -1, choices=connection_types)
        connection_type_choice.SetSelection(connection_types.index(connection_type))
        auto_connect_check = wx.CheckBox(diag, -1, "Auto-connect")
        auto_connect_check.Disable()

        top_row.Add(type_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        top_row.Add(connection_type_choice, 0, wx.RIGHT, 10)
        top_row.Add(auto_connect_check, 0, wx.ALIGN_CENTER_VERTICAL)
        header_box.Add(top_row, 0, wx.ALL, 6)
        sizer.Add(header_box, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 6)

        transport_row = wx.BoxSizer(wx.HORIZONTAL)

        bt_box = wx.StaticBoxSizer(wx.VERTICAL, diag, "Bluetooth Adapter")
        bluetooth_combo = wx.ComboBox(diag, -1, choices=bt_labels, style=wx.CB_DROPDOWN)
        bt_box.Add(bluetooth_combo, 0, wx.EXPAND | wx.ALL, 6)

        wifi_box = wx.StaticBoxSizer(wx.VERTICAL, diag, "WiFi settings")
        wifi_grid = wx.FlexGridSizer(rows=3, cols=2, vgap=4, hgap=6)
        wifi_grid.Add(wx.StaticText(diag, -1, "IP:"), 0, wx.ALIGN_CENTER_VERTICAL)
        wifi_ip_ctrl = wx.TextCtrl(diag, -1, "192.168.0.10", size=(130, -1))
        wifi_grid.Add(wifi_ip_ctrl, 0, wx.EXPAND)
        wifi_grid.Add(wx.StaticText(diag, -1, "Port:"), 0, wx.ALIGN_CENTER_VERTICAL)
        wifi_port_ctrl = wx.TextCtrl(diag, -1, "35000", size=(130, -1))
        wifi_grid.Add(wifi_port_ctrl, 0, wx.EXPAND)
        wifi_grid.Add(wx.StaticText(diag, -1, "Timeout:"), 0, wx.ALIGN_CENTER_VERTICAL)
        timeoutCtrl = wx.TextCtrl(diag, -1, "5", size=(80, -1))
        wifi_grid.Add(timeoutCtrl, 0, wx.EXPAND)
        wifi_box.Add(wifi_grid, 0, wx.ALL, 6)

        com_box = wx.StaticBoxSizer(wx.VERTICAL, diag, "COM settings")
        com_grid = wx.FlexGridSizer(rows=3, cols=2, vgap=4, hgap=6)
        com_grid.Add(wx.StaticText(diag, -1, "COM port:"), 0, wx.ALIGN_CENTER_VERTICAL)
        com_choice = wx.Choice(diag, -1, choices=ports)
        com_grid.Add(com_choice, 0, wx.EXPAND)
        com_grid.Add(wx.StaticText(diag, -1, "Baud rate:"), 0, wx.ALIGN_CENTER_VERTICAL)
        baud_choice = wx.Choice(diag, -1, choices=baudrates)
        com_grid.Add(baud_choice, 0, wx.EXPAND)
        auto_increase_check = wx.CheckBox(diag, -1, "Auto-increase")
        auto_increase_check.Disable()
        com_grid.Add(auto_increase_check, 0, wx.ALIGN_CENTER_VERTICAL)
        com_grid.Add((1, 1), 0)
        com_grid.AddGrowableCol(1, 1)
        com_box.Add(com_grid, 1, wx.EXPAND | wx.ALL, 6)

        transport_row.Add(bt_box, 1, wx.EXPAND | wx.ALL, 3)
        transport_row.Add(wifi_box, 0, wx.EXPAND | wx.ALL, 3)
        transport_row.Add(com_box, 0, wx.EXPAND | wx.ALL, 3)
        sizer.Add(transport_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 4)

        advanced_row = wx.BoxSizer(wx.HORIZONTAL)

        custom_box = wx.StaticBoxSizer(wx.VERTICAL, diag, "Custom target")
        custom_target_ctrl = wx.TextCtrl(diag, -1, "", size=(280, -1))
        custom_help = wx.StaticText(diag, -1, "Examples: socket://192.168.0.10:35000 or rfc2217://host:port")
        custom_box.Add(custom_target_ctrl, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 6)
        custom_box.Add(custom_help, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)

        protocol_box = wx.StaticBoxSizer(wx.VERTICAL, diag, "Protocol")
        mode_choice = wx.Choice(diag, -1, choices=["FAST", "NORMAL"])
        measurement_choice = wx.Choice(diag, -1, choices=["IMPERIAL", "METRIC"])
        reconnect_row = wx.BoxSizer(wx.HORIZONTAL)
        reconnect_row.Add(wx.StaticText(diag, -1, "Reconnect attempts:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        reconnectCtrl = wx.TextCtrl(diag, -1, str(self.RECONNATTEMPTS), size=(70, -1))
        reconnect_row.Add(reconnectCtrl, 0)
        protocol_box.Add(wx.StaticText(diag, -1, "Send mode:"), 0, wx.LEFT | wx.RIGHT | wx.TOP, 6)
        protocol_box.Add(mode_choice, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 6)
        protocol_box.Add(wx.StaticText(diag, -1, "Measurements:"), 0, wx.LEFT | wx.RIGHT | wx.TOP, 6)
        protocol_box.Add(measurement_choice, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 6)
        protocol_box.Add(reconnect_row, 0, wx.LEFT | wx.RIGHT | wx.TOP | wx.BOTTOM, 6)

        advanced_row.Add(custom_box, 1, wx.EXPAND | wx.ALL, 3)
        advanced_row.Add(protocol_box, 0, wx.EXPAND | wx.ALL, 3)
        sizer.Add(advanced_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 4)

        note_text = wx.StaticText(diag, -1, "Note: these changes will be applied on the next connect to vehicle")
        sizer.Add(note_text, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)

        link_and_buttons = wx.BoxSizer(wx.HORIZONTAL)
        self.OpenLinkButton = ModernButton(
            diag, "Order OBD adapter", self.theme, variant="secondary", size=(160, 40)
        )
        diag.Bind(wx.EVT_BUTTON, self.OnHelpOrder, self.OpenLinkButton)
        link_and_buttons.Add(self.OpenLinkButton, 0, wx.RIGHT, 10)
        link_and_buttons.AddStretchSpacer(1)
        ok_button = ModernButton(diag, "Save", self.theme, variant="primary", id=wx.ID_OK)
        cancel_button = ModernButton(
            diag, "Cancel", self.theme, variant="secondary", id=wx.ID_CANCEL
        )
        ok_button.Bind(wx.EVT_BUTTON, lambda _event: diag.EndModal(wx.ID_OK))
        cancel_button.Bind(wx.EVT_BUTTON, lambda _event: diag.EndModal(wx.ID_CANCEL))
        link_and_buttons.Add(ok_button, 0, wx.RIGHT, 6)
        link_and_buttons.Add(cancel_button, 0)
        sizer.Add(link_and_buttons, 0, wx.EXPAND | wx.ALL, 8)

        if (self.COMPORT != 0) and (self.COMPORT in ports):
            com_choice.SetSelection(ports.index(self.COMPORT))
        else:
            com_choice.SetSelection(ports.index("AUTO") if "AUTO" in ports else 0)

        if (self.BAUDRATE != 0) and (self.BAUDRATE in baudrates):
            baud_choice.SetSelection(baudrates.index(self.BAUDRATE))
        else:
            baud_choice.SetSelection(baudrates.index("AUTO"))

        if (self.FAST == "FAST") or (self.FAST == "NORMAL"):
            mode_choice.SetSelection(["FAST", "NORMAL"].index(self.FAST))
        else:
            mode_choice.SetSelection(0)

        if self.MEASUREMENT_SYSTEM in ["IMPERIAL", "METRIC"]:
            measurement_choice.SetSelection(["IMPERIAL", "METRIC"].index(self.MEASUREMENT_SYSTEM))
        else:
            measurement_choice.SetSelection(0)

        timeoutCtrl.SetValue(str(self.SERTIMEOUT or "5"))

        wifi_target = str(connection_target or "")
        if connection_type == "WIFI":
            if wifi_target.startswith("socket://"):
                wifi_target = wifi_target[len("socket://"):]
            if ":" in wifi_target:
                wifi_host, wifi_port = wifi_target.rsplit(":", 1)
            else:
                wifi_host, wifi_port = wifi_target, "35000"
            if wifi_host.strip() != "":
                wifi_ip_ctrl.SetValue(wifi_host.strip())
            if wifi_port.strip() != "":
                wifi_port_ctrl.SetValue(wifi_port.strip())

        bt_target = str(connection_target or "").strip()
        if connection_type == "BLUETOOTH" and bt_target != "":
            selected_label = None
            for label, value in bt_choices:
                if value == bt_target:
                    selected_label = label
                    break
            if selected_label is not None:
                bluetooth_combo.SetValue(selected_label)
            else:
                bluetooth_combo.SetValue(bt_target)
        else:
            bluetooth_combo.SetValue(bt_labels[0] if bt_labels else "AUTO")

        if connection_type == "CUSTOM":
            custom_target_ctrl.SetValue(str(connection_target or ""))

        # Keep all sections editable; selected connection type only determines which target is used on save.
        com_choice.Enable(True)
        baud_choice.Enable(True)
        bluetooth_combo.Enable(True)
        wifi_ip_ctrl.Enable(True)
        wifi_port_ctrl.Enable(True)
        custom_target_ctrl.Enable(True)

        diag.SetSizer(sizer)
        diag.SetAutoLayout(True)
        sizer.Fit(diag)
        diag.SetMinSize((840, 500))
        r = diag.ShowModal()
        if r == wx.ID_OK:

            # create section
            if self.config.sections() == []:
                self.config.add_section("pyOBD")
            # set and save COMPORT

            self.CONNECTION_TYPE = connection_types[connection_type_choice.GetSelection()]

            selected_port = ports[com_choice.GetSelection()]
            if self.CONNECTION_TYPE == "WIFI":
                wifi_host = wifi_ip_ctrl.GetValue().strip() or "192.168.0.10"
                wifi_port = wifi_port_ctrl.GetValue().strip() or "35000"
                self.CONNECTION_TARGET = wifi_host + ":" + wifi_port
            elif self.CONNECTION_TYPE == "BLUETOOTH":
                bt_value = bluetooth_combo.GetValue().strip() or "AUTO"
                self.CONNECTION_TARGET = bt_value_by_label.get(bt_value, bt_value)
            elif self.CONNECTION_TYPE == "CUSTOM":
                self.CONNECTION_TARGET = custom_target_ctrl.GetValue().strip()
            else:
                self.CONNECTION_TARGET = ""

            self.COMPORT = self._compose_comport(
                self.CONNECTION_TYPE,
                selected_port,
                self.CONNECTION_TARGET,
            )
            COMPORT = self.COMPORT
            self.config.set("pyOBD", "COMPORT", self.COMPORT)
            self.config.set("pyOBD", "CONNECTION_TYPE", self.CONNECTION_TYPE)
            self.config.set("pyOBD", "CONNECTION_TARGET", self.CONNECTION_TARGET)

            self.BAUDRATE = baudrates[baud_choice.GetSelection()]
            BAUDRATE = self.BAUDRATE
            self.config.set("pyOBD", "BAUDRATE", self.BAUDRATE)

            self.FAST = ["FAST", "NORMAL"][mode_choice.GetSelection()]
            self.config.set("pyOBD", "FAST", self.FAST)

            self.MEASUREMENT_SYSTEM = ["IMPERIAL", "METRIC"][measurement_choice.GetSelection()]
            self.config.set("pyOBD", "MEASUREMENT_SYSTEM", self.MEASUREMENT_SYSTEM)

            # set and save SERTIMEOUT
            self.SERTIMEOUT = timeoutCtrl.GetValue()
            self.config.set("pyOBD", "SERTIMEOUT", self.SERTIMEOUT)


            # set and save RECONNATTEMPTS
            try:
                self.RECONNATTEMPTS = max(1, int(reconnectCtrl.GetValue()))
            except ValueError:
                self.RECONNATTEMPTS = 5
            self.config.set("pyOBD", "RECONNATTEMPTS", self.RECONNATTEMPTS)

            # write configuration to cfg file
            self.config.write(open(self.configfilepath, 'w'))
            self._update_active_vehicle_header()

    def OnExitMenu(self, event=None):
        self.frame.Close()

    def OnWindowClose(self, event):
        if self._shutdown_started:
            event.Skip()
            return

        self._shutdown_started = True
        self._stop_session_replay()
        self._stop_sensor_recording()
        if self.sensor_filter_timer and self.sensor_filter_timer.IsRunning():
            self.sensor_filter_timer.Stop()
        self.ThreadControl = 666
        if self.senprod and self.senprod.is_alive():
            self.senprod.stop()
            self.senprod.join(timeout=2.0)
        event.Skip()


def main():
    app = MyApp(False)
    app.MainLoop()


if __name__ == "__main__":
    main()
