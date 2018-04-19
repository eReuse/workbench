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


def test_lenovo_7220w3t(lshw: MagicMock):
    pc, components = computer(lshw, 'lenovo-7220w3t.lshw')
    assert pc['manufacturer'] == 'LENOVO'
    assert pc['serialNumber'] == 'S4R6062'
    assert pc['model'] == '7220W3T'
    assert len(components['Processor']) == 1
    assert len(components['HardDrive']) == 1
    motherboard = components['Motherboard'][0]
    assert motherboard['serialNumber'] is None
    assert len(components['RamModule']) == 2
    for ram in components['RamModule']:
        assert ram['serialNumber'] is None
        assert ram['model'] is None
        assert ram['manufacturer'] is None
        assert ram['size'] == 2048
        assert ram['speed'] == 1067.0


def test_lenovo_type_as_intel(lshw: MagicMock):
    """
    Tests a lenovo computer whose LSHW output was wrongly taken
    as an Intel and without S/N.
    """
    pc, components = computer(lshw, 'lenovo-as-intel.lshw')
    assert pc['manufacturer'] == 'LENOVO'
    assert pc['serialNumber'] == 'S4R6460'
    assert pc['model'] == '7220W3T'
    hdd = components['HardDrive'][0]
    assert hdd['serialNumber'] == 'S1L6J9BZ103714'
    assert hdd['model'] == 'SAMSUNG HD251HJ'
    # todo model should be HD251HJ and manufacturer Samsung
    # assert hdd['model'] == 'HD251HJ'
    # assert hdd['manufacturer'] == 'Samsung'
    assert len(components['RamModule']) == 2
    for ram in components['RamModule']:
        assert ram['serialNumber'] is None
        assert ram['model'] is None
        # todo why when ram who as empty has a vendor of "48spaces"?


def test_asus_all_series(lshw: MagicMock):
    pc, components = computer(lshw, 'asus-all-series.lshw')
    # todo it doesn't work assert pc['serialNumber'] == '104094'
    ram = components['RamModule'][0]
    assert ram['manufacturer'] == 'Kingston'
    assert ram['model'] == '9905584-017.A00LF'
    assert ram['serialNumber'] == '9D341297'


def test_custom_pc(lshw: MagicMock):
    pc, components = computer(lshw, 'custom.lshw')
    ram = components['RamModule'][0]
    assert ram['manufacturer'] == 'Kingston'
    assert ram['model'] == '9905584-017.A00LF'
    assert ram['serialNumber'] == '9D341297'
    assert ram['size'] == 4096
    assert ram['speed'] == 1600


def test_all_series(lshw: MagicMock):
    pc, components = computer(lshw, 'all-series.lshw')
    assert 'RamModule' in components
    ram = components['RamModule'][0]
    assert ram['manufacturer'] == 'Kingston'
    assert ram['serialNumber'] == '290E5155'
    assert ram['model'] == '99U5584-003.A00LF'


def test_vostro_260(lshw: MagicMock):
    pc, components = computer(lshw, 'vostro-260.lshw')
    processor = components['Processor'][0]
    assert processor['serialNumber'] is None
    assert processor['model'] == 'Intel Core i3-2120 CPU @ 3.30GHz'
    assert processor['manufacturer'] == 'Intel Corp.'
    graphic_card = components['GraphicCard'][0]
    assert graphic_card['serialNumber'] is None
    assert graphic_card['model'] == '2nd Generation Core Processor Family ' \
                                    'Integrated Graphics Controller'


def test_ecs_computers(lshw: MagicMock):
    pc, components = computer(lshw, 'ecs-computers.lshw')
    assert len(components['HardDrive']) == 1
    hdd = components['HardDrive'][0]
    assert hdd['serialNumber'] == 'WD-WCC2ETY84203'  # printed sn is 'WCC2ETY84203'
    assert hdd['model'] == 'WDC WD5000AAKX-6'  # printed sn is 'WD5000AAKX'
    assert hdd['manufacturer'] == 'Western Digital'  # printed is the logo: 'WD'
    assert len(components['RamModule'])
    ram = components['RamModule'][0]
    assert ram['manufacturer'] == 'Kingston'
    assert ram['serialNumber'] == '8618F309'  # This is not present in the module
    assert ram['size'] == 4096
    assert ram['speed'] == 1600.0
    assert ram['model'] == '99U5584-003.A00LF'  # Exactly as printed
    assert len(components['SoundCard']) == 1
    sound_card = components['SoundCard'][0]
    assert sound_card['model'] == '8 Series/C220 Series Chipset ' \
                                  'High Definition Audio Controller'
    assert sound_card['serialNumber'] is None
    assert sound_card['manufacturer'] == 'Intel Corporation'
    assert len(components['Processor']) == 1
    cpu = components['Processor'][0]
    assert cpu['address'] == 64
    assert cpu['manufacturer'] == 'Intel Corp.'
    assert cpu['model'] == 'Intel Core i5-4440 CPU @ 3.10GHz'
    assert cpu['numberOfCores'] == 4
    assert cpu['serialNumber'] is None
    assert cpu['speed'] == 2.200311
    assert len(components['NetworkAdapter']) == 1
    net = components['NetworkAdapter'][0]
    assert net['manufacturer'] == 'Realtek Semiconductor Co., Ltd.'
    assert net['model'] == 'RTL8111/8168/8411 PCI Express Gigabit Ethernet Controller'
    assert net['serialNumber'] == 'e0:3f:49:1a:d0:44'
    assert net['speed'] == 1000
    assert len(components['Motherboard']) == 1
    mother = components['Motherboard'][0]
    assert mother['serialNumber'] == '131219772601195'  # Found in printed barcode but the
    # text is different
    assert mother['model'] == 'H81M-K'  # found exactly like this
    assert mother['manufacturer'] == 'ASUSTeK COMPUTER INC.'  # found as ASUS
    assert mother['totalSlots'] == 1  # Verified
    assert mother['usedSlots'] == 1  # It was not used though
    # todo assert net['connectors']['usb'] == 6 but only 3 recognized
    assert len(components['GraphicCard']) == 1
    assert components['GraphicCard'][0]['manufacturer'] == 'Intel Corporation'


def test_core2(lshw: MagicMock):
    pc, components = computer(lshw, 'core2.lshw')
    assert len(components) == 7
    ram = components['RamModule'][0]
    assert ram['manufacturer'] is None
    assert ram['serialNumber'] is None
    assert ram['model'] is None
    assert ram['size'] == 1024
    assert ram['speed'] == 667.0


def test_ecs2(lshw: MagicMock):
    pc, components = computer(lshw, 'ecs-2.lshw')
    assert len(components['RamModule']) == 3
    for ram in components['RamModule']:
        assert ram['manufacturer'] is None
        assert ram['serialNumber'] is None
        assert ram['model'] is None
        assert ram['speed'] == 533.0
        assert ram['size'] == 1024
