import json
import os
import uuid
from datetime import datetime
from multiprocessing import Process
from pathlib import Path
from subprocess import CalledProcessError, PIPE, Popen, check_call
from typing import Type
from urllib.parse import urlparse

import urllib3
from colorama import Fore, init
from ereuse_utils import DeviceHubJSONEncoder, now
from requests_toolbelt.sessions import BaseUrlSession

from ereuse_workbench.benchmarker import Benchmarker
from ereuse_workbench.computer import Computer, PrivateFields
from ereuse_workbench.eraser import EraseType, Eraser
from ereuse_workbench.tester import Smart, Tester
from ereuse_workbench.usb_sneaky import USBSneaky


class Workbench:
    """
    Create a full report of your computer with serials,
    testing, benchmarking, erasing and installing an OS.
    """

    def __init__(self, smart: Smart = False, erase: EraseType = False, erase_steps: int = 1,
                 erase_leading_zeros: bool = False, stress: int = 0,
                 install: str = False, server: str = None, tester: Type[Tester] = Tester,
                 computer: Type[Computer] = Computer, eraser: Type[Eraser] = Eraser,
                 benchmarker: Type[Benchmarker] = Benchmarker,
                 usb_sneaky: Type[USBSneaky] = USBSneaky):
        """
        Configures this Workbench.

        :param smart: Should we perform a SMART test to the hard-drives?
                      If so, pass :attr:`.Workbench.Smart.short` for a
                      short test and :attr:`.Workbench.Smart.long` for a
                      long test.
        :param erase: Should we erase the hard-drives? If so, pass the
                      :attr:`.Workbench.Erase.normal` way, which is
                      faster but it can't guarantee at 100% full
                      erasure, or :attr:`.Workbench.Erase.sectors` way,
                      which is slower but with 100% guarantee.
        :param erase_steps: In case `erase` is truthy, how many steps
                            overriding data should we perform? Policies
                            and regulations may set= a specific value.
                            Normal 'secure' value is `3`.
        :param erase_leading_zeros: In case `erase` is truthy,
                                    should we finish erasing with an
                                    extra step that
                                    writes zeroes? This can be enforced
                                    by policy and regulation.
        :param stress: How many minutes should stress the machine.
                       0 minutes disables this test. A stress test
                       puts the machine at 100% (CPU, RAM and HDD)
                       to ensure components can handle heavy work.
        :param install: Image name to install. A falsey value will
                        disable installation. The image is a FSA file
                        that will be installed on the first hard-drive.
                        Do not add the extension ('.fsa').
        :param server: An URL pointing to a WorkbenchServer. Setting a
                       truthy value will turn-on server functionality
                       like USBSneaky module, sending snapshots to
                       server and getting configuration from it.
        :param tester: Testing class to use to perform tests.
        :param computer: Computer class to use to retrieve computer
                         information.
        """
        if os.geteuid() != 0:
            raise EnvironmentError('Execute Workbench as root.')

        init(autoreset=True)
        self.smart = smart
        self.erase = erase
        self.erase_steps = erase_steps
        self.erase_leading_zeros = erase_leading_zeros
        self.stress = stress
        self.install = install
        self.server = server
        self.uuid = uuid.uuid4()
        self.install_path = Path('/media/workbench-images')

        if self.server:
            # Override the parameters from the configuration from the server
            self.session = BaseUrlSession(base_url=self.server)
            self.session.verify = False
            self.session.headers.update({'Content-Type': 'application/json'})
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            self.config_from_server()
            if self.install:
                # We get the OS to install from the server through a mounted samba
                self.mount_images(self.server)
            self.usb_sneaky = Process(target=usb_sneaky, args=(self.uuid, server))

        self.phases = 1 + bool(self.smart) + bool(self.stress) + bool(self.erase) + \
                      bool(self.install)
        """The number of phases we will be performing."""

        self.tester = tester()
        self.eraser = eraser(self.erase, self.erase_steps, self.erase_leading_zeros)
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

    def mount_images(self, server: str):
        """Mounts the folder where the OS images are."""
        self.install_path.mkdir(parents=True, exist_ok=True)
        ip, _ = urlparse(server).netloc.split(':')
        c = 'mount -t cifs -o guest,uid=root,forceuid,gid=root,forcegid "//{}/workbench-images" {}'
        c = c.format(ip, self.install_path)
        p = Popen(c, stdout=PIPE, stderr=PIPE, shell=True, universal_newlines=True)
        _, stderr = p.communicate()
        if stderr:
            raise CannotMount(stderr + '\nYou might need to "umount {}"'.format(self.install_path))

    def unmount_images(self):
        _, stderr = Popen('umount {}'.format(self.install_path), shell=True).communicate()
        if stderr:
            raise CannotMount(stderr.decode())

    def run(self) -> str:
        """Executes Workbench on this computer and returns a valid JSON for DeviceHub."""
        print('{}Starting eReuse.org Workbench'.format(Fore.CYAN))
        if self.server:
            self.usb_sneaky.start()

        print('{} Getting computer information...'.format(self._print_phase(1)))
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
            'date': now(),  # todo ensure we try to update local time through Internet
            '@type': 'devices:Snapshot'
        }
        self.after_phase(snapshot, init_time)

        if self.smart:
            print('{} Run SMART test and benchmark hard-drives...'.format(self._print_phase(2)))
            for hdd in filter(lambda x: x['@type'] == 'HardDrive', components):
                hdd['test'] = self.tester.smart(hdd[PrivateFields.logical_name], self.smart)
                if hdd['test']['error']:
                    print('{}Failed SMART for HDD {}'.format(Fore.RED, hdd.get('serialNumber')))
            self.after_phase(snapshot, init_time)

        if self.stress:
            print('{} Run stress tests for {} mins...'.format(self._print_phase(3), self.stress))
            snapshot['tests'] = [self.tester.stress(self.stress)]
            self.after_phase(snapshot, init_time)

        if self.erase:
            text = '{} Erase Hard-Drives with {} method, {} steps and {} overriding with zeros...'
            print(text.format(self._print_phase(4), self.erase.name, self.erase_steps,
                              '' if self.erase_leading_zeros else 'not'))
            for hdd in filter(lambda x: x['@type'] == 'HardDrive', components):
                hdd['erasure'] = self.eraser.erase(hdd[PrivateFields.logical_name])
                if not hdd['erasure']['success']:
                    print('{}Failed erasing HDD {}'.format(Fore.RED, hdd.get('serialNumber')))
            self.after_phase(snapshot, init_time)
            if self.server:
                self.send_to_server(snapshot)

        if self.install:
            print('{} Install {}...'.format(self._print_phase(5), self.install))
            snapshot['osInstallation'] = self.install_os()
            self.after_phase(snapshot, init_time)
            self.unmount_images()

        print('{}eReuse.org Workbench has finished properly.'.format(Fore.GREEN))

        # Comply with DeviceHub's Snapshot
        snapshot.pop('_phases', None)
        snapshot.pop('_totalPhases', None)
        return json.dumps(snapshot, skipkeys=True, cls=DeviceHubJSONEncoder, indent=2)

    def install_os(self) -> dict:
        # Customizations are passed as environment variables.
        env = os.environ.copy()
        env['IMAGE_NAME'] = self.install
        env['CONFIRM'] = 'no'
        env['LOCAL_MP'] = str(self.install_path)
        env['IMAGE_DIR'] = '.'
        env['REMOTE_TYPE'] = 'local'
        env['HD_SWAP'] = 'AUTO'
        env['HD_ROOT'] = 'FILL'

        init_time = now()
        try:
            check_call(['erwb-install-image'], env=env)
            success = True
        except CalledProcessError:
            # todo erwb-install-image never returns 1 so
            # this never executes
            success = False
        return {
            'elapsed': now() - init_time,
            'label': self.install,
            'success': success
        }

    def after_phase(self, snapshot: dict, init_time: datetime):
        snapshot['_phases'] += 1
        snapshot['elapsed'] = now() - init_time
        if self.server:
            self.send_to_server(snapshot)

    def send_to_server(self, snapshot: dict):
        url = '/snapshots/{}'.format(snapshot['_uuid'])
        r = self.session.patch(url,
                               data=json.dumps(snapshot, cls=DeviceHubJSONEncoder, skipkeys=True))
        r.raise_for_status()

    def _print_phase(self, phase: int):
        return '[ {}Phase {}{} ]'.format(Fore.CYAN, phase, Fore.RESET)


class CannotMount(Exception):
    pass
