import json
import os
import re
import subprocess
import uuid

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


class Inventory(object):
    def __init__(self):
        # http://www.ezix.org/project/wiki/HardwareLiSter
        # JSON
        lshw_js = subprocess.check_output(["lshw", "-json"], universal_newlines=True)
        self.lshw_json = json.loads(lshw_js)
        
        # Plain text (current)
        self.lshw = subprocess.check_output(["lshw"], universal_newlines=True)
        self.dmi = subprocess.check_output(["dmidecode"], universal_newlines=True)
        
        self.init_serials()
    
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
    def cpu(self):
        FREQ_UNIT = 'GHz'
        number_cpus = os.cpu_count()  # Python < 3.4 multiprocessing.cpu_count()
        number_cores = os.popen("lscpu | grep 'Core(s) per socket'").read().split(':')[1].strip()
        cpu_data = self.lshw_json['children'][0]['children'][1]
        
        # TODO lshw gets current CPU frequency and not maximum CPU frequency
        cpu_freq = utils.convert_frequency(cpu_data['size'], cpu_data['units'], FREQ_UNIT)
        
        return {
            'nom_cpu': cpu_data['product'],
            'fab_cpu': cpu_data['vendor'],  # was /proc/cpuinfo | grep vendor_id
            'speed_cpu': cpu_freq,
            'unit_speed_cpu': FREQ_UNIT,
            'number_cpu': number_cpus,
            'number_cores': number_cores,
            'score_cpu': benchmark.score_cpu(),
        }
    
    @property
    def ram(self):
        CAPACITY_UNIT = 'MB'
        ram_data = self.lshw_json['children'][0]['children'][0]
        dmidecode = utils.run("dmidecode -t 17")
        
        # TODO optimize to only use a dmidecode call
        total_slots = int(utils.run("dmidecode -t 17 | grep -o BANK | wc -l"))
        used_slots = int(utils.run("dmidecode -t 17 | grep Size | grep MB | awk '{print $2}' | wc -l"))
        speed = get_subsection_value(dmidecode, "Memory Device", "Speed")
        
        # FIXME why is not getting all the RAM? (power of 2)
        size = utils.convert_capacity(ram_data['size'], ram_data['units'], CAPACITY_UNIT)
        
        return {
            'size_ram': size,
            'unit_size': CAPACITY_UNIT,
            # EDO|SDRAM|DDR3|DDR2|DDR|RDRAM
            'interface_ram': get_subsection_value(dmidecode, "Memory Device", "Type"),
            'free_slots_ram': total_slots - used_slots,
            'used_slots_ram': used_slots,
            'score_ram': benchmark.score_ram(speed),
        }
    
    @property
    def hdd(self):
        # optimization? lshw -json -class disk
        # use dict lookup http://stackoverflow.com/a/27234926/1538221
        # NOTE only gets info of first HD
        logical_name = get_subsection_value(self.lshw, "*-disk", "logical name")
        interface = utils.run("udevadm info --query=all --name={0} | grep ID_BUS | cut -c 11-".format(logical_name))
        
        # TODO implement method for USB disk
        if interface == "usb":
            model = serial = size = "Unknown"
        
        else:
            # (S)ATA disk
            model = utils.run("hdparm -I {0} | grep 'Model\ Number' | cut -c 22-".format(logical_name))
            serial = utils.run("hdparm -I {0} | grep 'Serial\ Number' | cut -c 22-".format(logical_name))
            size = utils.run("hdparm -I {0} | grep 'device\ size\ with\ M' | head -n1 | awk '{{print $7}}'".format(logical_name))

        
        return {
            "model": model,
            "serial": serial,
            "size": size,
            "measure": "MB",
            "name": logical_name,
            "interface": interface,
        }
    
    @property
    def vga(self):
        product = get_subsection_value(self.lshw, "display", "product")
        vendor = get_subsection_value(self.lshw, "display", "vendor")
        if product or vendor:
            model_vga = "{vendor} {product}".format(vendor=vendor, product=product)
        else:
            model_vga = get_subsection_value(self.lshw, "display", "description")
        
        # Find VGA memory
        bus_info = get_subsection_value(self.lshw, "display", "bus info").split("@")[1]
        mem = utils.run("lspci -v -s {bus} | grep 'prefetchable' | grep -v 'non-prefetchable' | egrep -o '[0-9]{{1,3}}[KMGT]+'".format(bus=bus_info)).splitlines()
        
        # Get max memory value
        max_size = 0
        for value in mem:
            unit = re.split('\d+', value)[1]
            size = int(value.rstrip(unit))
            
            # convert all values to KB before compare
            if unit == 'K':
                size_kb = size
            elif unit == 'M':
                size_kb = size * 1024
            elif unit == 'G':
                size_kb = size * 1024 * 1024
            elif unit == 'T':
                size_kb = size * 1024 * 1024 * 1024
            
            if size_kb > max_size:
                max_size = size_kb
        
        return {
            "model_vga": model_vga,
            "size_vga": int(max_size/1024),
            "unit_size_vga": "MB",
            "score_vga": "",  # TODO
        }
    
    @property
    def audio(self):
        # TODO support several cards
        model = get_subsection_value(self.lshw, "*-multimedia", "product")
        return {
            "model_audio": model,
        }
    
    @property
    def network(self):
        # TODO get all the network interfaces
        model = get_subsection_value(self.lshw, "*-network", "product")
        speed = get_subsection_value(self.lshw, "*-network", "capacity")
        return {
            "model_net": model,
            "speed_net": speed,
        }
    
    @property
    def optical_drives(self):
        # TODO support multiple optical drives
        model = get_subsection_value(self.lshw, "*-cdrom", "product")
        description = get_subsection_value(self.lshw, "*-cdrom", "description")
        return [
            {
                "model_uni": model,
                "tipo_uni": description,  # TODO normalize values?
            },
        ]
    
    @property
    def connectors(self):
        CONNECTORS = (
            ("USB", "usb"),
            ("FireWire", "firewire"),
            ("Serial Port", "serial"),
            ("PCMCIA", "pcmcia"),
        )
        
        result = []
        for verbose, value in CONNECTORS:
            try:
                model = get_subsection_value(self.lshw, "*-{0}".format(value), "product")
            except IndexError:
                pass
            else:
                result.append({
                    "tipus_connector": verbose,
                    "nombre_connector": 1,  # TODO count available connectos
                })
        
        return {"connector": result}
    
    @property
    def brand_info(self):
        manufacturer = get_subsection_value(self.dmi, "System Information", "Manufacturer")
        product = get_subsection_value(self.dmi, "System Information", "Product Name")
        return {
            "fab_marca": manufacturer,
            "model_marca": product,
        }
