import json
import os
import uuid
from distutils.version import StrictVersion
from multiprocessing import Process
from pathlib import Path
from subprocess import CalledProcessError

import pkg_resources
import urllib3
from boltons import urlutils
from colorama import Fore, init
from ereuse_utils import cmd
from ereuse_utils.session import DevicehubClient

from ereuse_workbench.erase import EraseType
from ereuse_workbench.snapshot import Snapshot, SnapshotSoftware
from ereuse_workbench.test import TestDataStorageLength
from ereuse_workbench.usb_sneaky import USBSneaky


class Workbench:
    """Create a hardware report of your computer with components,
    serial numbers, testing, benchmarking, erasing, and installing
    an OS.

    By default Workbench only generates a report of the hardware
    characteristics of the computer, so it is safe to use.
    Parametrize it to make workbench perform tests, benchmarks...
    generating a bigger report including the results of those actions.

    You must run this software as root / sudo.
    """

    def __init__(self,
                 benchmark: bool = False,
                 smart: TestDataStorageLength = False,
                 erase: EraseType = False,
                 erase_steps: int = 1,
                 erase_leading_zeros: bool = False,
                 stress: int = 0,
                 install: str = False,
                 server: urlutils.URL = None,
                 json: Path = None):
        """
        Configures this Workbench.

        :param benchmark: Whether to execute all benchmarks.
        :param smart: Should we perform a SMART test to the hard-drives?
                      If so, pass :attr:`.Workbench.Smart.short` for a
                      short test and :attr:`.Workbench.Smart.long` for a
                      long test. Falsy values disables the
                      functionality.
        :param erase: Should we erase the hard-drives? Pass-in a
                      :attr:`.Workbench.Erase.normal` to perform
                      a normal erasure (quite secure) or
                      :attr:`.Workbench.Erase.sectors` to perform
                      a slower but fully secured erasure. Falsy values
                      disables the functionality.
                      See `a detailed explanation of the erasure
                      process in the FAQ
                      <https://ereuse-org.gitbooks.io/faq/content/w-
                      hich-is-the-data-wiping-process-performed.html>`_.
        :param erase_steps: In case `erase` is truthy, how many steps
                            overriding data should we perform? Policies
                            and regulations may set a specific value.
        :param erase_leading_zeros: In case `erase` is truthy,
                                    should we finish erasing with an
                                    extra step that writes zeroes?
                                    This can be enforced
                                    by policy and regulation.
        :param stress: How many minutes should stress the machine.
                       0 minutes disables this test. A stress test
                       puts the machine at 100% (CPU, RAM and HDD)
                       to ensure components can handle heavy work.
        :param install: Image name to install. A falsy value will
                        disable installation. The image is a FSA file
                        that will be installed on the first hard-drive.
                        Do not add the extension ('.fsa').
        :param server: An URL pointing to a WorkbenchServer. Setting a
                       truthy value will turn-on server functionality
                       like USBSneaky module, sending snapshots to
                       server and getting configuration from it.
        :param json: Save a JSON in path.
        """
        if os.geteuid() != 0:
            raise EnvironmentError('Execute Workbench as root.')

        init(autoreset=True)
        self.benchmark = benchmark
        self.smart = smart
        self.erase = erase
        self.erase_steps = erase_steps
        self.erase_leading_zeros = erase_leading_zeros
        self.stress = stress
        self.server = server
        self.uuid = uuid.uuid4()
        self.install = install
        self.install_path = Path('/media/workbench-images')
        self.json = json

        if self.server:
            # Override the parameters from the configuration from the server
            self.session = DevicehubClient(self.server)
            self.session.verify = False
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            self.config_from_server()
            if self.install:
                # We get the OS to install from the server through a mounted samba
                self.mount_images(self.server.host)
            # By setting daemon=True USB Sneaky will die when we die
            self.usb_sneaky = Process(target=USBSneaky, args=(self.uuid, server), daemon=True)

        # Devicehub and workbench-server will need this
        self.expected_events = []
        self._expected_events_iter = iter(self.expected_events)
        if self.benchmark:
            self.expected_events.append('Benchmark')
        if self.smart:
            self.expected_events.append('TestDataStorage')
        if self.stress:
            self.expected_events.append('StressTest')
        if self.erase:
            self.expected_events.append('EraseBasic')
        if self.install:
            self.expected_events.append('Install')

    @property
    def smart(self):
        return self._smart

    @smart.setter
    def smart(self, value):
        self._smart = TestDataStorageLength(value) if value else None

    @property
    def erase(self):
        return self._erase

    @erase.setter
    def erase(self, value):
        self._erase = EraseType(value) if value else None

    def config_from_server(self):
        """Configures the Workbench from a config endpoint in the server."""
        # todo test this ensuring values from json are well set
        config, _ = self.session.get('/config/')
        for key, value in config.items():
            setattr(self, key, value)

    def mount_images(self, ip: str):
        """Mounts the folder where the OS images are."""
        self.install_path.mkdir(parents=True, exist_ok=True)
        try:
            cmd.run('mount',
                    '-t', 'cifs',
                    '-o', 'guest,uid=root,forceuid,gid=root,forcegid',
                    '//{}/workbench-images'.format(ip),
                    self.install_path)
        except CalledProcessError as e:
            raise CannotMount('Did you umount?') from e

    def run(self) -> Snapshot:
        """
        Executes Workbench on this computer and
        returns a valid JSON for Devicehub.
        """

        print('{}eReuse.org Workbench {!s}.'.format(Fore.CYAN, self.version))
        if self.server:
            print('{}Connected to Workbench Server.'.format(Fore.CYAN))
        print('{}Performing {}:'.format(Fore.CYAN, ', '.join(self.expected_events)))
        try:
            snapshot = self._run()
        except Exception:
            print('{}Workbench panic - unexpected exception found. Please take '
                  'a photo of the screen and send it to eReuse Workbench Developers.'
                  .format(Fore.RED))
            raise
        finally:
            if self.server and self.install:
                # Un-mount images
                try:
                    cmd.run('umount', self.install_path)
                except CalledProcessError as e:
                    raise CannotMount() from e
        print('{}Workbench has finished properly \u2665'.format(Fore.GREEN))
        return snapshot

    def _run(self) -> Snapshot:
        if self.server:
            self.usb_sneaky.start()

        snapshot = Snapshot(self.uuid,
                            self.expected_events,
                            SnapshotSoftware.Workbench,
                            self.version)
        snapshot.computer()
        self.after_phase(snapshot, is_info_phase=True)

        if self.benchmark:
            snapshot.benchmarks()
            self.after_phase(snapshot)

        if self.smart:
            snapshot.test_smart(self.smart)
            self.after_phase(snapshot)

        if self.stress:
            snapshot.test_stress(self.stress)
            self.after_phase(snapshot)

        if self.erase:
            snapshot.erase(self.erase, self.erase_steps, self.erase_leading_zeros)
            self.after_phase(snapshot)

        if self.install:
            snapshot.install(self.install_path.joinpath(self.install))
            self.after_phase(snapshot)

        return snapshot

    def after_phase(self, snapshot: Snapshot, is_info_phase=False):
        actual = next(self._expected_events_iter) if not is_info_phase else None
        snapshot.close_if_needed(actual)
        if self.json:
            with self.json.open('w') as f:
                f.write(snapshot.to_json())
        if self.server:  # Send to workbench-server
            # todo to json and then back to dict and finally back to json...
            data = snapshot.to_json()
            data = json.loads(data)
            data['_phase'] = actual
            self.session.patch('/snapshots/', data, uri=snapshot.uuid, status=204)

    @property
    def version(self) -> StrictVersion:
        """
        The version of Workbench
        from https://stackoverflow.com/a/2073599
        This throws an exception if you git clone this package
        and did not install it with pip
        Perform ``pip install -e .`` or similar to fix
        """
        return StrictVersion(pkg_resources.require('ereuse-workbench')[0].version)


class CannotMount(Exception):
    pass
