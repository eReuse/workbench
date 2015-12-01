#!/usr/bin/env python
import time
import os
import sys
import fcntl
import struct

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
	
def get_cleaned_sectors():
	return os.system("fdisk -l /dev/sda | head -1 hardware['device'] | awk '{print $7, $8}'")

# INVENTORY

#def get_serial():

#MAIN

# Variables
hardware = dict()
dir = "/home/adria/GitHub/Donator/etc"
dirs = os.listdir(dir)
cert = ".cert"

# FOR every certificate, do...
for file in dirs:
	if file.endswith(cert):
		hardware['cert'] =  get_cert(file)
		hardware['device'] = get_device(file)
		hardware['timestamp'] = get_timestamp()
		hardware['cleaned_sectors'] = get_cleaned_sectors

# Program
		print(hardware)
