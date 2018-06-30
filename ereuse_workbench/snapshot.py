from datetime import datetime
from distutils.version import StrictVersion
from enum import Enum, unique
from pathlib import Path
from typing import List
from uuid import UUID

import click_spinner
from colorama import Fore

from ereuse_workbench.computer import Computer, DataStorage
from ereuse_workbench.erase import CannotErase, EraseType
from ereuse_workbench.install import CannotInstall
from ereuse_workbench.test import TestDataStorageLength
from ereuse_workbench.utils import Dumpeable, LJUST


@unique
class SnapshotSoftware(Enum):
    """The algorithm_software used to perform the Snapshot."""
    Workbench = 'Workbench'
    AndroidApp = 'AndroidApp'
    Web = 'Web'
    DesktopApp = 'DesktopApp'


class Snapshot(Dumpeable):
    def __init__(self,
                 uuid: UUID,
                 expected_events: List[str],
                 software: SnapshotSoftware,
                 version: StrictVersion) -> None:
        self.type = 'Snapshot'
        self._init_time = datetime.utcnow()
        self.uuid = uuid
        self.software = software
        self.version = version
        self.expected_events = expected_events
        self.closed = False
        self.date = datetime.utcnow()

    def computer(self):
        self._title('Retrieve computer information')
        with click_spinner.spinner():
            self.device, self.components = Computer.run()
            self._storages = tuple(c for c in self.components if isinstance(c, DataStorage))
            self._elapsed()
        self._done()

    def benchmarks(self):
        self._title('Benchmark')
        with click_spinner.spinner():
            for component in self.components:
                component.benchmarks()
        self._done()

    def test_smart(self, length: TestDataStorageLength):
        t = 'SMART test'
        self._warn_no_storage(t)
        for storage in self._storages:
            test = storage.test_smart(length)
            if test.error:
                self._title('{} {}'.format(t, storage.serial_number))
                self._error('failed.')
            else:
                self._done()
        self._elapsed()

    def test_stress(self, minutes):
        self.device.test_stress(minutes)
        self._elapsed()

    def erase(self, erase: EraseType, erase_steps: int, zeros: bool):
        t = 'Erase'
        self._warn_no_storage(t)
        for storage in self._storages:
            self._title('{} {}'.format(t, storage.serial_number))
            try:
                storage.erase(erase, erase_steps, zeros)
            except CannotErase as e:
                self._error(e)
        self._elapsed()

    def install(self, path_to_os_image: Path):
        t = 'Installing OS'
        self._warn_no_storage(t)
        for storage in self._storages:
            self._title('{} to {}'.format(t, storage.serial_number))
            try:
                with click_spinner.spinner():
                    storage.install(path_to_os_image)
            except CannotInstall as e:
                self._error(e)
            else:
                self._done()
        self._elapsed()

    def _elapsed(self):
        self.elapsed = datetime.now() - self._init_time

    def _done(self):
        print('{}done.'.format(Fore.GREEN))

    def _error(self, text):
        print('{}{}'.format(Fore.RED, text))

    def _warn_no_storage(self, text):
        if not self._storages:
            self._title(text)
            print('{}no data storage units.'.format(Fore.YELLOW))

    def _title(self, text):
        print('{}'.format(text).ljust(LJUST), end='')
