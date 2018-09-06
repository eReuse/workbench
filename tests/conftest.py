import json
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple
from unittest import mock
from unittest.mock import MagicMock

import pytest

from ereuse_workbench.computer import Component, Computer


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
    pc, components = Computer.run()
    assert lshw.called
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
