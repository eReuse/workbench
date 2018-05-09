import re
import sys
from contextlib import suppress, redirect_stdout
from datetime import datetime, timedelta
from enum import Enum
from subprocess import Popen
from time import sleep
from warnings import catch_warnings, filterwarnings

from dateutil import parser
from io import StringIO
from pySMART import Device
from tqdm import tqdm, trange


class Smart(Enum):
    short = 'short'
    long = 'long'

    def __str__(self):
        return self.value


class Tester:
    SMART_ATTRIBUTES = {
        5: 'reallocatedSectorCount',
        12: 'powerCycleCount',
        187: 'reportedUncorrectableErrors',
        188: 'CommandTimeout',
        197: 'CurrentPendingSectorCount',
        198: 'OfflineUncorrectable',
        169: 'RemainingLifetimePercentage',  # Can be reported in several places
        231: 'RemainingLifetimePercentage'
    }
    SMART_GRACE_TIME = timedelta(seconds=10)

    @staticmethod
    def stress(minutes):
        """Perform a CPU and memory stress test for the given `minutes`.

        The CPU stress test uses one thread per core, and the RAM stress test one
        thread per core, totalling all main memory available to user processes.

        Return a boolean indicating whether the stress test was successful.
        """
        with open('/proc/cpuinfo') as cpuinfo:
            ncores = len(re.findall(r'^processor\b', cpuinfo.read(), re.M))
        with open('/proc/meminfo') as meminfo:
            match = re.search(r'^MemAvailable:\s*([0-9]+) kB.*', meminfo.read(), re.M)
            mem_kib = int(match.group(1))
        # Exclude a percentage of available memory for the stress processes themselves.
        mem_worker_kib = (mem_kib / ncores) * 90 / 100
        with redirect_stdout(StringIO()):
            process = Popen(('stress',
                             '-c', str(ncores),
                             '-m', str(ncores),
                             '--vm-bytes', '{}K'.format(mem_worker_kib),
                             '-t', '{}m'.format(minutes)))
        for _ in trange(minutes * 60):  # update progress bar every second
            sleep(1)
        with redirect_stdout(StringIO()):
            process.communicate()  # wait for process, consume output
        return {
            '@type': 'StressTest',
            'elapsed': timedelta(minutes=minutes),
            'success': process.returncode == 0
        }

    @classmethod
    def smart(cls, disk: str, test_type: Smart) -> dict:
        # Enable SMART on hard drive
        with catch_warnings():
            filterwarnings('error')
            try:
                hdd = Device(disk)  # type: Device
            except Warning:
                status = 'SMART cannot be enabled on this device.'
                print(status, file=sys.stderr)
                return {
                    '@type': 'TestHardDrive',
                    'error': True,
                    'status': status
                }
        status_code, status_message, completion_time = hdd.run_selftest(test_type.value)
        if status_code > 1:
            print(status_message, file=sys.stderr)
            return {
                '@type': 'TestHardDrive',
                'error': True,
                'status': status_message,
            }

        # get estimated end of the test
        try:
            test_end = parser.parse(completion_time)
        except TypeError:  # completion_time is None, estimate end time
            duration = 2 if test_type == Smart.short else 120
            test_end = datetime.now() + timedelta(minutes=duration)
        print('            It will finish around {}:'.format(test_end))

        # follow progress of test until it ends or the estimated time is reached
        remaining = 100  # test completion pending percentage
        with tqdm(total=remaining, leave=True) as bar:
            while remaining > 0:
                sleep(2)  # wait a few seconds between smart retrievals
                hdd.update()
                try:
                    last_test = hdd.tests[0]
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
                if datetime.now() > test_end + cls.SMART_GRACE_TIME:
                    break
        # show last test
        hdd.update()
        last_test = hdd.tests[0]
        try:
            lba_first_error = int(last_test.LBA, 0)  # accept hex and decimal value
        except ValueError:
            lba_first_error = None
        ret = {
            '@type': 'TestHardDrive',
            'type': last_test.type,
            'error': bool(lba_first_error),
            'status': last_test.status,
            'firstError': lba_first_error,
            'passedLifetime': int(hdd.attributes[9].raw),
            'assessment': True if hdd.assessment == 'PASS' else False
        }
        with suppress(ValueError):
            ret['lifetime'] = int(last_test.hours)
        for key, name in cls.SMART_ATTRIBUTES.items():
            with suppress(AttributeError):
                ret[name] = int(hdd.attributes[key].raw)
        return ret
