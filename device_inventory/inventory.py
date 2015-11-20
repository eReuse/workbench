import abc
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


def get_xpath_text(node, path, default=None):
    try:
        return node.xpath("{0}/text()".format(path))[0]
    except IndexError:
        return default


class Device(object):
    __metaclass__ = abc.ABCMeta
    
    LSHW_NODE_ID = None
    
    @classmethod
    def retrieve(cls, lshw_xml):
        assert cls.LSHW_NODE_ID is not None, "LSHW_NODE_ID should be defined on the subclass."
        
        objects = []
        for node in lshw_xml.xpath('//node[@id="{0}"]'.format(cls.LSHW_NODE_ID)):
            objects.append(cls(node))
        
        return objects
    

class Motherboard(object):
    CONNECTORS = (
        ("USB", "usb"),
        ("FireWire", "firewire"),
        ("Serial Port", "serial"),
        ("PCMCIA", "pcmcia"),
    )
    
    def __init__(self, lshw_xml, dmi):
        self.serialNumber = get_subsection_value(dmi, "Base Board Information", "Serial Number")
        self.manufacturer =  get_subsection_value(dmi, "Base Board Information", "Manufacturer")
        self.model =  get_subsection_value(dmi, "Base Board Information", "Product Name")
        
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


class HardDrive(Device):
    # TODO USB and (S)ATA subclasses
    CAPACITY_UNITS = "MB"
    LSHW_NODE_ID = "disk"
    
    def __init__(self, node):
        self.serialNumber = get_xpath_text(node, 'serial')
        self.manufacturer = get_xpath_text(node, 'vendor')
        self.logical_name = get_xpath_text(node, 'logicalname')
        self.interface = utils.run("udevadm info --query=all --name={0} | grep ID_BUS | cut -c 11-".format(self.logical_name))
        
        # TODO implement method for USB disk
        if self.interface == "usb":
            self.model = self.serial = self.size = "Unknown"
        
        else:
            # (S)ATA disk
            self.model = utils.run("hdparm -I {0} | grep 'Model\ Number' | cut -c 22-".format(self.logical_name))
            self.serial = utils.run("hdparm -I {0} | grep 'Serial\ Number' | cut -c 22-".format(self.logical_name))
            self.size = utils.run("hdparm -I {0} | grep 'device\ size\ with\ M' | head -n1 | awk '{{print $7}}'".format(self.logical_name))
        
        # TODO read config to know if we should run SMART
        self.smart = self.run_smart()
    
    def run_smart(self):  # TODO allow choosing short or extended
        return benchmark.hard_disk_smart(disk=self.logical_name)


class GraphicCard(Device):
    CAPACITY_UNITS = "MB"
    LSHW_NODE_ID = "display"
     
    def __init__(self, node):
        self.serialNumber = None  # TODO could be retrieved?
        self.manufacturer = get_xpath_text(node, 'vendor')
        self.model = get_xpath_text(node, 'product')
        
        # Find VGA memory
        bus_info = get_xpath_text(node, 'businfo').split("@")[1]
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


class NetworkAdapter(Device):
    SPEED_UNIT = "Mbps"
    LSHW_NODE_ID = "network"
    
    def __init__(self, node):
        self.serialNumber = get_xpath_text(node, 'serial')
        self.model = get_xpath_text(node, 'product')
        self.manufacturer = get_xpath_text(node, 'vendor')
        self.speed = get_xpath_text(node, 'capacity')
        
        if self.speed is not None:
            units = "bps"  # net.xpath('capacity/@units')[0]
            self.speed = utils.convert_speed(self.speed, units, self.SPEED_UNIT)
        
        # TODO get serialNumber of wireless ifaces!!
        # lshw only provides to ethernet
        # use alternative method (e.g. ifconfig)


class OpticalDrive(Device):
    LSHW_NODE_ID = "cdrom"
    
    def __init__(self, node):
        self.serialNumber = None  # TODO could be retrieved?
        self.model = get_xpath_text(node, 'product')
        self.manufacturer = get_xpath_text(node, 'vendor')
        # TODO normalize values?
        self.description = get_xpath_text(node, 'description')


class Processor(Device):
    CLOCK_UNIT = 'MHz'
    SPEED_UNIT = 'GHz'
    LSHW_NODE_ID = 'cpu'
    
    def __init__(self, node):
        ## Search CPU's serial number, if there are several we choose the first
        # A) dmidecode -t processor
        # FIXME Serial Number returns "To be filled by OEM"
        # http://forum.giga-byte.co.uk/index.php?topic=14167.0
        # self.serialNumber = get_subsection_value(self.dmi, "Processor Information", "ID")
        self.serialNumber = get_xpath_text(node, "serial")
        # B) Try to call CPUID? https://en.wikipedia.org/wiki/CPUID
        # http://stackoverflow.com/a/4216034/1538221
        
        # FIXME support multiple CPUs
        #self.number_cpus = multiprocessing.cpu_count()  # Python > 3.4 os.cpu_count()
        self.numberOfCores = os.popen("lscpu | grep 'Core(s) per socket'").read().split(':')[1].strip()
        
        self.model = re.sub(r"\s+ ", " ", get_xpath_text(node, "product"))
        self.manufacturer = get_xpath_text(node, 'vendor')  # was /proc/cpuinfo | grep vendor_id
        
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
        #self.address = get_xpath_text(node, "size")
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
    
    def __init__(self):
        # TODO as we cannot retrieve this information initialize as None
        self.manufacturer = None
        self.model = None
        
        dmi_memory = subprocess.check_output(["dmidecode", "-t" "memory"], universal_newlines=True)
        self.serialNumber = get_subsection_value(dmi_memory, "Memory Device", "Serial Number")
        
        # dm = dmidecode.QueryTypeId(17)
        # self.manufacturer = dm[dm.keys()[0]]['data']['Manufacturer']
        
        dmidecode_out = utils.run("dmidecode -t 17")
        
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
        self.model = product


class Computer(object):
    DESKTOP = "Desktop"
    TYPES = (
        (DESKTOP, "desktop")
    )
    
    def __init__(self, load_data=False):
        if load_data:
            self.lshw = self.load_output_from_file('lshw.txt')
            self.lshw_xml = self.load_output_from_file('lshw.xml', format='xml')
            self.dmi = self.load_output_from_file('dmidecode.txt')
        else:
            self.call_hardware_inspectors()
        
        # Retrieve computer info
        self.type = self.DESKTOP  # TODO ask user or asume any value if not provided
        self.manufacturer = get_subsection_value(self.dmi, "System Information", "Manufacturer")
        self.model = get_subsection_value(self.dmi, "System Information", "Product Name")
        
        # Initialize computer fields
        self.serialNumber = get_subsection_value(self.dmi, "System Information", "Serial Number")
        
        # Initialize components
        self.processor = Processor.retrieve(self.lshw_xml)
        self.memory = MemoryModule()
        self.hard_disk = HardDrive.retrieve(self.lshw_xml)
        self.graphic_card = GraphicCard.retrieve(self.lshw_xml)
        self.motherboard = Motherboard(self.lshw_xml, self.dmi)
        self.network_interfaces = NetworkAdapter.retrieve(self.lshw_xml)
        self.optical_drives = OpticalDrive.retrieve(self.lshw_xml)
        
        # deprecated (only backwards compatibility)
        self.init_serials()
    
    def call_hardware_inspectors(self):
        # http://www.ezix.org/project/wiki/HardwareLiSter
        
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
            self.processor[0].serialNumber,
            self.memory.serialNumber,
            self.hard_disk[0].serialNumber
        )
        self.ID2 = os.popen(cmd).read().strip()
    
    @property
    def sound_cards(self):
        cards = []
        for node in self.lshw_xml.xpath('//node[@id="multimedia"]'):
            product = node.xpath('product/text()')[0]
            cards.append(SoundCard(product))
        return cards
