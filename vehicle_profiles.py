"""Persistent vehicle profile UI for pyOBD."""

import json
import re
import uuid

import wx

from ui_theme import ModernButton


class VehicleProfilesMixin:
    @staticmethod
    def _normalize_vin(vin):
        return re.sub(r"[^A-Za-z0-9]", "", str(vin)).upper()

    def _load_vehicle_profiles(self):
        if not self.config.has_section("pyOBD"):
            self.vehicle_profiles = {}
            self.active_vehicle_profile = ""
            return
        try:
            saved = json.loads(self.config.get("pyOBD", "VEHICLE_PROFILES", fallback="{}"))
        except (json.JSONDecodeError, TypeError, ValueError):
            saved = {}
        self.vehicle_profiles = saved if isinstance(saved, dict) else {}
        active = self.config.get("pyOBD", "ACTIVE_VEHICLE_PROFILE", fallback="")
        self.active_vehicle_profile = active if active in self.vehicle_profiles else ""

    def _save_vehicle_profiles(self):
        if not self.config.has_section("pyOBD"):
            self.config.add_section("pyOBD")
        self.config.set("pyOBD", "VEHICLE_PROFILES", json.dumps(self.vehicle_profiles))
        self.config.set("pyOBD", "ACTIVE_VEHICLE_PROFILE", self.active_vehicle_profile)
        with open(self.configfilepath, "w", encoding="utf-8") as config_file:
            self.config.write(config_file)

    @staticmethod
    def _vehicle_profile_name(profile):
        nickname = str(profile.get("nickname", "")).strip()
        if nickname:
            return nickname
        description = " ".join(
            str(profile.get(field, "")).strip() for field in ("year", "make", "model")
        ).strip()
        return description or str(profile.get("vin", "")).strip() or "Untitled vehicle"

    def _refresh_vehicle_profile_list(self, selected_id=None):
        self.vehicle_profile_order = list(self.vehicle_profiles)
        self.vehicle_profile_list.Set(
            [self._vehicle_profile_name(self.vehicle_profiles[item]) for item in self.vehicle_profile_order]
        )
        target = selected_id or self.active_vehicle_profile
        if target in self.vehicle_profile_order:
            self.vehicle_profile_list.SetSelection(self.vehicle_profile_order.index(target))
            self._show_vehicle_profile(target)
        else:
            self.vehicle_profile_list.SetSelection(wx.NOT_FOUND)
            self._show_vehicle_profile(None)

    def _show_vehicle_profile(self, profile_id):
        profile = self.vehicle_profiles.get(profile_id, {})
        self.active_vehicle_profile = profile_id or ""
        for field, control in self.vehicle_profile_fields.items():
            control.ChangeValue(str(profile.get(field, "")))
            control.Enable(bool(profile_id))
        dashboard_names = sorted(self.dashboard_layouts, key=str.casefold)
        self.vehicle_profile_dashboard_choice.Set(["No default"] + dashboard_names)
        default_dashboard = str(profile.get("default_dashboard", ""))
        selection = dashboard_names.index(default_dashboard) + 1 if default_dashboard in dashboard_names else 0
        self.vehicle_profile_dashboard_choice.SetSelection(selection)
        self.vehicle_profile_dashboard_choice.Enable(bool(profile_id))
        self.vehicle_profile_save_button.Enable(bool(profile_id))
        self.vehicle_profile_delete_button.Enable(bool(profile_id))
        self.vehicle_profile_status.SetLabel(
            "Select a vehicle or create a new profile." if not profile_id else ""
        )
        self._update_active_vehicle_header()

    def _update_active_vehicle_header(self):
        label = "No vehicle profile"
        if self.active_vehicle_profile in self.vehicle_profiles:
            label = self._vehicle_profile_name(
                self.vehicle_profiles[self.active_vehicle_profile]
            )
        is_demo = str(getattr(self, "CONNECTION_TYPE", "")).upper() == "DEMO"
        display_label = "DEMO MODE" if is_demo else label
        header = getattr(self, "header_vehicle_profile", None)
        if header:
            header.SetLabel(
                display_label if len(display_label) <= 22 else f"{display_label[:21]}…"
            )
            header.SetToolTip("Simulated vehicle data" if is_demo else label)
            header.SetForegroundColour(self.theme.warning if is_demo else self.theme.muted)
            header.SetFont(self.theme.font(10, bold=is_demo))
            header.GetParent().Layout()

    def _activate_vehicle_profile_for_vin(self, vin):
        normalized_vin = self._normalize_vin(vin)
        if not normalized_vin:
            return False
        for profile_id, profile in self.vehicle_profiles.items():
            profile_vin = self._normalize_vin(profile.get("vin", ""))
            if profile_vin and profile_vin == normalized_vin:
                self.active_vehicle_profile = profile_id
                self._save_vehicle_profiles()
                self._refresh_vehicle_profile_list(profile_id)
                self._apply_vehicle_default_dashboard(profile)
                self.vehicle_profile_status.SetLabel("Selected automatically from the connected VIN.")
                return True
        self.active_vehicle_profile = ""
        self._save_vehicle_profiles()
        self._refresh_vehicle_profile_list()
        return False

    def _apply_vehicle_default_dashboard(self, profile):
        return self._select_dashboard_layout(
            str(profile.get("default_dashboard", ""))
        )

    def _connected_vehicle_vin(self):
        try:
            vin = self._normalize_vin(self.status.GetItemText(4, 1))
        except (AttributeError, RuntimeError):
            return ""
        return vin if vin and vin not in {"NONE", "UNKNOWN"} else ""

    def OnVehicleProfileSelected(self, _event):
        selection = self.vehicle_profile_list.GetSelection()
        if selection == wx.NOT_FOUND:
            return
        self.active_vehicle_profile = self.vehicle_profile_order[selection]
        self._show_vehicle_profile(self.active_vehicle_profile)
        self._save_vehicle_profiles()
        self._apply_vehicle_default_dashboard(
            self.vehicle_profiles[self.active_vehicle_profile]
        )

    def OnNewVehicleProfile(self, _event):
        profile_id = uuid.uuid4().hex
        self.vehicle_profiles[profile_id] = {
            "vin": self._connected_vehicle_vin(),
            "nickname": "",
            "year": "",
            "make": "",
            "model": "",
            "notes": "",
            "default_dashboard": "",
        }
        self.active_vehicle_profile = profile_id
        self._save_vehicle_profiles()
        self._refresh_vehicle_profile_list(profile_id)
        self.vehicle_profile_fields["nickname"].SetFocus()

    def OnSaveVehicleProfile(self, _event):
        if self.active_vehicle_profile not in self.vehicle_profiles:
            return
        vin = re.sub(r"[^A-Za-z0-9]", "", self.vehicle_profile_fields["vin"].GetValue()).upper()
        year = self.vehicle_profile_fields["year"].GetValue().strip()
        if year and (not year.isdigit() or len(year) != 4):
            wx.MessageBox("Enter a four-digit year or leave it blank.", "Vehicle profile", wx.OK | wx.ICON_WARNING)
            return
        profile = {
            field: control.GetValue().strip()
            for field, control in self.vehicle_profile_fields.items()
        }
        profile["vin"] = vin
        profile["year"] = year
        dashboard_selection = self.vehicle_profile_dashboard_choice.GetSelection()
        profile["default_dashboard"] = (
            self.vehicle_profile_dashboard_choice.GetString(dashboard_selection)
            if dashboard_selection > 0
            else ""
        )
        self.vehicle_profiles[self.active_vehicle_profile] = profile
        self._save_vehicle_profiles()
        self._refresh_vehicle_profile_list(self.active_vehicle_profile)
        self._apply_vehicle_default_dashboard(profile)
        self.vehicle_profile_status.SetLabel("Vehicle profile saved.")

    def OnDeleteVehicleProfile(self, _event):
        if self.active_vehicle_profile not in self.vehicle_profiles:
            return
        name = self._vehicle_profile_name(self.vehicle_profiles[self.active_vehicle_profile])
        result = wx.MessageBox(
            f'Delete "{name}"?',
            "Delete vehicle profile",
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING,
        )
        if result != wx.YES:
            return
        del self.vehicle_profiles[self.active_vehicle_profile]
        self.active_vehicle_profile = next(iter(self.vehicle_profiles), "")
        self._save_vehicle_profiles()
        self._refresh_vehicle_profile_list()

    def build_vehicle_profiles_page(self):
        self._load_vehicle_profiles()
        self.vehicle_profiles_panel = wx.Panel(self.nb)
        self.vehicle_profiles_panel.SetBackgroundColour(self.theme.window)
        root = wx.BoxSizer(wx.HORIZONTAL)

        list_panel = wx.Panel(self.vehicle_profiles_panel)
        list_panel.SetBackgroundColour(self.theme.surface)
        list_root = wx.BoxSizer(wx.VERTICAL)
        list_title = wx.StaticText(list_panel, label="Saved vehicles")
        list_title.SetFont(self.theme.font(14, bold=True))
        list_title.SetForegroundColour(self.theme.text)
        self.vehicle_profile_list = wx.ListBox(list_panel, style=wx.LB_SINGLE)
        self.vehicle_profile_new_button = ModernButton(
            list_panel, "New vehicle", self.theme, variant="primary"
        )
        self.vehicle_profile_delete_button = ModernButton(
            list_panel, "Delete", self.theme, variant="danger"
        )
        list_root.Add(list_title, 0, wx.ALL, 16)
        list_root.Add(self.vehicle_profile_list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 16)
        list_root.Add(self.vehicle_profile_new_button, 0, wx.EXPAND | wx.ALL, 16)
        list_root.Add(self.vehicle_profile_delete_button, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 16)
        list_panel.SetSizer(list_root)
        list_panel.SetMinSize((260, -1))

        form_panel = wx.ScrolledWindow(self.vehicle_profiles_panel, style=wx.VSCROLL)
        form_panel.SetScrollRate(10, 10)
        form_panel.SetBackgroundColour(self.theme.surface)
        form_root = wx.BoxSizer(wx.VERTICAL)
        form_title = wx.StaticText(form_panel, label="Vehicle details")
        form_title.SetFont(self.theme.font(18, bold=True))
        form_title.SetForegroundColour(self.theme.text)
        form_help = wx.StaticText(
            form_panel,
            label="Save information used to identify this vehicle and organize future sessions.",
        )
        form_help.SetForegroundColour(self.theme.muted)
        form_help.Wrap(650)

        grid = wx.FlexGridSizer(0, 2, 10, 14)
        grid.AddGrowableCol(1, 1)
        self.vehicle_profile_fields = {}
        for field, label in (
            ("vin", "VIN"),
            ("nickname", "Nickname"),
            ("year", "Year"),
            ("make", "Make"),
            ("model", "Model"),
        ):
            text = wx.StaticText(form_panel, label=label)
            text.SetForegroundColour(self.theme.text)
            control = wx.TextCtrl(form_panel)
            if field == "vin":
                control.SetMaxLength(17)
            elif field == "year":
                control.SetMaxLength(4)
            self.vehicle_profile_fields[field] = control
            grid.Add(text, 0, wx.ALIGN_CENTER_VERTICAL)
            grid.Add(control, 1, wx.EXPAND)

        notes_label = wx.StaticText(form_panel, label="Notes")
        notes_label.SetForegroundColour(self.theme.text)
        notes = wx.TextCtrl(form_panel, style=wx.TE_MULTILINE)
        notes.SetMinSize((-1, 130))
        self.vehicle_profile_fields["notes"] = notes
        dashboard_label = wx.StaticText(form_panel, label="Default dashboard")
        dashboard_label.SetForegroundColour(self.theme.text)
        self.vehicle_profile_dashboard_choice = wx.Choice(form_panel)
        self.vehicle_profile_save_button = ModernButton(
            form_panel, "Save profile", self.theme, variant="primary"
        )
        self.vehicle_profile_status = wx.StaticText(form_panel, label="")
        self.vehicle_profile_status.SetForegroundColour(self.theme.muted)

        form_root.Add(form_title, 0, wx.LEFT | wx.RIGHT | wx.TOP | wx.BOTTOM, 20)
        form_root.Add(form_help, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 20)
        form_root.Add(grid, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 20)
        form_root.Add(notes_label, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)
        form_root.Add(notes, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 20)
        form_root.Add(dashboard_label, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)
        form_root.Add(
            self.vehicle_profile_dashboard_choice,
            0,
            wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM,
            20,
        )
        form_root.Add(self.vehicle_profile_save_button, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        form_root.Add(self.vehicle_profile_status, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 20)
        form_panel.SetSizer(form_root)

        root.Add(list_panel, 0, wx.EXPAND | wx.RIGHT, 12)
        root.Add(form_panel, 1, wx.EXPAND)
        self.vehicle_profiles_panel.SetSizer(root)
        self.nb.AddPage(self.vehicle_profiles_panel, "Vehicles")

        self.vehicle_profile_list.Bind(wx.EVT_LISTBOX, self.OnVehicleProfileSelected)
        self.vehicle_profile_new_button.Bind(wx.EVT_BUTTON, self.OnNewVehicleProfile)
        self.vehicle_profile_save_button.Bind(wx.EVT_BUTTON, self.OnSaveVehicleProfile)
        self.vehicle_profile_delete_button.Bind(wx.EVT_BUTTON, self.OnDeleteVehicleProfile)
        self._refresh_vehicle_profile_list()
        if self.active_vehicle_profile in self.vehicle_profiles:
            self._apply_vehicle_default_dashboard(
                self.vehicle_profiles[self.active_vehicle_profile]
            )
