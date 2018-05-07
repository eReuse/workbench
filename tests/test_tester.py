from unittest.mock import MagicMock, patch
from warnings import warn

import pySMART
import pytest

from ereuse_workbench.tester import Smart, Tester


@pytest.fixture()
def Device() -> MagicMock:
    class Device:
        pass

    with patch('ereuse_workbench.tester.Device') as m:
        m.side_effect = lambda _: Device()
        yield Device


def test_tester_smart(Device: pySMART.Device):
    Device.run_selftest = MagicMock(return_value=(0, None, 3))
    Device.update = MagicMock()
    Device.tests = [MagicMock()]
    Device.tests[0].remain = '0%'
    Device.tests[0].hours = '24'
    Device.tests[0].LBA = '0'
    Device.tests[0].type = 'foo-type'
    Device.tests[0].status = 'foo-status'
    Device.attributes = [None] * 10
    Device.attributes[9] = MagicMock()
    Device.attributes[9].raw = 99
    r = Tester.smart('/foo/bar', test_type=Smart.short)
    assert r == {
        'lifetime': 24,
        '@type': 'TestHardDrive',
        'error': False,
        'type': 'foo-type',
        'status': 'foo-status',
        'firstError': 0,
        'passedLifetime': 99
    }


def test_tester_no_smart(Device: pySMART.Device):
    """
    Tests the smart tester with a hard-drive that doesn't support SMART.
    """
    def init(_):
        warn('')

    Device.__init__ = init
    r = Tester.smart('/foo/bar', test_type=Smart.short)
    assert r == {
        'error': True,
        'status': 'SMART cannot be enabled on this device.',
        '@type': 'TestHardDrive'
    }
