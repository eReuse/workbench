#!/usr/bin/env python
import time
import os
import sys
import subprocess
import pprint
from subprocess import check_output

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

def get_firmware_revision(dev):
    disk = get_hdinfo(dev,"tran").stdout.read().rstrip(" \n")
    if disk != "usb":
        out = check_output(["hdparm", "-I", dev])
        firmware = out.splitlines()[6]

        if firmware.split()[0] == "Firmware":
            return firmware.split()[2]
        else:
            return "Null"

def main(argv=None):

    device = sys.argv[1]

    hardware = dict()

    #hardware['cert'] =  get_cert(device)
    #hardware['device'] = device
    timestamp = get_timestamp()
    cleaned_sectors = get_cleaned_sectors(device)
    device_type = get_hdinfo(device,"type").stdout.read().rstrip(" \n")
    device_model = get_hdinfo(device,"model").stdout.read().rstrip(" \n")
    device_vendor = get_hdinfo(device,"vendor").stdout.read().rstrip(" \n")
    device_serial = get_hdinfo(device,"serial").stdout.read().rstrip(" \n")
    firmware_revision = get_firmware_revision(device)
    
    # Real start of the certificate
    hardware = {'erasure_id': "1",
                'timestamp': timestamp,
                'cleaned_sectors': cleaned_sectors,
                'failed_sectors': "0",
                'total_errors': "0",
                'state': "Successful",
                'elapsed_time': '00:00:00',
                'start_time': '00:00:01',
                'end_time': '00:00:02',
                'erasure_standard_name': 'Zeros, Lower Standard',
                'overwriting_rounds': '1',
                'firmware_rounds': '0',
                'total_erasure_rounds': '1',
                'target': {
                    'target_id': "50",
                    'type': device_type,
                    'model': device_model,
                    'vendor': device_vendor,
                    'serial': device_serial,
                    'firmware_revision': firmware_revision} 
                }

    pprint.pprint(hardware)

if __name__ == "__main__":

# checking priveleges
    if os.geteuid() !=  0:
        sys.exit("Must be root to export certificates")

    try:
        arg_var = sys.argv[1]
    except IndexError:
        exit("No devices selected.")

    if len(arg_var) < 7:
        exit("Device not valid.")
        
    # Start
    if os.path.exists(arg_var):
        sys.exit(main(sys.argv))
    else:
        exit("Device does not exit.")

