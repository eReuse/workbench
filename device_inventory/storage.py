import logging
import paramiko
import pyudev
import shutil
import time

from . import utils


def copy_file_to_server(localpath, remotepath, username, password, server):
    """
    Any other exception will be passed through.
    
    :raises AuthenticationException: if authentication failed
    :raises SSHException: if there was any other error connecting or
        establishing an SSH session
    :raises socket.error: if a socket error occurred while connecting
    """
    print("Connecting to server...")
    # FIXME run os.path.isdir(remotepath) via SSH?
    assert not remotepath.endswith("/"), "SFTP needs a full filename path (not a folder)"
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(server, username=username, password=password, timeout=30)
    
    sftp = ssh.open_sftp()
    sftp.put(localpath, remotepath)
    sftp.close()
    ssh.close()


def copy_file_to_usb(localpath):
    context = pyudev.Context()
    monitor = pyudev.Monitor.from_netlink(context)
    monitor.filter_by('block')
    monitor.start()
    
    # Wait until a USB stick is connected
    print("Please insert a USB to copy the output.")
    while True:
        device = monitor.poll()
        logging.debug(device.get('DEVNAME'), device.action, device.device_type)
        if device.action == 'add':
            break
    
    # wait until partition is detected
    monitor.filter_by('partition')
    partition = monitor.poll()
    logging.debug(partition.get('DEVNAME'), partition.action, partition.device_type)

    partition = partition.get('DEVNAME')
    print("USB detected.")

    # wait and retrieve where is mounted the device
    dstpath = ''
    while not dstpath:
        dstpath = utils.run("mount | grep %s | awk '{print $3}'" % partition)
        logging.debug("Fetching to retrieve mount point '%s'.", dstpath)
        time.sleep(1)
    print("USB mounted on %s" % dstpath)
     
    # TODO mkdir on USB?
    shutil.copy(localpath, dstpath)
    utils.run("umount %s" % dstpath)
    print("File '%s' copied properly!" % localpath)
