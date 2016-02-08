import gnupg
import os
import shutil
import tempfile
import unittest

from device_inventory import utils


class TestSignature(unittest.TestCase):
    def setUp(self):
        self.workspace = tempfile.mkdtemp()
        self.gpg = gnupg.GPG(homedir=self.workspace)
    
    def tearDown(self):
        shutil.rmtree(self.workspace)
    
    def test_sign(self):
        foo = "Some random data."
        sig = utils.sign_data(foo)
        self.assertTrue(sig)
        
        basepath = os.path.dirname(__file__)
        with open(os.path.join(basepath, "../device_inventory/data/public.key")) as pubkey:
            self.gpg.import_keys(pubkey.read())
        
        verify = self.gpg.verify(sig)
        self.assertTrue(verify.valid)
