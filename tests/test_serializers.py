import json
import subprocess
import unittest

from device_inventory import inventory, serializers

class TestDeviceHubSerializer(unittest.TestCase):
    DEBUG = True
    
    def write_output(self, data, filename):
        with open(filename, "w") as outfile:
            json.dump(data, outfile, indent=4, sort_keys=True)

        print(subprocess.check_output(["cat", filename]))
        
    def test_retrieve_current_data(self):
        device = inventory.Computer()
        data = serializers.export_to_devicehub_schema(device)
        
        if self.DEBUG:
            self.write_output(data, "/tmp/computer_current.json")
    
    def test_load_stored_data(self):
        device = inventory.Computer(load_data=True)
        data = serializers.export_to_devicehub_schema(device)
        
        if self.DEBUG:
            self.write_output(data, "/tmp/computer_stored.json")
