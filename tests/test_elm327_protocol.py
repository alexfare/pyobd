import unittest
from unittest.mock import Mock

from obd.elm327 import ELM327
from obd.protocols import UnknownProtocol


class ELM327ProtocolTests(unittest.TestCase):
    def setUp(self):
        self.elm = ELM327.__new__(ELM327)
        self.elm._ELM327__protocol = UnknownProtocol([])

    def test_manual_protocol_accepts_vehicle_response(self):
        self.elm._ELM327__send = Mock(
            side_effect=[["OK"], ["7E8 06 41 00 BE 3E B8 13"]]
        )

        self.assertTrue(self.elm.manual_protocol("6"))
        self.assertEqual(self.elm.protocol_id(), "6")

    def test_manual_protocol_rejects_vehicle_errors(self):
        for response in ELM327._CONNECTION_ERRORS:
            with self.subTest(response=response):
                self.elm._ELM327__send = Mock(side_effect=[["OK"], [response]])
                self.assertFalse(self.elm.manual_protocol("6"))

    def test_auto_protocol_handles_empty_protocol_response(self):
        responses = [["OK"], ["NO DATA"], []]
        for protocol in ELM327._TRY_PROTOCOL_ORDER:
            responses.extend([["OK"], ["UNABLE TO CONNECT"]])
        self.elm._ELM327__send = Mock(side_effect=responses)

        self.assertFalse(self.elm.auto_protocol())

    def test_auto_protocol_accepts_automatic_prefix(self):
        self.elm._ELM327__send = Mock(
            side_effect=[
                ["OK"],
                ["7E8 06 41 00 BE 3E B8 13"],
                ["A6"],
            ]
        )

        self.assertTrue(self.elm.auto_protocol())
        self.assertEqual(self.elm.protocol_id(), "6")


if __name__ == "__main__":
    unittest.main()
