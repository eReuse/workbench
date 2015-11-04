import json
import os
import subprocess
import uuid

from . import benchmark
from .utils import run


def get_subsection_value(output, section_name, subsection_name):
    """Extract data from tabulated output like lshw and dmidecode."""
    section = output.find(section_name)
    subsection = output.find(subsection_name, section)
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
        self.SERIAL3 = get_subsection_value(self.dmi, "Processor Information", "ID")
        
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
    def cpu(self):
        number_cpus = os.cpu_count()  # Python < 3.4 multiprocessing.cpu_count()
        number_cores = os.popen("lscpu | grep 'Core(s) per socket'").read().split(':')[1].strip()
        cpu_data = self.lshw_json['children'][0]['children'][1]
        
        return {
            'nom_cpu': cpu_data['product'],
            'fab_cpu': cpu_data['vendor'],  # was /proc/cpuinfo | grep vendor_id
            'speed_cpu': cpu_data['size'],
            'unit_speed_cpu': cpu_data['units'],
            'number_cpu': number_cpus,
            'number_cores': number_cores,
            'score_cpu': benchmark.score_cpu(),
        }
    
    @property
    def ram(self):
        ram_data = self.lshw_json['children'][0]['children'][0]
        dmidecode = run("dmidecode -t 17")
        
        # TODO optimize to only use a dmidecode call
        total_slots = int(run("dmidecode -t 17 | grep -o BANK | wc -l"))
        used_slots = int(run("dmidecode -t 17 | grep Size | grep MB | awk '{print $2}' | wc -l"))
        speed = get_subsection_value(dmidecode, "Memory Device", "Speed")
        
        return {
            'size': ram_data['size'],
            'units': ram_data['units'],
            # EDO|SDRAM|DDR3|DDR2|DDR|RDRAM
            'interface': get_subsection_value(dmidecode, "Memory Device", "Type"),
            'free_slots': total_slots - used_slots,
            'used_slots': used_slots,
            'score_ram': benchmark.score_ram(speed),
        }
    
    @property
    def hdd(self):
        # optimization? lshw -json -class disk
        # use dict lookup http://stackoverflow.com/a/27234926/1538221
        raise NotImplementedError

    # vga
    # audio
    # network
    # optical disk drives (CDROM, DVDROM)
    # connectors
    # brand & manufacturer (trademark)
