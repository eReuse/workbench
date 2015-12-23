#!/usr/bin/env python
import time
import os
import sys
import fcntl
import struct
import subprocess

# checking priveleges
#if os.geteuid() !=  0:
#    print("ERROR: Must be root to export certificates")
#    sys.exit(1)

# Function definition
def get_cert(x):
    return os.path.join(dir,x)

def get_device(x):
    return "/dev/{0}".format(x[:3])

def get_timestamp():
    return time.strftime("%Y-%m-%d %H:%M:%S")

def get_cleaned_sectors(device):
    sectors = subprocess.Popen(["fdisk", "-l", device], stdout=subprocess.PIPE)
    sectors = sectors.stdout.read().split()
    return sectors[6]

def get_hdinfo(path,value):
    return subprocess.Popen(["lsblk",path,"--nodeps","-no",value], stdout=subprocess.PIPE)

def main(argv=None):
    device = sys.argv[1]

    hardware = dict()

    hardware['cert'] =  get_cert(device)
    hardware['device'] = device
    hardware['timestamp'] = get_timestamp()
    hardware['cleaned_sectors'] = get_cleaned_sectors(device) # review
    hardware['failed_sectors'] = "0" # review
    hardware['total_errors'] = "0" # review
    hardware['state'] = "Successful" # review
    hardware['elapsed_time'] = '00:00:00' # review
    hardware['start_time'] = '00:00:01' # review
    hardware['end_time'] = '00:00:02' # review
    hardware['erasure_standard_name'] = 'Zeros, Lower Standard' # review (type of erasure, by default is 1, fast)
    hardware['overwriting_rounds'] = '1' # review (depen of standard erasure)
    hardware['firmware_rounds'] = '0' # 0, no rounds on firmware
    hardware['total_erasure_rounds'] = '1' # total rounds
    hardware['target_id'] = "50" # !! Buscar informacio de que es aixo
    hardware['type'] = get_hdinfo(device,"type").stdout.read().rstrip(" \n")
    hardware['model'] = get_hdinfo(device,"model").stdout.read().rstrip(" \n")

    
    export_xml(hardware)

def export_xml(get):
    hardware = get
    export = "<blancco_erasure_report>"
    export = export + "\n\t<entries name=\"erasures\">"
    export = export + "\n\t\t<entries name=\"erasure\">"
    export = export + "\n\t\t\t<entry name=\"{0}\" type=\"{1}\">{2}</entry>".format("timestamp","string",hardware['timestamp'])
    export = export + "\n\t\t\t<entry name=\"{0}\" type=\"{1}\">{2}</entry>".format("cleaned_sectors","uint",hardware['cleaned_sectors'])
    export = export + "\n\t\t\t<entry name=\"{0}\" type=\"{1}\">{2}</entry>".format("failed_sectors","uint",hardware['failed_sectors'])
    export = export + "\n\t\t\t<entry name=\"{0}\" type=\"{1}\">{2}</entry>".format("total_errors","uint",hardware['total_errors'])
    export = export + "\n\t\t\t<entry name=\"{0}\" type=\"{1}\">{2}</entry>".format("state","string",hardware['state'])
    export = export + "\n\t\t\t<entry name=\"{0}\" type=\"{1}\">{2}</entry>".format("elapsed_time","string",hardware['elapsed_time'])
    export = export + "\n\t\t\t<entry name=\"{0}\" type=\"{1}\">{2}</entry>".format("start_time","string",hardware['start_time'])
    export = export + "\n\t\t\t<entry name=\"{0}\" type=\"{1}\">{2}</entry>".format("end_time","string",hardware['end_time'])
    export = export + "\n\t\t\t<entry name=\"{0}\" type=\"{1}\">{2}</entry>".format("erasure_standard_name","string",hardware['erasure_standard_name'])
    export = export + "\n\t\t\t<entry name=\"{0}\" type=\"{1}\">{2}</entry>".format("overwriting_rounds","uint",hardware['overwriting_rounds'])
    export = export + "\n\t\t\t<entry name=\"{0}\" type=\"{1}\">{2}</entry>".format("firmware_rounds","uint",hardware['firmware_rounds'])
    export = export + "\n\t\t\t<entry name=\"{0}\" type=\"{1}\">{2}</entry>".format("total_erasure_rounds","uint",hardware['total_erasure_rounds'])
    export = export + "\n\t\t\t<entries name=\"target\">"
    export = export + "\n\t\t\t\t<entry name=\"{0}\" type=\"{1}\">{2}</entry>".format("target_id","uint",hardware['target_id'])
    export = export + "\n\t\t\t\t<entry name=\"{0}\" type=\"{1}\">{2}</entry>".format("type","string",hardware['type'])
    export = export + "\n\t\t\t\t<entry name=\"{0}\" type=\"{1}\">{2}</entry>".format("model","string",hardware['model'])

    print export

if __name__ == "__main__":
    try:
        arg_var = sys.argv[1]
    except IndexError:
        exit("No devices selected.")
    if len(arg_var) < 7:
        exit("Device not valid.")
    if os.path.exists(arg_var):
        sys.exit(main(sys.argv))
    else:
        exit("Device does not exit.")

