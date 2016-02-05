#!/usr/bin/env python
import argparse
import calendar
import datetime
import json
import logging
import os
import socket
import sys
import time

from device_inventory import eraser, serializers, storage
from device_inventory.benchmark import hard_disk_smart, benchmark_hdd
from device_inventory.conf import settings
from device_inventory.inventory import Computer


def is_connected():
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


def get_device_status(run_smart):
    # legacy (only backwards compatibility)
    if run_smart:
        hdd = '/dev/sda'  # TODO select proper HD!
        result = hard_disk_smart(hdd)
        smart = {
            "check": "Yes",
            "device_check": hdd,
            "type_check": result['type'],
            "info_check": result['status'],
            "lifetime_check": result['lifetime'],
            "first_error_check": result['firstError'],
        }
    else:
        smart = {
            "check": "No",
            "device_check": 'null',
            "type_check": 'null',
            "info_check": 'null',
            "lifetime_check": 'null',
            "first_error_check": '-',
        }
    
    return {
        "dat_estat": datetime.date.today().isoformat(),
        "version": "1.0",
        "online": "SI" if is_connected() else "NO",
        "smartest": smart,
    }


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
    parser.add_argument('--smart', choices=['none', 'short', 'long'])
    args = parser.parse_args()
    
    # override settings with command line args
    if args.smart:
        settings.set('DEFAULT', 'smart', args.smart)
    
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


def legacy_main(**kwargs):
    # FIXME duplicated data initial_donator_time & status.date (dat_state)
    # initial_donator in seconds since 1970 UTC
    # dat_state only date on human friendly format
    beg_donator_time = calendar.timegm(time.gmtime())  # INITIAL_DONATOR_TIME
    device = Computer(backcomp=True, **kwargs)  # XXX pass device type and other user input?
    status = get_device_status(run_smart=settings.get('DEFAULT', 'smart') != 'none')
    end_donator_time = calendar.timegm(time.gmtime())  # END_DONATOR_TIME
    
    # Export to legacy XML
    legacy = serializers.export_to_legacy_schema(
        device, status, beg_donator_time, end_donator_time
    )
    serializers.dict_to_xml(legacy, "/tmp/equip.xml")
    print("END OF EXECUTION!!! look at /tmp/equip.xml")


if __name__ == "__main__":
    sys.exit(main(sys.argv))
