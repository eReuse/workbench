import hashlib
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from distutils.version import StrictVersion
from enum import Enum, unique
from pathlib import Path
from typing import List, Optional, Tuple, Type, Union
from uuid import UUID

import inflection
from ereuse_utils import cli
from ereuse_utils.cli import Line
from ereuse_utils.session import DevicehubClient

from ereuse_workbench.benchmark import Benchmark, BenchmarkProcessorSysbench
from ereuse_workbench.computer import Component, Computer, DataStorage, SoundCard
from ereuse_workbench.erase import CannotErase, Erase, EraseType
from ereuse_workbench.install import CannotInstall, Install
from ereuse_workbench.test import StressTest, Test, TestDataStorage, TestDataStorageLength
from ereuse_workbench.utils import Dumpeable


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
                 software: SnapshotSoftware,
                 version: StrictVersion,
                 session: Optional[DevicehubClient] = None,
                 debug=False) -> None:
        self.type = 'Snapshot'
        self._init_time = datetime.now(timezone.utc)
        self.uuid = uuid
        self.software = software
        self.version = version
        self.closed = False
        self.endTime = datetime.now(timezone.utc)
        self.elapsed = None
        self.device = None  # type: Computer
        self.components = None  # type: List[Component]
        self._storages = None
        self._session = session
        self._debug = debug

    def computer(self):
        """Retrieves information about the computer and components."""
        t = cli.title('Get computer info')
        with Line() as line, line.spin(t):
            self.device, self.components = Computer.run()
            if self._debug:
                self.debug = self.device._debug
            self._storages = tuple(c for c in self.components if isinstance(c, DataStorage))
            if self._session:
                self._session.post('/snapshots/', self, uri=self.uuid, status=204)
            line.close_message(t, self.device)
        # Submit
        for component in self.components:
            if not isinstance(component, SoundCard):  # soundcards are not really important
                print(cli.title(inflection.titleize(component.__class__.__name__)), component)
        print()

    def benchmarks(self):
        """Perform several benchmarks to the computer and its components."""
        # Get all benchmarks
        benchmarks = []  # type: List[Tuple[Optional[int], Benchmark]]
        for i, component in enumerate(self.components):
            for benchmark in component.benchmarks():
                benchmarks.append((i, benchmark))
        for benchmark in self.device.benchmarks():
            benchmarks.append((None, benchmark))

        # Process the benchmarks
        t = cli.title('Benchmark')
        with Line(len(benchmarks), desc=t) as line:
            for i, benchmark in benchmarks:
                benchmark.run()
                self._submit_action(benchmark, i)
                line.update(1)

            # Print CPU Sysbench Benchmark
            try:
                b = next(b[1] for b in benchmarks if isinstance(b[1], BenchmarkProcessorSysbench))
            except StopIteration:
                line.close_message(t, cli.done())
                logging.info('Benchmark done without CPU benchmarking.')
            else:
                line.close_message(t, 'CPU {}'.format(b))
                logging.info('Benchmark done with CPU %s.', b)

    def test_stress(self, minutes):
        """Performs a stress test."""
        t = cli.title('Stress test')
        with Line(minutes * 60, desc=t) as line:
            line.close_message(t, cli.done())
            progress = Progress(line, self.uuid, StressTest, self._session)
            test = self.device.test_stress(minutes, progress)
        self._submit_action(test)

    def storage(self,
                smart: TestDataStorageLength = None,
                erase: EraseType = None,
                erase_steps: int = None,
                zeros: bool = None,
                install=None):
        """SMART tests, erases and installs an OS to all the data storage
        units in parallel following the passed-in parameters.
        """
        if not self._storages:
            cli.warning('No data storage units.')
            return

        total = len(self._storages)
        lines = total * (bool(smart) + bool(erase) + bool(install))
        with Line.reserve_lines(lines), ThreadPoolExecutor() as executor:
            # Create a thread for each new data storage
            # this assumes there are no more data storage units than executors
            for pos, storage in enumerate(self._storages):
                executor.submit(self._storage, pos, total, storage, smart, erase, erase_steps,
                                zeros, install)

    def _storage(self,
                 num: int,
                 total: int,
                 storage: DataStorage,
                 smart: Optional[TestDataStorageLength],
                 erase: Optional[EraseType],
                 erase_steps: Optional[int],
                 zeros: Optional[bool],
                 install_path: Optional[Path]):
        """SMART tests, erases and installs an OS to a single data
        storage unit. """
        i = self.components.index(storage)
        logging.info('Process storage %s (%s) with %s %s %s %s %s',
                     i, storage, smart, erase, erase_steps, zeros, install_path)
        try:
            if smart:
                t = cli.title('{} {}'.format('SMART test', storage.serial_number))
                with Line(100, desc=t, position=num) as line:
                    logging.debug('Snapshot: Install storage %s (%s)', i, storage)
                    progress = Progress(line, self.uuid, TestDataStorage, self._session, i)
                    test = storage.test_smart(smart, progress)
                    if test:
                        line.close_message(t, cli.done('test successful: {}'.format(test)))
                    else:
                        line.close_message(t, cli.danger('failed: {}'.format(test)))
                self._submit_action(test, i)
            if erase:
                pos = total * bool(smart) + num
                t = cli.title('{} {}'.format('Erase', storage.serial_number))
                with Line(Erase.compute_total_steps(erase, erase_steps, zeros) * 100,
                          desc=t,
                          position=pos) as line:
                    progress = Progress(line, self.uuid, TestDataStorage, self._session, i)
                    try:
                        erasure = storage.erase(erase, erase_steps, zeros, progress)
                    except CannotErase as e:
                        line.close_message(t, cli.danger(e))
                    else:
                        line.close_message(t, cli.done(
                            'done in {}'.format(erasure.end_time - erasure.start_time)
                        ))
                        self._submit_action(erasure, i)
            if install_path:
                pos = total * (bool(smart) + bool(erase)) + num
                t = cli.title('{} {}'.format('Install OS', storage.serial_number))
                with Line(100, desc=t, position=pos) as line:
                    progress = Progress(line, self.uuid, Install, self._session, i)
                    try:
                        install = storage.install(install_path, callback=progress)
                    except CannotInstall:
                        line.close_message(t, cli.danger('error. Check logs.'))
                    else:
                        line.close_message(t, cli.done())
                        self._submit_action(install, i)
        except Exception as e:
            logging.error('Storage %s (%s) finished with exception:', i, storage)
            logging.exception(e)
            raise
        else:
            logging.info('Storage %s (%s) finished successfully.', i, storage)

    def _submit_action(self, action: Union[Test, Benchmark, Erase], component: int = None):
        """Submits the passed-in action to the Workbench Server, if there
        is a Workbench Server.
        """
        if not self._session:
            return
        base = '/snapshots/{}/'.format(self.uuid)
        uri = 'components/{}/action/'.format(component) if component else 'device/action/'
        self._session.post(base, action, uri=uri, status=204)

    def close(self):
        """Closes the Snapshot, submitting a final copy to the
        Workbench Server, if one.
        """
        self.closed = True
        self.elapsed = datetime.now(timezone.utc) - self._init_time
        if self._session:
            self._session.patch('/snapshots/', self, self.uuid, status=204)

    def hash(self):
        """Create snapshot hash to prevent manual modifications
         on json file.
         """
        snapshot_without_debug = self.dump()
        snapshot_without_debug.pop('debug')
        bfile = str(snapshot_without_debug).encode('utf-8')
        hash3 = hashlib.sha3_256(bfile).hexdigest()
        self.debug['hwinfo'] += hash3


class Progress:
    """Manages updating progress percentage to a Line and a Workbench
    Server, if any.
    """

    def __init__(self,
                 line: Line,
                 uuid: UUID,
                 action: Union[Type[Test], Type[Erase], Type[Install]],
                 session: DevicehubClient = None,
                 component: Optional[int] = None):
        super().__init__()
        self.line = line
        self.component = component
        self.action = action.__name__
        self.last_submission = datetime.now()
        self.session = session
        self.uuid = uuid

    def __call__(self, increment: int, percentage: int):
        """Perform an update with the new increment and percentage.

        This call is compatible with the callback of ereuse-util's
        ``cmd.ProgressiveCmd``.
        """
        logging.debug(
            'Incr of %s for comp %s for %s. n is %s, total %s, percentage from source %s',
            increment, self.component, self.action, self.line.n, self.line.total,
            percentage
        )
        self.line.update(increment)
        if self.session:
            self._submit(percentage)

    def _submit(self, percentage: int):
        if self.last_submission < datetime.now() - timedelta(seconds=4):
            try:
                self.session.post('/snapshots/{}/progress/'.format(self.uuid), {
                    'component': self.component,
                    'action': self.action,
                    'percentage': percentage,
                    'total': self.line.total
                }, status=204)
            except Exception as e:
                logging.error('Error in submit for comp %s for %s:', self.component, self.action)
                logging.exception(e)
            finally:
                self.last_submission = datetime.now()
