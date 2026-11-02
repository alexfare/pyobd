"""Stable Qt list model for dashboard widgets."""

from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt


class DashboardListModel(QAbstractListModel):
    ROLE_NAMES = (
        "widgetId", "pid", "title", "style", "minimum", "maximum",
        "xPosition", "yPosition", "widgetWidth", "widgetHeight", "layerValue",
        "readingValue", "unit", "numericValue",
    )
    ROLE_MAP = {
        Qt.UserRole + index + 1: name.encode()
        for index, name in enumerate(ROLE_NAMES)
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows = []

    def roleNames(self):
        return self.ROLE_MAP

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._rows)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(self._rows):
            return None
        name = self.ROLE_MAP.get(role)
        if name is None:
            return None
        return self._rows[index.row()].get(name.decode())

    def update_rows(self, rows):
        rows = [dict(row) for row in rows]
        old_order = [row.get("widgetId") for row in self._rows]
        new_order = [row.get("widgetId") for row in rows]
        if old_order != new_order:
            self.beginResetModel()
            self._rows = rows
            self.endResetModel()
            return
        changed = []
        for index, row in enumerate(rows):
            if self._rows[index] != row:
                self._rows[index] = row
                changed.append(index)
        if changed:
            self.dataChanged.emit(
                self.index(min(changed), 0),
                self.index(max(changed), 0),
                list(self.ROLE_MAP),
            )
