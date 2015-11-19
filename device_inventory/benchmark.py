"""
Devices benchmark

Set of programs, or other operations, in order to assess the relative
performance of an object, normally by running a number of standard
tests and trials against it.

"""
import re
import subprocess

from .utils import run


def hard_disk_smart(disk="/dev/sda"):
    # smartctl -a /dev/sda | grep "# 1"
    # # 1  Short offline       Completed without error       00%     10016         -
    # XXX extract data of smartest. Decide which info is relevant.
    try:
        smart = subprocess.check_output(["smartctl", "-a", disk],
                                        universal_newlines=True)
    except subprocess.CalledProcessError as e:
        # TODO analyze e.returncode
        smart = e.output
    
    # current output
    # Num  Test_Description  Status  Remaining  LifeTime(hours)  LBA_of_first_error
    beg = smart.index('# 1')
    end = smart.index('\n', beg)
    result = re.split(r'\s\s+', smart[beg:end])
    
    try:
        lba_first_error = int(result[5], 0)  # accepts hex and decimal value
    except ValueError:
        lba_first_error = None
    
    return {
        "device": disk,
        "type": result[1],
        "status": result[2],
        "lifetime": result[4],
        "firstError": lba_first_error,
    }


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
