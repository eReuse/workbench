import json
import subprocess
import uuid
from contextlib import redirect_stdout
from datetime import datetime
from inspect import getdoc
from multiprocessing import Process
from typing import Type

import os
import urllib3
from ereuse_utils import DeviceHubJSONEncoder, now
from io import StringIO
from os import path
from requests_toolbelt.sessions import BaseUrlSession

from ereuse_workbench.benchmarker import Benchmarker
from ereuse_workbench.computer import Computer, PrivateFields
from ereuse_workbench.eraser import EraseType, Eraser
from ereuse_workbench.tester import Smart, Tester
from ereuse_workbench.usb_sneaky import USBSneaky


class Workbench:
    """
    Create a full report of your computer with serials, testing, benchmarking, erasing and installing an OS.
    """

    def __init__(self, smart: Smart = False, erase: EraseType = False, erase_steps: int = 1,
                 erase_leading_zeros: bool = False, stress: int = 0,
                 install: str = False, install_path: str = False, server: str = None,
                 tester: Type[Tester] = Tester, computer: Type[Computer] = Computer,
                 eraser: Type[Eraser] = Eraser, benchmarker: Type[Benchmarker] = Benchmarker,
                 usb_sneaky: Type[USBSneaky] = USBSneaky):
        """
        Configures this Workbench.

        :param smart: Should we perform a SMART test to the hard-drives? If so, pass :attr:`.Workbench.Smart.short` for
                      a short test and :attr:`.Workbench.Smart.long` for a long test.
        :param erase: Should we erase the hard-drives? If so, pass the :attr:`.Workbench.Erase.normal` way, which is
                      faster but it can't guarantee at 100% full erasure, or :attr:`.Workbench.Erase.sectors` way,
                      which is slower but with 100% guarantee.
        :param erase_steps: In case `erase` is truthy, how many steps overriding data should we perform? Policies
                            and regulations may set= a specific value. Normal 'secure' value is `3`.
        :param erase_leading_zeros: In case `erase` is truthy, should we finish erasing with an extra step that
                                    writes zeroes? This can be enforced by policy and regulation.
        :param stress: How many minutes should stress the machine. 0 minutes disables this test. A stress test
                       puts the machine at 100% (CPU, RAM and HDD) to ensure components can handle heavy work.
        :param install: Image name to install. A falsey value will disable installation. The image is a FSA file
                        that will be installed on the first hard-drive. Do not add the extension ('.fsa').
        :param install_path: The path to the folder where the image to install is.
        :param server: An URL pointing to a WorkbenchServer. Setting a truthy value will turn-on server functionality
                       like USBSneaky module, sending snapshots to server and getting configuration from it.
        :param tester: Testing class to use to perform tests.
        :param computer: Computer class to use to retrieve computer information.
        """
        if os.geteuid() != 0:
            raise EnvironmentError('Execute Workbench as root.')

        self.smart = smart
        self.erase = erase
        self.erase_steps = erase_steps
        self.erase_leading_zeros = erase_leading_zeros
        self.stress = stress
        self.install = install
        self.install_path = install_path
        self.server = server
        self.uuid = uuid.uuid4()

        if self.server:
            # Override the parameters from the configuration from the server
            self.session = BaseUrlSession(base_url=self.server)
            self.session.verify = False
            self.session.headers.update({'Content-Type': 'application/json'})
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            self.config_from_server()
            self.usb_sneaky = Process(target=usb_sneaky, args=(self.uuid, server))

        self.phases = 1 + bool(self.smart) + bool(self.stress) + bool(self.erase) + bool(self.install)
        """The number of phases we will be performing."""

        self.tester = tester()
        self.eraser = eraser(erase, erase_steps, erase_leading_zeros)
        self.benchmarker = benchmarker()
        self.Computer = computer

    def config_from_server(self):
        """Configures the Workbench from a config endpoint in the server."""
        r = self.session.get('/config')
        r.raise_for_status()
        for key, value in r.json().items():
            if key == 'smart' and value:
                self.smart = Smart(value)
            elif key == 'erase' and value:
                self.erase = EraseType(value)
            else:
                setattr(self, key, value)

    def run(self) -> str:
        """Executes Workbench on this computer and returns a valid JSON for DeviceHub."""
        if self.server:
            self.usb_sneaky.start()

        print('Phase 0: Getting computer information...')
        init_time = now()
        computer, components = self.Computer(self.benchmarker).run()
        snapshot = {
            'device': computer,
            'components': components,
            '_uuid': self.uuid,
            '_totalPhases': self.phases,
            '_phases': 0,  # Counter of phases we have executed
            'snapshotSoftware': 'Workbench',
            'inventory': {
                'elapsed': now() - init_time
            },
            'date': now(),  # todo ensure we try to update local time through Internet if we are on a live-cd
            '@type': 'devices:Snapshot'
        }
        self.after_phase(snapshot, init_time)

        if self.smart:
            print('Phase 1: Running SMART test and benchmarking on hard-drives...')
            for hdd in filter(lambda x: x['@type'] == 'HardDrive', components):
                hdd['test'] = self.tester.smart(hdd[PrivateFields.logical_name], self.smart)
            self.after_phase(snapshot, init_time)

        if self.stress:
            print('Phase 2: Running stress tests for {} minutes...'.format(self.stress))
            snapshot['tests'] = [self.tester.stress(self.stress)]
            self.after_phase(snapshot, init_time)

        if self.erase:
            text = 'Phase 3: Erase Hard-Drives with {} method, {} steps and {} overriding with zeros...'
            print(text.format(self.erase.name, self.erase_steps, '' if self.erase_leading_zeros else 'not'))
            for hdd in filter(lambda x: x['@type'] == 'HardDrive', components):
                hdd['erasure'] = self.eraser.erase(hdd[PrivateFields.logical_name])
            self.after_phase(snapshot, init_time)
            if self.server:
                self.send_to_server(snapshot)

        if self.install:
            print('Phase 4: Installing {}...'.format(self.install))
            snapshot['osInstallation'] = self.install_os()
            self.after_phase(snapshot, init_time)

        print('eReuse.org Workbench has finished properly.')

        # Comply with DeviceHub's Snapshot
        snapshot.pop('_phases', None)
        snapshot.pop('_totalPhases', None)
        return json.dumps(snapshot, skipkeys=True, cls=DeviceHubJSONEncoder, indent=2)

    def install_os(self) -> dict:
        # Customizations are passed as environment variables.
        env = os.environ.copy()
        env['IMAGE_NAME'] = self.install
        env['CONFIRM'] = 'no'
        env['LOCAL_MP'] = path.dirname(self.install_path)
        env['IMAGE_DIR'] = self.install_path
        env['REMOTE_TYPE'] = 'local'
        env['HD_SWAP'] = 'AUTO'
        env['HD_ROOT'] = 'FILL'

        init_time = datetime.utcnow()
        subprocess.check_call(['erwb-install-image'], env=env)
        return {
            'elapsed': datetime.utcnow() - init_time,
            'label': self.install,
            'success': True
        }

    def after_phase(self, snapshot: dict, init_time: datetime):
        snapshot['_phases'] += 1
        snapshot['elapsed'] = now() - init_time
        if self.server:
            self.send_to_server(snapshot)

    def send_to_server(self, snapshot: dict):
        url = '/snapshots/{}'.format(snapshot['_uuid'])
        r = self.session.patch(url, data=json.dumps(snapshot, cls=DeviceHubJSONEncoder, skipkeys=True))
        r.raise_for_status()


if __name__ == "__main__":
    import argparse

    desc = getdoc(Workbench)
    epilog = 'Minimum example: erwb \n' \
             'Save a json file and perform some tests: erwb --smart --stress --quiet --print-json > snapshot.json'
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--smart', type=Smart, choices=list(Smart))
    parser.add_argument('-e', '--erase', type=EraseType, choices=list(EraseType))
    parser.add_argument('--erase-steps', type=int, default=1)
    parser.add_argument('--erase-leading-zeros', action='store_true')
    parser.add_argument('-ss', '--stress', metavar='MINUTES', type=int, default=0,
                        help='Run stress test for the given MINUTES (0 to disable, default)')
    parser.add_argument('-i', '--install', type=str,
                        help='The name of the FSA OS to install, without the ".fsa" extension.')
    parser.add_argument('--install-path', type=str, help='The path to the directory where the FSA OS file is.',
                        default='/srv/workbench-images')
    parser.add_argument('-sr', '--server', type=str, help='The URI to a WorkbenchServer.')
    parser.add_argument('-q', '--quiet', action='store_true', help='Do not show messages. Useful with --print-json')
    parser.add_argument('-j', '--print-json', action='store_true', help='Print the JSON on stdout.')
    args = vars(parser.parse_args())
    print_json = args.pop('print_json')
    if args.pop('quiet'):
        with redirect_stdout(StringIO()):
            snapshot = Workbench(**args).run()
    else:
        snapshot = Workbench(**args).run()
    if print_json:
        print(snapshot, flush=True)
