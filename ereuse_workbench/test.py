import re
from contextlib import suppress
from enum import Enum, unique
from subprocess import DEVNULL, Popen
from time import sleep
from warnings import catch_warnings, filterwarnings

from pySMART import Device

from ereuse_workbench.utils import Measurable, progressbar


@unique
class TestDataStorageLength(Enum):
    Short = 'short'
    Extended = 'long'

    def __str__(self):
        return self.value


class Test(Measurable):
    def __init__(self) -> None:
        super().__init__()
        self.type = self.__class__.__name__
        self.error = False

    def _error(self, status):
        self.status = status
        self.error = True


class TestDataStorage(Test):
    SMART_ATTRIBUTES = {
        5: 'reallocated_sector_count',
        12: 'power_cycle_count',
        187: 'reported_uncorrectable_errors',
        188: 'command_timeout',
        197: 'current_pending_sector_count',
        198: 'offline_uncorrectable',
        169: 'remaining_lifetime_percentage',  # Can be reported in several places
        231: 'remaining_lifetime_percentage'
    }
    SMART_GRACE_TIME = 10
    """Seconds to wait to retrieve the SMART test result."""

    def run(self, logical: str, length: TestDataStorageLength):
        self.length = length
        with self.measure():
            with catch_warnings():
                filterwarnings('error')
                try:
                    storage = Device(logical)  # type: Device
                except Warning:
                    return self._error('SMART cannot be enabled on this device.')
            code, message, completion_time = storage.run_selftest(length.value)
            if code > 1:
                return self._error(message)

            # follow progress of test until it ends or the estimated time is reached
            remaining = 100  # test completion pending percentage
            with progressbar(length=remaining + self.SMART_GRACE_TIME,
                             title='SMART test {}'.format(storage.model)) as bar:
                while remaining > 0:
                    sleep(2)  # wait a few seconds between smart retrievals
                    storage.update()
                    try:
                        last_test = storage.tests[0]
                    except (TypeError, IndexError):
                        pass
                        # The suppress: test is None, no tests
                        # work around because SMART has not been initialized
                        # yet but pySMART library doesn't wait
                        # Just ignore the error because we alreaday have an
                        # estimation of the ending time
                    else:
                        last = remaining
                        with suppress(ValueError):
                            remaining = int(last_test.remain.strip('%'))
                        completed = last - remaining
                        if completed > 0:
                            bar.update(completed)
                for _ in range(self.SMART_GRACE_TIME):
                    sleep(1)
                    bar.update(1)
            storage.update()
            last_test = storage.tests[0]

            self.error = bool(self._first_error(last_test.LBA))
            self.status = last_test.status
            self.lifetime = int(last_test.hours)
            self.assessment = True if storage.assessment == 'PASS' else False
            for key, name in self.SMART_ATTRIBUTES.items():
                with suppress(AttributeError):
                    setattr(self, name, int(storage.attributes[key].raw))

    @staticmethod
    def _first_error(LBA):
        with suppress(ValueError):
            return int(LBA, 0)  # accept hex and decimal value


class StressTest(Test):
    """
    Perform a CPU and memory stress test for the given `minutes`.

    The CPU stress test uses one thread per core, and the RAM stress test one
    thread per core, totalling all main memory available to user processes.

    Return a boolean indicating whether the stress test was successful.
    """

    def run(self, minutes: int):
        with open('/proc/cpuinfo') as cpuinfo:
            ncores = len(re.findall(r'^processor\b', cpuinfo.read(), re.M))
        with open('/proc/meminfo') as meminfo:
            match = re.search(r'^MemAvailable:\s*([0-9]+) kB.*', meminfo.read(), re.M)
            mem_kib = int(match.group(1))
        # Exclude a percentage of available memory for the stress processes themselves.
        mem_worker_kib = (mem_kib / ncores) * 90 / 100
        process = Popen(('stress',
                         '-c', str(ncores),
                         '-m', str(ncores),
                         '--quiet',
                         '--vm-bytes', '{}K'.format(mem_worker_kib),
                         '-t', '{}m'.format(minutes)), stdout=DEVNULL, stderr=DEVNULL)
        with progressbar(range(minutes * 60), title='Stress test') as bar:
            for _ in bar:
                sleep(1)
        process.communicate()  # wait for process, consume output
        self.elapsed = minutes * 60
        self.error = bool(process.returncode)
