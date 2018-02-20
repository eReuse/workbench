from unittest.mock import MagicMock

from ereuse_workbench.tests.assertions import has_ram
from ereuse_workbench.tests.conftest import computer

"""
Tests computers that broke the Workbench at one point in time.

These tests use the output of LSHW from those computers.
"""


def test_box_xavier(lshw: MagicMock):
    computer(lshw, 'box-xavier')


def test_eee_pc(lshw: MagicMock):
    pc, components = computer(lshw, 'eee-pc')
    assert len(components['Processor']) == 1
    assert has_ram(components)
    assert pc['model'] == '1000H', 'Model has noise enclosed between parenthesis'
    assert pc['serialNumber'] == '8BOAAQ191999'
    assert pc['type'] == 'Netbook'
    assert pc['@type'] == 'Computer'
    # todo assert components == jsonf('eee-pc-components-output')


def test_lenovo(lshw: MagicMock):
    pc, components = computer(lshw, 'lenovo')
    assert len(components['Processor']) == 1
    assert has_ram(components), 'Computer without RAM'


def test_pc_laudem(lshw: MagicMock):
    # todo fix
    pc, components = computer(lshw, 'pc-laudem')
    assert len(components['Processor']) == 1
    assert has_ram(components), 'Computer without RAM'


def test_virtualbox_client(lshw: MagicMock):
    """
    Tests a virtualized computer.

    Virtualized computers return much lesser information as they cannot
    directly access directly the hardware of the host machine.
    """
    pc, components = computer(lshw, 'virtualbox-client')


def test_xeon(lshw: MagicMock):
    pc, components = computer(lshw, 'xeon')

    assert 'HardDrive' not in components
    assert has_ram(components), 'Computer without RAM'


def test_xiaomi(lshw: MagicMock):
    pc, components = computer(lshw, 'xiaomi')
    assert len(components['Processor']) == 1
    assert has_ram(components), 'Computer without RAM'


def test_dell(lshw: MagicMock):
    pc, components = computer(lshw, 'dell-logicalname-network')
    assert len(components['Processor']) == 1
    assert has_ram(components), 'Computer without RAM'


def test_hp_dc7900(lshw: MagicMock):
    """Tests an HP DC 7900 with an erased HDD following HMG IS5."""
    # todo check totalSlots and usedSlots
    pc, components = computer(lshw, 'erased-i5.lshw')
    assert len(components['Processor']) == 1
    assert pc['@type'] == 'Computer'
    assert has_ram(components), 'Computer without RAM'


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


def test_nec(lshw: MagicMock):
    """
    Tests a NEC computer.

    See `issue
    <https://tree.taiga.io/project/ereuseorg-workbench/issue/55>`_ for
    computer information.
    """
    pc, components = computer(lshw, 'nec.lshw')
    assert len(components['Processor']) == 1
    # todo fails: assert pc['serialNumber'] == '210623170008'
    # todo fails: assert pc['model'] == 'DAK-BLU'
    assert len(components['HardDrive']) == 1
    hdd = components['HardDrive'][0]
    assert hdd['serialNumber'] == 'STA2L7MV39LL6D'
    # todo fails: assert hdd['model'] == 'HDT721032SLA380'
    assert hdd['manufacturer'] == 'Hitachi'
    assert hdd['size'] == 305245
    assert len(components['RamModule']) == 2
    # todo the printed model is M378T2863QZS-CE6 or M378T2863QZS (easy to mislead the last part)
    for ram in components['RamModule']:
        assert ram['model'] == 'M3 78T2863QZS-CE6'
        assert ram['size'] == 1024


def test_hp_compaq_8100(lshw: MagicMock):
    """
    Tests an HP Compaq 8100.

    See `issue
    <https://tree.taiga.io/project/ereuseorg-workbench/issue/54>`_ for
    more info.
    """
    pc, components = computer(lshw, 'hp-compaq-8100.lshw')
    assert pc['serialNumber'] == 'CZC0408YPV'
    assert pc['model'] == 'HP Compaq 8100 Elite SFF'
    assert pc['manufacturer'] == 'Hewlett-Packard'
    assert len(components['Processor']) == 1
    assert len(components['HardDrive']) == 1
    hdd = components['HardDrive'][0]
    # todo in picture serialNumber is exactly ``WCAV2U856544``
    assert hdd['serialNumber'] == 'WD-WCAV2U856544'
    assert hdd['size'] == 305245
    # todo in picture model is exactly ``WD3200AAJS``
    assert hdd['model'] == 'WDC WD3200AAJS-6'
    assert hdd['manufacturer'] == 'Western Digital'
    assert len(components['RamModule']) == 4
    for ram in components['RamModule']:
        assert ram['serialNumber'] in {'92072F30', 'A4482E29', '939E2E29', '48FD2E30'}
        assert ram['speed'] == 1333.0
        assert ram['size'] == 2048
