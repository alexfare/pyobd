import os
import sys
import tempfile
import time
import unittest
from unittest import mock

import wx

from pyobd import MyApp


@unittest.skipIf(
    sys.platform.startswith("linux") and not os.environ.get("DISPLAY"),
    "A display is required for the wx UI smoke test",
)
class DemoUISmokeTests(unittest.TestCase):
    def _pump_until(self, predicate, timeout=5):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            wx.YieldIfNeeded()
            if predicate():
                return True
            time.sleep(0.02)
        return False

    def test_demo_connect_navigate_refresh_disconnect_and_close(self):
        with tempfile.TemporaryDirectory() as directory:
            config_path = os.path.join(directory, "pyobd.ini")
            with open(config_path, "w", encoding="utf-8") as config:
                config.write(
                    "[pyOBD]\n"
                    "COMPORT = DEMO\n"
                    "CONNECTION_TYPE = DEMO\n"
                    "CONNECTION_TARGET =\n"
                    "RECONNATTEMPTS = 1\n"
                    "SERTIMEOUT = 1\n"
                    "BAUDRATE = AUTO\n"
                    "FAST = FAST\n"
                    "MEASUREMENT_SYSTEM = IMPERIAL\n"
                )

            with mock.patch("pyobd.user_config_path", return_value=config_path):
                try:
                    app = MyApp(False)
                except SystemExit as error:
                    self.skipTest(str(error))

            app.frame.Hide()
            try:
                app.OpenPort(None)
                self.assertTrue(self._pump_until(
                    lambda: app.status.GetItemText(0, 1) == "Car connected!"
                ))

                app._go_to_page(app.tests_panel)
                self.assertTrue(self._pump_until(
                    lambda: "ready" in app.tests_status_label.GetLabel().lower()
                ))
                self.assertEqual(app.nb.GetCurrentPage(), app.tests_panel)

                app.GetDTC(None)
                self.assertTrue(self._pump_until(lambda: app.dtc.GetItemCount() == 3))

                app.OnDisconnect(None)
                self.assertTrue(self._pump_until(
                    lambda: app.senprod is not None and not app.senprod.is_alive()
                ))

                app.frame.Close()
                self.assertTrue(self._pump_until(lambda: app._shutdown_started))
            finally:
                app.ThreadControl = 666
                if app.senprod and app.senprod.is_alive():
                    app.senprod.stop()
                    app.senprod.join(timeout=2)
                if app.frame:
                    app.frame.Destroy()
                app.Destroy()


if __name__ == "__main__":
    unittest.main()
