import json
from enum import Enum
from subprocess import PIPE, Popen, STDOUT

import re
from ereuse_utils.nested_lookup import get_nested_dicts_with_key_containing_value, get_nested_dicts_with_key_value
from pydash import clean, compact, find, py_

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
        p.to_lower().includes('system serial')
    ]

    def __init__(self, benchmarker: Benchmarker):
        self.benchmarker = benchmarker
        # Obtain raw from LSHW
        runcmd = Popen('LC_ALL=C lshw -json -quiet', stdout=PIPE, stderr=STDOUT, shell=True)
        raw, *_ = runcmd.communicate()
        self.lshw = json.loads(raw.decode())

    def run(self) -> (dict, list):
        # Process it
        node, *_ = get_nested_dicts_with_key_value(self.lshw, 'class', 'system')
        computer = self.computer(node)

        # Processors
        nodes = get_nested_dicts_with_key_value(self.lshw, 'class', 'processor')
        components = [self.processor(node) for node in nodes]

        # Ram_modules
        ram_slot, *_ = get_nested_dicts_with_key_value(self.lshw, 'id', 'memory')
        components.extend(self.ram_module(node) for node in ram_slot['children'])

        # Hard drives
        nodes = get_nested_dicts_with_key_containing_value(self.lshw, 'id', 'disk')
        components.extend(self.hard_drive(node) for node in nodes)

        # Graphic cards
        nodes = get_nested_dicts_with_key_value(self.lshw, 'class', 'display')
        components.extend(self.graphic_card(node) for node in nodes)

        # Motherboard
        node, *_ = get_nested_dicts_with_key_value(self.lshw, 'description', 'Motherboard')
        components.append(self.motherboard(node))

        # Network interfaces
        nodes = get_nested_dicts_with_key_value(self.lshw, 'class', 'network')
        components.extend(self.network_adapter(node) for node in nodes)

        # Sound cards
        nodes = get_nested_dicts_with_key_value(self.lshw, 'class', 'multimedia')
        components.extend(self.sound_card(node) for node in nodes)

        return computer, compact(components)

    def computer(self, node):
        return dict({
            'type': py_.get(node, 'configuration.chassis'),
            '@type': 'Computer'
        }, **self._common(node))

    def processor(self, node):
        return dict({
            '@type': 'Processor',
            'speed': utils.convert_frequency(node['size'], node['units'], 'GHz'),
            'numberOfCores': node['configuration']['cores'],
            'address': node['width'],
            'benchmark': {
                '@type': 'BenchmarkProcessor',
                'score': self.benchmarker.processor()
            }
        }, **self._common(node))

    def ram_module(self, module: dict):
        # Node with no size == empty ram slot
        if 'size' in module:
            return dict({
                '@type': 'RamModule',
                'size': utils.convert_capacity(module['size'], module['units'], 'MB'),
                'speed': utils.convert_frequency(module['clock'], 'Hz', 'MHz')
            }, **self._common(module))

    def hard_drive(self, node) -> dict or None:
        logical_name = node['logicalname']
        interface = utils.run('udevadm info --query=all --name={} | grep ID_BUS | cut -c 11-'.format(logical_name))
        interface = interface or 'ata'
        if interface != 'usb':
            return dict({
                '@type': 'HardDrive',
                'size': utils.convert_capacity(node['size'], node['units'], 'MB'),
                'interface': interface,
                PrivateFields.logical_name: logical_name,
                'benchmark': self.benchmarker.benchmark_hdd(logical_name)
            }, **self._common(node))

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

    def motherboard(self, node):
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

    def network_adapter(self, node):
        network = self._common(node)
        network['@type'] = 'NetworkAdapter'
        if 'capacity' in node:
            network['speed'] = utils.convert_speed(node['capacity'], 'bps', 'Mbps')
        network['serialNumber'] = network['serialNumber'] or utils.get_hw_addr(node['logicalname'])
        return network

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
