import os
import unittest

from inventory import Inventory

@unittest.skipUnless(os.geteuid() == 0, "Only root can run this script")
class TestInventory(unittest.TestCase):
    def test_serials(self):
        inventory = Inventory()
        # TODO be able to use lshw/dmidecode output files
        # instead of calling to the commands
        self.assertEqual(inventory.SERIAL1, "5MQ84N1")
        self.assertEqual(inventory.SERIAL2, ".5MQ84N1.CN7016607B001P.")
        self.assertEqual(inventory.SERIAL3, "52 06 02 00 FF FB EB BF")
        self.assertEqual(inventory.SERIAL4, "15723A13")
        self.assertEqual(inventory.SERIAL5, "WD-WXM1A50M9524")


if __name__ == '__main__':
    import sys
    print(sys.version)
    unittest.main()
