#!/usr/bin/env python
import argparse
import ConfigParser
import json
import logging
import logging.config
import os
import sys

from device_inventory import eraser, serializers, storage, utils
from device_inventory.conf import settings
from device_inventory.benchmark import benchmark_hdd
from device_inventory.inventory import Computer


def setup_logging(default_path='config_logging.json',
                  default_level=logging.ERROR, env_key='CFG_LOG'):
    """
    Setup logging configuration

    """
    path = os.path.join(os.path.dirname(__file__), default_path)
    value = os.getenv(env_key, None)
    if value:
        path = value
    if os.path.exists(path):
        with open(path, 'rt') as f:
            config = json.load(f)
        logging.config.dictConfig(config)
    else:
        logging.basicConfig(level=default_level)


def get_user_input():
    user_input = {}
    for field in ['label', 'comment', 'pid', '_id']:
        if settings.getboolean('DEFAULT', field):
            value = raw_input("%s: " % field).strip()
            if value:
                user_input[field] = value

    def get_option_default(opt_name, opt_class):
        try:
            default_opt = settings.get('DEFAULT', opt_name)
            default_val = opt_class(default_opt)
        except (ConfigParser.NoOptionError, ValueError):
            default_val = None
        return default_val

    def choose_from_dict(val_to_desc, msg_template):
        entry_to_item = dict(enumerate(val_to_desc.items(), start=1))
        choice_msg = '\n' + msg_template.format(
            '\n'.join('%d. %s' % (idx, desc)
                      for (idx, (_, desc)) in entry_to_item.items())
        )
        entry = None
        while entry not in entry_to_item:
            if entry is not None:
                print("Invalid choice, please try again.")
            try:
                entry = int(raw_input(choice_msg))
            except ValueError:
                entry = -1  # invalid and not none
        (val, desc) = entry_to_item[entry]
        print("Choice: {0}".format(desc))
        return val
    
    # Ask user for choosing the Device.type
    type_dflt = get_option_default('EQUIP', Computer.Type)
    user_input['device_type'] = type_dflt if type_dflt else choose_from_dict(
        Computer.TYPES, "Choose device type:\n{0}\nType: ")
    # Ask user for the device condition.
    cond_dflt = get_option_default('CONDITION', Computer.Condition)
    user_input['condition'] = cond_dflt if cond_dflt else choose_from_dict(
        Computer.CONDITIONS, "Choose device condition:\n{0}\nCondition: ")
    
    return user_input


def main(argv=None):
    if not os.geteuid() == 0:
        sys.exit("Only root can run this script")
    
    # configure logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
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
    
    # sign output
    if settings.getboolean('signature', 'sign_output'):
        signed_data = utils.sign_data(json.dumps(data, indent=4, sort_keys=True))
        filename = "{0}.json.asc".format(device.verbose_name)
        localpath = os.path.join("/tmp", filename)
        with open(localpath, "w") as outfile:
            outfile.write(signed_data)
    
    # send files to the PXE Server
    if settings.getboolean('DEFAULT', 'sendtoserver'):
        remotepath = os.path.join(settings.get('server', 'remotepath'), filename)
        username = settings.get('server', 'username')
        password = settings.get('server', 'password')
        server = settings.get('server', 'address')
        try:
            storage.copy_file_to_server(localpath, remotepath, username, password, server)
            print("The file `{0}` has been successfully sent to the server.".format(localpath))
        except Exception as e:
            logger.error("Error copying file '%s' to server '%s'", localpath, server)
            logger.debug(e, exc_info=True)
    
    # copy file to an USB drive
    if settings.getboolean('DEFAULT', 'copy_to_usb'):
        try:
            storage.copy_file_to_usb(localpath)
        except KeyboardInterrupt:
            print("Copy to USB cancelled by user!")
        except Exception as e:
            logger.error("Error copying file '%s' to USB", localpath)
            logger.debug(e, exc_info=True)
    
    print("Device Inventory has finished properly: {0}".format(localpath))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
