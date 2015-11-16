import os


def convert_base(value, src_unit, dst_unit, distance=1000):
    UNITS = ['unit', 'K', 'M', 'G', 'T']
    assert src_unit in UNITS, src_unit
    assert dst_unit in UNITS, dst_unit
    
    diff = UNITS.index(src_unit) - UNITS.index(dst_unit)
    
    return value * pow(distance, diff)


def convert_frequency(value, src_unit, dst_unit):
    UNITS = ['Hz', 'KHz', 'MHz', 'GHz']
    assert src_unit in UNITS, src_unit
    assert dst_unit in UNITS, dst_unit
    
    diff = UNITS.index(src_unit) - UNITS.index(dst_unit)
    
    return value * pow(1000, diff)


def convert_capacity(value, src_unit, dst_unit):
    # FIXME International System vs IEC
    # https://en.wikipedia.org/wiki/Units_of_information#Systematic_multiples
    UNITS = ["bytes", "KB", "MB", "GB"]
    assert src_unit in UNITS, src_unit
    assert dst_unit in UNITS, dst_unit
    
    diff = UNITS.index(src_unit) - UNITS.index(dst_unit)
    
    return value * pow(1024, diff)


def convert_speed(value, src_unit, dst_unit):
    # TODO convert to the bigger unit that returns an integer
    UNITS = ["bps", "Kbps", "Mbps", "Gbps"]
    assert src_unit in UNITS, src_unit
    assert dst_unit in UNITS, dst_unit
    
    value = int(value)
    diff = UNITS.index(src_unit) - UNITS.index(dst_unit)
    
    return int(value * pow(1000, diff))


def run(cmd):
    return os.popen(cmd).read().strip()
