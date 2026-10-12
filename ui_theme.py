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


def build_card(parent, theme):
    card = wx.Panel(parent, style=wx.BORDER_SIMPLE)
    card.SetBackgroundColour(theme.surface)
    card.SetForegroundColour(theme.text)
    return card
