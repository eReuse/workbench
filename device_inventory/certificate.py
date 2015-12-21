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


def main(argv=None):
    device = sys.argv[1]
    hardware = dict()

    hardware['cert'] =  get_cert(device)
    hardware['device'] = device
    hardware['timestamp'] = get_timestamp()
    hardware['cleaned_sectors'] = get_cleaned_sectors(device)

    print(hardware)

if __name__ == "__main__":
    sys.exit(main(sys.argv))

