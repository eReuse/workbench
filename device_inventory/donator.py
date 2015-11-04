#!/usr/bin/env python3
import calendar
import configparser
import datetime
import os
import socket
import sys
import time

from .benchmark import hard_disk_smart
from .inventory import Inventory
from .serializers import dict_to_xml


def load_config():
    # https://docs.python.org/3.4/library/configparser.html
    basepath = os.path.dirname(sys.argv[0])
    config = configparser.ConfigParser()
    config.read(os.path.join(basepath, 'config.ini'))  # donator.cfg merged here
    
    #print(config['DEFAULT']['DISC'])
    #print(config['DEFAULT'].getboolean('DISC'))
    #print(config['donator']['email'])
    
    # TODO set fallback values if config is empty
    # https://docs.python.org/3.4/library/configparser.html#fallback-values
    
    return config


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
    # TODO anything else??
    smart = {"check": "Yes" if run_smart else "No"}
    smart.update(hard_disk_smart())  # TODO select proper HD!
    
    return {
        "dat_estat": datetime.date.today().isoformat(),
        "version": "1.0",
        "online": "SI" if is_connected() else "NO",
        "smartest": smart,
    }



if __name__ == "__main__":
    if not os.geteuid() == 0:
        sys.exit("Only root can run this script")
    
    # FIXME duplicated data initial_donator_time & status.date (dat_state)
    # initial_donator in seconds since 1970 UTC
    # dat_state only date on human friendly format
    beg_donator_time = calendar.timegm(time.gmtime())  # INITIAL_DONATOR_TIME
    config = load_config()
    device = Inventory()  # XXX pass device type and other user input?
    device_status = get_device_status(run_smart=config['DEFAULT'].getboolean('DISC'))
##    hard_disk_smart()
    end_donator_time = calendar.timegm(time.gmtime())  # END_DONATOR_TIME
    
    equip = {
        "equip": {
            "id": device.ID,
            "id2": device.ID2,
            "ID_donant": "",
            "ID_2": "",
            "LABEL": "",
            "INITIAL_TIME": "0",
            "INITIAL_DONATOR_TIME": beg_donator_time,
            "comments": "some comment",
            "type": "1",
            "serials": {
                "serial_fab": "XXX",
                "serial_mot": "XXX",
                "serial_cpu": "XXX",
                "serial_ram": "XXX",
                "serial_hdd": "XXX",
            },
            "estat": device_status,
            "caracteristiques": {
                "cpu": device.cpu,
                "ram": device.ram,
                # TODO
            },
            "END_DONATOR_TIME": end_donator_time,
        }
    }
    
    dict_to_xml(equip)
    print("END OF EXECUTION!!! look at /tmp/equip.xml")
