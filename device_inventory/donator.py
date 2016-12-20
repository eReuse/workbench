#!/usr/bin/env python
import argparse
import collections
import ConfigParser
import enum
import json
import logging
import logging.config
import os
import re
import shutil
import subprocess
import sys
import time
import uuid

import tqdm

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
     """\
Choose device type:
{0}
Device type ({1}): """),
    # Visual grade
    ('appearance_grade', 'VISUAL_GRADE', ComputerGrade, VISUAL_GRADES, True,
     """\
Choose the option that better describes the visual grade of the computer:
{0}
Visual grade ({1}): """),
    # Functional grade
    ('functionality_grade', 'FUNCTIONAL_GRADE', ComputerGrade, FUNCTIONAL_GRADES, True,
     """\
Choose the option that better describes the functional grade of the computer:
{0}
Functional grade ({1}): """),
]

def get_user_input():
    user_input = {}

    # Ask the user for assorted identifiers.
    for field in ['label', 'pid', '_id']:
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
                      for (idx, (_, desc)) in entry_to_item.items()),
            ("1-%d, empty to skip" if allow_empty else "1-%d") % len(entry_to_item)
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

    # Let the user provide other information not requested previously.
    # Do this last to save the user from entering info in the comment
    # that is to be asked next.
    if settings.getboolean('DEFAULT', 'comment'):
        value = raw_input("Additional comments (empty to skip): ").strip()
        if value:
            user_input['comment'] = value
    
    return user_input


def stress(minutes):
    """Perform a CPU and memory stress test for the given `minutes`.

    The CPU stress test uses one thread per core, and the RAM stress test one
    thread per core, totalling all main memory available to user processes.

    Return a boolean indicating whether the stress test was successful.
    """
    with open('/proc/cpuinfo') as cpuinfo:
        ncores = len(re.findall(r'^processor\b', cpuinfo.read(), re.M))
    with open('/proc/meminfo') as meminfo:
        match = re.search(r'^MemAvailable:\s*([0-9]+) kB.*', meminfo.read(), re.M)
        mem_kib = int(match.group(1))
    # Exclude a percentage of available memory for the stress processes themselves.
    mem_worker_kib = (mem_kib / ncores) * 90 / 100
    proc = subprocess.Popen([
        "stress",
        "-c", str(ncores),
        "-m", str(ncores),
        "--vm-bytes", "%dK" % mem_worker_kib,
        "-t", "%dm" % minutes],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True)
    for _ in tqdm.trange(minutes * 60):  # update progress bar every second
        time.sleep(1)
    proc.communicate()  # wait for process, consume output
    return proc.returncode == 0

def install(name=None, confirm=True):
    """Install a system image to the local hard disk.

    If a `name` is provided, select that image for installation.

    If `confirm` is true, give the chance to cancel installation before
    proceeding.
    """
    # Customizations are passed as environment variables.
    env = os.environ.copy()

    if name is not None:
        env['IMAGE_NAME'] = name
    env['CONFIRM'] = 'yes' if confirm else 'no'

    env['SERVER'] = settings.get('installer', 'remote_addr')
    env['REMOTE_MP'] = settings.get('installer', 'remote_mp')
    env['IMAGE_DIR'] = settings.get('installer', 'image_dir')

    env['REMOTE_TYPE'] = 'CIFS'
    env['HD_SWAP'] = 'AUTO'
    env['HD_ROOT'] = 'FILL'

    subprocess.check_call(['di-install-image'], env=env)


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
    parser.add_argument('--install', choices=['ask', 'yes', 'no'],
            help='install a system image ("yes" avoids confirmation)')
    parser.add_argument('--image-name', metavar='NAME',
            help='select the system image with the given NAME for installation')
    parser.add_argument('--settings',
            help='file to be loaded as config file')
    parser.add_argument('--inventory',
            help='directory to copy the resulting file to (none to disable, default)')
    args = parser.parse_args()
    
    # load specified config file (if any)
    if args.settings:
        cfg = settings.load_config(config_file=args.settings)
    
    # override settings with command line args
    if args.smart:
        settings.set('DEFAULT', 'smart', args.smart)
    if args.erase:
        settings.set('eraser', 'erase', args.erase)
    if args.stress is not None:
        settings.set('DEFAULT', 'stress', str(args.stress))
    if args.install is not None:
        settings.set('installer', 'install', args.install)
    if args.image_name is not None:
        settings.set('installer', 'image_name', args.image_name)
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
    # Add a temporary, meaningless unique identifier just to avoid uploading
    # the very same file twice (this doesn't cover the case of e.g. running
    # the inventory twice on the same machine with different labels).  See
    # issue #57.
    data['_uuid'] = str(uuid.uuid4())  # random UUID
    
    # TODO save on the home
    def sanitize(comp):  # turn 'Foo Corp. -x-' into 'foo-corp-x'
        rep = '-'  # replacement character
        ret = comp.lower()  # turn to lowecase
        ret = re.sub(r'\W', rep, ret)  # replace non-letters and non-numbers
        ret = re.sub(r'-+', rep, ret)  # squash replacement char runs
        ret = ret.strip(rep)  # remove replacement char at the ends
        return ret
    # Turn (Foo Corp., MyComputer +50, L42) into 'foo-corp,mycomputer-50,l42'.
    filebase = ','.join(sanitize(c) for c in [
        data['device'].get('manufacturer', 'unknown'),
        data['device'].get('model', 'unknown'),
        (data.get('label') or device.verbose_name)
    ])
    filename = "{0}.json".format(filebase)  # get_option
    localpath = os.path.join("/tmp", filename)
    with open(localpath, "w") as outfile:
        json.dump(data, outfile, indent=4, sort_keys=True, cls=InvEncoder)
    
    # sign output
    if settings.getboolean('signature', 'sign_output'):
        signed_data = utils.sign_data(json.dumps(data, indent=4, sort_keys=True, cls=InvEncoder))
        filename = "{0}.json.asc".format(filebase)
        localpath = os.path.join("/tmp", filename)
        with open(localpath, "w") as outfile:
            outfile.write(signed_data)
    
    # copy files to the inventory directory
    if args.inventory:
        try:
            shutil.copy(localpath, args.inventory)
        except IOError as ioe:
            logger.error("Error copying file '%s' to inventory '%s'", localpath, args.inventory)
            logger.debug(ioe, exc_info=True)
    
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
        try:
            if stress(stress_mins):
                print("Stress test succeeded.")
            else:
                print("Stress test failed, please note this down.")
        except KeyboardInterrupt:
            print("Stress test cancelled by user!")
        except Exception as e:
            logger.error("Error running stress test")
            logger.debug(e, exc_info=True)
    else:
        print("Skipping stress test (not enabled in remote configuration file).")

    # install system image
    install_image = settings.get('installer', 'install')
    if install_image in ('yes', 'ask'):
        image_name = settings.get('installer', 'image_name')
        print("Starting installation of system image.")
        try:
            install(name=image_name, confirm=(install_image == 'ask'))
        except KeyboardInterrupt:
            print("System installation cancelled by user!")
        except Exception as e:
            logger.error("Error installing system image")
            logger.debug(e, exc_info=True)
    else:
        print("Skipping installation (not enabled in remote configuration file).")
    
    print("Device Inventory has finished properly: {0}".format(localpath))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
