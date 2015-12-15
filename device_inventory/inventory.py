import abc
import dmidecode
import logging
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


def get_xpath_text(node, path, default=None):
    try:
        return node.xpath("{0}/text()".format(path))[0]
    except IndexError:
        return default


def get_memory(values, units):
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
        return utils.convert_capacity(max_size, 'KB', units)
    return None


class Device(object):
    __metaclass__ = abc.ABCMeta
    
    LSHW_REGEX = r"^{value}(:\d+)?$"
    LSHW_NODE_ID = None
    
    @classmethod
    def retrieve(cls, lshw_xml):
        assert cls.LSHW_NODE_ID is not None, "LSHW_NODE_ID should be defined on the subclass."
        
        objects = []
        # lshw generates nodes' ids in two different ways:
        # a) "nodetype" if there is only a single instance.
        # b) "nodetype:n" if there are several, where n is the number
        #   of instance starting by zero.
        # IDs examples: "multimedia", "multimedia:0", "multimedia:1"
        # NOTE the use of regex has the side effect of including virtual
        # network adapters.
        regex = cls.LSHW_REGEX.format(value=cls.LSHW_NODE_ID)
        xpath_regex = '//node[re:match(@id, "{0}")]'.format(regex)
        namespaces = {"re": "http://exslt.org/regular-expressions"}
        for node in lshw_xml.xpath(xpath_regex, namespaces=namespaces):
            objects.append(cls(node))
        
        if len(objects) == 0:
            logging.debug("NOT found {0} {1}".format(cls, cls.LSHW_NODE_ID))
        
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
        
        self.connectors = {}
        for verbose, value in self.CONNECTORS:
            self.connectors[value] = self.number_of_connectors(lshw_xml, value)
        
        # TODO optimize to only use a dmidecode call
        self.totalSlots = int(utils.run("dmidecode -t 17 | grep -o BANK | wc -l"))
        self.usedSlots = int(utils.run("dmidecode -t 17 | grep Size | grep MB | awk '{print $2}' | wc -l"))
    
    def number_of_connectors(self, root, name):
        for i in range(10):
            if not root.xpath('//node[@id="{0}:{1}"]'.format(name, i)):
                return i
    
    @property
    def freeSlots(self):
        return self.totalSlots - self.usedSlots


class HardDrive(Device):
    # TODO USB and (S)ATA subclasses
    CAPACITY_UNITS = "MB"
    LSHW_NODE_ID = "disk"
    
    def __init__(self, node):
        self.serialNumber = get_xpath_text(node, 'serial')
        self.manufacturer = get_xpath_text(node, 'vendor')
        self.model = get_xpath_text(node, 'product')
        
        logical_name = get_xpath_text(node, 'logicalname')
        self.interface = utils.run("udevadm info --query=all --name={0} | grep ID_BUS | cut -c 11-".format(logical_name))
        self.interface = self.interface or 'ata'
        
        # TODO implement method for USB disk
        if self.interface == "usb":
            self.size = "Unknown"
        
        else:
            # (S)ATA disk
            try:
                size = int(get_xpath_text(node, 'size'))
            except TypeError, ValueError:
                self.size = None
            else:
                unit = 'bytes'  # node.xpath('size/@units')[0]
                self.size = utils.convert_capacity(size, unit, self.CAPACITY_UNITS)
        
        # TODO read config to know if we should run SMART
        if logical_name and self.interface != "usb":
            self.test = self.run_smart(logical_name)
        else:
            logging.error("Cannot execute SMART on device '%s'.", self.serialNumber)
    
    def run_smart(self, logical_name):  # TODO allow choosing short or extended
        return benchmark.hard_disk_smart(disk=logical_name)


class GraphicCard(Device):
    CAPACITY_UNITS = "MB"
    LSHW_NODE_ID = "display"
     
    def __init__(self, node):
        self.serialNumber = None  # TODO could be retrieved?
        self.manufacturer = get_xpath_text(node, 'vendor')
        self.model = get_xpath_text(node, 'product')
        
        # Find VGA memory
        # TODO include output on debug info
        bus_info = get_xpath_text(node, 'businfo').split("@")[1]
        mem = utils.run("lspci -v -s {bus} | "
                        "grep 'prefetchable' | "
                        "grep -v 'non-prefetchable' | "
                        "egrep -o '[0-9]{{1,3}}[KMGT]+'".format(bus=bus_info)
              ).splitlines()

        self.memory = get_memory(mem, self.CAPACITY_UNITS)
    
    @property
    def score(self):
        return benchmark.score_vga(self.model)


class NetworkAdapter(Device):
    SPEED_UNIT = "Mbps"
    LSHW_NODE_ID = "network"
    
    def __init__(self, node):
        self.model = get_xpath_text(node, 'product')
        self.manufacturer = get_xpath_text(node, 'vendor')
        self.serialNumber = self.get_serial(node)
        self.speed = get_xpath_text(node, 'capacity')
        
        if self.speed is not None:
            units = "bps"  # net.xpath('capacity/@units')[0]
            self.speed = utils.convert_speed(self.speed, units, self.SPEED_UNIT)
        
    def get_serial(self, node):
        serial = get_xpath_text(node, 'serial')
        
        # TODO get serialNumber of USB NetworkAdapter!!
        # lshw has other id="network:1"...
        if serial is None:
            logical_name = get_xpath_text(node, 'logicalname')
            if logical_name is None:
                error = "Error retrieving MAC: '%s'"
                logging.error(error, self.model)
                logging.debug(error, etree.tostring(node))
            else:
                serial = utils.get_hw_addr(logical_name)
        
        return serial


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
        # CPU serial number is a random value due to privacy EU policy
        # so we don't retrieve it anymore
        # self.serialNumber = get_subsection_value(self.dmi, "Processor Information", "ID")
        # self.serialNumber = get_xpath_text(node, "serial")
        self.serialNumber = None
        
        try:
            self.numberOfCores = int(os.popen("lscpu | grep 'Core(s) per socket'").read().split(':')[1].strip())
        except ValueError:
            self.numberOfCores = None
        
        self.model = self.sanitize_model(get_xpath_text(node, "product"))
        self.manufacturer = get_xpath_text(node, 'vendor')  # was /proc/cpuinfo | grep vendor_id
        
        try:
            dmi_processor = dmidecode.processor()['0x0004']['data']
        except KeyError:
            logging.debug("Cannot retrieve processor info from DMI.")
            logging.error("Processor.speed")
            logging.error("Processor.address")
        else:
            self.address = self.get_address(dmi_processor)
            self.speed = self.get_speed(dmi_processor)
    
    def get_address(self, dmi_processor):
        """Retrieve processor instruction size, e.g. 32 or 64 (bits)."""
        # address = get_xpath_text(node, "size")
        address = None
        for charac in dmi_processor.get('Characteristics') or []:
            match = re.search('(32|64)-bit', charac)
            if match:
                try:
                    address = int(match.group().rstrip('-bit'))
                except ValueError:
                    pass
                break
        return address
    
    def get_speed(self, dmi_processor):
        speed = dmi_processor.get('Current Speed', None)
        if speed is not None:
            speed = utils.convert_frequency(speed, 'MHz', self.SPEED_UNIT)
        return speed
    
    @property
    def score(self):
        return benchmark.score_cpu()
    
    def sanitize_model(self, value):
        if value is not None:
            value = re.sub(r"\s+ ", " ", value)
        return value


class RamModule(object):
    # TODO split computer.total_memory and RamModule(s) as components
    CAPACITY_UNIT = 'MB'
    SPEED_UNIT = 'Mhz'
    totalSize = 0
    
    @classmethod
    def retrieve(cls):
        ram_modules = []
        for key, value in dmidecode.memory().items():
            module = value['data']
            #is_module = module.get('Bank Locator') not in [None, 'None']
            is_module = module.get('Size') not in [None, 'None']
            if is_module:
                ram_modules.append(cls(
                    manufacturer=module.get('Manufacturer'),
                    serialNumber=module.get('Serial Number'),
                    size=module.get('Size'),
                    speed=module.get('Speed'),
                ))

        cls.totalSize = sum([module.size for module in ram_modules])
        
        return ram_modules
    
    def __init__(self, manufacturer, serialNumber, size, speed):
        self.manufacturer = manufacturer
        self.model = None  # TODO try to retrieve this information
        self.serialNumber = serialNumber
        self.speed = self.sanitize_speed(speed)
        
        # FIXME we cannot replace by dmidecode.QueryTypeId(17)
        # because Type is not filled! Is this a bug?
        dmidecode_out = utils.run("dmidecode -t 17")
        self.interface = get_subsection_value(dmidecode_out, "Memory Device", "Type")
        # EDO|SDRAM|DDR3|DDR2|DDR|RDRAM
        
        try:
            self.size = int(size.split()[0])
        except ValueError, IndexError:
            logging.debug("Cannot retrieve RamMmodule size '{0}'.".format(size))
            self.size = None
    
    @property
    def score(self):
        return benchmark.score_ram(self.speed)
    
    def sanitize_speed(self, value):
        speed = re.search('\d+', value)
        if speed is None:
            return None
        value = speed.group()
        try:
            return float(value)
        except ValueError:
            logging.error("Error sanitizing RAM speed: '{0}'".format(value))
            return None


class SoundCard(Device):
    LSHW_NODE_ID = "multimedia"
    
    def __init__(self, node):
        self.serialNumber = None  # FIXME could be retrieved?
        self.manufacturer = get_xpath_text(node, "vendor")
        self.model = get_xpath_text(node, "product")


class Computer(object):
    DESKTOP = "Desktop"
    LAPTOP = "Laptop"
    NETBOOK = "Netbook"
    SERVER = "Server"
    MICROTOWER = "Microtower"
    TYPES = (
        (DESKTOP, 1),
        (LAPTOP, 2),
        (NETBOOK, 3),
        (SERVER, 4),
        (MICROTOWER, 5),
    )
    COMPONENTS = [
        'graphic_card', 'hard_disk', 'memory', 'motherboard',
        'network_interfaces', 'optical_drives', 'processor', 'sound_cards'
    ]
    
    def __init__(self, load_data=False, **kwargs):
        if load_data:
            self.lshw = self.load_output_from_file(
                kwargs.get('lshw', 'lshw.txt')
            )
            self.lshw_xml = self.load_output_from_file(
                kwargs.get('lshw_xml', 'lshw.xml'),
                format='xml'
            )
            self.dmi = self.load_output_from_file(
                kwargs.get('dmidecode', 'dmidecode.txt')
            )
        else:
            self.call_hardware_inspectors()
        
        # Retrieve computer info
        self.type = kwargs.pop('type', self.DESKTOP)
        self.manufacturer = get_subsection_value(self.dmi, "System Information", "Manufacturer")
        self.model = get_subsection_value(self.dmi, "System Information", "Product Name")
        
        # Initialize computer fields
        self.serialNumber = get_subsection_value(self.dmi, "System Information", "Serial Number")
        
        # Initialize components
        self.processor = Processor.retrieve(self.lshw_xml)
        self.memory = RamModule.retrieve()
        # TODO USB Hard Drive excluded until they are properly implemented
        self.hard_disk = [hd for hd in HardDrive.retrieve(self.lshw_xml)
                          if hd.interface != "usb"]
        self.graphic_card = GraphicCard.retrieve(self.lshw_xml)
        self.motherboard = Motherboard(self.lshw_xml, self.dmi)
        self.network_interfaces = NetworkAdapter.retrieve(self.lshw_xml)
        self.optical_drives = OpticalDrive.retrieve(self.lshw_xml)
        self.sound_cards = SoundCard.retrieve(self.lshw_xml)
        
        # deprecated (only backwards compatibility)
        if kwargs.pop('backcomp', False):
            self.init_serials()
    
    def call_hardware_inspectors(self):
        # http://www.ezix.org/project/wiki/HardwareLiSter
        
        # XML
        self.lshw_xml = etree.fromstring(subprocess.check_output(["lshw", "-xml"]))
        
        # Plain text
        self.lshw = subprocess.check_output(["lshw"], universal_newlines=True)
        self.dmi = subprocess.check_output(["dmidecode"], universal_newlines=True)
        
    def load_output_from_file(self, filename, format=None):
        assert format in [None, 'xml']
        with  open(filename, 'r') as f:
            output = f.read()
        if format == 'xml':
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
            self.memory[0].serialNumber,
            self.hard_disk[0].serialNumber
        )
        self.ID2 = os.popen(cmd).read().strip()
    
    @property
    def verbose_name(self):
        if self.serialNumber is not None:
            return self.serialNumber
        
        if self.motherboard.serialNumber is not None:
            return self.motherboard.serialNumber
        
        for iface in self.network_interfaces:
            if iface.serialNumber is not None:
                return iface.serialNumber.replace(':', '')
        
        return str(uuid.getnode())
