"""Initial observable state boundary for the v3 interface."""

from PySide6.QtCore import Property, QObject, Signal, Slot


class AppModel(QObject):
    pageChanged = Signal()

    def __init__(self):
        super().__init__()
        self._page = "Overview"
        self._telemetry = [
            {"label": "Engine RPM", "value": "2,450", "unit": "RPM", "accent": "#2878f0"},
            {"label": "Vehicle Speed", "value": "52", "unit": "mph", "accent": "#2878f0"},
            {"label": "Coolant", "value": "194", "unit": "°F", "accent": "#25a96b"},
            {"label": "Voltage", "value": "14.2", "unit": "V", "accent": "#25a96b"},
        ]

    @Property(str, notify=pageChanged)
    def page(self):
        return self._page

    @Property("QVariantList", constant=True)
    def telemetry(self):
        return self._telemetry

    @Slot(str)
    def select_page(self, page):
        if page == self._page:
            return
        self._page = page
        self.pageChanged.emit()
