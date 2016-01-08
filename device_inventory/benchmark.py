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
from dateutil import parser
from datetime import datetime
from device_inventory import progress_bar

from .utils import run


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
        logging.error(status)
        logging.debug("%s: %s", status, e.output)
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
        logging.error(smt)
        return {
            "@type": "TestHardDrive",
            "error": True,
            "status": smt[1],
        }
    
    print("Runing SMART self-test. It will finish at {0}".format(smt[2]))
    
    # wait until test has finished
    test_end = parser.parse(smt[2])
    seconds = (test_end - datetime.now()).seconds
    seconds = seconds + 2 # wait SMART just 2 second more to be finished
    progress_bar.sec(seconds)
    
    # show last test
    dev.update()
    last_test = dev.tests[0]
    try:
        lifetime = int(last_test.hours)
    except ValueError:
        lifetime = -1
    try:
        lba_first_error = int(last_test.LBA, 0)  # accepts hex and decimal value
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
    return freq/lat


def score_vga(model_name):
    score = None
    for model in re.findall('\w*\d\w*', model_name):
        # TODO find matching on etc/vga.txt (e.g. ['GT218M', '310M'])
        pass
    return score
