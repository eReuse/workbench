import fcntl
import os
import socket
import struct


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


# http://stackoverflow.com/a/4789267/1538221
def get_hw_addr(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    info = fcntl.ioctl(s.fileno(), 0x8927,  struct.pack('256s', ifname[:15]))
    return ':'.join(['%02x' % ord(char) for char in info[18:24]])


def run(cmd):
    return os.popen(cmd).read().strip()


def strip_null_or_empty_values(dictionary):
    # read meaningless values from a file
    basepath = os.path.dirname(__file__)
    with open(os.path.join(basepath, 'data/meaningless_values.txt')) as f:
        meaningless = [m.strip() for m in f.readlines()]
    
    # See if there is a more efficient way (Dict Comprehensions)
    new = {}
    for key, value in dictionary.iteritems():
        if not (value is None or value in meaningless):
            new[key] = value
    return new
