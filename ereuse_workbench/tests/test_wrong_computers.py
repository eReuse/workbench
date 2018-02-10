from unittest.mock import MagicMock

from ereuse_workbench.tests.conftest import computer, jsonf

"""
Tests computers that broke the Workbench at one point in time.

These tests use the output of LSHW from those computers.
"""


def test_box_xavier(lshw: MagicMock):
    computer(lshw, 'box-xavier')


def test_eee_pc(lshw: MagicMock):
    pc, components = computer(lshw, 'eee-pc')
    assert pc['model'] == '1000H', 'Model has noise enclosed between parenthesis'
    assert pc['serialNumber'] == '8BOAAQ191999'
    assert pc['type'] == 'Netbook'
    assert pc['@type'] == 'Computer'
    assert components == jsonf('eee-pc-components-output')


def test_lenovo(lshw: MagicMock):
    computer(lshw, 'lenovo')


def test_pc_laudem(lshw: MagicMock):
    # todo fix
    computer(lshw, 'pc-laudem')


def test_virtualbox_client(lshw: MagicMock):
    computer(lshw, 'virtualbox-client')


def test_xeon(lshw: MagicMock):
    pc, components = computer(lshw, 'xeon')
    assert not any(c['@type'] == 'HardDrive' for c in components), 'There shouldn\'t be HDDs'


def test_xiaomi(lshw: MagicMock):
    computer(lshw, 'xiaomi')


def test_dell(lshw: MagicMock):
    computer(lshw, 'dell-logicalname-network')


def test_hp_dc7900(lshw: MagicMock):
    """Tests an HP DC 7900 with an erased HDD following HMG IS5."""
    # todo check totalSlots and usedSlots
    pc, components = computer(lshw, 'erased-i5.lshw')
    assert pc['@type'] == 'Computer'


def test_virtualbox_without_hdd_and_with_usb(lshw: MagicMock):
    """
    Tests that a Virtualbox with an USB plugged-in doesn't provide
    more information (like the USB or an extra hard-drive),
    and tests a system without hard-drive.

    In some computers it was detected that this behaviour it was
    triggered if there was no hard-drive.
    """
    original = computer(lshw, 'virtualbox-no-hdd')
    usb = computer(lshw, 'virtualbox-no-hdd-yes-usb')
    assert original == usb
