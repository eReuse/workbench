import logging
import pyudev
import shutil
import time

from . import utils


logger = logging.getLogger(__name__)


def copy_file_to_usb(localpath):
    context = pyudev.Context()
    monitor = pyudev.Monitor.from_netlink(context)
    monitor.filter_by('block')
    monitor.start()
    
    # Wait until a USB stick is connected
    print("Please insert a USB to copy the output or press Ctrl+C to omit.")
    while True:
        try:
            device = monitor.poll()
        except KeyboardInterrupt:
            raise
        logger.debug("%s %s %s", device.get('DEVNAME'), device.action,device.device_type)
        if device.action == 'add':
            break
    
    # wait until partition is detected
    monitor.filter_by('partition')
    partition = monitor.poll()
    logger.debug("%s %s %s", partition.get('DEVNAME'), partition.action, partition.device_type)

    partition = partition.get('DEVNAME')
    print("USB detected.")

    # wait and retrieve where is mounted the device
    dstpath = ''
    while not dstpath:
        dstpath = utils.run("mount | grep %s | awk '{print $3}'" % partition)
        logger.debug("Fetching to retrieve mount point '%s'.", dstpath)
        time.sleep(1)
    print("USB mounted on %s" % dstpath)
     
    # TODO mkdir on USB?
    shutil.copy(localpath, dstpath)
    
    # wait until copy is completed before umounting
    for _ in range(0, 10):
        if not utils.run("lsof -w %s" % dstpath):
            break
        time.sleep(1)
    utils.run("umount %s" % dstpath)
    print("File '%s' copied properly!" % localpath)
