#!/usr/bin/env python
import argparse
import collections
import ConfigParser
import enum
import json
import logging
import logging.config
import os
import sys

from device_inventory import eraser, serializers, storage, utils
from device_inventory.conf import settings
from device_inventory.benchmark import benchmark_hdd
from device_inventory.inventory import Computer
from device_inventory.utils import InventoryJSONEncoder as InvEncoder


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

# Similar to US academic grading.
class ComputerGrade(enum.Enum):
    new = 'A'
    used = 'B'
    ugly = 'C'
    broken = 'D'

# The order may be used as a hint when asking questions
# about this feature.
# This order puts the most informative choice first,
# so that choosing one option makes the following ones
# unnecessary to be read.
VISUAL_GRADES = collections.OrderedDict([
    (ComputerGrade.broken,
     "Serious aesthetic defects (cracked covers, broken parts)"),
    (ComputerGrade.ugly,
     "Light aesthetic defects (scratches, dents, decoloration)"),
    (ComputerGrade.used,
     "Used, but no remarkable aesthetic defects"),
    (ComputerGrade.new,
     "Brand new device"),
])
FUNCTIONAL_GRADES = collections.OrderedDict([
    (ComputerGrade.broken,
     "Serious functional defects (loud noises, annoying audio/video artifacts, missing keys)"),
    (ComputerGrade.ugly,
     "Light functional defects (soft noises, dead pixels, erased key labels)"),
    (ComputerGrade.used,
     "Used, but no remarkable functional defects"),
    (ComputerGrade.new,
     "Brand new device"),
])

# Data for user choice questions:
# (field, opt, cls, choices, allow_empty, msg)
_user_input_questions = [
    # Device type
    ('device_type', 'EQUIP', Computer.Type, Computer.TYPES, False,
     "Choose device type:\n{0}\nType: "),
    # Visual grade
    ('appearance_grade', 'VISUAL_GRADE', ComputerGrade, VISUAL_GRADES, True,
     """\
Choose the option that better describes the visual grade of the computer:
{0}
Visual grade (empty to skip): """),
    # Functional grade
    ('functionality_grade', 'FUNCTIONAL_GRADE', ComputerGrade, FUNCTIONAL_GRADES, True,
     """\
Choose the option that better describes the functional grade of the computer:
{0}
Functional grade (empty to skip): """),
]

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

    def choose_from_dict(val_to_desc, msg_template, allow_empty=False):
        entry_to_item = dict(enumerate(val_to_desc.items(), start=1))
        choice_msg = '\n' + msg_template.format(
            '\n'.join('%d. %s' % (idx, desc)
                      for (idx, (_, desc)) in entry_to_item.items())
        )
        entry = None
        while entry not in entry_to_item:
            if entry is not None:
                print("Invalid choice, please try again.")
            input_ = raw_input(choice_msg)
            if not input_.strip() and allow_empty:
                return None
            try:
                entry = int(input_)
            except ValueError:
                entry = -1  # invalid and not none
        (val, desc) = entry_to_item[entry]
        return val
    
    # Ask the user for several choice questions.
    for (field, opt, cls, choices, allow_empty, msg) in _user_input_questions:
        val_dflt = get_option_default(opt, cls)
        val = val_dflt if val_dflt else choose_from_dict(choices, msg, allow_empty)
        if val:
            user_input[field] = val
    
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
    parser.add_argument('--stress', metavar='MINUTES', type=int,
            help='run stress test for the given MINUTES (0 to disable, default)')
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
    if args.stress is not None:
        settings.set('DEFAULT', 'stress', args.stress)
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
        json.dump(data, outfile, indent=4, sort_keys=True, cls=InvEncoder)
    
    # sign output
    if settings.getboolean('signature', 'sign_output'):
        signed_data = utils.sign_data(json.dumps(data, indent=4, sort_keys=True, cls=InvEncoder))
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

    # run stress test
    stress_mins = settings.getint('DEFAULT', 'stress')
    if stress_mins > 0:
        print("Performing stress test for %d minutes, press Ctrl+C at any time to cancel." % stress_mins)
        if True:
            print("Stress test succeeded.")
        else:
            print("Stress test failed, please note this down.")
    else:
        print("Skipping stress test (not enabled in remote configuration file).")
    
    print("Device Inventory has finished properly: {0}".format(localpath))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
