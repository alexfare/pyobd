"""Customizable live dashboard UI for pyOBD."""

import json
import time

import wx

from ui_theme import ModernButton


TILE_SIZES = {
    "Small": (190, 128),
    "Medium": (270, 148),
    "Wide": (430, 148),
}

TILE_COLOURS = {
    "Blue": (37, 99, 235),
    "Green": (22, 163, 74),
    "Orange": (217, 119, 6),
    "Red": (220, 38, 38),
    "Purple": (126, 34, 206),
}


class DashboardTile(wx.Panel):
    def __init__(self, parent, owner, widget):
        super().__init__(parent, style=wx.BORDER_NONE)
        self.owner = owner
        self.widget = widget
        self.SetBackgroundColour(owner.theme.surface)
        self.SetMinSize(TILE_SIZES.get(widget.get("size"), TILE_SIZES["Medium"]))

        root = wx.BoxSizer(wx.HORIZONTAL)
        accent = wx.Panel(self, size=(6, -1))
        accent.SetBackgroundColour(wx.Colour(*TILE_COLOURS.get(
            widget.get("colour"), TILE_COLOURS["Blue"]
        )))
        content = wx.BoxSizer(wx.VERTICAL)

        title = wx.StaticText(self, label=widget.get("title") or widget["pid"])
        title.SetForegroundColour(owner.theme.text)
        title.SetFont(owner.theme.font(11, bold=True))
        pid = wx.StaticText(self, label=widget["pid"])
        pid.SetForegroundColour(owner.theme.muted)
        pid.SetFont(owner.theme.font(8))
        self.value = wx.StaticText(self, label="---")
        self.value.SetForegroundColour(owner.theme.text)
        self.value.SetFont(owner.theme.font(20, bold=True))

        content.Add(title, 0, wx.BOTTOM, 2)
        content.Add(pid, 0, wx.BOTTOM, 10)
        content.Add(self.value, 0, wx.BOTTOM, 6)

        self.gauge = None
        if widget.get("type") == "Gauge":
            self.gauge = wx.Gauge(self, range=100, style=wx.GA_HORIZONTAL)
            content.Add(self.gauge, 0, wx.EXPAND | wx.TOP, 2)

        hint = None
        if owner.dashboard_editing:
            hint = wx.StaticText(self, label="Drag to move  •  Right-click to edit")
            hint.SetForegroundColour(owner.theme.muted)
            hint.SetFont(owner.theme.font(8))
            content.AddStretchSpacer()
            content.Add(hint, 0, wx.TOP, 6)

        root.Add(accent, 0, wx.EXPAND)
        root.Add(content, 1, wx.EXPAND | wx.ALL, 14)
        self.SetSizer(root)

        controls = [self, title, pid, self.value, accent]
        if self.gauge:
            controls.append(self.gauge)
        if hint:
            controls.append(hint)
        for control in controls:
            control.Bind(wx.EVT_CONTEXT_MENU, self._on_context_menu)
            control.Bind(wx.EVT_LEFT_DOWN, self._on_left_down)
            control.Bind(wx.EVT_MOTION, self._on_motion)
            control.Bind(wx.EVT_LEFT_UP, self._on_left_up)

    @staticmethod
    def _screen_position(event):
        control = event.GetEventObject()
        return control.ClientToScreen(event.GetPosition())

    def _on_context_menu(self, _event):
        self.owner._show_dashboard_widget_menu(self.widget["id"])

    def _on_left_down(self, event):
        if not self.owner.dashboard_editing:
            event.Skip()
            return
        self.owner._begin_dashboard_drag(self.widget["id"], event.GetEventObject())

    def _on_motion(self, event):
        if self.owner.dashboard_editing and event.Dragging() and event.LeftIsDown():
            self.owner._update_dashboard_drag(self._screen_position(event))
        else:
            event.Skip()

    def _on_left_up(self, event):
        if self.owner.dashboard_editing:
            self.owner._finish_dashboard_drag(self._screen_position(event))
        else:
            event.Skip()

    def update_value(self, magnitude, text):
        self.value.SetLabel(text)
        if self.gauge is not None and magnitude is not None:
            minimum = float(self.widget.get("minimum", 0))
            maximum = float(self.widget.get("maximum", 100))
            span = max(0.0001, maximum - minimum)
            percent = int(max(0, min(100, ((float(magnitude) - minimum) / span) * 100)))
            self.gauge.SetValue(percent)
        self.Layout()


class DashboardUIMixin:
    def _default_dashboard_layouts(self):
        sequence = iter(range(1, 100))

        def widget(pid, title, widget_type="Digital", size="Medium", colour="Blue", minimum=0, maximum=100):
            return {
                "id": f"default-{next(sequence)}",
                "pid": pid,
                "title": title,
                "type": widget_type,
                "size": size,
                "colour": colour,
                "minimum": minimum,
                "maximum": maximum,
            }

        return {
            "Daily Driving": {"widgets": [
                widget("010C", "Engine RPM", "Gauge", "Medium", "Blue", 0, 7000),
                widget("010D", "Vehicle Speed", "Gauge", "Medium", "Green", 0, 140),
                widget("0105", "Coolant Temperature", "Digital", "Medium", "Orange"),
                widget("ATRV", "Battery Voltage", "Digital", "Small", "Purple"),
            ]},
        }

    def _load_dashboard_layouts(self):
        try:
            saved = json.loads(self.config.get("pyOBD", "DASHBOARD_LAYOUTS", fallback="{}"))
        except (TypeError, ValueError):
            saved = {}
        self.dashboard_layouts = (
            saved if isinstance(saved, dict) and saved else self._default_dashboard_layouts()
        )
        saved_current = self.config.get("pyOBD", "DASHBOARD_CURRENT", fallback="")
        self.dashboard_current = (
            saved_current if saved_current in self.dashboard_layouts
            else next(iter(self.dashboard_layouts))
        )

    def _save_dashboard_layouts(self):
        if not self.config.has_section("pyOBD"):
            self.config.add_section("pyOBD")
        self.config.set("pyOBD", "DASHBOARD_LAYOUTS", json.dumps(self.dashboard_layouts))
        self.config.set("pyOBD", "DASHBOARD_CURRENT", self.dashboard_current)
        try:
            with open(self.configfilepath, "w", encoding="utf-8") as config_file:
                self.config.write(config_file)
        except OSError as error:
            wx.MessageBox(
                f"Unable to save dashboard layouts.\n\n{error}",
                "Dashboard",
                wx.OK | wx.ICON_ERROR,
            )

    def _dashboard_widgets(self):
        return self.dashboard_layouts[self.dashboard_current].setdefault("widgets", [])

    def _dashboard_catalog(self):
        return {
            command.command.decode(errors="ignore").upper(): command
            for command in self.graph_command_catalog
        }

    def _refresh_dashboard_choices(self):
        names = sorted(self.dashboard_layouts, key=str.casefold)
        self.dashboard_layout_choice.Set(names)
        self.dashboard_layout_choice.SetSelection(names.index(self.dashboard_current))

    def _refresh_dashboard_poll_commands(self):
        catalog = self._dashboard_catalog()
        seen = set()
        self.dashboard_poll_commands = []
        for widget in self._dashboard_widgets():
            command = catalog.get(str(widget.get("pid", "")).upper())
            if command and command.command not in seen:
                seen.add(command.command)
                self.dashboard_poll_commands.append(command)

    def _rebuild_dashboard(self):
        self.dashboard_grid.Clear(delete_windows=True)
        self.dashboard_tiles = {}
        for widget in self._dashboard_widgets():
            tile = DashboardTile(self.dashboard_canvas, self, widget)
            self.dashboard_tiles[widget["id"]] = tile
            self.dashboard_grid.Add(tile, 0, wx.ALL, 6)
        self._refresh_dashboard_poll_commands()
        self.dashboard_canvas.Layout()
        self.dashboard_canvas.FitInside()

    def build_dashboard_page(self):
        self.dashboard_panel = wx.Panel(self.nb)
        self.dashboard_panel.SetBackgroundColour(self.theme.window)
        self.dashboard_editing = False
        self.dashboard_drag_id = None
        self.dashboard_drag_target = None
        self.dashboard_drag_capture = None
        self.dashboard_event_pending = False
        self.dashboard_poll_commands = []
        self.dashboard_tiles = {}
        self._load_dashboard_layouts()

        root = wx.BoxSizer(wx.VERTICAL)
        toolbar = wx.BoxSizer(wx.HORIZONTAL)
        self.dashboard_layout_choice = wx.Choice(self.dashboard_panel)
        self.dashboard_layout_choice.SetMinSize((190, 40))
        self.dashboard_manage_button = ModernButton(
            self.dashboard_panel, "Manage", self.theme, variant="secondary"
        )
        self.dashboard_edit_button = ModernButton(
            self.dashboard_panel, "Edit", self.theme, variant="secondary"
        )
        self.dashboard_add_button = ModernButton(
            self.dashboard_panel, "Add widget", self.theme, variant="primary"
        )
        self.dashboard_add_button.Enable(False)
        toolbar.Add(self.dashboard_layout_choice, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        toolbar.Add(self.dashboard_manage_button, 0)
        toolbar.AddStretchSpacer()
        toolbar.Add(self.dashboard_edit_button, 0, wx.RIGHT, 8)
        toolbar.Add(self.dashboard_add_button, 0)

        self.dashboard_canvas = wx.ScrolledWindow(self.dashboard_panel, style=wx.VSCROLL)
        self.dashboard_canvas.SetBackgroundColour(self.theme.window)
        self.dashboard_canvas.SetScrollRate(10, 10)
        self.dashboard_grid = wx.WrapSizer(wx.HORIZONTAL)
        self.dashboard_canvas.SetSizer(self.dashboard_grid)
        root.Add(toolbar, 0, wx.EXPAND | wx.ALL, 12)
        root.Add(self.dashboard_canvas, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)
        self.dashboard_panel.SetSizer(root)

        self.dashboard_layout_choice.Bind(wx.EVT_CHOICE, self.OnDashboardLayoutSelected)
        self.dashboard_manage_button.Bind(wx.EVT_BUTTON, self.OnManageDashboards)
        self.dashboard_edit_button.Bind(wx.EVT_BUTTON, self.OnToggleDashboardEditing)
        self.dashboard_add_button.Bind(wx.EVT_BUTTON, self.OnAddDashboardWidget)
        self.dashboard_canvas.Bind(wx.EVT_SIZE, self._on_dashboard_size)

        self.nb.AddPage(self.dashboard_panel, "Dashboard")
        self.dashboard_page_index = self.nb.GetPageCount() - 1
        self._refresh_dashboard_choices()
        self._rebuild_dashboard()

    def _on_dashboard_size(self, event):
        self.dashboard_canvas.Layout()
        self.dashboard_canvas.FitInside()
        event.Skip()

    def OnDashboardLayoutSelected(self, _event):
        selected = self.dashboard_layout_choice.GetStringSelection()
        if selected in self.dashboard_layouts:
            self.dashboard_current = selected
            self._save_dashboard_layouts()
            self._rebuild_dashboard()

    def OnToggleDashboardEditing(self, _event):
        self.dashboard_editing = not self.dashboard_editing
        self.dashboard_edit_button.SetLabel("Done" if self.dashboard_editing else "Edit")
        self.dashboard_edit_button.SetVariant("primary" if self.dashboard_editing else "secondary")
        self.dashboard_add_button.Enable(self.dashboard_editing)
        self._rebuild_dashboard()

    def _dashboard_widget_dialog(self, widget=None):
        dialog = wx.Dialog(self.frame, title="Dashboard Widget")
        root = wx.BoxSizer(wx.VERTICAL)
        grid = wx.FlexGridSizer(cols=2, vgap=10, hgap=10)
        grid.AddGrowableCol(1, 1)
        catalog = self._dashboard_catalog()
        keys = list(catalog)
        labels = [f"{key} - {catalog[key].desc}" for key in keys]
        pid_choice = wx.Choice(dialog, choices=labels)
        title_ctrl = wx.TextCtrl(dialog)
        type_choice = wx.Choice(dialog, choices=["Digital", "Gauge"])
        size_choice = wx.Choice(dialog, choices=list(TILE_SIZES))
        colour_choice = wx.Choice(dialog, choices=list(TILE_COLOURS))
        minimum_ctrl = wx.TextCtrl(dialog, value="0")
        maximum_ctrl = wx.TextCtrl(dialog, value="100")
        controls = [
            ("PID", pid_choice), ("Title", title_ctrl), ("Display", type_choice),
            ("Size", size_choice), ("Colour", colour_choice),
            ("Gauge minimum", minimum_ctrl), ("Gauge maximum", maximum_ctrl),
        ]
        for label, control in controls:
            grid.Add(wx.StaticText(dialog, label=label), 0, wx.ALIGN_CENTER_VERTICAL)
            grid.Add(control, 1, wx.EXPAND)
        if widget:
            pid = str(widget.get("pid", "")).upper()
            pid_choice.SetSelection(keys.index(pid) if pid in keys else 0)
            title_ctrl.SetValue(widget.get("title", ""))
            type_choice.SetStringSelection(widget.get("type", "Digital"))
            size_choice.SetStringSelection(widget.get("size", "Medium"))
            colour_choice.SetStringSelection(widget.get("colour", "Blue"))
            minimum_ctrl.SetValue(str(widget.get("minimum", 0)))
            maximum_ctrl.SetValue(str(widget.get("maximum", 100)))
        else:
            default_index = keys.index("010C") if "010C" in keys else 0
            pid_choice.SetSelection(default_index)
            type_choice.SetSelection(0)
            size_choice.SetStringSelection("Medium")
            colour_choice.SetStringSelection("Blue")
        buttons = dialog.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL)
        root.Add(grid, 1, wx.EXPAND | wx.ALL, 16)
        root.Add(buttons, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 16)
        dialog.SetSizerAndFit(root)
        dialog.SetMinSize((520, -1))
        if dialog.ShowModal() != wx.ID_OK:
            dialog.Destroy()
            return None
        pid = keys[pid_choice.GetSelection()]
        try:
            minimum = float(minimum_ctrl.GetValue())
            maximum = float(maximum_ctrl.GetValue())
            if maximum <= minimum:
                raise ValueError
        except ValueError:
            minimum, maximum = 0.0, 100.0
        result = {
            "pid": pid,
            "title": title_ctrl.GetValue().strip() or catalog[pid].desc,
            "type": type_choice.GetStringSelection(),
            "size": size_choice.GetStringSelection(),
            "colour": colour_choice.GetStringSelection(),
            "minimum": minimum,
            "maximum": maximum,
        }
        dialog.Destroy()
        return result

    def OnAddDashboardWidget(self, _event):
        settings = self._dashboard_widget_dialog()
        if not settings:
            return
        settings["id"] = str(time.time_ns())
        self._dashboard_widgets().append(settings)
        self._save_dashboard_layouts()
        self._rebuild_dashboard()

    def _configure_dashboard_widget(self, widget_id):
        widget = next((item for item in self._dashboard_widgets() if item["id"] == widget_id), None)
        if not widget:
            return
        settings = self._dashboard_widget_dialog(widget)
        if settings:
            widget.update(settings)
            self._save_dashboard_layouts()
            self._rebuild_dashboard()

    def _delete_dashboard_widget(self, widget_id):
        widgets = self._dashboard_widgets()
        widgets[:] = [widget for widget in widgets if widget["id"] != widget_id]
        self._save_dashboard_layouts()
        self._rebuild_dashboard()

    def _show_dashboard_widget_menu(self, widget_id):
        if not self.dashboard_editing:
            return
        menu = wx.Menu()
        configure = menu.Append(wx.ID_ANY, "Configure")
        delete = menu.Append(wx.ID_ANY, "Delete")
        menu.Bind(wx.EVT_MENU, lambda _event: self._configure_dashboard_widget(widget_id), configure)
        menu.Bind(wx.EVT_MENU, lambda _event: self._delete_dashboard_widget(widget_id), delete)
        self.dashboard_canvas.PopupMenu(menu)
        menu.Destroy()

    def _begin_dashboard_drag(self, widget_id, control):
        self.dashboard_drag_id = widget_id
        self.dashboard_drag_target = widget_id
        self.dashboard_drag_capture = control
        if not control.HasCapture():
            control.CaptureMouse()

    def _update_dashboard_drag(self, screen_position):
        for widget_id, tile in self.dashboard_tiles.items():
            if tile.GetScreenRect().Contains(screen_position):
                self.dashboard_drag_target = widget_id
                break

    def _finish_dashboard_drag(self, screen_position):
        capture = self.dashboard_drag_capture
        if capture and capture.HasCapture():
            capture.ReleaseMouse()
        self._update_dashboard_drag(screen_position)
        source_id = self.dashboard_drag_id
        target_id = self.dashboard_drag_target
        self.dashboard_drag_id = None
        self.dashboard_drag_target = None
        self.dashboard_drag_capture = None
        if not source_id or not target_id or source_id == target_id:
            return
        widgets = self._dashboard_widgets()
        source = next((widget for widget in widgets if widget["id"] == source_id), None)
        target_index = next((index for index, widget in enumerate(widgets) if widget["id"] == target_id), None)
        if source is None or target_index is None:
            return
        widgets.remove(source)
        widgets.insert(target_index, source)
        self._save_dashboard_layouts()
        self._rebuild_dashboard()

    def _new_dashboard(self, _event=None):
        dialog = wx.TextEntryDialog(self.frame, "Dashboard name:", "New Dashboard")
        try:
            if dialog.ShowModal() != wx.ID_OK:
                return
            name = dialog.GetValue().strip()
        finally:
            dialog.Destroy()
        if not name or name in self.dashboard_layouts:
            return
        self.dashboard_layouts[name] = {"widgets": []}
        self.dashboard_current = name
        self._save_dashboard_layouts()
        self._refresh_dashboard_choices()
        self._rebuild_dashboard()

    def _rename_dashboard(self, _event=None):
        old_name = self.dashboard_current
        dialog = wx.TextEntryDialog(self.frame, "Dashboard name:", "Rename Dashboard", old_name)
        try:
            if dialog.ShowModal() != wx.ID_OK:
                return
            new_name = dialog.GetValue().strip()
        finally:
            dialog.Destroy()
        if not new_name or new_name == old_name or new_name in self.dashboard_layouts:
            return
        self.dashboard_layouts[new_name] = self.dashboard_layouts.pop(old_name)
        self.dashboard_current = new_name
        self._save_dashboard_layouts()
        self._refresh_dashboard_choices()

    def _delete_dashboard(self, _event=None):
        if len(self.dashboard_layouts) <= 1:
            return
        if wx.MessageBox(
            f'Delete the dashboard "{self.dashboard_current}"?',
            "Dashboard",
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION,
        ) != wx.YES:
            return
        del self.dashboard_layouts[self.dashboard_current]
        self.dashboard_current = next(iter(self.dashboard_layouts))
        self._save_dashboard_layouts()
        self._refresh_dashboard_choices()
        self._rebuild_dashboard()

    def OnManageDashboards(self, _event):
        menu = wx.Menu()
        new_item = menu.Append(wx.ID_ANY, "New dashboard")
        rename_item = menu.Append(wx.ID_ANY, "Rename dashboard")
        delete_item = menu.Append(wx.ID_ANY, "Delete dashboard")
        delete_item.Enable(len(self.dashboard_layouts) > 1)
        menu.Bind(wx.EVT_MENU, self._new_dashboard, new_item)
        menu.Bind(wx.EVT_MENU, self._rename_dashboard, rename_item)
        menu.Bind(wx.EVT_MENU, self._delete_dashboard, delete_item)
        self.dashboard_manage_button.PopupMenu(menu)
        menu.Destroy()

    def OnDashboardValues(self, event):
        try:
            values = {item["pid"]: item for item in event.data}
            for widget in self._dashboard_widgets():
                value = values.get(widget["pid"])
                tile = self.dashboard_tiles.get(widget["id"])
                if value and tile:
                    tile.update_value(value["magnitude"], value["text"])
        finally:
            self.dashboard_event_pending = False

    def _reset_dashboard_values(self):
        for tile in self.dashboard_tiles.values():
            tile.update_value(None, "---")
