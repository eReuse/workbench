from unittest.mock import MagicMock, patch

import pytest

from ereuse_workbench.benchmark import BenchmarkProcessorSysbench, BenchmarkRamSysbench
from tests.conftest import fixture


@pytest.fixture()
def run() -> MagicMock:
    with patch('ereuse_workbench.benchmark.run') as mocked_run:
        yield mocked_run


class MockedRun:
    def __init__(self, stdout) -> None:
        self.stdout = stdout

    def __call__(self, *args, **kwargs):
        return self


def test_processor_benchmark(run: MagicMock):
    run.side_effect = MockedRun(fixture('processor.sysbench.txt'))
    b = BenchmarkProcessorSysbench()
    b.run()
    assert b.rate == 11.8707
    assert run.call_count == 1


def test_memory_benchmark(run: MagicMock):
    run.side_effect = MockedRun(fixture('ram.sysbench.txt'))
    b = BenchmarkRamSysbench()
    b.run()
    assert b.rate == 19.2744
    assert run.call_count == 1
