import json
import re
from enum import Enum
from itertools import chain
from subprocess import PIPE, Popen

from ereuse_utils.nested_lookup import get_nested_dicts_with_key_containing_value, get_nested_dicts_with_key_value
from pydash import clean, compact, find, find_key, get, py_

from ereuse_workbench import utils
from ereuse_workbench.benchmarker import Benchmarker


class PrivateFields(Enum):
    """These fields are not converted to JSON so they are kept private for internal usage"""
    logical_name = 'logical_name'


p = py_()


class Computer:
    CONNECTORS = 'usb', 'firewire', 'serial', 'pcmcia'
    MEANINGLESS = [
        p.to_lower().is_equal('to be filled'),
        p.to_lower().includes('o.e.m'),
        p.to_lower().includes('n/a'),
        p.to_lower().is_equal('na'),
        p.to_lower().includes('atapi'),
        p.to_lower().is_equal('system'),
        p.to_lower().includes('sernum0'),
        p.is_equal('['),
        p.to_lower().includes('none'),
        p.to_lower().includes('xxxxx'),
        p.to_lower().includes('prod'),
        p.to_lower().includes('system name'),
        p.to_lower().includes('not specified'),
        p.to_lower().includes('manufacturer'),
        p.to_lower().includes('modulepartnumber'),
        p.to_lower().includes('system manufacturer'),
        p.to_lower().includes('system serial'),
        p.includes('0001-067A-0000-0000-0000')
    ]

    CHASSIS_TO_TYPE = {
        # dmi types from https://ezix.org/src/pkg/lshw/src/master/src/core/dmi.cc#L632
        'Desktop': {'desktop', 'low-profile', 'tower', 'docking', 'all-in-one'},
        'Microtower': {'pizzabox', 'mini-tower', 'space-saving', 'lunchbox', 'mini', 'stick'},
        'Laptop': {'portable', 'laptop', 'convertible', 'tablet', 'detachable'},
        'Netbook': {'notebook', 'handheld', 'sub-notebook'},
        'Server': {'server'}
    }

    def __init__(self, benchmarker: Benchmarker = False):
        self.benchmarker = benchmarker
        # Obtain raw from LSHW
        cmd = 'LC_ALL=C lshw -json -quiet'
        stdout, _ = Popen(cmd, stdout=PIPE, shell=True, universal_newlines=True).communicate()
        self.lshw = json.loads(stdout)

    def run(self) -> (dict, list):
        # Process it
        computer = self.computer()
        components = chain(self.processors(), self.ram_modules(), self.hard_drives(), self.graphic_cards(),
                           [self.motherboard()], self.network_adapters(), self.sound_cards())
        return computer, compact(components)

    def computer(self):
        node, *_ = get_nested_dicts_with_key_value(self.lshw, 'class', 'system')
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
        processor = {
            '@type': 'Processor',
            'speed': utils.convert_frequency(node['size'], node['units'], 'GHz'),
            'numberOfCores': get(node, 'configuration.cores'),
            'address': node['width']
        }
        if self.benchmarker:
            processor['benchmark'] = {
                '@type': 'BenchmarkProcessor',
                'score': self.benchmarker.processor()
            }
        return dict(processor, **self._common(node))

    def ram_modules(self):
        # We can get flash memory (BIOS?), system memory and unknown types of meomry
        memories = get_nested_dicts_with_key_value(self.lshw, 'id', 'memory')
        main_memory = find(memories, lambda m: clean(m.get('description').lower()) == 'system memory')
        return (self.ram_module(node) for node in get(main_memory, 'children', []))

    def ram_module(self, module: dict):
        # Node with no size == empty ram slot
        if 'size' in module:
            return dict({
                '@type': 'RamModule',
                'size': utils.convert_capacity(module['size'], module['units'], 'MB'),
                'speed': utils.convert_frequency(module['clock'], 'Hz', 'MHz') if 'clock' in module else None
            }, **self._common(module))

    def hard_drives(self):
        nodes = get_nested_dicts_with_key_containing_value(self.lshw, 'id', 'disk')
        return (self.hard_drive(node) for node in nodes)

    def hard_drive(self, node) -> dict or None:
        logical_name = node['logicalname']
        interface = utils.run('udevadm info --query=all --name={} | grep ID_BUS | cut -c 11-'.format(logical_name))
        interface = interface or 'ata'
        if interface != 'usb':
            hdd = {
                '@type': 'HardDrive',
                'size': utils.convert_capacity(node['size'], node['units'], 'MB'),
                'interface': interface,
                PrivateFields.logical_name: logical_name
            }
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
            return utils.convert_capacity(max_size, 'KB', 'MB')
        return None

    def motherboard(self):
        node, *_ = get_nested_dicts_with_key_value(self.lshw, 'description', 'Motherboard')
        return dict({
            '@type': 'Motherboard',
            'connectors': {name: self.motherboard_num_of_connectors(name) for name in self.CONNECTORS},
            'totalSlots': int(utils.run('dmidecode -t 17 | grep -o BANK | wc -l')),
            'usedSlots': int(utils.run('dmidecode -t 17 | grep Size | grep MB | awk \'{print $2}\' | wc -l'))
        }, **self._common(node))

    def motherboard_num_of_connectors(self, connector_name):
        connectors = get_nested_dicts_with_key_containing_value(self.lshw, 'id', connector_name)
        if connector_name == 'usb':
            connectors = list(filter(lambda c: 'usbhost' not in c['id'], connectors))
        return len(connectors)

    def network_adapters(self):
        nodes = get_nested_dicts_with_key_value(self.lshw, 'class', 'network')
        return (self.network_adapter(node) for node in nodes)

    def network_adapter(self, node):
        network = self._common(node)
        network['@type'] = 'NetworkAdapter'
        if 'capacity' in node:
            network['speed'] = utils.convert_speed(node['capacity'], 'bps', 'Mbps')
        network['serialNumber'] = network['serialNumber'] or utils.get_hw_addr(node['logicalname'])
        return network

    def sound_cards(self):
        nodes = get_nested_dicts_with_key_value(self.lshw, 'class', 'multimedia')
        return (self.sound_card(node) for node in nodes)

    def sound_card(self, node):
        return dict({
            '@type': 'SoundCard'
        }, **self._common(node))

    def _common(self, node: dict) -> dict:
        return {
            'manufacturer': self.get(node, 'vendor'),
            'model': self.get(node, 'product'),
            'serialNumber': self.get(node, 'serial')
        }

    @classmethod
    def get(cls, node, key) -> object or None:
        """Gets a string value from the LSHW node totally sanitazed."""
        val = node.get(key)
        return clean(val) if val and not find(cls.MEANINGLESS, lambda p: p(val)) else None
