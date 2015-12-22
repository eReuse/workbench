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
    # CHECK IF IS A USB
    disk = get_hdinfo(device,"tran").stdout.read()
    print disk
    if disk == "usb":
        hardware['cleaned_sectors'] = "0" # review
        hardware['failed_sectors'] = "0" # review
        hardware['total_errors'] = "0" # review
    else:
        hardware['cleaned_sectors'] = get_cleaned_sectors(device) # review
        hardware['failed_sectors'] = "0" # review
        hardware['total_errors'] = "0" # review
    hardware['state'] = "Successful" # review
    hardware['elapsed_time'] = '00:00:00' # review


    print(hardware)

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

