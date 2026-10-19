"""Recorded diagnostic session management."""

import datetime
import json
import os
import re
import shutil

import wx

from ui_theme import ModernButton


class SessionUIMixin:
    def _session_directory(self):
        path = os.path.join(wx.StandardPaths.Get().GetUserDataDir(), "sessions")
        os.makedirs(path, exist_ok=True)
        return path

    @staticmethod
    def _session_metadata_path(csv_path):
        return os.path.splitext(csv_path)[0] + ".json"

    def _write_session_metadata(self, session):
        with open(session["metadata_path"], "w", encoding="utf-8") as metadata_file:
            json.dump(
                {
                    key: value
                    for key, value in session.items()
                    if key not in {"metadata_path", "csv_path"}
                },
                metadata_file,
                indent=2,
            )

    def _active_session_vehicle(self):
        profile = self.vehicle_profiles.get(self.active_vehicle_profile, {})
        return self._vehicle_profile_name(profile) if profile else "Unassigned"

    def _begin_recording_session(self, name):
        stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        safe_name = re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip("-.") or "session"
        csv_path = os.path.join(self._session_directory(), f"{stamp}-{safe_name}.csv")
        session = {
            "name": name,
            "file": os.path.basename(csv_path),
            "started_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
            "ended_at": "",
            "vehicle": self._active_session_vehicle(),
            "samples": 0,
            "duration_seconds": 0,
            "metadata_path": self._session_metadata_path(csv_path),
        }
        self._write_session_metadata(session)
        return csv_path, session

    def _finish_recording_session(self, session, samples, duration_seconds):
        if not session:
            return
        session["ended_at"] = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
        session["samples"] = samples
        session["duration_seconds"] = round(duration_seconds, 3)
        try:
            self._write_session_metadata(session)
        except OSError:
            pass
        self._refresh_session_list()

    def _discard_recording_session(self, session):
        if not session:
            return
        for path in (
            os.path.join(self._session_directory(), session.get("file", "")),
            session.get("metadata_path", ""),
        ):
            if path and os.path.isfile(path):
                try:
                    os.remove(path)
                except OSError:
                    pass

    def _load_recorded_sessions(self):
        sessions = []
        try:
            filenames = os.listdir(self._session_directory())
        except OSError:
            return sessions
        for filename in filenames:
            if not filename.endswith(".json"):
                continue
            metadata_path = os.path.join(self._session_directory(), filename)
            try:
                with open(metadata_path, "r", encoding="utf-8") as metadata_file:
                    session = json.load(metadata_file)
            except (OSError, ValueError):
                continue
            if not isinstance(session, dict):
                continue
            stored_file = os.path.basename(session.get("file", ""))
            if not stored_file:
                continue
            csv_path = os.path.join(self._session_directory(), stored_file)
            if not os.path.isfile(csv_path):
                continue
            session["metadata_path"] = metadata_path
            session["csv_path"] = csv_path
            active_session = getattr(self, "sensor_record_session", None) or {}
            if active_session.get("metadata_path") == metadata_path:
                continue
            sessions.append(session)
        return sorted(sessions, key=lambda item: item.get("started_at", ""), reverse=True)

    @staticmethod
    def _session_date_label(value):
        try:
            return datetime.datetime.fromisoformat(value).strftime("%b %d, %Y  %I:%M %p")
        except (TypeError, ValueError):
            return "Unknown"

    @staticmethod
    def _session_duration_label(seconds):
        seconds = max(0, int(seconds or 0))
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}" if hours else f"{minutes:02d}:{seconds:02d}"

    def _refresh_session_list(self):
        if not hasattr(self, "session_list"):
            return
        self.recorded_sessions = self._load_recorded_sessions()
        self.session_list.Freeze()
        self.session_list.DeleteAllItems()
        for session in self.recorded_sessions:
            index = self.session_list.InsertItem(
                self.session_list.GetItemCount(), session.get("name", "Untitled session")
            )
            self.session_list.SetItem(index, 1, session.get("vehicle", "Unassigned"))
            self.session_list.SetItem(index, 2, self._session_date_label(session.get("started_at")))
            self.session_list.SetItem(index, 3, str(session.get("samples", 0)))
            self.session_list.SetItem(index, 4, self._session_duration_label(session.get("duration_seconds")))
        self.session_list.Thaw()
        count = len(self.recorded_sessions)
        self.session_status_label.SetLabel(f"{count} recorded session{'s' if count != 1 else ''}")

    def _selected_recorded_session(self):
        index = self.session_list.GetFirstSelected()
        if index == -1 or index >= len(self.recorded_sessions):
            return None
        return self.recorded_sessions[index]

    def OnRenameSession(self, _event):
        session = self._selected_recorded_session()
        if not session:
            return
        dialog = wx.TextEntryDialog(
            self.frame, "Enter a new session name.", "Rename session", session.get("name", "")
        )
        try:
            if dialog.ShowModal() != wx.ID_OK or not dialog.GetValue().strip():
                return
            session["name"] = dialog.GetValue().strip()
            self._write_session_metadata(session)
        finally:
            dialog.Destroy()
        self._refresh_session_list()

    def OnExportSession(self, _event):
        session = self._selected_recorded_session()
        if not session:
            return
        safe_name = re.sub(r"[^A-Za-z0-9._-]+", "-", session.get("name", "session")).strip("-.")
        dialog = wx.FileDialog(
            self.frame,
            "Export recorded session",
            defaultDir=wx.StandardPaths.Get().GetDocumentsDir(),
            defaultFile=f"{safe_name or 'session'}.csv",
            wildcard="CSV files (*.csv)|*.csv",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        )
        try:
            if dialog.ShowModal() != wx.ID_OK:
                return
            shutil.copy2(session["csv_path"], dialog.GetPath())
        except OSError as error:
            wx.MessageBox(f"Unable to export the session.\n\n{error}", "Sessions", wx.OK | wx.ICON_ERROR)
        finally:
            dialog.Destroy()

    def OnDeleteSession(self, _event):
        session = self._selected_recorded_session()
        if not session:
            return
        if wx.MessageBox(
            f'Delete "{session.get("name", "Untitled session")}"?',
            "Delete session",
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING,
        ) != wx.YES:
            return
        for path in (session["csv_path"], session["metadata_path"]):
            try:
                os.remove(path)
            except OSError:
                pass
        self._refresh_session_list()

    def build_sessions_page(self):
        self.sessions_panel = wx.Panel(self.nb)
        self.sessions_panel.SetBackgroundColour(self.theme.window)

        self.session_status_label = wx.StaticText(self.sessions_panel, label="No recorded sessions")
        self.session_status_label.SetForegroundColour(self.theme.muted)
        rename_button = ModernButton(self.sessions_panel, "Rename", self.theme, variant="secondary")
        export_button = ModernButton(self.sessions_panel, "Export", self.theme, variant="primary")
        delete_button = ModernButton(self.sessions_panel, "Delete", self.theme, variant="danger")

        toolbar = wx.BoxSizer(wx.HORIZONTAL)
        toolbar.Add(self.session_status_label, 0, wx.ALIGN_CENTER_VERTICAL)
        toolbar.AddStretchSpacer()
        toolbar.Add(rename_button, 0, wx.RIGHT, 8)
        toolbar.Add(export_button, 0, wx.RIGHT, 8)
        toolbar.Add(delete_button)

        self.session_list = self.MyListCtrl(
            self.sessions_panel,
            wx.NewIdRef(),
            style=wx.LC_REPORT | wx.BORDER_NONE | wx.LC_HRULES | wx.LC_SINGLE_SEL,
        )
        self.session_list.InsertColumn(0, "Session", width=280)
        self.session_list.InsertColumn(1, "Vehicle", width=200)
        self.session_list.InsertColumn(2, "Recorded", width=190)
        self.session_list.InsertColumn(3, "Samples", format=wx.LIST_FORMAT_RIGHT, width=100)
        self.session_list.InsertColumn(4, "Duration", format=wx.LIST_FORMAT_RIGHT, width=100)
        self.theme.style_list(self.session_list)

        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(toolbar, 0, wx.EXPAND | wx.ALL, 16)
        root.Add(self.session_list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 16)
        self.sessions_panel.SetSizer(root)
        self.nb.AddPage(self.sessions_panel, "Sessions")

        rename_button.Bind(wx.EVT_BUTTON, self.OnRenameSession)
        export_button.Bind(wx.EVT_BUTTON, self.OnExportSession)
        delete_button.Bind(wx.EVT_BUTTON, self.OnDeleteSession)
        self._refresh_session_list()
