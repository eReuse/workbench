import json
from collections import defaultdict
from datetime import datetime
from distutils.version import StrictVersion
from pathlib import Path
from typing import Dict, List, Tuple
from unittest import mock
from unittest.mock import MagicMock
from uuid import UUID

import pytest

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
def lshw() -> MagicMock:
    """
    Mocks the call to LSHW from Computer.

    Set ``mocked.return_value.json`` with a JSON string, where
    ``mocked`` is the injected parameter you receive in your test.
    """

    class Run:
        def __init__(self) -> None:
            self.json = ''
            super().__init__()

        def __call__(self, cmd, **kwargs):
            cmd = str(cmd)
            if 'lshw' in cmd:
                return Result(self.json)
            elif 'dmidecode' in cmd:
                return Result(1)
            else:
                return Result('')

    class Result:
        def __init__(self, stdout) -> None:
            self.stdout = stdout

    with mock.patch('ereuse_workbench.computer.run') as run:
        run.side_effect = Run()
        yield run


@pytest.fixture()
def pysmart_device() -> MagicMock:
    with mock.patch('ereuse_workbench.computer.pySMART.Device') as smart:
        smart.side_effect = Warning()
        yield smart


def computer(lshw: MagicMock, json_name: str) -> Tuple[Computer, Dict[str, List[Component]]]:
    """Given a LSHW output and a LSHW mock, runs Computer."""
    lshw.side_effect.json = fixture(json_name + '.json')
    s = Snapshot(UUID(int=000000), [], SnapshotSoftware.Workbench, StrictVersion('11.0a1'))
    s.computer()
    s.close_if_needed(None)
    assert s.closed
    pc, components = s.device, s.components
    assert lshw.called

    # Ensure the resulting Snapshot has not changed
    # when comparing it to a reference snapshot
    # This is important to ensure two things:
    # 1. Workbench produces consistent values over modifications
    # 2. The value matches the Devicehub API
    file = Path(__file__).parent / 'output' / (json_name + '.snapshot.json')
    test_snapshot = json.loads(s.to_json())
    # time is the only changing variable through snapshots: let's normalize it
    test_snapshot['endTime'] = str(datetime.min)
    try:
        with file.open() as f:
            reference_snapshot = json.load(f)
        assert test_snapshot == reference_snapshot, 'This snapshot differs from the reference one.'
    except FileNotFoundError:
        # new test. just auto-save the file as the reference
        with file.open('w') as f:
            json.dump(test_snapshot, f, indent=2)

    # Group components in a dictionary by their @type
    grouped = defaultdict(list)
    for component in components:
        grouped[component.type].append(component)
    return pc, grouped


@pytest.fixture()
def subprocess_os_installer() -> MagicMock:
    with mock.patch('ereuse_workbench.os_installer.subprocess') as subprocess:
        subprocess.run = MagicMock()
        yield subprocess
