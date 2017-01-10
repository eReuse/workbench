import unittest

from ereuse_ddi import inventory, utils
from lxml import etree


class TestUtils(unittest.TestCase):
    def test_strip_null_or_empty_values(self):
        filename = 'tests/fixtures/processor_to_be_filled_serial.xml'
        with  open(filename, 'r') as f:
            output = f.read()
        node = etree.fromstring(output)
        proc = inventory.Processor(node)
        data = utils.strip_null_or_empty_values(proc.__dict__)
        self.assertNotIn('serialNumber', data)
