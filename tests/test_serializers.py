import json
import subprocess
import unittest

from ereuse_ddi import inventory, serializers
from ereuse_ddi.utils import InventoryJSONEncoder as InvEncoder

class TestDeviceHubSerializer(unittest.TestCase):
    DEBUG = True
    
    def write_output(self, data, filename):
        with open(filename, "w") as outfile:
            json.dump(data, outfile, indent=4, sort_keys=True, cls=InvEncoder)

        print(subprocess.check_output(["cat", filename]))
        
    def test_retrieve_current_data(self):
        device = inventory.Computer()
        data = serializers.export_to_devicehub_schema(device)
        
        if self.DEBUG:
            self.write_output(data, "/tmp/computer_current.json")
    
    def test_retrieve_current_data_debug_mode(self):
        device = inventory.Computer()
        data = serializers.export_to_devicehub_schema(device, debug=True)
    
    def test_load_stored_data(self):
        device = inventory.Computer(load_data=True)
        data = serializers.export_to_devicehub_schema(device)
        
        # Check if every component has the mandatory fields
        for comp in data["components"]:
            for field in ["serialNumber", "manufacturer", "model"]:
                self.assertIn(field, comp,
                              "{0} not in {1}".format(field, comp["@type"]))
        
        if self.DEBUG:
            self.write_output(data, "/tmp/computer_stored.json")
    
    def test_load_stored_data_usb_disk(self):
        device = inventory.Computer(load_data=True, lshw_xml="lshw_usb_hd.xml")
        data = serializers.export_to_devicehub_schema(device)
        
        if self.DEBUG:
            self.write_output(data, "/tmp/computer_stored_usb_disk.json")
    
    def test_snapshot_includes_version(self):
        device = inventory.Computer(load_data=True)
        data = serializers.export_to_devicehub_schema(device)
        self.assertIn('version', data)
