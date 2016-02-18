#!/usr/bin/env python
import argparse
import json
import logging
import os
import socket
import sys

from device_inventory import eraser, serializers, storage
from device_inventory.conf import settings
from device_inventory.benchmark import benchmark_hdd
from device_inventory.inventory import Computer


def is_connected():
    # TODO move to utils package
    # TODO: unittests?
    # [Errno -5] No address associated with hostname
    # https://docs.python.org/3.4/library/socket.html#exceptions
    REMOTE_SERVER = "upc.edu"  # TODO make it a configuration option
    try:
        # see if we can resolve the host name (DNS)
        host = socket.gethostbyname(REMOTE_SERVER)
        # connect to the host (network reachable)
        s = socket.create_connection((host, 80), 2)
        return True
    except (socket.herror, socket.gaierror, socket.timeout) as e: # OSError as e:
        pass
    return False


def get_user_input():
    # XXX configurable user input fields
    label = raw_input("Label ID: ")
    comment = raw_input("Comment: ")
    
    # Ask user for choosing the Device.type
    CHOICES = dict((key, value) for value, key in Computer.TYPES)
    formated_choices = "\n".join(["{0}. {1}".format(k,v) for k, v in CHOICES.items()])
    choose_msg = "Choose device type \n{0}\nType: ".format(formated_choices)
    device_type = None
    while device_type not in CHOICES.keys():
        try:
            device_type = int(raw_input(choose_msg))
        except ValueError:
            print("Invalid choice.")
    
    return dict(label=label, comment=comment, device_type=CHOICES[device_type])


def main(argv=None):
    if not os.geteuid() == 0:
        sys.exit("Only root can run this script")
    
    parser = argparse.ArgumentParser()
    
    # allow enabling/disabling debug mode
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--debug', action='store_true',
            help='enable debug mode (extended output file!)')
    group.add_argument('--no-debug', dest='debug', action='store_false',
            help='disable debug mode')
    parser.set_defaults(debug=None)
    
    parser.add_argument('--smart', choices=['none', 'short', 'long'])
    parser.add_argument('--erase', choices=['ask', 'yes', 'no'])
    parser.add_argument('--settings',
            help='file to be loaded as config file')
    args = parser.parse_args()
    
    # try to get custom config file from PXE server
    server = settings.get('server', 'address')
    username = settings.get('server', 'username')
    password = settings.get('server', 'password')
    
    localpath = '/tmp/remote_custom_config.ini'
    remotepath = '/home/ereuse/config.ini'
    try:
        storage.get_file_from_server(remotepath, localpath, username, password, server)
    except Exception as e:  # TODO catch specific exceptions to avoid mask errors
        logging.error("Error retrieving config file '%s' from server '%s'",
                      remotepath, server)
        logging.debug(e)
    else:
        print("Loading configuration from '%s'" % localpath)
        settings.load_config(config_file=localpath)
    
    # load specified config file (if any)
    if args.settings:
        cfg = settings.load_config(config_file=args.settings)
    
    # override settings with command line args
    if args.smart:
        settings.set('DEFAULT', 'smart', args.smart)
    if args.erase:
        settings.set('eraser', 'erase', args.erase)
    if args.debug is not None:
        settings.set('DEFAULT', 'debug', str(args.debug).lower())
    
    debug = settings.getboolean('DEFAULT', 'debug')
    
    user_input = get_user_input()
    kwargs = dict(type=user_input.pop('device_type'),
                  smart=args.smart)
    
    device = Computer(**kwargs)
    # TODO move smart call here!!!
    
    # call eraser for every hard disk!
    for hd in device.hard_disk:
        hd.erasure = eraser.do_erasure(hd.logical_name)
        hd.benchmark = benchmark_hdd(hd.logical_name)
        # FIXME hack to exclude logical_name from serialization
        # create serializer where you can exclude fields
        delattr(hd, 'logical_name')
    
    data = serializers.export_to_devicehub_schema(device, user_input, debug)
    
    # TODO save on the home
    filename = "{0}.json".format(device.verbose_name)  # get_option
    localpath = os.path.join("/tmp", filename)
    with open(localpath, "w") as outfile:
        json.dump(data, outfile, indent=4, sort_keys=True)
    
    # send files to the PXE Server
    if settings.getboolean('DEFAULT', 'sendtoserver'):
        remotepath = os.path.join(settings.get('server', 'remotepath'), filename)
        username = settings.get('server', 'username')
        password = settings.get('server', 'password')
        server = settings.get('server', 'address')
        try:
            storage.copy_file_to_server(localpath, remotepath, username, password, server)
        except Exception as e:
            logging.error("Error copying file '%s' to server '%s'", localpath, server)
            logging.debug(e)
    
    # copy file to an USB drive
    if settings.getboolean('DEFAULT', 'copy_to_usb'):
        try:
            storage.copy_file_to_usb(localpath)
        except KeyboardInterrupt:
            print("Copy to USB cancelled by user!")
        except Exception as e:
            logging.error("Error copying file '%s' to USB", localpath)
            logging.debug(e)
    
    print("Device Inventory has finished properly: {0}".format(localpath))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
