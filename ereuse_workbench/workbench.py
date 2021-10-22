import logging
import os
import uuid
from contextlib import suppress
from datetime import datetime
from distutils.version import StrictVersion
from multiprocessing import Process
from pathlib import Path
from subprocess import CalledProcessError

import ereuse_utils
from boltons import urlutils
from colorama import Fore, init
from ereuse_utils import cmd
from ereuse_utils.session import DevicehubClient, retry

from ereuse_workbench.config import WorkbenchConfig
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
                 json: Path = None,
                 debug: bool = False):
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
        :param debug: Add extra debug information to the resulting
                      snapshot?
        """
        if os.geteuid() != 0:
            raise EnvironmentError('Execute Workbench as root.')

        init(autoreset=True)
        self.benchmark = benchmark or WorkbenchConfig.WB_BENCHMARK
        self.smart = smart or WorkbenchConfig.WB_SMART_TEST
        self.erase = erase or WorkbenchConfig.WB_ERASE
        self.erase_steps = erase_steps or WorkbenchConfig.WB_ERASE_STEPS
        self.erase_leading_zeros = erase_leading_zeros or WorkbenchConfig.WB_ERASE_LEADING_ZEROS
        self.stress = stress or WorkbenchConfig.WB_STRESS_TEST
        self.server = server
        self.uuid = uuid.uuid4()
        self.install = install
        self.install_path = Path('/media/workbench-images')
        self.json = json
        self.session = None
        self.debug = debug
        self.snapshots_path = Path('/home/user/snapshots')

        if self.server:
            # Override the parameters from the configuration from the server
            self.session = retry(DevicehubClient(self.server))
            self.config_from_server()
            if self.install:
                # We get the OS to install from the server through a mounted samba
                self.mount_images(self.server.host)
            # By setting daemon=True USB Sneaky will die when we die
            self.usb_sneaky = Process(target=USBSneaky, args=(self.uuid, server), daemon=True)

        self.config_environment()

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

    def config_environment(self):
        """Configures snapshots folder and save json name"""
        self.snapshots_path.mkdir(parents=True, exist_ok=True)
        self.json = Path('{snapshots_path}/{date}_{uuid}_computer.json'.format(snapshots_path=self.snapshots_path,
                                                                               date=datetime.now().strftime(
                                                                                   "%Y-%m-%d-%H:%M:%S"),
                                                                               uuid=self.uuid))

    def config_from_server(self):
        """Configures the Workbench from a config endpoint in the server."""
        # todo test this ensuring values from json are well set
        config, _ = self.session.get('/settings/')
        for key, value in config.items():
            if key == 'eraseSteps':
                key = 'erase_steps'
            elif key == 'eraseLeadingZeros':
                key = 'erase_leading_zeros'
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

        print('{}eReuse.org Workbench {}.'.format(Fore.CYAN, self.version))
        if self.server:
            print('{}Connected to Workbench Server.'.format(Fore.CYAN))

        # Show to the user what we are doing
        actions = []
        if self.benchmark:
            actions.append('benchmarks')
        if self.stress:
            actions.append('stress test of {} minutes'.format(self.stress))
        if self.smart:
            actions.append('{} SMART test'.format(self.smart))
        if self.erase:
            zeros = ' and extra erasure with zeros' if self.erase_leading_zeros else ''
            actions.append('{} with {} steps{}'.format(self.erase, self.erase_steps, zeros))
        if self.install:
            actions.append('installing {}'.format(self.install))

        logging.info('New run with %s', actions)
        print('{}Performing {}:'.format(Fore.CYAN, ', '.join(actions)))

        try:
            snapshot = self._run()
        except Exception as e:
            logging.error('Run failed:')
            logging.exception(e)
            print('{}Workbench had an error and stopped. '
                  'Please take a photo of the screen and send it to the developers.'
                  .format(Fore.RED))
            if self.server:
                with suppress(OSError):
                    print('The local IP of this device is {}'
                          .format(ereuse_utils.local_ip(self.server.host)))
            raise
        else:
            logging.info('Run finished successfully.')
        finally:
            if self.session:
                self.session.close()
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
                            SnapshotSoftware.Workbench,
                            self.version,
                            self.session,
                            self.debug)
        snapshot.computer()

        if self.benchmark:
            snapshot.benchmarks()

        if self.stress:
            snapshot.test_stress(self.stress)

        if self.smart or self.erase or self.install:
            snapshot.storage(self.smart,
                             self.erase,
                             self.erase_steps,
                             self.erase_leading_zeros,
                             (self.install_path / self.install) if self.install else None)

        snapshot.close()
        self.json.write_text(snapshot.encode('7KU4ZzsEfe'))
        return snapshot

    @property
    def version(self) -> StrictVersion:
        """The version of this software."""
        return ereuse_utils.version('ereuse-workbench')


class CannotMount(Exception):
    pass
