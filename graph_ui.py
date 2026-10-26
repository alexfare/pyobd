"""Graph page UI and interaction logic for pyOBD."""

import json

import wx
from wx.lib import plot as wxplot

import obd
from ui_theme import ModernButton


GRAPH_COLOURS = [
    "#2563EB", "#DC2626", "#16A34A", "#D97706",
    "#7E22CE", "#A16207", "#0891B2", "#DB2777",
]


class GraphUIMixin:
    """Owns graph selection, controls, layout, and rendering."""

    def _build_graph_command_catalog(self):
        excluded = {b"0100", b"0101", b"0120", b"0140", b"0103", b"0102", b"011C", b"0113", b"0141", b"0151"}
        self.graph_command_catalog = [
            command for command in obd.commands[1]
            if command and command.command not in excluded
        ]
        self.graph_command_catalog.append(obd.commands.ELM_VOLTAGE)
        self.graph_command_labels = [
            f"{command.command.decode(errors='ignore')} - {command.desc}"
            for command in self.graph_command_catalog
        ]
        self.selected_graph_commands = []
        self.isolated_graph_command_key = None

    def _load_graph_presets(self):
        try:
            saved = json.loads(self.config.get("pyOBD", "GRAPH_PRESETS", fallback="{}"))
        except (TypeError, ValueError):
            saved = {}
        self.graph_presets = {
            str(name): [str(command) for command in commands]
            for name, commands in saved.items()
            if str(name).strip() and isinstance(commands, list)
        } if isinstance(saved, dict) else {}

    def _save_graph_presets(self):
        if not self.config.has_section("pyOBD"):
            self.config.add_section("pyOBD")
        self.config.set("pyOBD", "GRAPH_PRESETS", json.dumps(self.graph_presets, sort_keys=True))
        try:
            with open(self.configfilepath, "w", encoding="utf-8") as config_file:
                self.config.write(config_file)
        except OSError as error:
            wx.MessageBox(
                f"Unable to save graph presets.\n\n{error}",
                "Graph Presets",
                wx.OK | wx.ICON_ERROR,
            )
            return False
        return True

    def _refresh_graph_preset_choice(self, selected_name=None):
        names = sorted(self.graph_presets, key=str.casefold)
        self.graph_preset_choice.Set(["Select preset"] + names)
        if selected_name in names:
            self.graph_preset_choice.SetSelection(names.index(selected_name) + 1)
        else:
            self.graph_preset_choice.SetSelection(0)

    def _selected_graph_preset_name(self):
        return (
            self.graph_preset_choice.GetStringSelection()
            if self.graph_preset_choice.GetSelection() > 0
            else None
        )

    def _apply_graph_preset(self, name):
        catalog = {
            command.command.decode(errors="ignore").upper(): command
            for command in self.graph_command_catalog
        }
        commands = []
        seen = set()
        for key in self.graph_presets.get(name, []):
            command = catalog.get(key.upper())
            if command and command.command not in seen:
                commands.append(command)
                seen.add(command.command)
        self.selected_graph_commands = commands
        self.isolated_graph_command_key = None
        self._refresh_graph_selection_ui()

    def OnGraphPresetSelected(self, _event):
        name = self._selected_graph_preset_name()
        if name:
            self._apply_graph_preset(name)

    def _save_current_graph_preset(self, _event=None):
        if not self.selected_graph_commands:
            wx.MessageBox(
                "Add at least one PID before saving a preset.",
                "Graph Presets",
                wx.OK | wx.ICON_INFORMATION,
            )
            return
        current_name = self._selected_graph_preset_name() or ""
        dialog = wx.TextEntryDialog(self.frame, "Preset name:", "Save Graph Preset", current_name)
        try:
            if dialog.ShowModal() != wx.ID_OK:
                return
            name = dialog.GetValue().strip()
        finally:
            dialog.Destroy()
        if not name:
            return
        if name in self.graph_presets and wx.MessageBox(
            f'Replace the existing preset "{name}"?',
            "Graph Presets",
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION,
        ) != wx.YES:
            return
        self.graph_presets[name] = [
            command.command.decode(errors="ignore")
            for command in self.selected_graph_commands
        ]
        if self._save_graph_presets():
            self._refresh_graph_preset_choice(name)

    def _rename_graph_preset(self, _event=None):
        old_name = self._selected_graph_preset_name()
        if not old_name:
            return
        dialog = wx.TextEntryDialog(self.frame, "Preset name:", "Rename Graph Preset", old_name)
        try:
            if dialog.ShowModal() != wx.ID_OK:
                return
            new_name = dialog.GetValue().strip()
        finally:
            dialog.Destroy()
        if not new_name or new_name == old_name:
            return
        if new_name in self.graph_presets:
            wx.MessageBox(
                "A preset with that name already exists.",
                "Graph Presets",
                wx.OK | wx.ICON_INFORMATION,
            )
            return
        self.graph_presets[new_name] = self.graph_presets.pop(old_name)
        if self._save_graph_presets():
            self._refresh_graph_preset_choice(new_name)

    def _delete_graph_preset(self, _event=None):
        name = self._selected_graph_preset_name()
        if not name or wx.MessageBox(
            f'Delete the preset "{name}"?',
            "Graph Presets",
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION,
        ) != wx.YES:
            return
        del self.graph_presets[name]
        if self._save_graph_presets():
            self._refresh_graph_preset_choice()

    def OnManageGraphPresets(self, _event):
        menu = wx.Menu()
        save_item = menu.Append(wx.ID_ANY, "Save current as…")
        rename_item = menu.Append(wx.ID_ANY, "Rename selected")
        delete_item = menu.Append(wx.ID_ANY, "Delete selected")
        has_selection = self._selected_graph_preset_name() is not None
        rename_item.Enable(has_selection)
        delete_item.Enable(has_selection)
        self.graph_preset_button.Bind(wx.EVT_MENU, self._save_current_graph_preset, save_item)
        self.graph_preset_button.Bind(wx.EVT_MENU, self._rename_graph_preset, rename_item)
        self.graph_preset_button.Bind(wx.EVT_MENU, self._delete_graph_preset, delete_item)
        self.graph_preset_button.PopupMenu(menu)
        menu.Destroy()

    def _set_graph_streaming(self, enabled):
        self.graph_streaming_enabled = bool(enabled)
        self.graph_has_received_data = False
        if hasattr(self, "graph_play_button"):
            self.graph_play_button.SetLabel(
                "Stop Graph" if self.graph_streaming_enabled else "Start Graph"
            )
            self.graph_play_button.SetVariant("danger" if self.graph_streaming_enabled else "success")

        if not self.graph_streaming_enabled:
            for row in range(self.graph_list_ctrl.GetItemCount()):
                self.graph_list_ctrl.SetItem(row, 2, "---")
            self._clear_graph_canvases()
        if hasattr(self, "graph_status_label"):
            self._update_graph_control_state()

    def _set_graph_connection_state(self, connected):
        self.graph_connected = bool(connected)
        if not self.graph_connected and self.graph_streaming_enabled:
            self._set_graph_streaming(False)
        elif hasattr(self, "graph_status_label"):
            self._update_graph_control_state()

    def _update_graph_control_state(self):
        pid_count = len(self.selected_graph_commands)
        selected_count = len(self._selected_graph_keys())
        self.graph_selection_label.SetLabel(
            f"{pid_count} PID{'s' if pid_count != 1 else ''}  •  "
            f"{selected_count} selected"
        )
        self.remove_graph_pid_button.Enable(selected_count > 0)
        self.graph_play_button.Enable(self.graph_connected and pid_count > 0)

        if not self.graph_connected:
            status = "Disconnected"
            colour = self.theme.muted
            state = "Connect to a vehicle to begin graphing live data."
        elif not pid_count:
            status = "Add PIDs to begin"
            colour = self.theme.muted
            state = "Add one or more PIDs to create a live graph."
        elif self.graph_streaming_enabled:
            status = "●  Live"
            colour = self.theme.success
            state = "Waiting for graph data…"
        else:
            status = "Paused"
            colour = self.theme.warning
            state = "Graph paused. Current selections are ready to start."

        self.graph_status_label.SetLabel(status)
        self.graph_status_label.SetForegroundColour(colour)
        self.graph_state_label.SetLabel(state)
        self.graph_state_label.Show(
            not self.graph_streaming_enabled or not self.graph_has_received_data
        )
        self.graph_panel.Layout()

    def OnToggleGraphStreaming(self, _event):
        if not self.graph_streaming_enabled:
            if not self.selected_graph_commands:
                wx.MessageBox(
                    "Add at least one PID before starting the graph.",
                    "Graph",
                    wx.OK | wx.ICON_INFORMATION,
                )
                return
            self.graph_title_override = None
            self._set_graph_streaming(True)
        else:
            self._set_graph_streaming(False)

    def _selected_graph_keys(self):
        keys = []
        selected = self.graph_list_ctrl.GetFirstSelected()
        while selected != wx.NOT_FOUND:
            if 0 <= selected < len(self.selected_graph_commands):
                keys.append(self.selected_graph_commands[selected].command)
            selected = self.graph_list_ctrl.GetNextSelected(selected)
        return keys

    def _refresh_graph_selection_ui(self):
        selected_keys = set(self._selected_graph_keys()) if hasattr(self, "graph_list_ctrl") else set()
        self.graph_list_ctrl.Freeze()
        self.graph_list_ctrl.DeleteAllItems()
        for index, command in enumerate(self.selected_graph_commands):
            self.graph_list_ctrl.InsertItem(index, command.command.decode(errors="ignore"))
            self.graph_list_ctrl.SetItem(index, 1, command.desc)
            self.graph_list_ctrl.SetItem(index, 2, "---")
            self.graph_list_ctrl.SetItemTextColour(
                index, wx.Colour(GRAPH_COLOURS[index % len(GRAPH_COLOURS)])
            )
            if command.command in selected_keys:
                self.graph_list_ctrl.Select(index)
        self.graph_list_ctrl.Thaw()

        valid_keys = {command.command for command in self.selected_graph_commands}
        if self.isolated_graph_command_key not in valid_keys:
            self.isolated_graph_command_key = None
        if self.graph_individual_mode or self.panel is None:
            self._rebuild_graph_canvases()
        self._update_graph_control_state()

    def _add_graph_commands_by_catalog_indices(self, catalog_indices):
        existing_keys = {command.command for command in self.selected_graph_commands}
        additions = []
        for index in catalog_indices:
            if not 0 <= index < len(self.graph_command_catalog):
                continue
            command = self.graph_command_catalog[index]
            if command.command not in existing_keys:
                additions.append(command)
                existing_keys.add(command.command)

        if additions:
            self.selected_graph_commands.extend(additions)
            self._refresh_graph_selection_ui()
        return len(additions)

    def _show_add_graph_pid_dialog(self):
        dialog = wx.Dialog(self.frame, -1, "Add PID", size=(680, 540))
        dialog.SetBackgroundColour(self.theme.window)
        root = wx.BoxSizer(wx.VERTICAL)
        heading = wx.StaticText(dialog, label="Choose live-data PIDs")
        heading.SetForegroundColour(self.theme.text)
        heading.SetFont(self.theme.font(16, bold=True))
        search_ctrl = wx.SearchCtrl(dialog, style=wx.TE_PROCESS_ENTER)
        search_ctrl.SetDescriptiveText("Search PID or sensor")
        search_ctrl.ShowCancelButton(True)
        list_box = wx.ListBox(dialog, style=wx.LB_EXTENDED)
        list_box.SetBackgroundColour(self.theme.surface)
        list_box.SetForegroundColour(self.theme.text)
        result_label = wx.StaticText(dialog, label="")
        result_label.SetForegroundColour(self.theme.muted)
        add_button = ModernButton(dialog, "Add Selected", self.theme, variant="primary")
        done_button = ModernButton(
            dialog, "Done", self.theme, variant="secondary", id=wx.ID_CANCEL
        )

        button_row = wx.BoxSizer(wx.HORIZONTAL)
        button_row.Add(add_button)
        button_row.AddStretchSpacer()
        button_row.Add(done_button)

        root.Add(heading, 0, wx.LEFT | wx.RIGHT | wx.TOP, 16)
        root.Add(search_ctrl, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 16)
        root.Add(result_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 16)
        root.Add(list_box, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 16)
        root.Add(button_row, 0, wx.EXPAND | wx.ALL, 16)
        dialog.SetSizer(root)

        filtered_indices = []
        selected_catalog_indices = set()

        def current_catalog_indices():
            return [
                filtered_indices[index]
                for index in list_box.GetSelections()
                if 0 <= index < len(filtered_indices)
            ]

        def update_filter(_event=None):
            selected_catalog_indices.update(current_catalog_indices())
            query = search_ctrl.GetValue().strip().lower()
            filtered_indices.clear()
            labels = []
            existing_keys = {command.command for command in self.selected_graph_commands}
            for index, label in enumerate(self.graph_command_labels):
                command = self.graph_command_catalog[index]
                if command.command not in existing_keys and (not query or query in label.lower()):
                    filtered_indices.append(index)
                    labels.append(label)
            list_box.Freeze()
            list_box.Set(labels)
            for view_index, catalog_index in enumerate(filtered_indices):
                if catalog_index in selected_catalog_indices:
                    list_box.SetSelection(view_index)
            list_box.Thaw()
            result_label.SetLabel(f"{len(filtered_indices)} available PIDs")

        def add_selected(_event=None):
            selected_catalog_indices.update(current_catalog_indices())
            if not selected_catalog_indices:
                wx.MessageBox("Select at least one PID to add.", "Graph", wx.OK | wx.ICON_INFORMATION)
                return
            self._add_graph_commands_by_catalog_indices(sorted(selected_catalog_indices))
            selected_catalog_indices.clear()
            update_filter()
            search_ctrl.SetFocus()

        search_ctrl.Bind(wx.EVT_TEXT, update_filter)
        add_button.Bind(wx.EVT_BUTTON, add_selected)
        done_button.Bind(wx.EVT_BUTTON, lambda _event: dialog.EndModal(wx.ID_CANCEL))
        list_box.Bind(wx.EVT_LISTBOX_DCLICK, add_selected)
        self.graph_interaction_paused = True
        try:
            update_filter()
            search_ctrl.SetFocus()
            dialog.ShowModal()
        finally:
            self.graph_interaction_paused = False
            dialog.Destroy()

    def OnAddGraphPid(self, _event):
        self._show_add_graph_pid_dialog()

    def OnRemoveGraphPid(self, _event):
        selected_indices = []
        selected = self.graph_list_ctrl.GetFirstSelected()
        while selected != wx.NOT_FOUND:
            selected_indices.append(selected)
            selected = self.graph_list_ctrl.GetNextSelected(selected)

        if not selected_indices:
            return

        self._clear_graph_selection()
        for index in reversed(selected_indices):
            if 0 <= index < len(self.selected_graph_commands):
                del self.selected_graph_commands[index]
        self._refresh_graph_selection_ui()

    def _toggle_graph_row_selection(self, index):
        if not 0 <= index < self.graph_list_ctrl.GetItemCount():
            return
        is_selected = bool(self.graph_list_ctrl.GetItemState(index, wx.LIST_STATE_SELECTED))
        self.graph_list_ctrl.Select(index, not is_selected)
        self._update_graph_control_state()

    def OnGraphListClick(self, event):
        index, _flags = self.graph_list_ctrl.HitTest(event.GetPosition())
        if index == wx.NOT_FOUND:
            event.Skip()
            return
        # Consume the native click so choosing one row does not clear other rows.
        self._toggle_graph_row_selection(index)

    def OnGraphViewToggle(self, _event):
        self.graph_individual_mode = not self.graph_individual_mode
        self.isolated_graph_command_key = None
        self._update_graph_view_button()
        self._rebuild_graph_canvases()

    def _update_graph_view_button(self):
        if self.graph_individual_mode:
            self.graph_view_button.SetLabel("≋")
            self.graph_view_button.SetToolTip("Show all PIDs on one combined graph")
        else:
            self.graph_view_button.SetLabel("▦")
            self.graph_view_button.SetToolTip("Show one graph for each PID")

    def _clear_graph_selection(self):
        for index in range(self.graph_list_ctrl.GetItemCount()):
            self.graph_list_ctrl.Select(index, False)
        self._update_graph_control_state()

    def _on_graph_selection_changed(self, event):
        wx.CallAfter(self._update_graph_control_state)
        event.Skip()

    def _isolate_graph_index(self, index):
        if not 0 <= index < len(self.selected_graph_commands):
            return
        self.isolated_graph_command_key = self.selected_graph_commands[index].command
        self.graph_individual_mode = False
        self._update_graph_view_button()
        self._rebuild_graph_canvases()

    def _show_all_graphs(self):
        self.isolated_graph_command_key = None
        self._rebuild_graph_canvases()

    def OnGraphListRightClick(self, event):
        index = event.GetIndex()
        if not 0 <= index < len(self.selected_graph_commands):
            return
        if not self.graph_list_ctrl.IsSelected(index):
            self.graph_list_ctrl.Select(index, True)

        menu = wx.Menu()
        isolate_item = menu.Append(wx.ID_ANY, "Isolate on Graph")
        show_all_item = menu.Append(wx.ID_ANY, "Show All on Graph")
        menu.AppendSeparator()
        delete_item = menu.Append(wx.ID_ANY, "Delete Selected")
        clear_item = menu.Append(wx.ID_ANY, "Clear Selection")

        self.graph_list_ctrl.Bind(wx.EVT_MENU, lambda _evt: self._isolate_graph_index(index), isolate_item)
        self.graph_list_ctrl.Bind(wx.EVT_MENU, lambda _evt: self._show_all_graphs(), show_all_item)
        self.graph_list_ctrl.Bind(wx.EVT_MENU, self.OnRemoveGraphPid, delete_item)
        self.graph_list_ctrl.Bind(wx.EVT_MENU, lambda _evt: self._clear_graph_selection(), clear_item)
        self.graph_list_ctrl.PopupMenu(menu)
        menu.Destroy()

    def _clear_graph_host(self):
        if not hasattr(self, "graph_plot_sizer"):
            return
        self.graph_plot_sizer.Clear(delete_windows=True)
        self.panel = None
        self.individual_graph_canvases = []

    def _new_plot_canvas(self, minimum_height=260):
        canvas = wxplot.PlotCanvas(self.graph_plot_host)
        canvas.SetMinSize((-1, minimum_height))
        self.graph_plot_sizer.Add(canvas, 1 if minimum_height >= 300 else 0, wx.EXPAND | wx.ALL, 4)
        return canvas

    def _rebuild_graph_canvases(self):
        if not hasattr(self, "graph_plot_host"):
            return
        self._clear_graph_host()
        if self.graph_individual_mode:
            for _command in self.selected_graph_commands:
                self.individual_graph_canvases.append(self._new_plot_canvas(220))
        else:
            self.panel = self._new_plot_canvas(320)
        self.graph_plot_host.SetScrollRate(10, 10)
        self.graph_plot_host.FitInside()
        self.graph_plot_host.Layout()

    def _clear_graph_canvases(self):
        canvases = list(getattr(self, "individual_graph_canvases", []))
        panel = getattr(self, "panel", None)
        if panel is not None:
            canvases.append(panel)
        for canvas in canvases:
            try:
                canvas.Clear()
            except Exception:
                pass

    def build_graph_page(self):
        self.graph_panel = wx.Panel(self.nb)
        self.graph_panel.SetBackgroundColour(self.theme.window)
        root = wx.BoxSizer(wx.VERTICAL)
        toolbar_panel = wx.Panel(self.graph_panel)
        toolbar_panel.SetBackgroundColour(self.theme.surface)
        toolbar_root = wx.BoxSizer(wx.VERTICAL)
        status_row = wx.BoxSizer(wx.HORIZONTAL)
        toolbar = wx.BoxSizer(wx.HORIZONTAL)

        self.graph_status_label = wx.StaticText(toolbar_panel, label="Disconnected")
        self.graph_status_label.SetForegroundColour(self.theme.muted)
        self.graph_status_label.SetFont(self.theme.font(10, bold=True))
        self.graph_selection_label = wx.StaticText(toolbar_panel, label="0 PIDs  •  0 selected")
        self.graph_selection_label.SetForegroundColour(self.theme.muted)
        status_row.Add(self.graph_status_label, 1, wx.ALIGN_CENTER_VERTICAL)
        status_row.Add(self.graph_selection_label, 0, wx.ALIGN_CENTER_VERTICAL)

        self.add_graph_pid_button = ModernButton(
            toolbar_panel, "Add PID", self.theme, variant="primary"
        )
        self.remove_graph_pid_button = ModernButton(
            toolbar_panel, "Remove Selected", self.theme, variant="danger"
        )
        self.remove_graph_pid_button.SetMinSize((160, 40))
        self.graph_play_button = ModernButton(
            toolbar_panel, "Start Graph", self.theme, variant="success"
        )
        self.graph_play_button.SetMinSize((120, 40))
        self.graph_preset_choice = wx.Choice(toolbar_panel, choices=["Select preset"])
        self.graph_preset_choice.SetMinSize((170, 40))
        self.graph_preset_button = ModernButton(
            toolbar_panel, "Manage", self.theme, variant="secondary"
        )
        self.graph_preset_button.SetToolTip("Save, rename, or delete graph presets")
        self.graph_view_button = ModernButton(
            toolbar_panel, "▦", self.theme, variant="secondary", size=(48, 42)
        )
        self.graph_individual_mode = False
        view_font = self.graph_view_button.GetFont()
        view_font.SetPointSize(18)
        self.graph_view_button.SetFont(view_font)

        toolbar.Add(self.add_graph_pid_button, 0, wx.RIGHT, 8)
        toolbar.Add(self.remove_graph_pid_button, 0, wx.RIGHT, 8)
        toolbar.Add(self.graph_play_button, 0, wx.RIGHT, 16)
        toolbar.AddStretchSpacer(1)
        toolbar.Add(self.graph_preset_choice, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        toolbar.Add(self.graph_preset_button, 0, wx.RIGHT, 8)
        toolbar.Add(self.graph_view_button, 0, wx.ALIGN_CENTER_VERTICAL)
        toolbar_root.Add(status_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 10)
        toolbar_root.Add(toolbar, 0, wx.EXPAND | wx.ALL, 10)
        toolbar_panel.SetSizer(toolbar_root)

        self.graph_list_ctrl = self.MyListCtrl(
            self.graph_panel,
            wx.NewIdRef(),
            style=wx.LC_REPORT | wx.BORDER_NONE | wx.LC_HRULES,
        )
        self.graph_list_ctrl.InsertColumn(0, "PID", width=80)
        self.graph_list_ctrl.InsertColumn(1, "Sensor", width=360)
        self.graph_list_ctrl.InsertColumn(2, "Value", width=180)
        self.graph_list_ctrl.SetMinSize((-1, 170))
        self.graph_list_ctrl.SetToolTip(
            "Click rows to select or unselect them. Right-click a row for graph actions."
        )

        self.graph_state_label = wx.StaticText(
            self.graph_panel,
            label="Connect to a vehicle to begin graphing live data.",
        )
        self.graph_state_label.SetForegroundColour(self.theme.muted)
        self.graph_state_label.SetFont(self.theme.font(11))

        self.graph_plot_host = wx.ScrolledWindow(self.graph_panel, style=wx.VSCROLL)
        self.graph_plot_sizer = wx.BoxSizer(wx.VERTICAL)
        self.graph_plot_host.SetSizer(self.graph_plot_sizer)
        self.individual_graph_canvases = []

        root.AddSpacer(8)
        root.Add(toolbar_panel, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 20)
        root.Add(self.graph_list_ctrl, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 20)
        root.Add(self.graph_state_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 20)
        root.Add(self.graph_plot_host, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 16)
        self.graph_panel.SetSizer(root)

        self._build_graph_command_catalog()
        self._load_graph_presets()
        self._refresh_graph_preset_choice()
        self.graph_streaming_enabled = False
        self.graph_connected = False
        self.graph_has_received_data = False
        self.graph_interaction_paused = False
        self.graph_event_pending = False
        self.add_graph_pid_button.Bind(wx.EVT_BUTTON, self.OnAddGraphPid)
        self.remove_graph_pid_button.Bind(wx.EVT_BUTTON, self.OnRemoveGraphPid)
        self.graph_play_button.Bind(wx.EVT_BUTTON, self.OnToggleGraphStreaming)
        self.graph_preset_choice.Bind(wx.EVT_CHOICE, self.OnGraphPresetSelected)
        self.graph_preset_button.Bind(wx.EVT_BUTTON, self.OnManageGraphPresets)
        self.graph_view_button.Bind(wx.EVT_BUTTON, self.OnGraphViewToggle)
        self.graph_list_ctrl.Bind(wx.EVT_LEFT_DOWN, self.OnGraphListClick)
        self.graph_list_ctrl.Bind(wx.EVT_LIST_ITEM_SELECTED, self._on_graph_selection_changed)
        self.graph_list_ctrl.Bind(wx.EVT_LIST_ITEM_DESELECTED, self._on_graph_selection_changed)
        self.graph_list_ctrl.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK, self.OnGraphListRightClick)

        self.nb.AddPage(self.graph_panel, "Graph")
        self._update_graph_view_button()
        self._rebuild_graph_canvases()
        self._set_graph_streaming(False)

    def _draw_series(self, canvas, series_list, title, graph_counter):
        lines = []
        for index, series in enumerate(series_list):
            xy_data = list(zip(series[0], series[1]))
            if len(xy_data) < 2:
                continue
            lines.append(wxplot.PolyLine(
                xy_data,
                colour=GRAPH_COLOURS[index % len(GRAPH_COLOURS)],
                width=2,
                style=wx.PENSTYLE_SOLID,
            ))
        if not lines:
            canvas.Clear()
            return
        graphics = wxplot.PlotGraphics(lines, title, "frame", "value")
        canvas.Draw(graphics, xAxis=(max(0, graph_counter - 450), max(1, graph_counter)))

    def OnGraph(self, event):
        plot_series, graph_counter, _first_time = event.data
        if not self.graph_streaming_enabled:
            self.graph_event_pending = False
            return

        try:
            if plot_series and not self.graph_has_received_data:
                self.graph_has_received_data = True
                self.graph_state_label.Hide()
                self.graph_panel.Layout()
            if self.graph_individual_mode:
                if len(self.individual_graph_canvases) != len(self.selected_graph_commands):
                    self._rebuild_graph_canvases()
                series_by_key = {series[4]: series for series in plot_series}
                for index, command in enumerate(self.selected_graph_commands):
                    series = series_by_key.get(command.command)
                    self._draw_series(
                        self.individual_graph_canvases[index],
                        [series] if series else [],
                        command.desc,
                        graph_counter,
                    )
            else:
                visible_series = plot_series
                title = getattr(self, "graph_title_override", None) or "Live Graphs"
                if self.isolated_graph_command_key is not None:
                    visible_series = [
                        series for series in plot_series
                        if series[4] == self.isolated_graph_command_key
                    ]
                    if visible_series:
                        title = visible_series[0][3]
                self._draw_series(self.panel, visible_series, title, graph_counter)
        except Exception:
            self._clear_graph_canvases()
        finally:
            self.graph_event_pending = False

    def OnGraphValue(self, event):
        command_key, column, value = event.data
        for row, command in enumerate(self.selected_graph_commands):
            if command.command == command_key:
                if row < self.graph_list_ctrl.GetItemCount():
                    self.graph_list_ctrl.SetItem(row, column, value)
                return

