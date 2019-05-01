import json
import logging
import os
import re
from contextlib import suppress
from datetime import datetime
from enum import Enum, unique
from fractions import Fraction
from math import floor, hypot
from pathlib import Path
from subprocess import CalledProcessError, PIPE, run
from typing import Iterator, List, Optional, Tuple, Type, TypeVar
from warnings import catch_warnings, filterwarnings

import dateutil.parser
import pySMART
from ereuse_utils import cmd, getter as g, text
from ereuse_utils.nested_lookup import get_nested_dicts_with_key_containing_value, \
    get_nested_dicts_with_key_value

from ereuse_workbench import utils
from ereuse_workbench.benchmark import BenchmarkDataStorage, BenchmarkProcessor, \
    BenchmarkProcessorSysbench, BenchmarkRamSysbench
from ereuse_workbench.erase import Erase, EraseType
from ereuse_workbench.install import Install
from ereuse_workbench.test import MeasureBattery, StressTest, TestDataStorage, \
    TestDataStorageLength
from ereuse_workbench.utils import Dumpeable


class Device(Dumpeable):
    """
    Base class for a computer and each component, containing
    its physical characteristics (like serial number) and Devicehub
    events. For Devicehub events, this class has an interface to execute
    :meth:`.benchmarks`.
    """

    def __init__(self, *sources) -> None:
        """Gets the device information."""
        self.events = set()
        self.type = self.__class__.__name__
        super().__init__()

    def from_lshw(self, lshw_node: dict):
        self.manufacturer = g.dict(lshw_node, 'vendor', default=None, type=str)
        self.model = g.dict(lshw_node,
                            'product',
                            remove={self.manufacturer} if self.manufacturer else set(),
                            default=None,
                            type=str)
        self.serial_number = g.dict(lshw_node, 'serial', default=None, type=str)

    def benchmarks(self):
        """
        Creates and yields the benchmarks for this device. You can then execute
        them with ``benchmark.run()``. Executing this always generates
        new benchmarks.

        Each device overrides this method with its available benchmarks.
        """
        yield from ()  # empty

    def __str__(self) -> str:
        return ' '.join(x for x in (self.model, self.serial_number) if x)


C = TypeVar('C', bound='Component')


class Component(Device):
    @classmethod
    def new(cls, lshw, hwinfo, **kwargs) -> Iterator[C]:
        raise NotImplementedError()


class Processor(Component):
    @classmethod
    def new(cls, lshw: dict, **kwargs) -> Iterator[C]:
        nodes = get_nested_dicts_with_key_value(lshw, 'class', 'processor')
        # We want only the physical cpu's, not the logic ones
        # In some cases we may get empty cpu nodes, we can detect them because
        # all regular cpus have at least a description (Intel Core i5...)
        return (cls(node) for node in nodes if
                'logical' not in node['id']
                and 'description' in node
                and node.get('description').lower() != 'co-processor'
                and not node.get('disabled')
                and 'co-processor' not in node.get('model', '').lower()
                and 'co-processor' not in node.get('description', '').lower()
                and 'width' in node)

    def __init__(self, node: dict) -> None:
        super().__init__(node)
        self.from_lshw(node)
        self.speed = utils.convert_frequency(node['size'], node['units'], 'GHz')
        self.address = node['width']
        try:
            self.cores = int(node['configuration']['cores'])
            self.threads = int(node['configuration']['threads'])
        except KeyError:
            self.threads = os.cpu_count()
            if self.threads == 1:
                self.cores = 1  # If there is only one thread there is only one core
        self.serial_number = None  # Processors don't have valid SN :-(
        if not (0.1 <= self.speed <= 9):
            logging.warning('Speed should be between 0.1 and 9, but is %s', self.speed)
        self.brand, self.generation = self.processor_brand_generation(self.model)

        assert not hasattr(self, 'cores') or 1 <= self.cores <= 16

    def benchmarks(self):
        for Benchmark in BenchmarkProcessor, BenchmarkProcessorSysbench:
            benchmark = Benchmark()
            self.events.add(benchmark)
            yield benchmark

    @staticmethod
    def processor_brand_generation(model: str):
        """Generates the ``brand`` and ``generation`` fields for the given model.

        This returns a tuple with:

        - The brand as a string or None.
        - The generation as an int or None.
        """
        # Intel desktop processor numbers: https://www.intel.com/content/www/us/en/processors/processor-numbers.html
        # Intel server processor numbers: https://www.intel.com/content/www/us/en/processors/processor-numbers-data-center.html

        if 'Duo' in model:
            return 'Core2 Duo', None
        if 'Quad' in model:
            return 'Core2 Quad', None
        if 'Atom' in model:
            return 'Atom', None
        if 'Celeron' in model:
            return 'Celeron', None
        if 'Pentium' in model:
            return 'Pentium', None
        if 'Xeon Platinum' in model:
            generation = int(re.findall(r'\bPlatinum \d{4}\w', model)[0][10])
            return 'Xeon Platinum', generation
        if 'Xeon Gold' in model:
            generation = int(re.findall(r'\bGold \d{4}\w', model)[0][6])
            return 'Xeon Gold', generation
        if 'Xeon' in model:  # Xeon E5...
            generation = 1
            results = re.findall(r'\bV\d\b', model)  # find V1, V2...
            if results:
                generation = int(results[0][1])
            return 'Xeon', generation
        results = re.findall(r'\bi\d-\w+', model)  # i3-XXX..., i5-XXX...
        if results:  # i3, i5...
            return 'Core i{}'.format(results[0][1]), int(results[0][3])
        results = re.findall(r'\bi\d CPU \w+', model)
        if results:  # i3 CPU XXX
            return 'Core i{}'.format(results[0][1]), 1
        results = re.findall(r'\bm\d-\w+', model)  # m3-XXXX...
        if results:
            return 'Core m{}'.format(results[0][1]), None
        return None, None

    def __str__(self) -> str:
        return super().__str__() + (
            ' ({} generation)'.format(self.generation) if self.generation else ''
        )


class RamModule(Component):
    @classmethod
    def new(cls, lshw, **kwargs) -> Iterator[C]:
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
        self.from_lshw(node)
        description = node['description'].upper()
        self.format = 'SODIMM' if 'SODIMM' in description else 'DIMM'
        self.size = int(utils.convert_capacity(node['size'], node['units'], 'MB'))
        for w in description.split():
            if w.startswith('DDR'):  # We assume all DDR are SDRAM
                self.interface = w
                break
            elif w.startswith('SDRAM'):
                # Fallback. SDRAM is generic denomination for DDR types.
                self.interface = w
        if 'clock' in node:
            self.speed = int(utils.convert_frequency(node['clock'], 'Hz', 'MHz'))

        # size is power of 2
        assert 128 <= self.size <= 2 ** 15 and (self.size & (self.size - 1) == 0)
        assert not hasattr(self, 'speed') or 100 <= self.speed <= 10000

    def __str__(self) -> str:
        return '{} {} {}'.format(super().__str__(), self.format, self.size)


class DataStorage(Component):
    @classmethod
    def new(cls, lshw, hwinfo, **kwargs) -> Iterator[C]:
        disks = get_nested_dicts_with_key_containing_value(lshw, 'id', 'disk')

        usb_disks = list()  # List of disks that are plugged in an USB host
        for usb in get_nested_dicts_with_key_containing_value(lshw, 'id', 'usbhost'):
            usb_disks.extend(get_nested_dicts_with_key_containing_value(usb, 'id', 'disk'))

        for disk in (n for n in disks if n not in usb_disks):
            # We can get nodes that are not truly disks as they don't have size
            if 'size' in disk:
                interface = DataStorage.get_interface(disk)
                removable = interface == 'usb' or \
                            disk.get('capabilities', {}).get('removable', False)
                if not removable:
                    yield cls(disk, interface)

    SSD = 'SolidStateDrive'
    HDD = 'HardDrive'

    @unique
    class DataStorageInterface(Enum):
        ATA = 'ATA'
        USB = 'USB'
        PCI = 'PCI'

        def __str__(self):
            return self.value

    def __init__(self, node: dict, interface: str) -> None:
        super().__init__(node)
        self.from_lshw(node)
        self.size = floor(utils.convert_capacity(node['size'], node.get('units', 'bytes'), 'MB'))
        self.interface = self.DataStorageInterface(interface.upper()) if interface else None
        self._logical_name = node['logicalname']
        self.variant = node['version']

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

    def __str__(self) -> str:
        return '{} {} {} with {} MB'.format(super().__str__(), self.interface, self.type,
                                            self.size)

    def benchmarks(self):
        """
        Computes the reading and writing speed of a hard-drive by
        writing and reading a piece of the hard-drive.

        This method does not destroy existing data.
        """
        b = BenchmarkDataStorage(self._logical_name)
        self.events.add(b)
        yield b

    def test_smart(self, length: TestDataStorageLength, callback):
        test = TestDataStorage(callback)
        test.run(self._logical_name, length)
        self.events.add(test)
        return test

    def erase(self, erase: EraseType, erase_steps: int, zeros: bool, callback):
        erasure = Erase(erase, erase_steps, zeros, callback)
        erasure.run(self._logical_name)
        self.events.add(erasure)
        return erasure

    def install(self, path_to_os_image: Path, callback):
        install = Install(path_to_os_image, self._logical_name)
        install.run(callback)
        self.events.add(install)
        return install

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
    @classmethod
    def new(cls, lshw, hwinfo, **kwargs) -> Iterator[C]:
        nodes = get_nested_dicts_with_key_value(lshw, 'class', 'display')
        return (cls(n) for n in nodes if n['configuration'].get('driver', None))

    def __init__(self, node: dict) -> None:
        super().__init__(node)
        self.from_lshw(node)
        self.memory = self._memory(node['businfo'].split('@')[1])

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

    def __str__(self) -> str:
        return '{} with {} MB'.format(super().__str__(), self.memory)


class Motherboard(Component):
    INTERFACES = 'usb', 'firewire', 'serial', 'pcmcia'

    @classmethod
    def new(cls, lshw, hwinfo, **kwargs) -> C:
        node = next(get_nested_dicts_with_key_value(lshw, 'description', 'Motherboard'))
        bios_node = next(get_nested_dicts_with_key_value(lshw, 'id', 'firmware'))
        memory_array = next(g.indents(hwinfo, 'Physical Memory Array', indent='    '), None)
        return cls(node, bios_node, memory_array)

    def __init__(self, node: dict, bios_node: dict, memory_array: Optional[List[str]]) -> None:
        super().__init__(node)
        self.from_lshw(node)
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
        self.bios_date = dateutil.parser.parse(bios_node['date'])
        self.version = bios_node['version']
        self.ram_slots = self.ram_max_size = None
        if memory_array:
            self.ram_slots = g.kv(memory_array, 'Slots', default=None)
            self.ram_max_size = g.kv(memory_array, 'Max. Size', default=None)
            if self.ram_max_size:
                self.ram_max_size = next(text.numbers(self.ram_max_size))

    @staticmethod
    def num_interfaces(node: dict, interface: str) -> int:
        interfaces = get_nested_dicts_with_key_containing_value(node, 'id', interface)
        if interface == 'usb':
            interfaces = (c for c in interfaces
                          if 'usbhost' not in c['id'] and 'usb' not in c['businfo'])
        return len(tuple(interfaces))

    def __str__(self) -> str:
        return super().__str__()


class NetworkAdapter(Component):
    @classmethod
    def new(cls, lshw, hwinfo, **kwargs) -> Iterator[C]:
        nodes = get_nested_dicts_with_key_value(lshw, 'class', 'network')
        return (cls(node) for node in nodes)

    def __init__(self, node: dict) -> None:
        super().__init__(node)
        self.from_lshw(node)
        self.speed = None
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

        self.variant = node.get('version', None)
        self.wireless = bool(node.get('configuration', {}).get('wireless', False))

    def __str__(self) -> str:
        return '{} {} {}'.format(super().__str__(), self.speed,
                                 'wireless' if self.wireless else 'ethernet')


class SoundCard(Component):
    @classmethod
    def new(cls, lshw, hwinfo, **kwargs) -> Iterator[C]:
        nodes = get_nested_dicts_with_key_value(lshw, 'class', 'multimedia')
        return (cls(node) for node in nodes)

    def __init__(self, node) -> None:
        super().__init__(node)
        self.from_lshw(node)


class Display(Component):
    INCHES = 0.03987
    """Inches to mm conversion."""
    TECHS = 'CRT', 'TFT', 'LED', 'PDP', 'LCD', 'OLED', 'AMOLED'
    """Display technologies"""

    @classmethod
    def new(cls, lshw, hwinfo, **kwargs) -> Iterator[C]:
        for node in g.indents(hwinfo, 'Monitor'):
            yield cls(node)

    def __init__(self, node: dict) -> None:
        super().__init__(node)
        self.model = g.kv(node, 'Model')
        self.manufacturer = g.kv(node, 'Vendor')
        self.serial_number = g.kv(node, 'Serial ID', default=None, type=str)
        self.resolution_width, self.resolution_height, self.refresh_rate = text.numbers(
            g.kv(node, 'Resolution')
        )  # pixel, pixel, Hz
        with suppress(StopIteration):
            # some monitors can have several resolutions, and the one
            # in "Detailed Timings" seems the highest one
            timings = next(g.indents(node, 'Detailed Timings', indent='     '))
            self.resolution_width, self.resolution_height = text.numbers(
                g.kv(timings, 'Resolution')
            )
        x, y = text.numbers(g.kv(node, 'Size'))  # mm
        self.size = round(hypot(x, y) * self.INCHES, 1)  # inch
        self.technology = next((t for t in self.TECHS if t in node[0]), None)
        d = '{} {} 0'.format(g.kv(node, 'Year of Manufacture'), g.kv(node, 'Week of Manufacture'))
        # We assume it has been produced the first day of such week
        self.production_date = datetime.strptime(d, '%Y %W %w')
        self._aspect_ratio = Fraction(self.resolution_width, self.resolution_height)

    def __str__(self) -> str:
        return '{0} {1.resolution_width}x{1.resolution_height} {1.size} inches {2}'.format(
            super().__str__(), self, self._aspect_ratio)


class Battery(Component):
    PRE = 'POWER_SUPPLY_'

    @classmethod
    def new(cls, lshw, hwinfo, **kwargs) -> Iterator[C]:
        try:
            uevent = cmd \
                .run('cat', '/sys/class/power_supply/BAT*/uevent', shell=True) \
                .stdout.splitlines()
        except CalledProcessError:
            return
        yield cls(uevent)

    def __init__(self, node: List[str]) -> None:
        super().__init__(node)
        self.serial_number = g.kv(node, self.PRE + 'SERIAL_NUMBER', sep='=', type=str)
        self.manufacturer = g.kv(node, self.PRE + 'MANUFACTURER', sep='=')
        self.model = g.kv(node, self.PRE + 'MODEL_NAME', sep='=')
        self.size = g.kv(node, self.PRE + 'CHARGE_FULL_DESIGN', sep='=') // 1000  # mAh
        self.technology = g.kv(node, self.PRE + 'TECHNOLOGY', sep='=')
        measure = MeasureBattery(
            size=g.kv(node, self.PRE + 'CHARGE_FULL', sep='='),
            voltage=g.kv(node, self.PRE + 'VOLTAGE_NOW', sep='='),
            cycle_count=g.kv(node, self.PRE + 'CYCLE_COUNT', sep='=')
        )
        self.events.add(measure)
        self._wear = round(1 - measure.size / self.size, 2) if self.size and measure.size else None
        self._node = node

    def __str__(self) -> str:
        return '{0} {1.technology}. Size: {1.size} Wear: {1._wear:%}'.format(super().__str__(),
                                                                             self)


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

    COMPONENTS = list(Component.__subclasses__())  # type: List[Type[Component]]
    COMPONENTS.remove(Motherboard)

    def __init__(self, node: dict) -> None:
        super().__init__(node)
        self.from_lshw(node)
        chassis = node['configuration'].get('chassis', '_virtual')
        self.type = next(t for t, values in self.CHASSIS_TYPE.items() if chassis in values)
        self.chassis = next(t for t, values in self.CHASSIS_DH.items() if chassis in values)
        self.sku = g.dict(node, ('configuration', 'sku'), default=None, type=str)
        self.version = g.dict(node, 'version', default=None, type=str)
        self._ram = None

    @classmethod
    def run(cls) -> Tuple['Computer', List[Component]]:
        """
        Gets hardware information from the computer and its components,
        like serial numbers or model names, and benchmarks them.

        This function uses ``LSHW`` as the main source of hardware information,
        which is obtained once when it is instantiated.
        """
        lshw = json.loads(cmd.run('lshw', '-json', '-quiet').stdout)
        hwinfo_raw = cmd.run('hwinfo', '--reallyall').stdout
        hwinfo = hwinfo_raw.splitlines()
        computer = cls(lshw)
        components = []
        for Component in cls.COMPONENTS:
            if Component == Display and computer.type != 'Laptop':
                continue  # Only get display info when computer is laptop
            components.extend(Component.new(lshw=lshw, hwinfo=hwinfo))
        components.append(Motherboard.new(lshw, hwinfo))

        computer._ram = sum(ram.size for ram in components if isinstance(ram, RamModule))
        computer._debug = {
            'lshw': lshw,
            'hwinfo': hwinfo_raw,
            'battery': next(('\n'.join(b._node) for b in components if isinstance(b, Battery)),
                            None)
        }
        return computer, components

    def test_stress(self, minutes: int, callback):
        test = StressTest()
        test.run(minutes, callback)
        self.events.add(test)
        return test

    def benchmarks(self):
        # Benchmark runs for all ram modules so we can't set it
        # to a specific RamModule
        b = BenchmarkRamSysbench()
        self.events.add(b)
        yield b

    def __str__(self) -> str:
        specs = super().__str__()
        return '{} with {} MB of RAM.'.format(specs, self._ram)
