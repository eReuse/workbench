import unittest

from ereuse_workbench import benchmark


class TestBenchmark(unittest.TestCase):
    def test_score_cpu(self):
        score = benchmark.processor()
        self.assertGreater(score, 0)
    
class TestSmart(unittest.TestCase):
    def test_smart(self):
        # TODO make a more exigent test
        smart = benchmark.hard_disk_smart(disk="/dev/sda")
        print(smart)
        self.assertIsNotNone(smart)
    
    def test_smart_invalid_device(self):
        # TODO make a more exigent test
        smart = benchmark.hard_disk_smart(disk="/dev/XXX")
        print(smart)
        self.assertIsNotNone(smart)
