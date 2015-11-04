"""
Devices benchmark

Set of programs, or other operations, in order to assess the relative
performance of an object, normally by running a number of standard
tests and trials against it.

"""
import re
import subprocess


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
    
    return {
        'device_check': disk,  # DEVICE_CHECK
        'type_check': result[1],  # TYPE_CHECK_HDD
        'info_check': result[2],  # CHECK_HDD
        'lifetime_check': result[4],   # LIFETIME_HDD
        'first_error_check': result[5],   # FIRST_ERROR_HDD
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


def score_ram(ram_data):
    # Score is the relation between memory frequency and memory latency.
    # - higher frequency is better
    # - lower latency is better
    #FREQ_RAM=`dmidecode --type 17 | grep Speed | grep -vi unknown | tail -1 | awk {'print $4'}`
    #LAT_RAM=`dmidecode --type 17 | grep Speed | grep -vi unknown | tail -1 | cut -d'(' -f2 | cut -d' ' -f1`
    #SCORE_RAM=`echo ${FREQ_RAM} / ${LAT_RAM} | bc 2>/dev/null`
    raise NotImplementedError
