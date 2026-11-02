"""Qt application entry point for pyOBD v3."""

from pathlib import Path
import sys

from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle

from .app_model import AppModel


def main():
    QQuickStyle.setStyle("Basic")
    app = QGuiApplication(sys.argv)
    app.setApplicationDisplayName("pyOBD v3")
    app.setOrganizationName("Fare Brothers, LLC")

    project_root = Path(__file__).resolve().parent.parent
    icon_path = project_root / "assets" / "pyobd.png"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    engine = QQmlApplicationEngine()
    model = AppModel()
    app.aboutToQuit.connect(model.shutdown)
    engine.rootContext().setContextProperty("appModel", model)
    engine.load(QUrl.fromLocalFile(str(Path(__file__).parent / "ui" / "Main.qml")))
    if not engine.rootObjects():
        return 1
    return app.exec()
