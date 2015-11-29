import os
import types
import unittest

from device_inventory import inventory
from lxml import etree


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
        self.assertEqual(device.memory[0].serialNumber, "15723A13")
        self.assertEqual(device.hard_disk[0].serialNumber, "WD-WXM1A50M9524")


class TestRamModule(unittest.TestCase):
    def test_size(self):
        device = inventory.Computer(
            load_data=True,
            #lshw_xml="tests/fixtures/vostro3300_lshw.xml"
            dmidecode="tests/fixtures/vostro3300_dmidecode.txt"
        )
        for module in device.memory:
            self.assertIsNotNone(module.size)
            # TODO more especific tests


class TestNetworkAdapter(unittest.TestCase):
    # FIXME Cannot retrieve MAC of USB network adapters
    @unittest.expectedFailure
    def test_serial_number(self):
        device = inventory.Computer(load_data=True)
        for iface in device.network_interfaces:
            self.assertIsNotNone(iface.serialNumber, iface.model)


class TestProcessor(unittest.TestCase):
    def test_number_of_cores(self):
        device = inventory.Computer(load_data=True)
        for proc in device.processor:
            self.assertIs(type(proc.numberOfCores), types.IntType)
            self.assertIs(type(proc.address), types.IntType)
    
    def test_product(self):
        filename = 'tests/fixtures/processor_without_product.xml'
        with  open(filename, 'r') as f:
            output = f.read()
        node = etree.fromstring(output)
        proc = inventory.Processor(node)
    
    def test_size(self):
        # Force trying to retrieve address without having data
        filename = 'tests/fixtures/processor_without_product.xml'
        with  open(filename, 'r') as f:
            output = f.read()
        node = etree.fromstring(output)
        proc = inventory.Processor(node)
        self.assertIsNone(proc.get_address({}))
    
    def test_speed(self):
        filename = 'tests/fixtures/processor_without_product.xml'
        with  open(filename, 'r') as f:
            output = f.read()
        node = etree.fromstring(output)
        proc = inventory.Processor(node)
        # Force trying to retrieve speed without having data
        self.assertIsNone(proc.get_speed({}))
        self.assertEqual(proc.get_speed({'Current Speed': 1000}), 1)
