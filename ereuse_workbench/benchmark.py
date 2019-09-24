import logging
from subprocess import PIPE, run

from ereuse_workbench import unit, MBs
from ereuse_workbench.utils import Measurable


class Benchmark(Measurable):
    def __init__(self) -> None:
        super().__init__()
        self.type = self.__class__.__name__

    @staticmethod
    def execute_sysbench(*args):
        res = run(args, universal_newlines=True, stdout=PIPE, check=True).stdout.splitlines()
        return float(next(l.split()[-1][0:-1] for l in res if 'total time:' in l))

    def run(self):
        raise NotImplementedError()


class BenchmarkProcessor(Benchmark):
    """Gets the BogoMips of the processor."""

    def run(self):
        with self.measure(), open('/proc/cpuinfo') as f:
            self.rate = sum(float(ln.split(':')[1]) for ln in f if ln.startswith('bogomips'))


class BenchmarkProcessorSysbench(Benchmark):
    """Benchmarks the processor with ``sysbench``."""

    def run(self):
        with self.measure():
            self.rate = self.execute_sysbench('sysbench',
                                              '--test=cpu',
                                              '--cpu-max-prime=25000',
                                              '--num-threads=16',
                                              'run')

    def __str__(self) -> str:
        return str(self.rate)


class BenchmarkRamSysbench(Benchmark):
    def run(self):
        with self.measure():
            self.rate = self.execute_sysbench('sysbench',
                                              '--test=memory',
                                              '--memory-block-size=1K',
                                              '--memory-scope=global',
                                              '--memory-total-size=50G',
                                              '--memory-oper=write',
                                              'run')


class BenchmarkDataStorage(Benchmark):
    BENCHMARK_ARGS = 'bs=1M', 'count=256', 'oflag=dsync'

    def __init__(self, logical_name: str) -> None:
        super().__init__()
        self._logical_name = logical_name

    def run(self):
        with self.measure():
            # Read
            cmd_read = ('dd',
                        'if={}'.format(self._logical_name),
                        'of=/dev/null') + self.BENCHMARK_ARGS
            self.read_speed = self._benchmark_hdd_to_mb(run(cmd_read, stderr=PIPE).stderr)

            # Write
            cmd_write = ('dd',
                         'of={}'.format(self._logical_name),
                         'if={}'.format(self._logical_name)) + self.BENCHMARK_ARGS
            self.write_speed = self._benchmark_hdd_to_mb(run(cmd_write, stderr=PIPE).stderr)

    @staticmethod
    def _benchmark_hdd_to_mb(output: bytes) -> float:
        output = output.decode()
        value = float(output.split()[-2].replace(',', '.'))
        speed = unit.Quantity(value, output.split()[-1][0:2] + '/s').to(MBs).m
        if speed < 5.0:
            logging.warning('Speed should be above 5 MB/S but is %s.'
                            'This could be a defect on the drive or a measure problem.', speed)
        return speed
