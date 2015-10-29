import unittest

from device_inventory import benchmark


class TestBenchmark(unittest.TestCase):
    def test_score_cpu(self):
        score = benchmark.score_cpu()
        self.assertGreater(score, 0)
