"""Shared visual theme and small reusable UI helpers."""

import wx


class AppTheme:
    def __init__(self):
        try:
            self.dark = wx.SystemSettings.GetAppearance().IsDark()
        except Exception:
            self.dark = False

        if self.dark:
            self.window = wx.Colour(20, 24, 31)
            self.surface = wx.Colour(30, 36, 46)
            self.surface_alt = wx.Colour(38, 45, 57)
            self.border = wx.Colour(58, 68, 83)
            self.text = wx.Colour(241, 245, 249)
            self.muted = wx.Colour(159, 171, 188)
            self.sidebar = wx.Colour(14, 18, 24)
            self.sidebar_hover = wx.Colour(33, 42, 55)
        else:
            self.window = wx.Colour(244, 247, 251)
            self.surface = wx.Colour(255, 255, 255)
            self.surface_alt = wx.Colour(237, 242, 248)
            self.border = wx.Colour(217, 225, 235)
            self.text = wx.Colour(22, 30, 43)
            self.muted = wx.Colour(91, 105, 124)
            self.sidebar = wx.Colour(22, 30, 43)
            self.sidebar_hover = wx.Colour(38, 50, 68)

        self.accent = wx.Colour(37, 99, 235)
        self.accent_hover = wx.Colour(29, 78, 216)
        self.success = wx.Colour(22, 163, 74)
        self.success_hover = wx.Colour(21, 128, 61)
        self.info = wx.Colour(2, 136, 209)
        self.info_hover = wx.Colour(3, 105, 161)
        self.warning = wx.Colour(217, 119, 6)
        self.danger = wx.Colour(220, 38, 38)
        self.sidebar_text = wx.Colour(226, 232, 240)
        self.sidebar_muted = wx.Colour(148, 163, 184)

    @staticmethod
    def font(size, bold=False):
        weight = wx.FONTWEIGHT_BOLD if bold else wx.FONTWEIGHT_NORMAL
        return wx.Font(size, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, weight)

    def style_list(self, control):
        control.SetBackgroundColour(self.surface)
        control.SetForegroundColour(self.text)


class ModernButton(wx.Control):
    def __init__(
        self,
        parent,
        label,
        theme,
        variant="secondary",
        id=wx.ID_ANY,
        size=wx.DefaultSize,
        align="center",
    ):
        super().__init__(parent, id=id, size=size, style=wx.WANTS_CHARS | wx.BORDER_NONE)
        self.theme = theme
        self.variant = variant
        self.align = align
        self.hovered = False
        self.pressed = False
        self.SetLabel(label)
        self.SetName(label)
        self.SetFont(theme.font(10, bold=True))
        self.SetCursor(wx.Cursor(wx.CURSOR_HAND))
        self.SetBackgroundStyle(wx.BG_STYLE_PAINT)
        self.SetMinSize((88, 40) if size == wx.DefaultSize else size)

        self.Bind(wx.EVT_PAINT, self._on_paint)
        self.Bind(wx.EVT_ENTER_WINDOW, self._on_enter)
        self.Bind(wx.EVT_LEAVE_WINDOW, self._on_leave)
        self.Bind(wx.EVT_LEFT_DOWN, self._on_left_down)
        self.Bind(wx.EVT_LEFT_UP, self._on_left_up)
        self.Bind(wx.EVT_MOUSE_CAPTURE_LOST, self._on_capture_lost)
        self.Bind(wx.EVT_KEY_DOWN, self._on_key_down)
        self.Bind(wx.EVT_SET_FOCUS, self._refresh)
        self.Bind(wx.EVT_KILL_FOCUS, self._refresh)

    def DoGetBestSize(self):
        return wx.Size(max(88, len(self.GetLabel()) * 8 + 32), 40)

    def SetLabel(self, label):
        super().SetLabel(label)
        self.InvalidateBestSize()
        self.Refresh()

    def SetVariant(self, variant):
        if self.variant != variant:
            self.variant = variant
            self.Refresh()

    def Enable(self, enable=True):
        changed = super().Enable(enable)
        self.SetCursor(wx.Cursor(wx.CURSOR_HAND if enable else wx.CURSOR_ARROW))
        self.Refresh()
        return changed

    def _colours(self):
        variants = {
            "primary": (self.theme.accent, self.theme.accent_hover, wx.WHITE, self.theme.accent),
            "success": (self.theme.success, self.theme.success_hover, wx.WHITE, self.theme.success),
            "danger": (self.theme.danger, wx.Colour(185, 28, 28), wx.WHITE, self.theme.danger),
            "sidebar": (self.theme.sidebar, self.theme.sidebar_hover, self.theme.sidebar_text, self.theme.sidebar),
            "sidebar_active": (self.theme.accent, self.theme.accent_hover, wx.WHITE, self.theme.accent),
            "ghost": (self.theme.surface, self.theme.surface_alt, self.theme.text, self.theme.border),
            "secondary": (self.theme.surface_alt, self.theme.border, self.theme.text, self.theme.border),
        }
        if not self.IsEnabled():
            return self.theme.surface_alt, self.theme.surface_alt, self.theme.muted, self.theme.border
        return variants.get(self.variant, variants["secondary"])

    def _on_paint(self, _event):
        dc = wx.AutoBufferedPaintDC(self)
        parent_colour = self.GetParent().GetBackgroundColour()
        dc.SetBackground(wx.Brush(parent_colour))
        dc.Clear()

        normal, hover, foreground, border = self._colours()
        background = hover if self.hovered or self.pressed else normal
        if self.pressed:
            background = background.ChangeLightness(88)

        width, height = self.GetClientSize()
        dc.SetBrush(wx.Brush(background))
        focus_border = self.theme.accent if self.HasFocus() else border
        dc.SetPen(wx.Pen(focus_border, 2 if self.HasFocus() else 1))
        dc.DrawRoundedRectangle(1, 1, max(0, width - 2), max(0, height - 2), 8)

        dc.SetFont(self.GetFont())
        dc.SetTextForeground(foreground)
        text_width, text_height = dc.GetTextExtent(self.GetLabel())
        x = 16 if self.align == "left" else max(0, (width - text_width) // 2)
        y = max(0, (height - text_height) // 2)
        dc.DrawText(self.GetLabel(), x, y)

    def _refresh(self, event):
        self.Refresh()
        event.Skip()

    def _on_enter(self, event):
        if self.IsEnabled():
            self.hovered = True
            self.Refresh()
        event.Skip()

    def _on_leave(self, event):
        self.hovered = False
        self.pressed = False
        self.Refresh()
        event.Skip()

    def _on_left_down(self, _event):
        if not self.IsEnabled():
            return
        self.SetFocus()
        self.pressed = True
        if not self.HasCapture():
            self.CaptureMouse()
        self.Refresh()

    def _on_left_up(self, event):
        if self.HasCapture():
            self.ReleaseMouse()
        activate = self.IsEnabled() and self.pressed and self.GetClientRect().Contains(event.GetPosition())
        self.pressed = False
        self.Refresh()
        if activate:
            self._emit_click()

    def _on_key_down(self, event):
        if self.IsEnabled() and event.GetKeyCode() in (
            wx.WXK_RETURN,
            wx.WXK_NUMPAD_ENTER,
            wx.WXK_SPACE,
        ):
            self._emit_click()
            return
        event.Skip()

    def _on_capture_lost(self, _event):
        self.pressed = False
        self.Refresh()

    def _emit_click(self):
        event = wx.CommandEvent(wx.EVT_BUTTON.typeId, self.GetId())
        event.SetEventObject(self)
        self.ProcessWindowEvent(event)


class ActionCard(wx.Panel):
    def __init__(self, parent, theme, title, description, colour, hover_colour, handler):
        super().__init__(parent, style=wx.WANTS_CHARS | wx.BORDER_NONE)
        self.theme = theme
        self.handler = handler
        self.colour = colour
        self.hover_colour = hover_colour
        self.hovered = False
        self.SetMinSize((220, 92))
        self.SetName(title)
        self.SetBackgroundColour(colour)
        self.SetBackgroundStyle(wx.BG_STYLE_PAINT)

        self.title = wx.StaticText(self, label=title)
        self.title.SetFont(theme.font(15, bold=True))
        self.title.SetForegroundColour(wx.WHITE)
        self.title.SetBackgroundColour(colour)
        self.description = None
        if description:
            self.description = wx.StaticText(self, label=description)
            self.description.SetFont(theme.font(10))
            self.description.SetForegroundColour(wx.Colour(226, 232, 240))
            self.description.SetBackgroundColour(colour)

        content = wx.BoxSizer(wx.VERTICAL)
        content.AddStretchSpacer()
        content.Add(self.title, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.LEFT | wx.RIGHT, 24)
        if self.description:
            content.Add(
                self.description,
                0,
                wx.ALIGN_CENTER_HORIZONTAL | wx.LEFT | wx.RIGHT | wx.TOP,
                24,
            )
        content.AddStretchSpacer()
        self.SetSizer(content)

        for control in (self, self.title, self.description):
            if control is None:
                continue
            control.SetCursor(wx.Cursor(wx.CURSOR_HAND))
            control.Bind(wx.EVT_ENTER_WINDOW, self._on_enter)
            control.Bind(wx.EVT_LEAVE_WINDOW, self._on_leave)
            control.Bind(wx.EVT_LEFT_UP, self._on_activate)

        self.Bind(wx.EVT_PAINT, self._on_paint)
        self.Bind(wx.EVT_SET_FOCUS, self._on_focus)
        self.Bind(wx.EVT_KILL_FOCUS, self._on_focus)
        self.Bind(wx.EVT_KEY_DOWN, self._on_key_down)

    def _on_paint(self, event):
        dc = wx.AutoBufferedPaintDC(self)
        dc.SetBackground(wx.Brush(self.GetParent().GetBackgroundColour()))
        dc.Clear()
        background = self.hover_colour if self.hovered else self.colour
        border = wx.WHITE if self.HasFocus() else background
        dc.SetBrush(wx.Brush(background))
        dc.SetPen(wx.Pen(border, 2 if self.HasFocus() else 1))
        width, height = self.GetClientSize()
        dc.DrawRoundedRectangle(1, 1, max(0, width - 2), max(0, height - 2), 10)

    def _set_hovered(self, hovered):
        if self.hovered == hovered:
            return
        self.hovered = hovered
        background = self.hover_colour if hovered else self.colour
        self.title.SetBackgroundColour(background)
        if self.description:
            self.description.SetBackgroundColour(background)
        self.Refresh()

    def _on_enter(self, event):
        self._set_hovered(True)
        event.Skip()

    def _on_leave(self, event):
        wx.CallAfter(self._sync_hover)
        event.Skip()

    def _sync_hover(self):
        self._set_hovered(self.GetScreenRect().Contains(wx.GetMousePosition()))

    def _on_activate(self, event):
        self.SetFocus()
        self.handler(event)

    def _on_focus(self, event):
        self.Refresh()
        event.Skip()

    def _on_key_down(self, event):
        if event.GetKeyCode() in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER, wx.WXK_SPACE):
            self.handler(event)
            return
        event.Skip()


def build_card(parent, theme):
    card = wx.Panel(parent, style=wx.BORDER_SIMPLE)
    card.SetBackgroundColour(theme.surface)
    card.SetForegroundColour(theme.text)
    return card
