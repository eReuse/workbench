import re
from contextlib import redirect_stdout, suppress
from datetime import datetime, timedelta
from enum import Enum, unique
from io import StringIO
from subprocess import Popen
from time import sleep
from warnings import catch_warnings, filterwarnings

from click import progressbar
from dateutil import parser
from pySMART import Device

from ereuse_workbench.utils import LJUST, Measurable


@unique
class TestDataStorageLength(Enum):
    Short = 'Short'
    Extended = 'Extended'

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
    SMART_GRACE_TIME = timedelta(seconds=10)

    def run(self, logical: str, length: TestDataStorageLength):
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

            # get estimated end of the test
            try:
                test_end = parser.parse(completion_time)
            except TypeError:  # completion_time is None, estimate end time
                duration = 2 if length == TestDataStorageLength.Short else 120
                test_end = datetime.now() + timedelta(minutes=duration)
            print('            It will finish around {}:'.format(test_end))

            # follow progress of test until it ends or the estimated time is reached
            remaining = 100  # test completion pending percentage
            with progressbar(length=remaining,
                             width=20,
                             label='SMART test {}'.format(storage.model).ljust(LJUST - 2)) as bar:
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

                    # only allow a few seconds more than the estimated time
                    if datetime.now() > test_end + self.SMART_GRACE_TIME:
                        break
            # show last test
            storage.update()
            last_test = storage.tests[0]

            self.length = length
            self.first_error = self._first_error(last_test.LBA)
            self.error = bool(self.first_error)
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
                         '-t', '{}m'.format(minutes)))
        with progressbar(range(minutes * 60),
                         width=20,
                         label='Stress test'.ljust(LJUST - 2)) as bar:
            for _ in bar:
                sleep(1)
        with redirect_stdout(StringIO()):
            process.communicate()  # wait for process, consume output
        self.elapsed = minutes
        self.error = bool(process.returncode)
