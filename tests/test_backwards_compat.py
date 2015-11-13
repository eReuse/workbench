import operator
import os
import pprint
import subprocess
import unittest

from device_inventory import donator, utils, xml2dict


class TestBackwardsCompat(unittest.TestCase):
    def test_compare_outputs(self):
        # Load old XML
        path = os.path.dirname(__file__)
        old = xml2dict.ConvertXmlToDict(os.path.join(path, "chk.orig.xml"))
        
        # Generate new XML
        donator.main()
        new = xml2dict.ConvertXmlToDict("/tmp/equip.xml")
        
        old_file = "/tmp/old.txt"
        new_file = "/tmp/new.txt"
        with open(old_file, "w") as f:
            pprint.pprint(sorted(old['equip'].items(), key=operator.itemgetter(0)), f)
        
        with open(new_file, "w") as f:
            pprint.pprint(sorted(new['equip'].items(), key=operator.itemgetter(0)), f)
        
        try:
            diff = subprocess.check_output(["diff", "-y", "--suppress-common-lines",
                                            old_file, new_file])
        except subprocess.CalledProcessError as e:
            self.fail(e.output)
