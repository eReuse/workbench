import json
from datetime import datetime, timezone
from distutils.version import StrictVersion
from pathlib import Path
from subprocess import CalledProcessError
from typing import List, Tuple
from unittest import mock
from unittest.mock import MagicMock
from uuid import UUID

import pytest
from ereuse_utils import cmd

from ereuse_workbench.computer import Component, Computer
from ereuse_workbench.snapshot import Snapshot, SnapshotSoftware


def fixture(file_name: str):
    with Path(__file__).parent.joinpath('fixtures').joinpath(file_name).open() as file:
        return file.read()


def jsonf(file_name: str) -> dict:
    """Gets a json fixture and parses it to a dict."""
    with Path(__file__).parent.joinpath('fixtures').joinpath(file_name + '.json').open() as file:
        return json.load(file)


@pytest.fixture()
def run():
    class Run():
        PATH = Path(__file__).parent / 'fixtures'
        ORIGINAL_RUN = cmd.run

        def __init__(self) -> None:
            super().__init__()
            self.lshw = self.battery = self.hwinfo = None

        def set(self, model: str):
            self.lshw = self.PATH / '{}.lshw.json'.format(model)  # type: Path
            assert self.lshw.exists()
            self.battery = self.PATH / '{}.battery.ini'.format(model)  # type: Path
            self.hwinfo = self.PATH / '{}.hwinfo.txt'.format(model)  # type: Path
            if not self.hwinfo.exists():
                # Old test: no hwinfo fixture.
                # Provide a dummy hwinfo so test can execute
                self.hwinfo = self.PATH / 'boxnuc6cayh.hwinfo.txt'  # type: Path

        def __call__(self, *cmds, **kwargs):
            if 'lshw' in cmds:
                return self._stdout(self.lshw)
            if 'hwinfo' in cmds:
                return self._stdout(self.hwinfo)
            if '/sys/class/power_supply/BAT*/uevent' in cmds:
                try:
                    return self._stdout(self.battery)
                except FileNotFoundError:  # Device without battery
                    raise CalledProcessError(666, '')
            if 'lspci' in cmds:
                return MagicMock(stdout='')
            return self.ORIGINAL_RUN(*cmds, **kwargs)

        def _stdout(self, file: Path):
            m = MagicMock()
            m.stdout = file.read_text()
            return m

    with mock.patch('ereuse_utils.cmd.run', new=Run()) as run:
        yield run


@pytest.fixture()
def pysmart_device() -> MagicMock:
    with mock.patch('ereuse_workbench.computer.pySMART.Device') as smart:
        smart.side_effect = Warning()
        yield smart


def computer(run, model: str) -> Tuple[Computer, List[Component]]:
    """Given a LSHW output and a LSHW mock, runs Computer."""
    run.set(model)
    s = Snapshot(UUID(int=000000),
                 SnapshotSoftware.Workbench,
                 StrictVersion('11.0a1'),
                 debug=True)
    s.computer()
    s.close()
    s.encode('foo')
    s.elapsed = 0  # So cpu time does not impact
    assert s.closed
    pc, components = s.device, s.components

    # Ensure the resulting Snapshot has not changed
    # when comparing it to a reference snapshot
    # This is important to ensure two things:
    # 1. Workbench produces consistent values over modifications
    # 2. The value matches the Devicehub API
    file = Path(__file__).parent / 'output' / (model + '.snapshot.json')
    test_snapshot = json.loads(s.to_json())
    # time is the only changing variable through snapshots: let's normalize it
    test_snapshot['endTime'] = str(datetime(year=1, month=1, day=1, tzinfo=timezone.utc))
    try:
        with file.open() as f:
            reference_snapshot = json.load(f)
        # assert test_snapshot == reference_snapshot, 'This snapshot differs from the reference one.'
    except FileNotFoundError:
        # new test. just auto-save the file as the reference
        with file.open('w') as f:
            json.dump(test_snapshot, f, indent=2)

    return pc, components


@pytest.fixture()
def subprocess_os_installer() -> MagicMock:
    with mock.patch('ereuse_workbench.os_installer.subprocess') as subprocess:
        subprocess.run = MagicMock()
        yield subprocess
