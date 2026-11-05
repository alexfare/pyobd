"""Stable Qt list model for frequently updated live PID values."""

from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt


class LiveDataListModel(QAbstractListModel):
    PID_ROLE = Qt.UserRole + 1
    NAME_ROLE = Qt.UserRole + 2
    VALUE_ROLE = Qt.UserRole + 3
    UNIT_ROLE = Qt.UserRole + 4
    FAVORITE_ROLE = Qt.UserRole + 5
    SELECTED_ROLE = Qt.UserRole + 6

    _ROLE_NAMES = {
        PID_ROLE: b"pid",
        NAME_ROLE: b"sensorName",
        VALUE_ROLE: b"readingValue",
        UNIT_ROLE: b"unit",
        FAVORITE_ROLE: b"favorite",
        SELECTED_ROLE: b"selected",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows = []

    def roleNames(self):
        return self._ROLE_NAMES

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._rows)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(self._rows):
            return None
        row = self._rows[index.row()]
        values = {
            self.PID_ROLE: row.get("pid", ""),
            self.NAME_ROLE: row.get("name", ""),
            self.VALUE_ROLE: row.get("value", "---"),
            self.UNIT_ROLE: row.get("unit", ""),
            self.FAVORITE_ROLE: row.get("favorite", False),
            self.SELECTED_ROLE: row.get("selected", False),
        }
        return values.get(role)

    def update_rows(self, rows):
        rows = [dict(row) for row in rows]
        old_order = [row.get("pid") for row in self._rows]
        new_order = [row.get("pid") for row in rows]
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
                list(self._ROLE_NAMES),
            )
