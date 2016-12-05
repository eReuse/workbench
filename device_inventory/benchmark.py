"""
Devices benchmark

Set of programs, or other operations, in order to assess the relative
performance of an object, normally by running a number of standard
tests and trials against it.

"""
import logging
import pySMART
import re
import subprocess
import time
import tqdm
from dateutil import parser
from datetime import datetime, timedelta

from .utils import run, convert_capacity


logger = logging.getLogger(__name__)


def benchmark_hdd(disk):
    # READ
    cmd_read = ["dd", "if=%s" % disk, "of=/dev/null", "bs=1M", "count=256",
                "oflag=dsync"]
    p = subprocess.Popen(cmd_read, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    out, err = p.communicate()
    
    # Convert value to MB
    value = float(err.split()[-2].replace(',', '.'))
    unit = err.split()[-1]
    reading = convert_capacity(value, unit[0:2], "MB")

    # WRITE
    cmd_write = ["dd", "of=%s" % disk, "if=%s" % disk, "bs=1M", "count=256",
                 "oflag=dsync"]
    p = subprocess.Popen(cmd_write, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    out, err = p.communicate()
    
    # Convert value to MB
    value = float(err.split()[-2].replace(',', '.'))
    unit = err.split()[-1]
    writting = convert_capacity(value, unit[0:2], "MB")
    
    return {
        "@type": "BenchmarkHardDrive",
        "readingSpeed": reading,
        "writingSpeed": writting,
    }


def hard_disk_smart(disk, test_type="short"):
    TEST_TYPES = ["short", "long"]
    if test_type not in TEST_TYPES:
        raise ValueError("SMART test_type should be {0}".format(TEST_TYPES))
    
    error = False
    status = ""
    
    # Enable SMART on hard drive
    try:
        s = subprocess.check_output(["smartctl", "-s", "on", disk],
                                    universal_newlines=True)
    except subprocess.CalledProcessError as e:
        error = True
        status = "SMART cannot be enabled on this device."
        logger.error(status)
        logger.debug("%s: %s", status, e.output)
        return {
            "@type": "TestHardDrive",
            "error": error,
            "status": status,
        }
    
    dev = pySMART.Device(disk)
    smt = dev.run_selftest(test_type)
    """
    smt = (0, 'Self-test started successfully', 'Sat Dec 12 20:14:20 2015')
    0 - Self-test initiated successfully
    1 - Previous self-test running. Must wait for it to finish.
    2 - Unknown or illegal test type requested.
    3 - Unspecified smartctl error. Self-test not initiated.
    """
    if smt[0] > 1:
        logger.error(smt)
        return {
            "@type": "TestHardDrive",
            "error": True,
            "status": smt[1],
        }
    
    # get estimated end of the test
    try:
        test_end = parser.parse(smt[2])
    except AttributeError:  # smt[2] is None, estimate end time
        duration = 2 if test_type == "short" else 120
        test_end = datetime.now() + timedelta(minutes=duration)
    print("Runing SMART self-test. It will finish at {0}".format(test_end))

    # follow progress of test until it ends or the estimated time is reached
    grace_time = timedelta(seconds=10)
    remaining = 100  # test completion pending percentage
    with tqdm.tqdm(total=remaining, leave=True) as smartbar:
        while remaining > 0:
            time.sleep(5)  # wait a few seconds between smart retrievals
            smarterr = None

            dev.update()
            try:
                last_test = dev.tests[0]
            except (TypeError, IndexError) as smarterr:  # test is None, no tests
                pass  # work around because SMART has not been initialized
                      # yet but pySMART library doesn't wait
                      # Just ignore the error because we alreday have an
                      # estimation of the ending time

            if not smarterr:
                last = remaining
                try:
                    remaining = int(last_test.remain.strip('%'))
                except ValueError as smarterr:
                    pass
                smartbar.update(last - remaining)

            if smarterr:
                logger.error(smarterr)

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
        "@type": "TestHardDrive",
        "type": last_test.type,
        "error": error,
        "status": last_test.status,
        "lifetime": lifetime,
        "firstError": lba_first_error,
    }
    
    return test


def score_cpu():
    # https://en.wikipedia.org/wiki/BogoMips
    # score = sum(cpu.bogomips for cpu in device.cpus)
    mips = []
    with open("/proc/cpuinfo") as f:
        for line in f:
            if line.startswith("bogomips"):
                mips.append(float(line.split(':')[1]))
    
    return sum(mips)


def score_ram(speed):
    """
    Score is the relation between memory frequency and memory latency.
    - higher frequency is better
    - lower latency is better
    
    """
    # http://www.cyberciti.biz/faq/check-ram-speed-linux/
    # Expected input "800 MHz (1.2 ns)"
    try:
        freq = float(speed.split()[0])
        lat = float(speed[speed.index("("):speed.index("ns)")])
    except (IndexError, ValueError):
        return "Unknown"
    return freq / lat


def score_vga(model_name):
    score = None
    for model in re.findall('\w*\d\w*', model_name):
        # TODO find matching on etc/vga.txt (e.g. ['GT218M', '310M'])
        pass
    return score
