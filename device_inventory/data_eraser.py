#!/usr/bin/env python
import subprocess
import os
import time
import sys
from datetime import datetime

from .conf import settings


def get_hdinfo(path,value):
    return subprocess.Popen(["lsblk",path,"--nodeps","-no",value], stdout=subprocess.PIPE)

def show_selected(sdx_path):
    size = get_hdinfo(sdx_path,"size").stdout.read()
    model = get_hdinfo(sdx_path,"model").stdout.read()
    disk = get_hdinfo(sdx_path,"tran").stdout.read()
    print "Selected %s (Model: %s) (Size:%s) (Type: %s)." % (sdx_path,model.rstrip(" \n"),size.rstrip(" \n"),disk.rstrip(" \n"))

def get_user_input(sdx_path):
    show_selected(sdx_path)
    config_erase = raw_input("Do you want to erase \"{0}\"? [y/N] ".format(sdx_path))
    return config_erase

def erasetor(dev, erase_mode="0"):
    if erase_mode == "0":
        standard = "All zeros, lower Standard"
        steps = "0"
    elif erase_mode == "1":
        standard = "Sector by sector, high Standard"
        raise NotImplementedError
    time_start = time.strftime("%Y-%m-%d %H:%M:%S")
    FMT = "%Y-%m-%d %H:%M:%S"
    try:
         subprocess.call(["shred", "-zvn", steps, dev])
         state = "Successful"
         time_end = time.strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        state = "With errors."
        print "Cannot erase the hard drive '{0}'".format(dev)
    elapsed = datetime.strptime(time_end, FMT) - datetime.strptime(time_start, FMT)
    dict = {'erasure_standard_name': standard,
            'state': state,
            'elapsed_time': str(elapsed),
            'start_time': time_start,
            'end_time': time_end }
    return dict

def do_erasure(sdx):
    erase = settings.get('DEFAULT', 'erase')

    if erase == "yes":
        show_selected(sdx)
        print("Eraser will start in 10 seconds, ALL DATA WILL BE LOST! Press "
              "Ctrl+C to cancel.")
        try:
            time.sleep(10)
        except KeyboardInterrupt:
            print("Eraser on disk '{0}' cancelled by user!".format(sdx))
            return
        return erasetor(sdx)
    
    elif erase == "ask":
        erase = get_user_input(sdx)
        if erase.lower().strip() == "y" or erase.lower().strip() == "yes":
            return erasetor(sdx)

def main(argv=None):
    device = sys.argv[1]
    print do_erasure(device)
    

if __name__ == "__main__":
# checking priveleges
    if os.geteuid() !=  0:
        sys.exit("Must be root to erase data.")

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
