import collections
import dmidecode
import json
import multiprocessing
import os
import re
import subprocess

from lxml import etree

from . import benchmark
from . import utils


def get_subsection_value(output, section_name, subsection_name):
    """Extract data from tabulated output like lshw and dmidecode."""
    section = output.find(section_name)
    ## end_section = output.find("*-", section)
    ## XXX WIP try to limit context to a section (how to detect end on dmidecode?)
    ## NOTE will be replaced with dmidecode Python2 library
    subsection = output.find(subsection_name, section)#, end_section)
    end = output.find("\n", subsection)
    return output[subsection:end].split(':')[1].strip()

Connector = collections.namedtuple('Connector', ['name', 'count', 'verbose_name'])

class Motherboard(object):
    CONNECTORS = (
        ("USB", "usb"),
        ("FireWire", "firewire"),
        ("Serial Port", "serial"),
        ("PCMCIA", "pcmcia"),
    )
    
    def __init__(self, lshw_xml, dmi):
        self.serialNumber = get_subsection_value(dmi, "Base Board Information", "Serial Number")
        
        self.connectors = []
        for verbose, value in self.CONNECTORS:
            count = self.number_of_connectors(lshw_xml, value)
            self.connectors.append(
                Connector(name=value, count=count, verbose_name=verbose)
            )
    
    def number_of_connectors(self, root, name):
        for i in range(10):
            if not root.xpath('//node[@id="{0}:{1}"]'.format(name, i)):
                return i


class HardDisk(object):
    # TODO USB and (S)ATA subclasses
    CAPACITY_UNITS = "MB"
    
    def __init__(self, lshw):
        # optimization? lshw -json -class disk
        # use dict lookup http://stackoverflow.com/a/27234926/1538221
        # NOTE only gets info of first HD
        
        
        ## Search hard disk's serial number, if there are several we choose the first
        # FIXME JSON loads fails because of a bug on lshw
        # https://bugs.launchpad.net/ubuntu/+source/lshw/+bug/1405873
        # lshw_disk = json.loads(subprocess.check_output(["lshw", "-json", "-class", "disk"]))
        self.serialNumber = get_subsection_value(lshw, "*-disk", "serial")

        self.logical_name = get_subsection_value(lshw, "*-disk", "logical name")
        self.interface = utils.run("udevadm info --query=all --name={0} | grep ID_BUS | cut -c 11-".format(self.logical_name))
        
        # TODO implement method for USB disk
        if self.interface == "usb":
            self.model = self.serial = self.size = "Unknown"
        
        else:
            # (S)ATA disk
            self.model = utils.run("hdparm -I {0} | grep 'Model\ Number' | cut -c 22-".format(self.logical_name))
            self.serial = utils.run("hdparm -I {0} | grep 'Serial\ Number' | cut -c 22-".format(self.logical_name))
            self.size = utils.run("hdparm -I {0} | grep 'device\ size\ with\ M' | head -n1 | awk '{{print $7}}'".format(self.logical_name))


class GraphicCard(object):
    CAPACITY_UNITS = "MB"
    
    def __init__(self, lshw):
        self.serialNumber = None  # TODO could be retrieved?
        self.manufacturer = get_subsection_value(lshw, "display", "vendor")
        self.model = (get_subsection_value(lshw, "display", "product") or
                      get_subsection_value(lshw, "display", "description"))  # FIXME move to field description?
        
        # Find VGA memory
        bus_info = get_subsection_value(lshw, "display", "bus info").split("@")[1]
        mem = utils.run("lspci -v -s {bus} | grep 'prefetchable' | grep -v 'non-prefetchable' | egrep -o '[0-9]{{1,3}}[KMGT]+'".format(bus=bus_info)).splitlines()
        
        # Get max memory value
        max_size = 0
        for value in mem:
            unit = re.split('\d+', value)[1]
            size = int(value.rstrip(unit))
            
            # convert all values to KB before compare
            size_kb = utils.convert_base(size, unit, 'K', distance=1024)
            if size_kb > max_size:
                max_size = size_kb

        self.memory = utils.convert_capacity(max_size, 'KB', 'MB')
    
    @property
    def score(self):
        return benchmark.score_vga(self.model)


class NetworkInterface(object):
    def __init__(self, net_xml):
        self.product = net_xml.xpath('product/text()')[0]
        try:
            speed = net_xml.xpath('capacity/text()')[0]
            units = "bps"  # net.xpath('capacity/@units')[0]
        except IndexError as e:
            self.speed_net = None
        else:
            # FIXME convert speed to Mbps?
            speed = utils.convert_speed(speed, units, "Mbps")
            self.speed_net = "{0} {1}".format(speed, "Mbps")


class OpticalDrive(object):
    def __init__(self, node_xml):
        self.product = node_xml.xpath('product/text()')[0]
        # TODO normalize values?
        self.description = node_xml.xpath('description/text()')[0]


class Processor(object):
    CLOCK_UNIT = 'MHz'
    SPEED_UNIT = 'GHz'
    
    def __init__(self, lshw, lshw_json):
        ## Search CPU's serial number, if there are several we choose the first
        # A) dmidecode -t processor
        # FIXME Serial Number returns "To be filled by OEM"
        # http://forum.giga-byte.co.uk/index.php?topic=14167.0
        # self.serialNumber = get_subsection_value(self.dmi, "Processor Information", "ID")
        self.serialNumber = get_subsection_value(lshw, "*-cpu", "serial")
        # B) Try to call CPUID? https://en.wikipedia.org/wiki/CPUID
        # http://stackoverflow.com/a/4216034/1538221
        
        # FIXME support multiple CPUs
        #self.number_cpus = multiprocessing.cpu_count()  # Python > 3.4 os.cpu_count()
        self.numberOfCores = os.popen("lscpu | grep 'Core(s) per socket'").read().split(':')[1].strip()
        
        cpu_data = lshw_json['children'][0]['children'][1]
        self.model = re.sub(r"\s+ ", " ", cpu_data['product'])
        self.manufacturer = cpu_data['vendor']  # was /proc/cpuinfo | grep vendor_id
        
        dmi_processor = dmidecode.processor()['0x0004']['data']
        self.speed = utils.convert_frequency(
            dmi_processor['Current Speed'],
            'MHz',
            self.SPEED_UNIT
        )
        self.busClock = utils.convert_frequency(
            dmi_processor['External Clock'],
            'MHz',
            self.CLOCK_UNIT
        )
        # address (32b/64b)
        #self.address = get_subsection_value(lshw, "*-cpu", "size")
        self.address = None
        for charac in dmi_processor['Characteristics']:
            match = re.search('(32|64)-bit', charac)
            if match:
                self.address = match.group().replace('-bit', 'b')
                break
    
    @property
    def score(self):
        return benchmark.score_cpu()


class MemoryModule(object):
    # TODO split computer.total_memory and MemoryModule(s) as components
    CAPACITY_UNIT = 'MB'
    
    def __init__(self, lshw_json):
        dmi_memory = subprocess.check_output(["dmidecode", "-t" "memory"], universal_newlines=True)
        self.serialNumber = get_subsection_value(dmi_memory, "Memory Device", "Serial Number")

        ram_data = lshw_json['children'][0]['children'][0]
        dmidecode_out = utils.run("dmidecode -t 17")
        # dmidecode.QueryTypeId(7)
        
        # TODO optimize to only use a dmidecode call
        self.total_slots = int(utils.run("dmidecode -t 17 | grep -o BANK | wc -l"))
        self.used_slots = int(utils.run("dmidecode -t 17 | grep Size | grep MB | awk '{print $2}' | wc -l"))
        self.speed = get_subsection_value(dmidecode_out, "Memory Device", "Speed")
        self.interface = get_subsection_value(dmidecode_out, "Memory Device", "Type")
        # EDO|SDRAM|DDR3|DDR2|DDR|RDRAM
        
        # FIXME get total size but describe slot per slot
        size = 0
        for key, value in dmidecode.memory().iteritems():
            if value['data'].get('Size', None) is not None:
                size += int(value['data']['Size'].split()[0])
        
        self.size = size
    
    @property
    def free_slots(self):
        return self.total_slots - self.used_slots
    
    @property
    def score(self):
        return benchmark.score_ram(self.speed)


class SoundCard(object):
    def __init__(self, product):
        self.product = product


class Computer(object):
    DESKTOP = "Desktop"
    TYPES = (
        (DESKTOP, "desktop")
    )
    
    def __init__(self, load_data=False):
        if load_data:
            self.lshw = self.load_output_from_file('lshw.txt')
            self.lshw_json = self.load_output_from_file('lshw.json', format='json')
            self.lshw_xml = self.load_output_from_file('lshw.xml', format='xml')
            self.dmi = self.load_output_from_file('dmidecode.txt')
        else:
            self.call_hardware_inspectors()
        
        # Retrieve computer info
        self.type = self.DESKTOP  # TODO ask user or asume any value if not provided
        self.manufacturer = get_subsection_value(self.dmi, "System Information", "Manufacturer")
        self.product = get_subsection_value(self.dmi, "System Information", "Product Name")
        
        # Initialize computer fields
        self.serialNumber = get_subsection_value(self.dmi, "System Information", "Serial Number")
        
        # Initialize components
        self.processor = Processor(self.lshw, self.lshw_json)
        self.memory = MemoryModule(self.lshw_json)
        self.hard_disk = HardDisk(self.lshw)
        self.graphic_card = GraphicCard(self.lshw)
        self.motherboard = Motherboard(self.lshw_xml, self.dmi)
        
        # deprecated (only backwards compatibility)
        self.init_serials()
    
    def call_hardware_inspectors(self):
        # http://www.ezix.org/project/wiki/HardwareLiSter
        # JSON
        lshw_js = subprocess.check_output(["lshw", "-json"], universal_newlines=True)
        self.lshw_json = json.loads(lshw_js)
        
        # XML
        self.lshw_xml = etree.fromstring(subprocess.check_output(["lshw", "-xml"]))
        
        # Plain text
        self.lshw = subprocess.check_output(["lshw"], universal_newlines=True)
        self.dmi = subprocess.check_output(["dmidecode"], universal_newlines=True)
        
    def load_output_from_file(self, filename, format=None):
        assert format in [None, 'json', 'xml']
        with  open(filename, 'r') as f:
            output = f.read()
        if format == 'json':
            output = json.loads(output)
        elif format == 'xml':
            output = etree.fromstring(output)
        return output
    
    def init_serials(self):
        """
        Legacy IDs and serials retrieval.
        (only for backwards compatibility)
        
        """
        match = re.search("([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}", self.lshw)
        if match is not None:
            self.ID = match.group(0).replace(':', '')
        else:
            # The system does not seem to have a valid MAC
            self.ID = "000000000000"
        
        # Deprecated: cksum CRC32 joining 5 serial numbers as secundary ID
        #ID2=`echo ${SERIAL1} ${SERIAL2} ${SERIAL3} ${SERIAL4} ${SERIAL5} | cksum | awk {'print $1'}`
        cmd = "echo {0} {1} {2} {3} {4} | cksum | awk {{'print $1'}}".format(
            self.serialNumber,
            self.motherboard.serialNumber,
            self.processor.serialNumber,
            self.memory.serialNumber,
            self.hard_disk.serialNumber
        )
        self.ID2 = os.popen(cmd).read().strip()
    
    @property
    def sound_cards(self):
        cards = []
        for node in self.lshw_xml.xpath('//node[@id="multimedia"]'):
            product = node.xpath('product/text()')[0]
            cards.append(SoundCard(product))
        return cards
    
    @property
    def network_interfaces(self):
        net_cards = []
        for net_xml in self.lshw_xml.xpath('//node[@id="network"]'):
            net_cards.append(NetworkInterface(net_xml))
        return net_cards
    
    @property
    def optical_drives(self):
        drives = []
        for node in self.lshw_xml.xpath('//node[@id="cdrom"]'):
            drives.append(OpticalDrive(node))
        return drives
