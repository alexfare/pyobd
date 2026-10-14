import unittest

import obd
from obd_io import _DemoConnection, _FakeMisfireValue
from sensor_worker import READINESS_MONITORS, SensorProducer


class Monitor:
    def __init__(self, available, complete):
        self.available = available
        self.complete = complete


class DiagnosticTests(unittest.TestCase):
    def test_readiness_maps_ready_not_ready_and_unsupported(self):
        status = type("Status", (), {})()
        for name in READINESS_MONITORS:
            setattr(status, name, Monitor(False, False))
        setattr(status, READINESS_MONITORS[0], Monitor(True, True))
        setattr(status, READINESS_MONITORS[1], Monitor(True, False))

        results, counts = SensorProducer._readiness_results(status)

        self.assertEqual(results[0]["status"], "Ready")
        self.assertEqual(results[1]["status"], "Not ready")
        self.assertEqual(results[2]["status"], "Unsupported")
        self.assertEqual(counts, {"ready": 1, "not_ready": 1, "unsupported": 13})

    def test_mode_06_formats_supported_and_unsupported_results(self):
        self.assertEqual(SensorProducer._misfire_result(_FakeMisfireValue(4)), "4 misfires")
        self.assertEqual(SensorProducer._misfire_result(None), "Unsupported")

    def test_demo_exposes_all_misfire_monitors(self):
        connection = _DemoConnection()
        for cylinder in range(1, 13):
            command = getattr(obd.commands, f"MONITOR_MISFIRE_CYLINDER_{cylinder}")
            self.assertIsNotNone(connection.query(command).value)

    def test_dtc_categories_and_clear_behavior(self):
        connection = _DemoConnection()

        rows, counts = SensorProducer._collect_dtc_results(connection)

        self.assertEqual(counts, {"Stored": 1, "Pending": 1, "Permanent": 1})
        self.assertEqual({row[1] for row in rows}, {"Stored", "Pending", "Permanent"})

        connection.query(obd.commands.CLEAR_DTC)
        rows, counts = SensorProducer._collect_dtc_results(connection)
        self.assertEqual(counts, {"Stored": 0, "Pending": 0, "Permanent": 1})
        self.assertEqual([row[1] for row in rows], ["Permanent"])


if __name__ == "__main__":
    unittest.main()
