import json
import re
from enum import Enum, unique
from itertools import chain
from math import floor
from pathlib import Path
from subprocess import PIPE, run
from typing import Iterator, List, Set, Tuple, Union
from warnings import catch_warnings, filterwarnings

import pySMART
from ereuse_utils.nested_lookup import get_nested_dicts_with_key_containing_value, \
    get_nested_dicts_with_key_value
from pydash import clean

from ereuse_workbench import utils
from ereuse_workbench.benchmark import BenchmarkDataStorage, BenchmarkProcessor, \
    BenchmarkProcessorSysbench, BenchmarkRamSysbench
from ereuse_workbench.erase import Erase, EraseType
from ereuse_workbench.install import Install
from ereuse_workbench.test import StressTest, TestDataStorage, TestDataStorageLength
from ereuse_workbench.utils import Dumpeable


class Device(Dumpeable):
    """
    Base class for a computer and each component, containing
    its physical characteristics (like serial number) and Devicehub
    events. For Devicehub events, this class has an interface to execute
    :meth:`.benchmarks`.
    """

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

    CHARS_TO_REMOVE = '(){}[]'
    """
    Remove those *characters* from the value. 
    All chars inside those are removed. Ex: foo (bar) => foo
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
        'fffff'
    }
    """Discard a value if any of these values are inside it. """
    assert all(v.lower() == v for v in MEANINGLESS), 'All values need to be lower-case'

    def __init__(self, node: dict) -> None:
        """Gets the device information."""
        self.manufacturer = self.get(node, 'vendor')
        self.model = self.get(node, 'product',
                              remove={self.manufacturer} if self.manufacturer else None)
        self.serial_number = self.get(node, 'serial')
        self.events = set()
        self.type = self.__class__.__name__
        super().__init__()

    @classmethod
    def get(cls, dictionary: dict, key: str, remove: Set[str] = None) -> str or None:
        """
        Gets a string value from the dictionary and sanitizes it.
        Returns ``None`` if the value does not exist or it doesn't
        have meaning.

        Values are patterned and compared against sets
        of meaningless characters usually found in LSHW's output.

        :param dictionary: A dictionary potentially containing the value.
        :param key: The key in ``dictionary`` where the value
                    potentially is.
        :param remove: Remove these words if found.
        """
        remove = (remove or set()) | cls.TO_REMOVE
        regex = r'({})\W'.format('|'.join(s for s in remove))
        val = re.sub(regex, '', dictionary.get(key, ''), flags=re.IGNORECASE)
        val = '' if val.lower() in remove else val  # regex's `\W` != whole string
        val = re.sub(r'\([^)]*\)', '', val)  # Remove everything between CHARS_TO_REMOVE
        for char_to_remove in cls.CHARS_TO_REMOVE:
            val = val.replace(char_to_remove, '')
        val = clean(val)
        if val and not any(meaningless in val.lower() for meaningless in cls.MEANINGLESS):
            return val
        else:
            return None

    def benchmarks(self):
        """
        Execute all available benchmarks, if any.

        Each device overrides this method with its available benchmarks.
        """
        pass


class Component(Device):
    @classmethod
    def from_lshw(cls, lshw: dict) -> Union[Iterator['Device'], 'Device']:
        """Obtains all the devices of this type from the LSHW output."""
        raise NotImplementedError()


class Processor(Component):
    @classmethod
    def from_lshw(cls, lshw: dict) -> Iterator['Processor']:
        nodes = get_nested_dicts_with_key_value(lshw, 'class', 'processor')
        # We want only the physical cpu's, not the logic ones
        # In some cases we may get empty cpu nodes, we can detect them because
        # all regular cpus have at least a description (Intel Core i5...)
        return (cls(node) for node in nodes if
                'logical' not in node['id'] and 'description' in node and not node.get('disabled'))

    def __init__(self, node: dict) -> None:
        super().__init__(node)
        self.speed = utils.convert_frequency(node['size'], node['units'], 'GHz')
        self.address = node['width']
        if 'cores' in node['configuration']:
            self.cores = int(node['configuration']['cores'])
        self.serial_number = None  # Processors don't have valid SN :-(
        assert 0.1 <= self.speed <= 9
        assert not hasattr(self, 'cores') or 1 <= self.cores <= 16

    def benchmarks(self):
        for Benchmark in BenchmarkProcessor, BenchmarkProcessorSysbench:
            benchmark = Benchmark()
            benchmark.run()
            self.events.add(benchmark)


class RamModule(Component):
    @classmethod
    def from_lshw(cls, lshw: dict) -> Iterator['RamModule']:
        # We can get flash memory (BIOS?), system memory and unknown types of memory
        memories = get_nested_dicts_with_key_value(lshw, 'class', 'memory')
        TYPES = {'ddr', 'sdram', 'sodimm'}
        for memory in memories:
            physical_ram = any(t in memory.get('description', '').lower() for t in TYPES)
            not_empty = 'size' in memory
            if physical_ram and not_empty:
                yield cls(memory)

    def __init__(self, node: dict) -> None:
        # Node with no size == empty ram slot
        super().__init__(node)
        description = node['description'].upper()
        self.form = 'SODIMM' if 'SODIMM' in description else 'DIMM'
        self.size = int(utils.convert_capacity(node['size'], node['units'], 'MB'))
        for w in description.split():
            if w.startswith('DDR'):
                self.interface = w
                break
            elif w.startswith('SDRAM') or w.startswith('SODIMM'):
                self.interface = w
        if 'clock' in node:
            self.speed = utils.convert_frequency(node['clock'], 'Hz', 'MHz')

        # size is power of 2
        assert 128 <= self.size <= 2 ** 15 and (self.size & (self.size - 1) == 0)
        assert not hasattr(self, 'speed') or 100 <= self.speed <= 10000

    def benchmarks(self):
        b = BenchmarkRamSysbench()
        b.run()
        self.events.add(b)


class DataStorage(Component):
    @classmethod
    def from_lshw(cls, lshw: dict) -> Iterator['DataStorage']:
        nodes = get_nested_dicts_with_key_containing_value(lshw, 'id', 'disk')
        # We can get nodes that are not truly disks as they don't have
        # size. Let's just forget about those.
        for node in nodes:
            if 'size' in node:
                interface = DataStorage.get_interface(node)
                removable = interface == 'usb' or \
                            node.get('capabilities', {}).get('removable', False)
                if not removable:
                    yield cls(node, interface)

    SSD = 'SolidStateDrive'
    HDD = 'HardDrive'

    @unique
    class DataStorageInterface(Enum):
        ATA = 'ATA'
        USB = 'USB'
        PCI = 'PCI'

    def __init__(self, node: dict, interface: str) -> None:
        super().__init__(node)
        self.size = floor(utils.convert_capacity(node['size'], node['units'], 'MB'))
        self.interface = self.DataStorageInterface(interface.upper()) if interface else None
        self._logical_name = node['logicalname']

        with catch_warnings():
            filterwarnings('error')
            try:
                smart = pySMART.Device(self._logical_name)
            except Warning:
                self.type = self.HDD
            else:
                self.type = self.SSD if smart.is_ssd else self.HDD
                self.serial_number = self.serial_number or smart.serial
                self.model = self.model or smart.model

        assert 10000 < self.size < 10 ** 8, 'Invalid HDD size {} MB'.format(self.size)

    def benchmarks(self):
        """
        Computes the reading and writing speed of a hard-drive by
        writing and reading a piece of the hard-drive.

        This method does not destroy existing data.
        """
        b = BenchmarkDataStorage()
        b.run(self._logical_name)
        self.events.add(b)

    def test_smart(self, length: TestDataStorageLength):
        test = TestDataStorage()
        test.run(self._logical_name, length)
        self.events.add(test)
        return test

    def erase(self, erase: EraseType, erase_steps: int, zeros: bool):
        erasure = Erase(erase, erase_steps, zeros)
        erasure.run(self._logical_name)
        self.events.add(erasure)

    def install(self, path_to_os_image: Path):
        install = Install(path_to_os_image, self._logical_name)
        install.run()
        self.events.add(install)

    @staticmethod
    def get_interface(node: dict):
        interface = run('udevadm info '
                        '--query=all '
                        '--name={} | '
                        'grep '
                        'ID_BUS | '
                        'cut -c 11-'.format(node['logicalname']),
                        check=True, universal_newlines=True, shell=True, stdout=PIPE).stdout
        # todo not sure if ``interface != usb`` is needed
        return interface.strip()


class GraphicCard(Component):
    def __init__(self, node: dict) -> None:
        super().__init__(node)
        self.memory = self._memory(node['businfo'].split('@')[1])

    @classmethod
    def from_lshw(cls, lshw: dict) -> Iterator['GraphicCard']:
        nodes = get_nested_dicts_with_key_value(lshw, 'class', 'display')
        return (cls(n) for n in nodes if n['configuration'].get('driver', None))

    @staticmethod
    def _memory(bus_info):
        ret = run('lspci -v -s {bus} |'
                  'grep \'prefetchable\' | '
                  'grep -v \'non-prefetchable\' | '
                  'egrep -o \'[0-9]{{1,3}}[KMGT]+\''.format(bus=bus_info),
                  stdout=PIPE,
                  shell=True,
                  universal_newlines=True)
        # Get max memory value
        max_size = 0
        for value in ret.stdout.splitlines():
            unit = re.split('\d+', value)[1]
            size = int(value.rstrip(unit))

            # convert all values to KB before compare
            size_kb = utils.convert_base(size, unit, 'K', distance=1024)
            if size_kb > max_size:
                max_size = size_kb

        if max_size > 0:
            size = utils.convert_capacity(max_size, 'KB', 'MB')
            assert 8 < size < 2 ** 14, 'Invalid Graphic Card size {} MB'.format(size)
            return size
        return None


class Motherboard(Component):
    INTERFACES = 'usb', 'firewire', 'serial', 'pcmcia'

    def __init__(self, node: dict) -> None:
        super().__init__(node)
        self.usb = self.num_interfaces(node, 'usb')
        self.firewire = self.num_interfaces(node, 'firewire')
        self.serial = self.num_interfaces(node, 'serial')
        self.pcmcia = self.num_interfaces(node, 'pcmcia')
        self.slots = int(run('dmidecode -t 17 | '
                             'grep -o BANK | '
                             'wc -l',
                             check=True,
                             universal_newlines=True,
                             shell=True,
                             stdout=PIPE).stdout)

    @staticmethod
    def num_interfaces(node: dict, interface: str) -> int:
        interfaces = get_nested_dicts_with_key_containing_value(node, 'id', interface)
        if interface == 'usb':
            interfaces = (c for c in interfaces
                          if 'usbhost' not in c['id'] and 'usb' not in c['businfo'])
        return len(tuple(interfaces))

    @classmethod
    def from_lshw(cls, lshw: dict) -> 'Motherboard':
        node = next(get_nested_dicts_with_key_value(lshw, 'description', 'Motherboard'))
        return cls(node)


class NetworkAdapter(Component):
    def __init__(self, node: dict) -> None:
        super().__init__(node)
        if 'capacity' in node:
            self.speed = utils.convert_speed(node['capacity'], 'bps', 'Mbps')
        if 'logicalname' in node:  # todo this was taken from 'self'?
            # If we don't have logicalname it means we don't have the
            # (proprietary) drivers fot that NetworkAdaptor
            # which means we can't access at the MAC address
            # (note that S/N == MAC) "sudo /sbin/lspci -vv" could bring
            # the MAC even if no drivers are installed however more work
            # has to be done in ensuring it is reliable, really needed,
            # and to parse it
            # https://www.redhat.com/archives/redhat-list/2010-October/msg00066.html
            # workbench-live includes proprietary firmwares
            self.serial_number = self.serial_number or utils.get_hw_addr(node['logicalname'])

    @classmethod
    def from_lshw(cls, lshw: dict) -> Iterator['NetworkAdapter']:
        nodes = get_nested_dicts_with_key_value(lshw, 'class', 'network')
        return (cls(node) for node in nodes)


class SoundCard(Component):
    @classmethod
    def from_lshw(cls, lshw: dict) -> Union[Iterator['Device'], 'Device']:
        nodes = get_nested_dicts_with_key_value(lshw, 'class', 'multimedia')
        return (cls(node) for node in nodes)


class Computer(Device):
    CHASSIS_TYPE = {
        'Desktop': {'desktop', 'low-profile', 'tower', 'docking', 'all-in-one', 'pizzabox',
                    'mini-tower', 'space-saving', 'lunchbox', 'mini', 'stick'},
        'Laptop': {'portable', 'laptop', 'convertible', 'tablet', 'detachable', 'notebook',
                   'handheld', 'sub-notebook'},
        'Server': {'server'},
        'Computer': {'_virtual'}
    }
    """
    A translation dictionary whose keys are Devicehub types and values 
    are possible chassis values that `dmi <https://ezix.org/src/pkg/
    lshw/src/master/src/core/dmi.cc#L632>`_ can offer.
    """
    CHASSIS_DH = {
        'Tower': {'desktop', 'low-profile', 'tower', 'server'},
        'Docking': {'docking'},
        'AllInOne': {'all-in-one'},
        'Microtower': {'mini-tower', 'space-saving', 'mini'},
        'PizzaBox': {'pizzabox'},
        'Lunchbox': {'lunchbox'},
        'Stick': {'stick'},
        'Netbook': {'notebook', 'sub-notebook'},
        'Handheld': {'handheld'},
        'Laptop': {'portable', 'laptop'},
        'Convertible': {'convertible'},
        'Detachable': {'detachable'},
        'Tablet': {'tablet'},
        'Virtual': {'_virtual'}
    }
    """
    A conversion table from DMI's chassis type value Devicehub 
    chassis value.
    """

    COMPONENTS = list(Component.__subclasses__())
    COMPONENTS.remove(Motherboard)

    def __init__(self, node: dict) -> None:
        super().__init__(node)
        chassis = node['configuration'].get('chassis', '_virtual')
        self.type = next(t for t, values in self.CHASSIS_TYPE.items() if chassis in values)
        self.chassis = next(t for t, values in self.CHASSIS_DH.items() if chassis in values)

    @classmethod
    def run(cls) -> Tuple['Computer', List[Component]]:
        """
        Gets hardware information from the computer and its components,
        like serial numbers or model names, and benchmarks them.

        This function uses ``LSHW`` as the main source of hardware information,
        which is obtained once when it is instantiated.
        """
        stdout = run(('lshw', '-json', '-quiet'),
                     check=True,
                     stdout=PIPE,
                     universal_newlines=True).stdout
        lshw = json.loads(stdout)
        computer = cls(lshw)
        components = list(chain.from_iterable(D.from_lshw(lshw) for D in cls.COMPONENTS))
        components.append(Motherboard.from_lshw(lshw))
        return computer, components

    def test_stress(self, minutes: int):
        test = StressTest()
        test.run(minutes)
        self.events.add(test)
