import json
from pathlib import Path
from typing import List
from unittest import mock
from unittest.mock import MagicMock

import pytest

from ereuse_workbench.computer import Computer


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
    class LSHW:
        def __init__(self) -> None:
            self.json = ''
            super().__init__()

        def communicate(self):
            return self.json, None

    with mock.patch('ereuse_workbench.computer.Popen') as Popen:
        Popen.return_value = LSHW()
        yield Popen


def computer(lshw: MagicMock, json_name: str) -> (dict, List[dict]):
    """Given a LSHW output and a LSHW mock, runs Computer."""
    lshw.return_value.json = fixture(json_name + '.json')
    computer_getter = Computer()
    assert lshw.called
    return computer_getter.run()
