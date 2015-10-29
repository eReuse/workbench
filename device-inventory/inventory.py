import json
import subprocess
import uuid


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
        #lshw = subprocess.check_output(["lshw", "-json"], universal_newlines=True)
        #self.lshw = json.loads(lshw)
        
        # Plain text (current)
        self.lshw = subprocess.check_output(["lshw"], universal_newlines=True)
        self.dmi = subprocess.check_output(["dmidecode"], universal_newlines=True)
        
        self.init_serials()
    
    def init_serials(self):
        # getnode attempts to obtain the hardware address, if fails it
        # chooses a random 48-bit number with its eight bit set to 1
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
    
    @property
    def cpu(self):
        number_cpus = os.cpu_count()  # Python < 3.4 multiprocessing.cpu_count()
        number_cores = None  # TODO lscpu | grep "Core(s) per socket"
        cpu_data = self.lshw_json['children'][0]['children'][1]
        
        return {
            'model_name': cpu_data['product'],
            'vendor': cpu_data['vendor'],  # was /proc/cpuinfo | grep vendor_id
            'speed': cpu_data['size'],
            'units': cpu_data['units'],
            'number_cpus': number_cpus,
            'number_cores': number_cores,
            # XXX 'score_cpu': benchmark.score_cpu(cpu_data),
        }
    
    @property
    def ram(self):
        ram_data = self.lshw_json['children'][0]['children'][0]
        return {
            'size': ram_data['size'],
            'units': ram_data['units'],
            # TODO based on dmidecode
            # http://www.cyberciti.biz/faq/check-ram-speed-linux/
            #'interface': ## FIXME EDO|SDRAM|DDR3|DDR2|DDR|RDRAM
            #'free_slots':
            #'used_slots':
            #'score_ram': benchmark.score_ram(ram_data)
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
