#!/usr/bin/env python
import calendar
try:
    import ConfigParser as configparser  # Python2
except ImportError:
    import configparser
import datetime
import os
import socket
import sys
import time

from . import serializers
from .benchmark import hard_disk_smart
from .inventory import Computer


def load_config():
    # https://docs.python.org/3.4/library/configparser.html
    path = os.path.dirname(__file__)
    config_file = os.path.join(path, 'config.ini')
    assert os.path.exists(config_file), config_file

    config = configparser.ConfigParser()
    config.read(config_file)  # donator.cfg merged here
    
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
    # legacy (only backwards compatibility)
    if run_smart:
        result = hard_disk_smart()  # TODO select proper HD!
        smart = {
            "check": "Yes",
            "device_check": result['device'],
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



def main(load_data=False):
    if not os.geteuid() == 0:
        sys.exit("Only root can run this script")
    
    # FIXME duplicated data initial_donator_time & status.date (dat_state)
    # initial_donator in seconds since 1970 UTC
    # dat_state only date on human friendly format
    beg_donator_time = calendar.timegm(time.gmtime())  # INITIAL_DONATOR_TIME
    config = load_config()
    device = Computer(load_data=load_data)  # XXX pass device type and other user input?
    status = get_device_status(run_smart=config.getboolean('DEFAULT', 'DISC'))
    end_donator_time = calendar.timegm(time.gmtime())  # END_DONATOR_TIME
    
    # Export to legacy XML
    legacy = serializers.export_to_legacy_schema(
        device, status, beg_donator_time, end_donator_time
    )
    serializers.dict_to_xml(legacy, "/tmp/equip.xml")
    print("END OF EXECUTION!!! look at /tmp/equip.xml")


if __name__ == "__main__":
    sys.exit(main())
