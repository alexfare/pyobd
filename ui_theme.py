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


class ActionCard(wx.Panel):
    def __init__(self, parent, theme, title, description, colour, hover_colour, handler):
        super().__init__(parent, style=wx.WANTS_CHARS | wx.BORDER_NONE)
        self.theme = theme
        self.handler = handler
        self.colour = colour
        self.hover_colour = hover_colour
        self.hovered = False
        self.SetMinSize((260, 110))
        self.SetName(title)
        self.SetBackgroundColour(colour)
        self.SetBackgroundStyle(wx.BG_STYLE_PAINT)

        self.title = wx.StaticText(self, label=title)
        self.title.SetFont(theme.font(15, bold=True))
        self.title.SetForegroundColour(wx.WHITE)
        self.title.SetBackgroundColour(colour)
        self.description = wx.StaticText(self, label=description)
        self.description.SetFont(theme.font(10))
        self.description.SetForegroundColour(wx.Colour(226, 232, 240))
        self.description.SetBackgroundColour(colour)

        content = wx.BoxSizer(wx.VERTICAL)
        content.AddStretchSpacer()
        content.Add(self.title, 0, wx.LEFT | wx.RIGHT, 24)
        content.Add(self.description, 0, wx.LEFT | wx.RIGHT | wx.TOP, 24)
        content.AddStretchSpacer()
        self.SetSizer(content)

        for control in (self, self.title, self.description):
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
