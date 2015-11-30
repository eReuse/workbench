"""
Devices benchmark

Set of programs, or other operations, in order to assess the relative
performance of an object, normally by running a number of standard
tests and trials against it.

"""
import logging
import re
import subprocess

from .utils import run


def hard_disk_smart(disk="/dev/sda"):
    # smartctl -a /dev/sda | grep "# 1"
    # # 1  Short offline       Completed without error       00%     10016         -
    # XXX extract data of smartest. Decide which info is relevant.
    assert disk is not None
    error = False
    try:
        smart = subprocess.check_output(["smartctl", "-a", disk],
                                        universal_newlines=True)
    except subprocess.CalledProcessError as e:
        smart = e.output
        # analyze e.returncode
        if e.returncode == pow(2, 0):  # bit 0
            raise  # command line did not parse
        elif e.returncode == pow(2, 1):  # bit 1
            pass  # only warning because low-power
        elif e.returncode == pow(2, 2):  # bit 2
            error = True  # TODO cannot perform SMART
        else: # bit 3, 4, 5, 6, 7  device log with errors
            error = True
    
    test = {
        "@type": "TestHardDrive",
        #"device": disk,
        "error": error,
    }

    # excepted output
    # Num  Test_Description  Status  Remaining  LifeTime(hours)  LBA_of_first_error
    try:
        beg = smart.index('# 1')
        end = smart.index('\n', beg)
        result = re.split(r'\s\s+', smart[beg:end])
    except ValueError:
        logging.error("Error retrieving SMART info from '%s'", disk)
    else:
        try:
            lifetime = int(result[4])
        except ValueError:
            lifetime = -1
        try:
            lba_first_error = int(result[5], 0)  # accepts hex and decimal value
        except ValueError:
            lba_first_error = None
        
        test.update({
            "type": result[1],
            "status": result[2],
            "lifetime": lifetime,
            "firstError": lba_first_error,
        })
    
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
