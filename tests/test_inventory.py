import os
import unittest

from device_inventory import inventory


@unittest.skipUnless(os.geteuid() == 0, "Only root can run this script")
class TestComputer(unittest.TestCase):
    def test_serials(self):
        device = inventory.Computer(
            load_data=True,
            lshw_xml="tests/fixtures/vostro3300_lshw.xml"
        )
        self.assertEqual(device.processor[0].serialNumber, None)
        self.assertEqual(device.motherboard.serialNumber, ".5MQ84N1.CN7016607B001P.")
        self.assertEqual(device.network_interfaces[1].serialNumber, "a4:ba:db:da:f0:c8")
        self.assertEqual(device.memory.serialNumber, "15723A13")
        self.assertEqual(device.hard_disk[0].serialNumber, "WD-WXM1A50M9524")


class TestNetworkAdapter(unittest.TestCase):
    def test_serial_number(self):
        device = inventory.Computer(load_data=True)
        for iface in device.network_interfaces:
            self.assertIsNotNone(iface.serialNumber, iface.model)
