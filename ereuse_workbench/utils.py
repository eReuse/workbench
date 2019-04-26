import datetime
import fcntl
import re
import socket
import struct
from contextlib import contextmanager
from enum import Enum
from itertools import chain
from typing import Any, Iterable, Set

import yaml
from ereuse_utils import Dumpeable
from pydash import clean, get

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


class SanitizedGetter:
    TO_REMOVE = {
        'none',
        'prod',
        'o.e.m',
        'oem',
        r'n/a',
        'atapi',
        'pc',
        'unknown'
    }
    """Delete those *words* from the value"""
    assert all(v.lower() == v for v in TO_REMOVE), 'All words need to be lower-case'

    REMOVE_CHARS_BETWEEN = '(){}[]'
    """
    Remove those *characters* from the value. 
    All chars inside those are removed. Ex: foo (bar) => foo
    """
    CHARS_TO_REMOVE = '*'
    """Remove the characters.

    '*' Needs to be removed or otherwise it is interpreted
    as a glob expression by regexes.
    """

    MEANINGLESS = {
        'to be filled',
        'system manufacturer',
        'system product',
        'sernum',
        'xxxxx',
        'system name',
        'not specified',
        'modulepartnumber',
        'system serial',
        '0001-067a-0000',
        'partnum',
        'manufacturer',
        '0000000',
        'fffff',
        'jedec id:ad 00 00 00 00 00 00 00',
        '012000',
        'x.x',
        'sku'
    }
    """Discard a value if any of these values are inside it. """
    assert all(v.lower() == v for v in MEANINGLESS), 'All values need to be lower-case'

    def dict(self, dictionary: dict, path: str, remove: Set[str] = set(), default: Any = -1,
             type=None):
        """Gets a string value from the dictionary and sanitizes it.
        Returns ``None`` if the value does not exist or it doesn't
        have meaning.

        Values are patterned and compared against sets
        of meaningless characters usually found in LSHW's output.

        :param dictionary: A dictionary potentially containing the value.
        :param path: The key in ``dictionary`` where the value
                    potentially is.
        :param remove: Remove these words if found.
        """
        try:
            v = get(dictionary, path)
        except KeyError:
            return self._default(path, default)
        else:
            return self._sanitize(v, remove, type=type)

    def kv(self, iterable: Iterable, key: str, default: Any = -1, sep=':', type=None) -> Any:
        for line in iterable:
            try:
                k, value, *_ = line.strip().split(sep)
            except ValueError:
                continue
            else:
                if key == k:
                    return self._sanitize(value, type=type)
        return self._default(key, default)

    def sections(self, iterable: Iterable[str], keyword: str, indent='  '):
        section_pos = None
        for i, line in enumerate(iterable):
            if not line.startswith(indent):
                if keyword in line:
                    section_pos = i
                elif section_pos:
                    yield iterable[section_pos:i]
                    section_pos = None
        return

    @staticmethod
    def _default(key, default):
        if default == -1:
            raise IndexError('Value {} not found.'.format(key))
        else:
            return default

    def _sanitize(self, value, remove=set(), type=None):
        if value is None:
            return None
        remove = remove | self.TO_REMOVE
        regex = r'({})\W'.format('|'.join(s for s in remove))
        val = re.sub(regex, '', value, flags=re.IGNORECASE)
        val = '' if val.lower() in remove else val  # regex's `\W` != whole string
        val = re.sub(r'\([^)]*\)', '', val)  # Remove everything between
        for char_to_remove in chain(self.REMOVE_CHARS_BETWEEN, self.CHARS_TO_REMOVE):
            val = val.replace(char_to_remove, '')
        val = clean(val)
        if val and not any(meaningless in val.lower() for meaningless in self.MEANINGLESS):
            return type(val) if type else yaml.load(val, Loader=yaml.SafeLoader)
        else:
            return None
