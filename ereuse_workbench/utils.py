import datetime
import fcntl
import socket
import struct
from contextlib import contextmanager
from enum import Enum

import click
from ereuse_utils import Dumpeable

LJUST = 38
"""Left-justify the print output to X characters."""


class Severity(Enum):
    Info = 'Info'
    Error = 'Error'


def convert_base(value, src_unit, dst_unit, distance=1000) -> float:
    UNITS = 'unit', 'K', 'M', 'G', 'T'
    assert src_unit in UNITS, src_unit
    assert dst_unit in UNITS, dst_unit

    diff = UNITS.index(src_unit) - UNITS.index(dst_unit)

    return value * pow(distance, diff)


def convert_frequency(value, src_unit, dst_unit) -> float:
    UNITS = 'Hz', 'KHz', 'MHz', 'GHz'
    assert src_unit in UNITS, src_unit
    assert dst_unit in UNITS, dst_unit

    diff = UNITS.index(src_unit) - UNITS.index(dst_unit)

    return value * pow(1000, diff)


def convert_capacity(value, src_unit, dst_unit) -> float:
    # FIXME International System vs IEC
    # https://en.wikipedia.org/wiki/Units_of_information#Systematic_multiples
    UNITS = 'bytes', 'KB', 'MB', 'GB'
    assert src_unit in UNITS, src_unit
    assert dst_unit in UNITS, dst_unit

    diff = UNITS.index(src_unit) - UNITS.index(dst_unit)

    return value * pow(1024, diff)


def convert_speed(value, src_unit, dst_unit) -> int:
    UNITS = 'bps', 'Kbps', 'Mbps', 'Gbps'
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


def progressbar(iterable=None, length=None, title=''):
    """Customized :def:`click.progressbar` to keep it DRY."""
    return click.progressbar(iterable,
                             length=length,
                             label='{}'.format(title).ljust(LJUST - 2),
                             width=20)
