import datetime
import os
import stat
import subprocess
import time

from .conf import settings


def get_hdinfo(path,value):
    return subprocess.check_output(["lsblk", path, "--nodeps", "-no", value]).strip()


def erase_process(dev, options, steps):
    # Erasing
    try:
        subprocess.check_call(["shred", options, str(steps), dev])
        state = True
    except subprocess.CalledProcessError:
        state = False
        print "Cannot erase the hard drive '{0}'".format(dev)
    return state
def erase_sectors(disk, output):
    try:
        subprocess.check_output(["badblocks", "-st", "random", "-w", disk, "-o", output])
        return True
    except subprocess.CalledProcessError:
        print "Cannot erase the hard drive '{0}'".format(disk)
        return False

def get_output(output):
    with open(output) as f:
        content = f.readlines()
    return content

def erase_disk(dev):
    time_start = get_datetime()
    mode= settings.get('eraser', 'MODE')
    zeros = settings.getboolean('eraser', 'ZEROS')
    steps = settings.getint('eraser', 'STEPS')
    count = steps
    step = []
    
    # RANDOM WITH SHRED
    if mode == "EraseBasic":
        while count != 0:
            step.append({
                '@type': 'Random',
                'startingTime': get_datetime(),
                'success': erase_process(dev, '-vn', 1),
                'endingTime': get_datetime(),
            })
            count -= 1
    # RANDOM WITH BADBLOCK
    elif mode == "StepByStep":
        while count != 0:
            output = "/tmp/badblocks"
            step.append({
                '@type': 'Random',
                'startingTime': get_datetime(),
                'success': erase_sectors(dev, output),
                'endingTime': get_datetime(),
                'errorOutput': get_output(output),
            })
            count -= 1
    
    # ZEROS WITH SHRED
    if zeros == True:
        step.append({
            '@type': 'Zeros',
            'startingTime': get_datetime(),
            'success': erase_process(dev, '-zvn', 0),
            'endingTime': get_datetime(),
        })
        
    time_end = get_datetime()
    return {
        '@type': mode,
        'secureRandomSteps': steps,
        'cleanWithZeros': zeros,
        'startingTime': time_start,
        'endingTime': time_end,
        'steps': step
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

    erase = settings.get('eraser', 'ERASE')
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


# TODO move to utils
def get_datetime():
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat()
