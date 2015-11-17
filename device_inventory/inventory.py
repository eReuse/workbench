import collections
import dmidecode
import json
import multiprocessing
import os
import re
import subprocess
import uuid

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
    
    def __init__(self, lshw_xml):
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
        product = get_subsection_value(lshw, "display", "product")
        vendor = get_subsection_value(lshw, "display", "vendor")
        if product or vendor:
            self.model = "{vendor} {product}".format(vendor=vendor, product=product)
        else:
            self.model = get_subsection_value(lshw, "display", "description")
        
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

        self.size = utils.convert_capacity(max_size, 'KB', 'MB')
    
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
    FREQ_UNIT = 'GHz'
    
    def __init__(self, lshw_json):
        self.number_cpus = multiprocessing.cpu_count()  # Python > 3.4 os.cpu_count()
        self.number_cores = os.popen("lscpu | grep 'Core(s) per socket'").read().split(':')[1].strip()
        
        cpu_data = lshw_json['children'][0]['children'][1]
        self.product = re.sub(r"\s+ ", " ", cpu_data['product'])
        self.vendor = cpu_data['vendor']  # was /proc/cpuinfo | grep vendor_id
        
        speed = dmidecode.processor()['0x0004']['data']['Current Speed']
        self.freq = utils.convert_frequency(speed, 'MHz', self.FREQ_UNIT)
    
    @property
    def score(self):
        return benchmark.score_cpu()


class MemoryModule(object):
    # TODO split computer.total_memory and MemoryModule(s) as components
    CAPACITY_UNIT = 'MB'
    
    def __init__(self, lshw_json):
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
    def __init__(self):
        # http://www.ezix.org/project/wiki/HardwareLiSter
        # JSON
        lshw_js = subprocess.check_output(["lshw", "-json"], universal_newlines=True)
        self.lshw_json = json.loads(lshw_js)

        # XML
        self.lshw_xml = etree.fromstring(subprocess.check_output(["lshw", "-xml"]))
        
        # Plain text (current)
        self.lshw = subprocess.check_output(["lshw"], universal_newlines=True)
        self.dmi = subprocess.check_output(["dmidecode"], universal_newlines=True)
        
        self.init_serials()
        
        # Retrieve computer info
        self.manufacturer = get_subsection_value(self.dmi, "System Information", "Manufacturer")
        self.product = get_subsection_value(self.dmi, "System Information", "Product Name")
        
        # Initialize components
        self.processor = Processor(self.lshw_json)
        self.memory = MemoryModule(self.lshw_json)
        self.hard_disk = HardDisk(self.lshw)
        self.graphic_card = GraphicCard(self.lshw)
        self.motherboard = Motherboard(self.lshw_xml)
    
    def init_serials(self):
        # getnode attempts to obtain the hardware address, if fails it
        # chooses a random 48-bit number with its eight bit set to 1
        # Deprecated hw_addr as ID. TODO use device SN as ID
        self.ID = uuid.getnode()
        if (self.ID >> 40) % 2:
            raise OSError("The system does not seem to have a valid MAC.")
        
        ## Search manufacturer's serial number
        self.SERIAL1 = get_subsection_value(self.dmi, "System Information", "Serial Number")
        
        ## Search motherboard's serial number
        self.SERIAL2 = get_subsection_value(self.dmi, "Base Board Information", "Serial Number")
        
        ## Search CPU's serial number, if there are several we choose the first
        # A) dmidecode -t processor
        # FIXME Serial Number returns "To be filled by OEM"
        # http://forum.giga-byte.co.uk/index.php?topic=14167.0
        # self.SERIAL3 = get_subsection_value(self.dmi, "Processor Information", "ID")
        self.SERIAL3 = get_subsection_value(self.lshw, "*-cpu", "serial")
        
        # B) Try to call CPUID? https://en.wikipedia.org/wiki/CPUID
        # http://stackoverflow.com/a/4216034/1538221
        
        ## Search RAM's serial number, if there are several we choose the first
        dmi_memory = subprocess.check_output(["dmidecode", "-t" "memory"], universal_newlines=True)
        self.SERIAL4 = get_subsection_value(dmi_memory, "Memory Device", "Serial Number")
        
        ## Search hard disk's serial number, if there are several we choose the first
        # FIXME JSON loads fails because of a bug on lshw
        # https://bugs.launchpad.net/ubuntu/+source/lshw/+bug/1405873
        # lshw_disk = json.loads(subprocess.check_output(["lshw", "-json", "-class", "disk"]))
        self.SERIAL5 = get_subsection_value(self.lshw, "*-disk", "serial")
        
        # Deprecated: cksum CRC32 joining 5 serial numbers as secundary ID
        #ID2=`echo ${SERIAL1} ${SERIAL2} ${SERIAL3} ${SERIAL4} ${SERIAL5} | cksum | awk {'print $1'}`
        cmd = "echo {0} {1} {2} {3} {4} | cksum | awk {{'print $1'}}".format(
            self.SERIAL1, self.SERIAL2, self.SERIAL3, self.SERIAL4, self.SERIAL5)
        self.ID2 = os.popen(cmd).read().strip()
    
    @property
    def serials(self):
        return {
            "serial_fab": self.SERIAL1,
            "serial_mot": self.SERIAL2,
            "serial_cpu": self.SERIAL3,
            "serial_ram": self.SERIAL4,
            "serial_hdd": self.SERIAL5,
        }
    
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
