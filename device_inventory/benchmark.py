"""
Devices benchmark

Set of programs, or other operations, in order to assess the relative
performance of an object, normally by running a number of standard
tests and trials against it.

"""

def hard_disk_smart():
    # smartctl -a /dev/sda | grep "# 1"
    # # 1  Short offline       Completed without error       00%     10016         -
    # XXX extract data of smartest. Decide which info is relevant.
    raise NotImplementedError


def score_cpu(cpu_data):
    # https://en.wikipedia.org/wiki/BogoMips
    # score = sum(cpu.bogomips for cpu in device.cpus)
    #for i in `grep bogomips /proc/cpuinfo 2>/dev/null | awk {'print $3'} | cut -d '.' -f1`
    #do
    #    SCORE_CPU=`expr ${SCORE_CPU} + ${i}`
    #done
    raise NotImplementedError


def score_ram(ram_data):
    # Score is the relation between memory frequency and memory latency.
    # - higher frequency is better
    # - lower latency is better
    #FREQ_RAM=`dmidecode --type 17 | grep Speed | grep -vi unknown | tail -1 | awk {'print $4'}`
    #LAT_RAM=`dmidecode --type 17 | grep Speed | grep -vi unknown | tail -1 | cut -d'(' -f2 | cut -d' ' -f1`
    #SCORE_RAM=`echo ${FREQ_RAM} / ${LAT_RAM} | bc 2>/dev/null`
    raise NotImplementedError
