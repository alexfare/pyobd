import unittest
from types import SimpleNamespace

from obd.decoders import decode_encoded_string


class EncodedStringDecoderTests(unittest.TestCase):
    def test_vin_preserves_trailing_digits(self):
        for ending in "012":
            vin = ("1HGBH41JXMN10918" + ending).encode("ascii")
            message = SimpleNamespace(data=b"\x49\x02\x01" + vin + b"\x00\x00")

            self.assertEqual(decode_encoded_string([message], 17), vin)

    def test_vin_removes_protocol_padding_only(self):
        vin = b"1HGBH41JXMN109186"
        message = SimpleNamespace(data=b"\x49\x02\x00\x01" + vin + b"\x00")

        self.assertEqual(decode_encoded_string([message], 17), vin)


if __name__ == "__main__":
    unittest.main()
