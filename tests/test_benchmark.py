import unittest

from device_inventory import benchmark


class TestBenchmark(unittest.TestCase):
    def test_score_cpu(self):
        score = benchmark.score_cpu()
        self.assertGreater(score, 0)
    
    def test_smart(self):
        # TODO make a more exigent test
        smart = benchmark.hard_disk_smart()
        self.assertIsNotNone(smart)
