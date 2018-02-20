import json
import re
from enum import Enum
from itertools import chain
from math import floor
from subprocess import PIPE, Popen
from typing import List

from ereuse_utils.nested_lookup import get_nested_dicts_with_key_containing_value, \
    get_nested_dicts_with_key_value
from pydash import clean, compact, find_key, get, py_

from ereuse_workbench import utils
from ereuse_workbench.benchmarker import Benchmarker


class PrivateFields(Enum):
    """
    These fields are not converted to JSON so they are kept
    private for internal usage.
    """
    logical_name = 'logical_name'


class Computer:
    """
    Gets hardware information from the computer and its components,
    like serial numbers or model names. At the same time and
    if a Benchmarker is passed-in, benchmarks some of them.

    This class is divided by the methods that extract the hardware
    information for each component individually and a ``.run()``
    method that glues them.

    This class uses ``LSHW`` as the main source of hardware information,
    which is obtained once when it is instantiated.
    """
    CONNECTORS = 'usb', 'firewire', 'serial', 'pcmcia'
    TO_REMOVE = {
        'none',
        'prod',
        'o.e.m',
        'oem',
        'n/a',
        'atapi',
        'pc'
    }
    """Delete those *words* from the value."""
    CHARS_TO_REMOVE = '{}[]'
    """Remove those *characters* from the value."""
    MEANINGLESS = {
        'to be filled',
        'system manufacturer',
        'system product',
        'sernum0',
        'xxxxx',
        'system name',
        'not specified',
        'modulepartnumber',
        'system serial',
        '0001-067A-0000-0000-0000',
        'partnum0',
        'manufacturer0'
    }
    """Discard a value if any of these values are inside it."""

    CHASSIS_TO_TYPE = {
        # dmi types from https://ezix.org/src/pkg/lshw/src/master/src/core/dmi.cc#L632
        'Desktop': {'desktop', 'low-profile', 'tower', 'docking', 'all-in-one'},
        'Microtower': {'pizzabox', 'mini-tower', 'space-saving', 'lunchbox', 'mini', 'stick'},
        'Laptop': {'portable', 'laptop', 'convertible', 'tablet', 'detachable'},
        'Netbook': {'notebook', 'handheld', 'sub-notebook'},
        'Server': {'server'}
    }
    """A conversion table from DMI's chassis type value to our type value."""

    def __init__(self, benchmarker: Benchmarker = False):
        self.benchmarker = benchmarker
        # Obtain raw from LSHW
        cmd = 'LC_ALL=C lshw -json -quiet'
        stdout, _ = Popen(cmd, stdout=PIPE, shell=True, universal_newlines=True).communicate()
        self.lshw = json.loads(stdout)

    def run(self) -> (dict, List[dict]):
        """
        Get the hardware information.

        This method returns *almost* DeviceHub ready information in a
        tuple, where the first element is information related to the
        overall machine, like the S/N of the computer, and the second
        item is a list of hardware information per component.
        """
        computer = self.computer()
        components = chain(self.processors(), self.ram_modules(), self.hard_drives(),
                           self.graphic_cards(), [self.motherboard()], self.network_adapters(),
                           self.sound_cards())
        return computer, compact(components)

    def computer(self):
        node = next(get_nested_dicts_with_key_value(self.lshw, 'class', 'system'))
        # Get type
        chassis = py_.get(node, 'configuration.chassis')
        _type = find_key(self.CHASSIS_TO_TYPE, lambda values, key: chassis in values)
        return dict({
            'type': _type,
            '@type': 'Computer'
        }, **self._common(node))

    def processors(self):
        nodes = get_nested_dicts_with_key_value(self.lshw, 'class', 'processor')
        # We want only the physical cpu's, not the logic ones
        # In some cases we may get empty cpu nodes, we can detect them because
        # all regular cpus have at least a description (Intel Core i5...)
        return (self.processor(node) for node in nodes if
                'logical' not in node['id'] and 'description' in node and not node.get('disabled'))

    def processor(self, node):
        speed = utils.convert_frequency(node['size'], node['units'], 'GHz')
        assert 0.1 <= speed <= 9, 'Frequency is not in reasonable GHz'
        processor = {
            '@type': 'Processor',
            'speed': speed,
            'address': node['width']
        }
        if 'cores' in node['configuration']:
            processor['numberOfCores'] = cores = int(node['configuration']['cores'])
            assert 1 <= cores <= 16
        if self.benchmarker:
            processor['benchmark'] = {
                '@type': 'BenchmarkProcessor',
                'score': self.benchmarker.processor()
            }
        processor = dict(processor, **self._common(node))
        processor['serialNumber'] = None  # Processors don't have valid SN :-(
        return processor

    def ram_modules(self):
        # We can get flash memory (BIOS?), system memory and unknown types of memory
        memories = get_nested_dicts_with_key_value(self.lshw, 'class', 'memory')
        is_system_memory = lambda m: clean(m.get('description').lower()) == 'system memory'
        main_memory = next((m for m in memories if is_system_memory(m)), None)
        return (self.ram_module(node) for node in get(main_memory, 'children', []))

    def ram_module(self, module: dict):
        # Node with no size == empty ram slot
        if 'size' in module:
            ram = dict({
                '@type': 'RamModule',
                'size': int(utils.convert_capacity(module['size'], module['units'], 'MB'))
            }, **self._common(module))
            # power of 2
            assert 128 <= ram['size'] <= 2 ** 15 and (ram['size'] & (ram['size'] - 1) == 0), \
                'Invalid value {} MB for RAM Speed'.format(ram['size'])
            if 'clock' in module:
                ram['speed'] = speed = utils.convert_frequency(module['clock'], 'Hz', 'MHz')
                assert 100 <= speed <= 10000, 'Invalid value {} Mhz for RAM speed'.format(speed)
            return ram

    def hard_drives(self):
        nodes = get_nested_dicts_with_key_containing_value(self.lshw, 'id', 'disk')
        # We can get nodes that are not truly disks as they don't have
        # size. Let's just forget about those.
        return (self.hard_drive(node) for node in nodes if 'size' in node)

    def hard_drive(self, node) -> dict or None:
        logical_name = node['logicalname']
        interface = utils.run('udevadm info --query=all --name={} | grep ID_BUS | cut -c 11-'
                              .format(logical_name))
        # todo not sure if ``interface != usb`` is needed
        if interface != 'usb' and not get(node, 'capabilities.removable'):
            hdd = {
                '@type': 'HardDrive',
                'size': floor(utils.convert_capacity(node['size'], node['units'], 'MB')),
                'interface': interface,
                PrivateFields.logical_name: logical_name
            }
            assert 20000 < hdd['size'] < 10 ** 8, 'Invalid HDD size {} MB'.format(hdd['size'])
            if self.benchmarker:
                hdd['benchmark'] = self.benchmarker.benchmark_hdd(logical_name)
            return dict(hdd, **self._common(node))

    def graphic_cards(self):
        nodes = get_nested_dicts_with_key_value(self.lshw, 'class', 'display')
        return (self.graphic_card(node) for node in nodes)

    def graphic_card(self, node) -> dict:
        return dict({
            '@type': 'GraphicCard',
            'memory': self._graphic_card_memory(node['businfo'].split('@')[1])
        }, **self._common(node))

    @staticmethod
    def _graphic_card_memory(bus_info):
        values = utils.run("lspci -v -s {bus} | "
                           "grep 'prefetchable' | "
                           "grep -v 'non-prefetchable' | "
                           "egrep -o '[0-9]{{1,3}}[KMGT]+'".format(bus=bus_info)).splitlines()
        # Get max memory value
        max_size = 0
        for value in values:
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

    def motherboard(self):
        node = next(get_nested_dicts_with_key_value(self.lshw, 'description', 'Motherboard'))
        return dict({
            '@type': 'Motherboard',
            'connectors': {name: self.motherboard_num_of_connectors(name) for name in
                           self.CONNECTORS},
            'totalSlots': int(utils.run('dmidecode -t 17 | grep -o BANK | wc -l')),
            'usedSlots': int(
                utils.run('dmidecode -t 17 | grep Size | grep MB | awk \'{print $2}\' | wc -l'))
        }, **self._common(node))

    def motherboard_num_of_connectors(self, connector_name) -> int:
        connectors = get_nested_dicts_with_key_containing_value(self.lshw, 'id', connector_name)
        if connector_name == 'usb':
            connectors = (c for c in connectors
                          if 'usbhost' not in c['id'] and 'usb' not in c['businfo'])
        return len(tuple(connectors))

    def network_adapters(self):
        nodes = get_nested_dicts_with_key_value(self.lshw, 'class', 'network')
        return (self.network_adapter(node) for node in nodes)

    def network_adapter(self, node):
        network = self._common(node)
        network['@type'] = 'NetworkAdapter'
        if 'capacity' in node:
            network['speed'] = utils.convert_speed(node['capacity'], 'bps', 'Mbps')
        if 'logicalname' in network:
            # If we don't have logicalname it means we don't have the
            # (proprietary) drivers fot that NetworkAdaptor
            # which means we can't access at the MAC address
            # (note that S/N == MAC) "sudo /sbin/lspci -vv" could bring
            # the MAC even if no drivers are installed however more work
            # has to be done in ensuring it is reliable, really needed,
            # and to parse it
            # https://www.redhat.com/archives/redhat-list/2010-October/msg00066.html
            # workbench-live includes proprietary firmwares
            if not network['serialNumber']:
                network['serialNumber'] = utils.get_hw_addr(node['logicalname'])
        return network

    def sound_cards(self):
        nodes = get_nested_dicts_with_key_value(self.lshw, 'class', 'multimedia')
        return (self.sound_card(node) for node in nodes)

    def sound_card(self, node):
        return dict({
            '@type': 'SoundCard'
        }, **self._common(node))

    def _common(self, node: dict) -> dict:
        manufacturer = self.get(node, 'vendor')
        return {
            'manufacturer': manufacturer,
            'model': self.get(node, 'product', remove=manufacturer),
            'serialNumber': self.get(node, 'serial')
        }

    @classmethod
    def get(cls, node: dict, key: str, remove=None) -> object or None:
        """
        Gets a string value from the LSHW node sanitized.

        Words without meaning are removed, spaces trimmed and
        discarded meaningless values.

        :param remove: Remove this word if found.
        """
        to_remove = cls.TO_REMOVE
        if remove:
            to_remove.add(remove)
        regex = re.compile('\\b({})\W'.format('|'.join(re.escape(s) for s in to_remove)), re.I)
        val = regex.sub('', node.get(key, ''))
        val = re.sub(r'\([^)]*\)', '', val)  # Remove everything between ()
        for char_to_remove in cls.CHARS_TO_REMOVE:
            val = val.replace(char_to_remove, '')
        val = clean(val)
        if val and not any(meaningless in val.lower() for meaningless in cls.MEANINGLESS):
            return val
        else:
            return None
