import os
import unittest

from device_inventory import inventory

@unittest.skipUnless(os.geteuid() == 0, "Only root can run this script")
class TestComputer(unittest.TestCase):
    def test_serials(self):
        device = inventory.Computer()
        # TODO be able to use lshw/dmidecode output files
        # instead of calling to the commands
        self.assertEqual(device.SERIAL1, "5MQ84N1")
        self.assertEqual(device.SERIAL2, ".5MQ84N1.CN7016607B001P.")
        self.assertEqual(device.SERIAL3, "52 06 02 00 FF FB EB BF")
        self.assertEqual(device.SERIAL4, "15723A13")
        self.assertEqual(device.SERIAL5, "WD-WXM1A50M9524")


if __name__ == '__main__':
    import sys
    print(sys.version)
    unittest.main()
