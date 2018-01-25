from unittest.mock import MagicMock

from ereuse_workbench.tests.conftest import computer

"""
Tests computers that broke the Workbench at one point in time.

These tests use the output of LSHW from those computers.
"""


def test_box_xavier(lshw: MagicMock):
    computer(lshw, 'box-xavier')


def test_eee_pc(lshw: MagicMock):
    computer(lshw, 'eee-pc')


def test_lenovo(lshw: MagicMock):
    computer(lshw, 'lenovo')


def test_pc_laudem(lshw: MagicMock):
    # todo fix
    computer(lshw, 'pc-laudem')


def test_virtualbox_client(lshw: MagicMock):
    computer(lshw, 'virtualbox-client')


def test_xeon(lshw: MagicMock):
    pc, components = computer(lshw, 'xeon')
    assert not [c for c in components if c['@type'] == 'HardDrive'], 'There shouldn\'t be HDDs'


def test_xiaomi(lshw: MagicMock):
    computer(lshw, 'xiaomi')
