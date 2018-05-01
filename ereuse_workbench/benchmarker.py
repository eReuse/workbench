from subprocess import PIPE, run
from typing import Sequence
from warnings import warn

from .utils import convert_capacity


class Benchmarker:
    """
    Set of method that run standard tests to assess the relative
    performance of components or the entire machine.

    See each method to know what they benchmark.
    """
    BENCHMARK_HDD_COMMON = 'bs=1M', 'count=256', 'oflag=dsync'

    def benchmark_hdd(self, disk):
        """
        Computers the reading and writing speed of a hard-drive by
        writing and reading a piece of the hard-drive.

        This method does not destroy existing data.
        """
        # Read
        cmd_read = ('dd', 'if={}'.format(disk), 'of=/dev/null') + self.BENCHMARK_HDD_COMMON
        reading = self._benchmark_hdd_to_mb(run(cmd_read, stderr=PIPE).stderr)

        # Write
        cmd_write = ('dd', 'of={}'.format(disk), 'if={}'.format(disk)) + self.BENCHMARK_HDD_COMMON
        writing = self._benchmark_hdd_to_mb(run(cmd_write, stderr=PIPE).stderr)

        return {
            '@type': 'BenchmarkHardDrive',
            'readingSpeed': reading,
            'writingSpeed': writing
        }

    @staticmethod
    def _benchmark_hdd_to_mb(output: bytes) -> float:
        output = output.decode()
        value = float(output.split()[-2].replace(',', '.'))
        speed = convert_capacity(value, output.split()[-1][0:2], 'MB')
        if speed > 300:
            warn('Detected {} MB/s is far superior from normal HDD speed'.format(speed))
        assert 5 < speed, 'Speed must be above 5 MB/S and is {}'.format(speed)
        return speed

    @staticmethod
    def processor():
        """Gets the BogoMips of the processor."""
        # https://en.wikipedia.org/wiki/BogoMips
        # score = sum(cpu.bogomips for cpu in device.cpus)
        with open('/proc/cpuinfo') as f:
            return {
                'score': sum(float(ln.split(':')[1]) for ln in f if ln.startswith('bogomips')),
                '@type': 'BenchmarkProcessor'
            }

    def processor_sysbench(self) -> dict:
        """
        Benchmarks the processor with ``sysbench``.
        """
        return self._execute_sysbench(('sysbench',
                                       '--test=cpu',
                                       '--cpu-max-prime=25000',
                                       '--num-threads=16',
                                       'run'),
                                      type='BenchmarkProcessorSysbench')

    def benchmark_memory(self) -> dict:
        return self._execute_sysbench(('sysbench',
                                       '--test=memory',
                                       '--memory-block-size=1K',
                                       '--memory-scope=global',
                                       '--memory-total-size=50G',
                                       '--memory-oper=write',
                                       'run'),
                                      type='BenchmarkRamSysbench')

    @staticmethod
    def _execute_sysbench(args: Sequence, type: str) -> dict:
        res = run(args, universal_newlines=True, stdout=PIPE, check=True).stdout.splitlines()
        return {
            '@type': type,
            'score': float(next(l.split()[-1][0:-1] for l in res if 'total time:' in l))
        }
