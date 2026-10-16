"""Customizable live dashboard UI for pyOBD."""

import json
import math
import time

import wx

from ui_theme import ModernButton


CANVAS_SIZE = (1600, 900)
TILE_SIZES = {
    "Small": (190, 128),
    "Medium": (270, 180),
    "Wide": (430, 180),
}
TILE_COLOURS = {
    "Blue": (37, 99, 235),
    "Green": (22, 163, 74),
    "Orange": (217, 119, 6),
    "Red": (220, 38, 38),
    "Purple": (126, 34, 206),
    "Cyan": (8, 145, 178),
}


class DashboardTile(wx.Control):
    def __init__(self, parent, owner, widget):
        super().__init__(parent, style=wx.BORDER_NONE)
        self.owner = owner
        self.widget = widget
        self.primary_magnitude = None
        self.primary_text = "---"
        self.center_text = "---"
        self.SetBackgroundStyle(wx.BG_STYLE_PAINT)
        self.SetCursor(wx.Cursor(wx.CURSOR_HAND if owner.dashboard_editing else wx.CURSOR_ARROW))
        self.SetToolTip("Drag to move • Right-click to customize" if owner.dashboard_editing else "")
        self.Bind(wx.EVT_PAINT, self._on_paint)
        self.Bind(wx.EVT_CONTEXT_MENU, self._on_context_menu)
        self.Bind(wx.EVT_LEFT_DOWN, self._on_left_down)
        self.Bind(wx.EVT_MOTION, self._on_motion)
        self.Bind(wx.EVT_LEFT_UP, self._on_left_up)
        self.Bind(wx.EVT_MOUSE_CAPTURE_LOST, self._on_capture_lost)

    def _on_paint(self, _event):
        dc = wx.AutoBufferedPaintDC(self)
        dc.SetBackground(wx.Brush(self.owner.theme.window))
        dc.Clear()
        width, height = self.GetClientSize()
        accent = wx.Colour(*TILE_COLOURS.get(
            self.widget.get("colour"), TILE_COLOURS["Blue"]
        ))
        graphics = wx.GraphicsContext.Create(dc)
        graphics.SetBrush(wx.Brush(self.owner.theme.surface))
        graphics.SetPen(wx.Pen(accent, 3))
        shape = self.widget.get("shape", "Rounded")
        if shape == "Circle":
            graphics.DrawEllipse(2, 2, width - 4, height - 4)
        elif shape == "Rectangle":
            graphics.DrawRectangle(2, 2, width - 4, height - 4)
        else:
            graphics.DrawRoundedRectangle(2, 2, width - 4, height - 4, 18)
        del graphics

        self._draw_fitted_title(dc, self.widget.get("title") or self.widget["pid"], width)
        display = self.widget.get("type", "Digital")
        if display in ("Dial", "Combined"):
            self._draw_dial(dc, width, height, accent, display == "Combined")
        else:
            self._draw_centered(dc, self.primary_text, height // 2 - 16, 24, True)
            self._draw_centered(dc, self.widget["pid"], height - 30, 8, False, self.owner.theme.muted)

        if self.owner.dashboard_editing:
            dc.SetPen(wx.Pen(accent, 1, wx.PENSTYLE_DOT))
            dc.SetBrush(wx.TRANSPARENT_BRUSH)
            dc.DrawRectangle(6, 6, width - 12, height - 12)

    def _draw_centered(self, dc, text, y, size, bold=False, colour=None):
        dc.SetFont(self.owner.theme.font(size, bold=bold))
        dc.SetTextForeground(colour or self.owner.theme.text)
        text = str(text)
        text_width, _ = dc.GetTextExtent(text)
        dc.DrawText(text, max(8, (self.GetClientSize().width - text_width) // 2), y)

    def _draw_fitted_title(self, dc, text, width):
        text = str(text).strip()
        max_width = max(60, width - 36)
        for size in range(11, 6, -1):
            dc.SetFont(self.owner.theme.font(size, bold=True))
            words = text.split()
            lines = []
            current = ""
            for word in words:
                candidate = f"{current} {word}".strip()
                candidate_width, _ = dc.GetTextExtent(candidate)
                if current and candidate_width > max_width:
                    lines.append(current)
                    current = word
                else:
                    current = candidate
            if current:
                lines.append(current)
            line_widths = [dc.GetTextExtent(line)[0] for line in lines]
            if len(lines) <= 2 and all(line_width <= max_width for line_width in line_widths):
                break
        lines = lines[:2]
        if lines:
            last_line = len(lines) - 1
            while lines[last_line] and dc.GetTextExtent(f"{lines[last_line]}…")[0] > max_width:
                lines[last_line] = lines[last_line][:-1]
            if lines[last_line] != text and (
                len(lines) == 1 or " ".join(lines) != text
            ):
                lines[last_line] += "…"
        dc.SetTextForeground(self.owner.theme.text)
        for index, line in enumerate(lines):
            text_width, text_height = dc.GetTextExtent(line)
            dc.DrawText(line, max(8, (width - text_width) // 2), 10 + index * text_height)

    def _draw_dial(self, dc, width, height, accent, show_center):
        center_x = width // 2
        center_y = max(62, height // 2 + 10)
        radius = max(30, min(width // 2 - 24, height // 2 - 32))
        minimum = float(self.widget.get("minimum", 0))
        maximum = float(self.widget.get("maximum", 100))
        span = max(0.0001, maximum - minimum)
        divisions = max(2, min(20, int(self.widget.get("divisions", 10))))
        dc.SetPen(wx.Pen(self.owner.theme.border, 2))
        dc.SetFont(self.owner.theme.font(7))
        dc.SetTextForeground(self.owner.theme.muted)
        for step in range(divisions + 1):
            angle = math.radians(135 + (270 * step / divisions))
            outer_x = center_x + int(math.cos(angle) * radius)
            outer_y = center_y + int(math.sin(angle) * radius)
            inner_x = center_x + int(math.cos(angle) * (radius - 9))
            inner_y = center_y + int(math.sin(angle) * (radius - 9))
            dc.DrawLine(inner_x, inner_y, outer_x, outer_y)
            label = f"{minimum + span * step / divisions:g}"
            label_width, label_height = dc.GetTextExtent(label)
            label_radius = radius - 22
            label_x = center_x + int(math.cos(angle) * label_radius) - label_width // 2
            label_y = center_y + int(math.sin(angle) * label_radius) - label_height // 2
            dc.DrawText(label, label_x, label_y)

        if self.primary_magnitude is not None:
            value = max(minimum, min(maximum, float(self.primary_magnitude)))
            angle = math.radians(135 + 270 * ((value - minimum) / span))
            needle_x = center_x + int(math.cos(angle) * (radius - 16))
            needle_y = center_y + int(math.sin(angle) * (radius - 16))
            dc.SetPen(wx.Pen(accent, 4))
            dc.DrawLine(center_x, center_y, needle_x, needle_y)
        dc.SetBrush(wx.Brush(accent))
        dc.SetPen(wx.Pen(accent))
        dc.DrawCircle(center_x, center_y, 5)

        if show_center:
            self._draw_centered(dc, self.center_text, center_y + 10, 13, True)

    def _event_screen_position(self, event):
        return self.ClientToScreen(event.GetPosition())

    def _on_context_menu(self, _event):
        self.owner._show_dashboard_widget_menu(self.widget["id"], self)

    def _on_left_down(self, event):
        if not self.owner.dashboard_editing:
            event.Skip()
            return
        self.owner._begin_dashboard_drag(
            self.widget["id"], self, self._event_screen_position(event)
        )

    def _on_motion(self, event):
        if self.owner.dashboard_editing and event.Dragging() and event.LeftIsDown():
            self.owner._update_dashboard_drag(self._event_screen_position(event))
        else:
            event.Skip()

    def _on_left_up(self, event):
        if self.owner.dashboard_editing:
            self.owner._finish_dashboard_drag(self._event_screen_position(event))
        else:
            event.Skip()

    def _on_capture_lost(self, _event):
        self.owner._cancel_dashboard_drag()

    def update_values(self, primary, center=None):
        if primary:
            self.primary_magnitude = primary["magnitude"]
            self.primary_text = primary["text"]
        else:
            self.primary_magnitude = None
            self.primary_text = "---"
        if self.widget.get("center_pid"):
            self.center_text = center["text"] if center else "---"
        else:
            self.center_text = self.primary_text
        self.Refresh(False)


class DashboardUIMixin:
    def _default_dashboard_layouts(self):
        return {
            "Daily Driving": {"widgets": [
                self._new_dashboard_widget(
                    "010C", "Engine RPM", "Combined", "Circle", "Blue",
                    0, 7000, 40, 30, 260, 260, "010D",
                ),
                self._new_dashboard_widget(
                    "010D", "Vehicle Speed", "Dial", "Circle", "Green",
                    0, 140, 330, 45, 230, 230,
                ),
                self._new_dashboard_widget(
                    "0105", "Coolant Temperature", "Digital", "Rounded", "Orange",
                    0, 260, 590, 60, 280, 150,
                ),
                self._new_dashboard_widget(
                    "ATRV", "Battery Voltage", "Digital", "Rounded", "Purple",
                    0, 20, 610, 245, 240, 130,
                ),
            ]},
        }

    @staticmethod
    def _new_dashboard_widget(
        pid, title, display="Digital", shape="Rounded", colour="Blue",
        minimum=0, maximum=100, x=20, y=20, width=270, height=180,
        center_pid="",
    ):
        return {
            "id": str(time.time_ns()), "pid": pid, "center_pid": center_pid,
            "title": title, "type": display, "shape": shape, "colour": colour,
            "minimum": minimum, "maximum": maximum,
            "divisions": 10,
            "x": x, "y": y, "width": width, "height": height,
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
        self._migrate_dashboard_layouts()

    def _migrate_dashboard_layouts(self):
        for layout in self.dashboard_layouts.values():
            if not isinstance(layout, dict):
                continue
            for index, widget in enumerate(layout.get("widgets", [])):
                width, height = TILE_SIZES.get(widget.pop("size", "Medium"), TILE_SIZES["Medium"])
                widget.setdefault("id", str(time.time_ns() + index))
                widget.setdefault("type", "Digital")
                if widget["type"] == "Gauge":
                    widget["type"] = "Dial"
                widget.setdefault("shape", "Rounded")
                widget.setdefault("center_pid", "")
                widget.setdefault("divisions", 10)
                widget.setdefault("x", 20 + (index % 3) * 290)
                widget.setdefault("y", 20 + (index // 3) * 200)
                widget.setdefault("width", width)
                widget.setdefault("height", height)

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
                "Dashboard", wx.OK | wx.ICON_ERROR,
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
            pids = [widget.get("pid")]
            if widget.get("type") == "Combined":
                pids.append(widget.get("center_pid"))
            for pid in pids:
                command = catalog.get(str(pid or "").upper())
                if command and command.command not in seen:
                    seen.add(command.command)
                    self.dashboard_poll_commands.append(command)

    def _rebuild_dashboard(self):
        for tile in self.dashboard_tiles.values():
            tile.Destroy()
        self.dashboard_tiles = {}
        for widget in self._dashboard_widgets():
            tile = DashboardTile(self.dashboard_canvas, self, widget)
            tile.SetSize(
                int(widget.get("x", 20)), int(widget.get("y", 20)),
                int(widget.get("width", 270)), int(widget.get("height", 180)),
            )
            self.dashboard_tiles[widget["id"]] = tile
        self._refresh_dashboard_poll_commands()
        self._update_dashboard_canvas_size()
        self.dashboard_canvas.Refresh()

    def _update_dashboard_canvas_size(self):
        client_width, client_height = self.dashboard_canvas.GetClientSize()
        max_width, max_height = CANVAS_SIZE
        for widget in self._dashboard_widgets():
            max_width = max(max_width, int(widget.get("x", 0)) + int(widget.get("width", 0)) + 40)
            max_height = max(max_height, int(widget.get("y", 0)) + int(widget.get("height", 0)) + 40)
        self.dashboard_canvas.SetVirtualSize(max(client_width, max_width), max(client_height, max_height))

    def build_dashboard_page(self):
        self.dashboard_panel = wx.Panel(self.nb)
        self.dashboard_panel.SetBackgroundColour(self.theme.window)
        self.dashboard_editing = False
        self.dashboard_drag_id = None
        self.dashboard_drag_capture = None
        self.dashboard_drag_offset = (0, 0)
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

        self.dashboard_canvas = wx.ScrolledWindow(
            self.dashboard_panel, style=wx.HSCROLL | wx.VSCROLL | wx.BORDER_NONE
        )
        self.dashboard_canvas.SetBackgroundStyle(wx.BG_STYLE_PAINT)
        self.dashboard_canvas.SetBackgroundColour(self.theme.window)
        self.dashboard_canvas.SetScrollRate(10, 10)
        root.Add(toolbar, 0, wx.EXPAND | wx.ALL, 12)
        root.Add(self.dashboard_canvas, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)
        self.dashboard_panel.SetSizer(root)

        self.dashboard_layout_choice.Bind(wx.EVT_CHOICE, self.OnDashboardLayoutSelected)
        self.dashboard_manage_button.Bind(wx.EVT_BUTTON, self.OnManageDashboards)
        self.dashboard_edit_button.Bind(wx.EVT_BUTTON, self.OnToggleDashboardEditing)
        self.dashboard_add_button.Bind(wx.EVT_BUTTON, self.OnAddDashboardWidget)
        self.dashboard_canvas.Bind(wx.EVT_SIZE, self._on_dashboard_size)
        self.dashboard_canvas.Bind(wx.EVT_PAINT, self._on_dashboard_canvas_paint)

        self.nb.AddPage(self.dashboard_panel, "Dashboard")
        self.dashboard_page_index = self.nb.GetPageCount() - 1
        self._refresh_dashboard_choices()
        self._rebuild_dashboard()

    def _on_dashboard_size(self, event):
        self._update_dashboard_canvas_size()
        event.Skip()

    def _on_dashboard_canvas_paint(self, event):
        dc = wx.AutoBufferedPaintDC(self.dashboard_canvas)
        dc.SetBackground(wx.Brush(self.theme.window))
        dc.Clear()
        if not self.dashboard_editing:
            return
        self.dashboard_canvas.PrepareDC(dc)
        dc.SetPen(wx.Pen(self.theme.border, 1, wx.PENSTYLE_DOT))
        width, height = self.dashboard_canvas.GetVirtualSize()
        for x in range(0, width, 20):
            dc.DrawLine(x, 0, x, height)
        for y in range(0, height, 20):
            dc.DrawLine(0, y, width, y)

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

    @staticmethod
    def _set_choice(choice, value, fallback=0):
        if not choice.SetStringSelection(str(value)):
            choice.SetSelection(fallback)

    def _dashboard_widget_dialog(self, widget=None):
        dialog = wx.Dialog(self.frame, title="Dashboard Widget")
        root = wx.BoxSizer(wx.VERTICAL)
        grid = wx.FlexGridSizer(cols=2, vgap=10, hgap=10)
        grid.AddGrowableCol(1, 1)
        catalog = self._dashboard_catalog()
        keys = list(catalog)
        labels = [f"{key} - {catalog[key].desc}" for key in keys]
        pid_choice = wx.Choice(dialog, choices=labels)
        center_pid_choice = wx.Choice(dialog, choices=["Same as main PID"] + labels)
        title_ctrl = wx.TextCtrl(dialog)
        type_choice = wx.Choice(dialog, choices=["Digital", "Dial", "Combined"])
        shape_choice = wx.Choice(dialog, choices=["Rounded", "Circle", "Rectangle"])
        colour_choice = wx.Choice(dialog, choices=list(TILE_COLOURS))
        width_ctrl = wx.SpinCtrl(dialog, min=120, max=800, initial=270)
        height_ctrl = wx.SpinCtrl(dialog, min=100, max=600, initial=180)
        minimum_ctrl = wx.TextCtrl(dialog, value="0")
        maximum_ctrl = wx.TextCtrl(dialog, value="100")
        divisions_ctrl = wx.SpinCtrl(dialog, min=2, max=20, initial=10)
        rows = {}

        def add_row(key, label, control):
            label_control = wx.StaticText(dialog, label=label)
            grid.Add(label_control, 0, wx.ALIGN_CENTER_VERTICAL)
            grid.Add(control, 1, wx.EXPAND)
            rows[key] = (label_control, control)

        add_row("pid", "Main PID", pid_choice)
        add_row("title", "Widget name", title_ctrl)
        add_row("display", "Display", type_choice)
        add_row("center_pid", "Center PID", center_pid_choice)
        add_row("shape", "Shape", shape_choice)
        add_row("colour", "Colour", colour_choice)
        add_row("width", "Width", width_ctrl)
        add_row("height", "Height", height_ctrl)
        add_row("minimum", "Dial minimum", minimum_ctrl)
        add_row("maximum", "Dial maximum", maximum_ctrl)
        add_row("divisions", "Dial divisions", divisions_ctrl)
        if widget:
            pid = str(widget.get("pid", "")).upper()
            pid_choice.SetSelection(keys.index(pid) if pid in keys else 0)
            center_pid = str(widget.get("center_pid", "")).upper()
            center_pid_choice.SetSelection(keys.index(center_pid) + 1 if center_pid in keys else 0)
            title_ctrl.SetValue(widget.get("title", ""))
            self._set_choice(type_choice, widget.get("type", "Digital"))
            self._set_choice(shape_choice, widget.get("shape", "Rounded"))
            self._set_choice(colour_choice, widget.get("colour", "Blue"))
            width_ctrl.SetValue(int(widget.get("width", 270)))
            height_ctrl.SetValue(int(widget.get("height", 180)))
            minimum_ctrl.SetValue(str(widget.get("minimum", 0)))
            maximum_ctrl.SetValue(str(widget.get("maximum", 100)))
            divisions_ctrl.SetValue(int(widget.get("divisions", 10)))
        else:
            pid_choice.SetSelection(keys.index("010C") if "010C" in keys else 0)
            center_pid_choice.SetSelection(0)
            type_choice.SetStringSelection("Digital")
            shape_choice.SetStringSelection("Rounded")
            colour_choice.SetStringSelection("Blue")

        def update_display_rows(_event=None):
            display = type_choice.GetStringSelection()
            visibility = {
                "center_pid": display == "Combined",
                "minimum": display in ("Dial", "Combined"),
                "maximum": display in ("Dial", "Combined"),
                "divisions": display in ("Dial", "Combined"),
            }
            for key, visible in visibility.items():
                for control in rows[key]:
                    control.Show(visible)
            dialog.Layout()
            dialog.Fit()

        type_choice.Bind(wx.EVT_CHOICE, update_display_rows)
        update_display_rows()
        buttons = dialog.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL)
        root.Add(grid, 1, wx.EXPAND | wx.ALL, 16)
        root.Add(buttons, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 16)
        dialog.SetSizerAndFit(root)
        dialog.SetMinSize((560, -1))
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
        center_selection = center_pid_choice.GetSelection()
        display = type_choice.GetStringSelection()
        width = width_ctrl.GetValue()
        height = height_ctrl.GetValue()
        if shape_choice.GetStringSelection() == "Circle":
            width = height = max(width, height)
        result = {
            "pid": pid,
            "center_pid": (
                keys[center_selection - 1]
                if display == "Combined" and center_selection > 0 else ""
            ),
            "title": title_ctrl.GetValue().strip() or catalog[pid].desc,
            "type": display,
            "shape": shape_choice.GetStringSelection(),
            "colour": colour_choice.GetStringSelection(),
            "width": width, "height": height,
            "minimum": minimum, "maximum": maximum,
            "divisions": divisions_ctrl.GetValue(),
        }
        dialog.Destroy()
        return result

    def OnAddDashboardWidget(self, _event):
        settings = self._dashboard_widget_dialog()
        if not settings:
            return
        settings.update({"id": str(time.time_ns()), "x": 20, "y": 20})
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

    def _move_dashboard_widget_layer(self, widget_id, front):
        widgets = self._dashboard_widgets()
        widget = next((item for item in widgets if item["id"] == widget_id), None)
        if not widget:
            return
        widgets.remove(widget)
        widgets.append(widget) if front else widgets.insert(0, widget)
        self._save_dashboard_layouts()
        self._rebuild_dashboard()

    def _show_dashboard_widget_menu(self, widget_id, tile):
        if not self.dashboard_editing:
            return
        menu = wx.Menu()
        configure = menu.Append(wx.ID_ANY, "Configure")
        front = menu.Append(wx.ID_ANY, "Bring to front")
        back = menu.Append(wx.ID_ANY, "Send to back")
        menu.AppendSeparator()
        delete = menu.Append(wx.ID_ANY, "Delete")
        menu.Bind(wx.EVT_MENU, lambda _event: self._configure_dashboard_widget(widget_id), configure)
        menu.Bind(wx.EVT_MENU, lambda _event: self._move_dashboard_widget_layer(widget_id, True), front)
        menu.Bind(wx.EVT_MENU, lambda _event: self._move_dashboard_widget_layer(widget_id, False), back)
        menu.Bind(wx.EVT_MENU, lambda _event: self._delete_dashboard_widget(widget_id), delete)
        tile.PopupMenu(menu)
        menu.Destroy()

    def _dashboard_pointer_position(self, screen_position):
        client_position = self.dashboard_canvas.ScreenToClient(screen_position)
        logical_position = self.dashboard_canvas.CalcUnscrolledPosition(client_position)
        return logical_position.x, logical_position.y

    def _begin_dashboard_drag(self, widget_id, control, screen_position):
        widget = next(item for item in self._dashboard_widgets() if item["id"] == widget_id)
        pointer_x, pointer_y = self._dashboard_pointer_position(screen_position)
        self.dashboard_drag_id = widget_id
        self.dashboard_drag_capture = control
        self.dashboard_drag_offset = (
            pointer_x - int(widget.get("x", 0)), pointer_y - int(widget.get("y", 0))
        )
        control.Raise()
        if not control.HasCapture():
            control.CaptureMouse()

    def _update_dashboard_drag(self, screen_position):
        if not self.dashboard_drag_id:
            return
        pointer_x, pointer_y = self._dashboard_pointer_position(screen_position)
        x = max(0, pointer_x - self.dashboard_drag_offset[0])
        y = max(0, pointer_y - self.dashboard_drag_offset[1])
        self.dashboard_tiles[self.dashboard_drag_id].SetPosition((x, y))

    def _finish_dashboard_drag(self, screen_position):
        widget_id = self.dashboard_drag_id
        capture = self.dashboard_drag_capture
        self._update_dashboard_drag(screen_position)
        if widget_id:
            tile = self.dashboard_tiles[widget_id]
            x, y = tile.GetPosition()
            widget = next(item for item in self._dashboard_widgets() if item["id"] == widget_id)
            widget["x"], widget["y"] = x, y
            widgets = self._dashboard_widgets()
            widgets.remove(widget)
            widgets.append(widget)
            self._save_dashboard_layouts()
            self._update_dashboard_canvas_size()
        self.dashboard_drag_id = None
        self.dashboard_drag_capture = None
        if capture and capture.HasCapture():
            capture.ReleaseMouse()

    def _cancel_dashboard_drag(self):
        self.dashboard_drag_id = None
        self.dashboard_drag_capture = None

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
            f'Delete the dashboard "{self.dashboard_current}"?', "Dashboard",
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
        menu.AppendSeparator()
        import_item = menu.Append(wx.ID_ANY, "Import layouts")
        export_item = menu.Append(wx.ID_ANY, "Export layouts")
        menu.Bind(wx.EVT_MENU, self._new_dashboard, new_item)
        menu.Bind(wx.EVT_MENU, self._rename_dashboard, rename_item)
        menu.Bind(wx.EVT_MENU, self._delete_dashboard, delete_item)
        menu.Bind(wx.EVT_MENU, self._import_dashboard_layouts, import_item)
        menu.Bind(wx.EVT_MENU, self._export_dashboard_layouts, export_item)
        self.dashboard_manage_button.PopupMenu(menu)
        menu.Destroy()

    def _export_dashboard_layouts(self, _event=None):
        dialog = wx.FileDialog(
            self.frame,
            "Export Dashboard Layouts",
            defaultFile="pyobd-dashboard-layouts.json",
            wildcard="JSON files (*.json)|*.json",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        )
        try:
            if dialog.ShowModal() != wx.ID_OK:
                return
            payload = {
                "format": "pyobd-dashboard-layouts",
                "version": 1,
                "current": self.dashboard_current,
                "layouts": self.dashboard_layouts,
            }
            with open(dialog.GetPath(), "w", encoding="utf-8") as export_file:
                json.dump(payload, export_file, indent=2)
        except OSError as error:
            wx.MessageBox(
                f"Unable to export dashboard layouts.\n\n{error}",
                "Dashboard", wx.OK | wx.ICON_ERROR,
            )
        finally:
            dialog.Destroy()

    def _import_dashboard_layouts(self, _event=None):
        dialog = wx.FileDialog(
            self.frame,
            "Import Dashboard Layouts",
            wildcard="JSON files (*.json)|*.json",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        )
        try:
            if dialog.ShowModal() != wx.ID_OK:
                return
            with open(dialog.GetPath(), "r", encoding="utf-8") as import_file:
                payload = json.load(import_file)
        except (OSError, ValueError) as error:
            wx.MessageBox(
                f"Unable to import dashboard layouts.\n\n{error}",
                "Dashboard", wx.OK | wx.ICON_ERROR,
            )
            return
        finally:
            dialog.Destroy()

        layouts = payload.get("layouts") if isinstance(payload, dict) else None
        if not isinstance(layouts, dict) or not layouts:
            wx.MessageBox(
                "This file does not contain valid pyOBD dashboard layouts.",
                "Dashboard", wx.OK | wx.ICON_ERROR,
            )
            return
        valid_layouts = {
            str(name): layout
            for name, layout in layouts.items()
            if str(name).strip()
            and isinstance(layout, dict)
            and isinstance(layout.get("widgets"), list)
            and all(
                isinstance(widget, dict) and str(widget.get("pid", "")).strip()
                for widget in layout["widgets"]
            )
        }
        if not valid_layouts:
            wx.MessageBox(
                "No valid dashboard layouts were found.",
                "Dashboard", wx.OK | wx.ICON_ERROR,
            )
            return
        duplicates = set(valid_layouts).intersection(self.dashboard_layouts)
        if duplicates and wx.MessageBox(
            "Replace existing dashboards with the same names?",
            "Import Dashboard Layouts",
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION,
        ) != wx.YES:
            valid_layouts = {
                name: layout for name, layout in valid_layouts.items()
                if name not in duplicates
            }
        if not valid_layouts:
            return
        self.dashboard_layouts.update(valid_layouts)
        imported_current = payload.get("current")
        if imported_current in valid_layouts:
            self.dashboard_current = imported_current
        self._migrate_dashboard_layouts()
        self._save_dashboard_layouts()
        self._refresh_dashboard_choices()
        self._rebuild_dashboard()

    def OnDashboardValues(self, event):
        try:
            values = {item["pid"]: item for item in event.data}
            for widget in self._dashboard_widgets():
                tile = self.dashboard_tiles.get(widget["id"])
                if tile:
                    tile.update_values(
                        values.get(widget["pid"]),
                        values.get(widget.get("center_pid")),
                    )
        finally:
            self.dashboard_event_pending = False

    def _reset_dashboard_values(self):
        for tile in self.dashboard_tiles.values():
            tile.update_values(None)
