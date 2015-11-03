#!/usr/bin/env python3
import calendar
import configparser
import datetime
import os
import socket
import sys
import time

from .benchmark import hard_disk_smart


def load_config():
    # https://docs.python.org/3.4/library/configparser.html
    config = configparser.ConfigParser()
    config.read('config.ini')  # donator.cfg merged here
    
    #print(config['DEFAULT']['DISC'])
    print(config['DEFAULT'].getboolean('DISC'))
    print(config['donator']['email'])
    
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


def get_device_status():
    # TODO anything else??
    return {
        'date': datetime.datetime.now(),
        'online': is_connected(),
    }



if __name__ == "__main__":
    if not os.geteuid() == 0:
        sys.exit("Only root can run this script")
    
    # FIXME duplicated data initial_donator_time & status.date (dat_state)
    # initial_donator in seconds since 1970 UTC
    # dat_state only date on human friendly format
    beg_donator_time = calendar.timegm(time.gmtime())  # INITIAL_DONATOR_TIME
    config = load_config()
    inventory = Inventory()  # XXX pass device type and other user input?
    device_status = get_device_status()
##    hard_disk_smart()
    end_donator_time = calendar.timegm(time.gmtime())  # END_DONATOR_TIME
