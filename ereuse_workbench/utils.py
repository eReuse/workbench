import datetime
import fcntl
import json
import socket
import struct
from contextlib import contextmanager

import click
import inflection
from ereuse_utils import JSONEncoder

LJUST = 38
"""Left-justify the print output to X characters."""


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


class Dumpeable:
    """
    A base class to allow inner classes to generate ``json`` and similar
    structures in an easy-way. It prevents private and
    constants to be in the JSON and camelCases field names.
    """

    def dump(self):
        """
        Creates a dictionary consisting of the
        non-private fields of this instance with camelCase field names.
        """
        d = vars(self).copy()
        for name in vars(self).keys():
            if name.startswith('_') or name[0].isupper():
                del d[name]
            else:
                d[inflection.camelize(name, uppercase_first_letter=False)] = d.pop(name)
        return d

    def to_json(self):
        """
        Creates a JSON representation of the non-private fields of
        this class.
        """
        return json.dumps(self, cls=DumpeableJSONEncoder, indent=2)


class Measurable(Dumpeable):
    """A base class that allows measuring execution times."""

    def __init__(self) -> None:
        super().__init__()
        self.elapsed = None

    @contextmanager
    def measure(self):
        init = datetime.datetime.utcnow()
        yield
        self.elapsed = datetime.datetime.utcnow() - init


class DumpeableJSONEncoder(JSONEncoder):
    """Performs ``dump`` on ``Dumpeable`` objects."""

    def default(self, obj):
        if isinstance(obj, Dumpeable):
            return obj.dump()
        return super().default(obj)


def progressbar(iterable=None, length=None, title=''):
    """Customized :def:`click.progressbar` to keep it DRY."""
    return click.progressbar(iterable,
                             length=length,
                             label='{}'.format(title).ljust(LJUST - 2),
                             width=20)
