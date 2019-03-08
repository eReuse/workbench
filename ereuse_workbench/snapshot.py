from concurrent import futures
from datetime import datetime, timezone
from distutils.version import StrictVersion
from enum import Enum, unique
from itertools import chain
from pathlib import Path
from typing import List
from uuid import UUID

import click_spinner
from colorama import Fore
from ereuse_utils import cli
from ereuse_utils.cli import Line

from ereuse_workbench.computer import Computer, DataStorage
from ereuse_workbench.erase import CannotErase, EraseType
from ereuse_workbench.install import CannotInstall
from ereuse_workbench.test import TestDataStorageLength
from ereuse_workbench.utils import Dumpeable, Severity


@unique
class SnapshotSoftware(Enum):
    """The algorithm_software used to perform the Snapshot."""
    Workbench = 'Workbench'
    AndroidApp = 'AndroidApp'
    Web = 'Web'
    DesktopApp = 'DesktopApp'


class Snapshot(Dumpeable):
    """
    Generates the Snapshot report for Devicehub by obtaining the
    data from the computer, performing benchmarks and tests...

    After instantiating the class, run :meth:`.computer` before any
    other method.
    """

    def __init__(self,
                 uuid: UUID,
                 expected_events: List[str],
                 software: SnapshotSoftware,
                 version: StrictVersion) -> None:
        self.type = 'Snapshot'
        self._init_time = datetime.now(timezone.utc)
        self.uuid = uuid
        self.software = software
        self.version = version
        self.expected_events = expected_events
        self.closed = False
        self.endTime = datetime.now(timezone.utc)

    def computer(self):
        """Retrieves information about the computer and components."""
        self._title('Retrieve computer information')
        with click_spinner.spinner():
            self.device, self.components = Computer.run()
            self._storages = tuple(c for c in self.components if isinstance(c, DataStorage))
            self._elapsed()
        self._done()

    def benchmarks(self):
        """Perform several benchmarks to the computer and its components."""
        self._title('Benchmark')
        with click_spinner.spinner():
            for device in chain(self.components, [self.device]):
                device.benchmarks()
        self._done()

    def test_smart(self, length: TestDataStorageLength):
        """Performs a SMART test to all the data storage units."""
        self._process_data_storages('SMART test', self.test_smart_one, length)

    def test_smart_one(self, t, pos: int, storage: DataStorage, length: TestDataStorageLength):
        title = cli.title('{} {}'.format(t, storage))
        with Line(total=100, desc=title, position=pos) as line:
            test = storage.test_smart(length, self._update_line_factory(line))
            if test.severity == Severity.Error:
                line.write_at_line(title, cli.danger('failed.'))
            else:
                line.write_at_line(title, cli.done())

    def test_stress(self, minutes):
        """Performs a stress test."""
        self.device.test_stress(minutes)
        self._elapsed()

    def erase(self, erase: EraseType, erase_steps: int, zeros: bool):
        """Erases all the data storage units."""
        self._process_data_storages('Erase', self.erase_one, erase, erase_steps, zeros)

    def erase_one(self,
                  t: str,
                  pos: int,
                  storage: DataStorage,
                  erase: EraseType,
                  erase_steps: int,
                  zeros: bool):
        title = cli.title('{} {}'.format(t, storage))
        with Line(total=(erase_steps + int(zeros)) * 100, desc=title, position=pos) as line:
            try:
                storage.erase(erase, erase_steps, zeros, self._update_line_factory(line))
            except CannotErase as e:
                line.write_at_line(title, cli.danger(e))
            else:
                line.write_at_line(title, cli.done())

    def install(self, path_to_os_image: Path):
        """Installs an OS to all data storage units.

        Note that, for bandwidth reasons, this process is done
        iteratively.
        """
        t = 'Installing OS'
        self._warn_no_storage(t)
        for storage in self._storages:
            self._title('{} to {}'.format(t, storage))
            try:
                with click_spinner.spinner():
                    storage.install(path_to_os_image)
            except CannotInstall as e:
                self._error(e)
            else:
                self._done()
        self._elapsed()

    def close_if_needed(self, actual_event):
        """Closes the Snapshot if it has done all expected events."""
        if not self.expected_events or actual_event == self.expected_events[-1]:
            self.closed = True

    def _elapsed(self):
        self.elapsed = datetime.now(timezone.utc) - self._init_time

    def _process_data_storages(self, t, method, *args):
        self._warn_no_storage(t)
        with cli.Line.reserve_lines(len(self._storages)), futures.ThreadPoolExecutor() as executor:
            for i, storage in enumerate(self._storages):
                executor.submit(method, t, i, storage, *args)
        self._elapsed()

    def _done(self):
        print(cli.done())

    def _error(self, text):
        print(cli.danger(text))

    def _warn_no_storage(self, text):
        if not self._storages:
            self._title(text)
            print('{}no data storage units.'.format(Fore.YELLOW))

    def _title(self, text):
        print(cli.title(text), end='')

    def _update_line_factory(self, line: Line):
        def _update_line(increment):
            line.update(increment)

        return _update_line
