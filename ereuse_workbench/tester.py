import re
import sys
import time
from contextlib import suppress
from datetime import datetime, timedelta
from enum import Enum
from subprocess import Popen, run, CalledProcessError
from time import sleep

import pySMART
import tqdm
from dateutil import parser


class Smart(Enum):
    short = 'short'
    long = 'long'

    def __str__(self):
        return self.value


class Tester:
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
        process = Popen(('stress',
                         '-c', str(ncores),
                         '-m', str(ncores),
                         '--vm-bytes', '{}K'.format(mem_worker_kib),
                         '-t', '{}m'.format(minutes)))
        for _ in tqdm.trange(minutes * 60):  # update progress bar every second
            sleep(1)
        process.communicate()  # wait for process, consume output
        return {
            '@type': 'StressTest',
            'elapsed': timedelta(minutes=minutes),
            'success': process.returncode == 0
        }

    def smart(self, disk, test_type: Smart):
        # Enable SMART on hard drive
        try:
            run(('smartctl', '-s', 'on', disk), universal_newlines=True, check=True)
        except CalledProcessError as e:
            status = 'SMART cannot be enabled on this device.'
            print(status, file=sys.stderr)
            print(e, file=sys.stderr)
            return {
                '@type': 'TestHardDrive',
                'error': True,
                'status': status,
            }

        dev = pySMART.Device(disk)
        smt = dev.run_selftest(test_type.value)
        '''
        smt = (0, 'Self-test started successfully', 'Sat Dec 12 20:14:20 2015')
        0 - Self-test initiated successfully
        1 - Previous self-test running. Must wait for it to finish.
        2 - Unknown or illegal test type requested.
        3 - Unspecified smartctl error. Self-test not initiated.
        '''
        if smt[0] > 1:
            print(smt[1], file=sys.stderr)
            return {
                '@type': 'TestHardDrive',
                'error': True,
                'status': smt[1],
            }

        # get estimated end of the test
        try:
            test_end = parser.parse(smt[2])
        except TypeError:  # smt[2] is None, estimate end time
            duration = 2 if test_type == Smart.short else 120
            test_end = datetime.now() + timedelta(minutes=duration)
        print('Runing SMART self-test. It will finish at {0}:'.format(test_end))

        # follow progress of test until it ends or the estimated time is reached
        grace_time = timedelta(seconds=10)
        remaining = 100  # test completion pending percentage
        with tqdm.tqdm(total=remaining, leave=True) as smartbar:
            while remaining > 0:
                time.sleep(5)  # wait a few seconds between smart retrievals
                dev.update()
                try:
                    last_test = dev.tests[0]
                except (TypeError, IndexError) as err:
                    print(err, file=sys.stderr)
                    # The supppress: test is None, no tests
                    # work around because SMART has not been initialized
                    # yet but pySMART library doesn't wait
                    # Just ignore the error because we alreday have an
                    # estimation of the ending time
                else:
                    last = remaining
                    with suppress(ValueError):
                        remaining = int(last_test.remain.strip('%'))
                    smartbar.update(last - remaining)

                # only allow a few seconds more than the estimated time
                if datetime.now() > test_end + grace_time:
                    break

        # show last test
        dev.update()
        last_test = dev.tests[0]
        try:
            lifetime = int(last_test.hours)
        except ValueError:
            lifetime = -1
        try:
            lba_first_error = int(last_test.LBA, 0)  # accept hex and decimal value
        except ValueError:
            lba_first_error = None
        test = {
            '@type': 'TestHardDrive',
            'type': last_test.type,
            'error': bool(lba_first_error),
            'status': last_test.status,
            'lifetime': lifetime,
            'firstError': lba_first_error,
        }

        return test
