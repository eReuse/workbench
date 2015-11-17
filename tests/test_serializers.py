import json
import subprocess
import unittest

from device_inventory import inventory, serializers

class TestDeviceHubSerializer(unittest.TestCase):
    def test_1(self):
        device = inventory.Computer()
        snap = serializers.export_to_devicehub_schema(device)
        
        
        with open("/tmp/computer.json", "w") as outfile:
            json.dump(snap, outfile, indent=4, sort_keys=True)

#            json.dump(device.processor.__dict__, outfile, indent=4, sort_keys=True)
#            json.dump(device.hard_disk.__dict__, outfile, indent=4, sort_keys=True)
#            json.dump(device.motherboard.__dict__, outfile, indent=4, sort_keys=True)
    
        print(subprocess.check_output(["cat", "/tmp/computer.json"]))
    
    # TODO optimize to load lshw output directly from a file!
