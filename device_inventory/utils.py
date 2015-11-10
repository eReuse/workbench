import os


def convert_frequency(value, src_unit, dst_unit):
    # Hz < KHz < MHz < GHz
    # TODO make more generic
    assert src_unit == "Hz"
    assert dst_unit == "GHz"
    
    return float(value)/pow(1000, 3)


def convert_capacity(value, src_unit, dst_unit):
    # FIXME International System vs IEC
    # https://en.wikipedia.org/wiki/Units_of_information#Systematic_multiples
    # byte < KB < MB < GB
    # TODO make more generic
    assert src_unit == "bytes"
    assert dst_unit == "MB"
    
    return float(value)/pow(1024, 3)


def run(cmd):
    return os.popen(cmd).read().strip()
