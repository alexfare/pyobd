"""About page and shared program information."""

import os
import sys

import wx
import webbrowser


APP_VERSION = "2.3.0"
PROJECT_URL = "https://github.com/alexfare/pyobd"
RELEASES_URL = f"{PROJECT_URL}/releases/latest"
ISSUES_URL = f"{PROJECT_URL}/issues"
APP_DESCRIPTION = (
    "Open-source OBD-II diagnostics for viewing live vehicle data, custom dashboards, "
    "graphs, readiness monitors, freeze-frame data, and diagnostic trouble codes."
)
CREDITS_TEXT = (
    "Maintained by FareBrothers, LLC\n"
    "Based on work by Jure Poljsak, SeCons Ltd., and Charles Donour Sizemore"
)
LICENSE_SUMMARY = (
    "pyOBD is free software licensed under GPL-2.0. You may redistribute and modify it "
    "under the terms of that license. It comes with absolutely no warranty."
)

ABOUT_DIALOG_TEXT = f"""pyOBD v{APP_VERSION}
Open-source OBD-II diagnostics

{APP_DESCRIPTION}

Credits
{CREDITS_TEXT}

Project source: {PROJECT_URL}
Releases: {RELEASES_URL}
Report an issue: {ISSUES_URL}

{LICENSE_SUMMARY}
See COPYING and THIRD_PARTY_NOTICES.md for complete licensing information.
"""


def _bundled_text(filename, fallback):
    base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    try:
        with open(os.path.join(base_path, filename), "r", encoding="utf-8") as text_file:
            return text_file.read()
    except OSError:
        return fallback


def _show_text(parent, title, text):
    dialog = wx.Dialog(parent, title=title, size=(760, 600))
    root = wx.BoxSizer(wx.VERTICAL)
    license_text = wx.TextCtrl(
        dialog,
        value=text,
        style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_DONTWRAP,
    )
    buttons = dialog.CreateStdDialogButtonSizer(wx.OK)
    root.Add(license_text, 1, wx.EXPAND | wx.ALL, 12)
    root.Add(buttons, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)
    dialog.SetSizer(root)
    dialog.ShowModal()
    dialog.Destroy()


def build_about_page(notebook):
    panel = wx.ScrolledWindow(notebook, style=wx.VSCROLL)
    panel.SetScrollRate(10, 10)
    panel.SetMinSize((640, 420))
    root = wx.BoxSizer(wx.VERTICAL)

    def add_link(label, url, bottom=8):
        link = wx.StaticText(panel, label=label)
        link.SetForegroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_HOTLIGHT))
        link_font = link.GetFont()
        link_font.SetUnderlined(True)
        link.SetFont(link_font)
        link.SetCursor(wx.Cursor(wx.CURSOR_HAND))
        link.Bind(wx.EVT_LEFT_UP, lambda _event, target=url: webbrowser.open(target))
        root.Add(link, 0, wx.BOTTOM, bottom)

    def add_section_title(label):
        section = wx.StaticText(panel, label=label)
        section.SetFont(wx.Font(14, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        root.Add(section, 0, wx.TOP | wx.BOTTOM, 8)

    title = wx.StaticText(panel, label="pyOBD")
    title.SetFont(wx.Font(22, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))

    version = wx.StaticText(panel, label=f"Version {APP_VERSION}  •  Desktop")
    version.SetForegroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT))

    intro = wx.StaticText(
        panel,
        label=APP_DESCRIPTION,
    )
    intro.Wrap(760)

    credits = wx.StaticText(
        panel,
        label=CREDITS_TEXT,
    )
    credits.Wrap(760)

    license_summary = wx.StaticText(
        panel,
        label=LICENSE_SUMMARY,
    )
    license_summary.Wrap(760)

    license_link = wx.StaticText(panel, label="View GNU GPL-2.0 License")
    license_link.SetForegroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_HOTLIGHT))
    license_font = license_link.GetFont()
    license_font.SetUnderlined(True)
    license_link.SetFont(license_font)
    license_link.SetCursor(wx.Cursor(wx.CURSOR_HAND))
    license_link.Bind(
        wx.EVT_LEFT_UP,
        lambda _event: _show_text(
            panel,
            "GNU General Public License v2.0",
            _bundled_text("COPYING", "The GPL-2.0 license file could not be opened."),
        ),
    )

    notices_link = wx.StaticText(panel, label="View Third-Party Software Notices")
    notices_link.SetForegroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_HOTLIGHT))
    notices_link.SetFont(license_font)
    notices_link.SetCursor(wx.Cursor(wx.CURSOR_HAND))
    notices_link.Bind(
        wx.EVT_LEFT_UP,
        lambda _event: _show_text(
            panel,
            "Third-Party Software Notices",
            _bundled_text(
                "THIRD_PARTY_NOTICES.md",
                "The third-party notices file could not be opened.",
            ),
        ),
    )

    root.Add(title, 0, wx.BOTTOM, 4)
    root.Add(version, 0, wx.BOTTOM, 16)
    root.Add(intro, 0, wx.BOTTOM, 14)
    add_section_title("Project")
    add_link("View source code", PROJECT_URL)
    add_link("Download the latest release", RELEASES_URL)
    add_link("Report an issue", ISSUES_URL, bottom=12)
    add_section_title("Credits")
    root.Add(credits, 0, wx.BOTTOM, 12)
    add_section_title("Open-source licenses")
    root.Add(license_summary, 0, wx.BOTTOM, 10)
    root.Add(license_link, 0, wx.BOTTOM, 8)
    root.Add(notices_link)
    panel.SetSizer(root)
    root.SetMinSize((800, 620))
    panel.SetVirtualSize(root.GetMinSize())
    notebook.AddPage(panel, "About")
    return panel
