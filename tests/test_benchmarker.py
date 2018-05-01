from unittest.mock import MagicMock, patch

import pytest

from ereuse_workbench.benchmarker import Benchmarker
from tests.conftest import fixture


@pytest.fixture()
def run() -> MagicMock:
    with patch('ereuse_workbench.benchmarker.run') as mocked_run:
        yield mocked_run


class MockedRun:
    def __init__(self, stdout) -> None:
        self.stdout = stdout

    def __call__(self, *args, **kwargs):
        return self


def test_processor_benchmark(run: MagicMock):
    run.side_effect = MockedRun(fixture('processor.sysbench.txt'))
    result = Benchmarker().processor_sysbench()
    assert result == {
        '@type': 'BenchmarkProcessorSysbench',
        'score': 11.8707
    }
    assert run.call_count == 1


def test_memory_benchmark(run: MagicMock):
    run.side_effect = MockedRun(fixture('ram.sysbench.txt'))
    result = Benchmarker().benchmark_memory()
    assert result == {
        '@type': 'BenchmarkRamSysbench',
        'score': 19.2744
    }
    assert run.call_count == 1
