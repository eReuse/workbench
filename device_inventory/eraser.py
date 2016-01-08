import os
import stat
import subprocess
import time

from datetime import datetime
from .conf import settings


def get_hdinfo(path,value):
    return subprocess.check_output(["lsblk", path, "--nodeps", "-no", value]).strip()


def erase_disk(dev, erase_mode="0"):
    if erase_mode == "0":
        standard = "All zeros, low standard"
        iterations = "0"  # zero extra iterations (-z implies one)
    elif erase_mode == "1":
        standard = "Sector by sector, high standard"
        raise NotImplementedError
    
    FMT = "%Y-%m-%d %H:%M:%S"
    time_start = time.strftime(FMT)
    try:
        subprocess.check_call(["shred", "-zvn", iterations, dev])
        state = "Successful"
    except subprocess.CalledProcessError:
        state = "With errors."
        print "Cannot erase the hard drive '{0}'".format(dev)
    time_end = time.strftime("%Y-%m-%d %H:%M:%S")
    elapsed = datetime.strptime(time_end, FMT) - datetime.strptime(time_start, FMT)
    
    return {
        'erasure_standard_name': standard,
        'state': state,
        'elapsed_time': str(elapsed),
        'start_time': time_start,
        'end_time': time_end
    }


def do_erasure(sdx):
    if not os.path.exists(sdx):
        raise ValueError("Device '{0}' does not exist.".format(sdx))

    # check if file is a block special device
    if not stat.S_ISBLK(os.stat(sdx).st_mode):
        raise ValueError("File '{0}' is not a block special device.".format(sdx))
    
    print(
        "Selected '{disk}' (model: {model}, size: {size}, type: {connector})".format(
            disk=sdx,
            model=get_hdinfo(sdx, "model"),
            size=get_hdinfo(sdx, "size"),
            connector=get_hdinfo(sdx, "tran")
        )
    )

    erase = settings.get('DEFAULT', 'erase')
    if erase == "yes":
        print("Eraser will start in 10 seconds, ALL DATA WILL BE LOST! Press "
              "Ctrl+C to cancel.")
        try:
            time.sleep(10)
        except KeyboardInterrupt:
            print("Eraser on disk '{0}' cancelled by user!".format(sdx))
            return
        return erase_disk(sdx)
    
    elif erase == "ask":
        confirm = raw_input("Do you want to erase \"{0}\"? [y/N] ".format(sdx))
        if confirm.lower().strip() == "y" or confirm.lower().strip() == "yes":
            return erase_disk(sdx)
    
    print("No disk erased.")
