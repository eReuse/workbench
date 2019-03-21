import datetime
import fcntl
import socket
import struct
from contextlib import contextmanager
from enum import Enum

from ereuse_utils import Dumpeable

LJUST = 38
"""Left-justify the print output to X characters."""


class Severity(Enum):
    Info = 'Info'
    Error = 'Error'


def convert_base(value, src_unit: str, dst_unit: str, distance=1000) -> float:
    src_unit = src_unit.upper()
    dst_unit = dst_unit.upper()
    UNITS = 'UNIT', 'K', 'M', 'G', 'T'
    assert src_unit in UNITS, src_unit
    assert dst_unit in UNITS, dst_unit

    diff = UNITS.index(src_unit) - UNITS.index(dst_unit)

    return value * pow(distance, diff)


def convert_frequency(value, src_unit: str, dst_unit: str) -> float:
    src_unit = src_unit.upper()
    dst_unit = dst_unit.upper()
    UNITS = 'HZ', 'KHZ', 'MHZ', 'GHZ'
    assert src_unit in UNITS, src_unit
    assert dst_unit in UNITS, dst_unit

    diff = UNITS.index(src_unit) - UNITS.index(dst_unit)

    return value * pow(1000, diff)


def convert_capacity(value, src_unit: str, dst_unit: str) -> float:
    # FIXME International System vs IEC
    # https://en.wikipedia.org/wiki/Units_of_information#Systematic_multiples
    src_unit = src_unit.upper()
    dst_unit = dst_unit.upper()
    UNITS = 'BYTES', 'KB', 'MB', 'GB'
    assert src_unit in UNITS, src_unit
    assert dst_unit in UNITS, dst_unit

    diff = UNITS.index(src_unit) - UNITS.index(dst_unit)

    return value * pow(1024, diff)


def convert_speed(value, src_unit: str, dst_unit: str) -> int:
    src_unit = src_unit.upper()
    dst_unit = dst_unit.upper()
    UNITS = 'BPS', 'KBPS', 'MBPS', 'GBPS'
    assert src_unit in UNITS, src_unit
    assert dst_unit in UNITS, dst_unit

    value = int(value)
    diff = UNITS.index(src_unit) - UNITS.index(dst_unit)

    return int(value * pow(1000, diff))


def get_hw_addr(ifname):
    # http://stackoverflow.com/a/4789267/1538221
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    info = fcntl.ioctl(s.fileno(), 0x8927, struct.pack('256s', ifname[:15]))
    return ':'.join('%02x' % ord(char) for char in info[18:24])


class Measurable(Dumpeable):
    """A base class that allows measuring execution times."""

    def __init__(self) -> None:
        super().__init__()
        self.elapsed = None

    @contextmanager
    def measure(self):
        init = datetime.datetime.now(datetime.timezone.utc)
        yield
        self.elapsed = datetime.datetime.now(datetime.timezone.utc) - init
        assert self.elapsed.total_seconds() > 0
