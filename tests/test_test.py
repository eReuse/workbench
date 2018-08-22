from unittest.mock import MagicMock, patch
from warnings import warn

import pySMART
import pytest

from ereuse_workbench.test import TestDataStorage, TestDataStorageLength


@pytest.fixture()
def Device() -> MagicMock:
    class Device:
        pass

    with patch('ereuse_workbench.test.Device') as m:
        m.side_effect = lambda _: Device()
        yield Device


def test_tester_smart(Device: pySMART.Device):
    Device.run_selftest = MagicMock(return_value=(0, None, 3))
    Device.model = 'foo'
    Device.get_selftest_result = MagicMock()
    Device.get_current_test_status = MagicMock(return_value=(None, ' '))
    Device.update = MagicMock()
    Device.tests = [MagicMock()]
    Device.tests[0].remain = '0%'
    Device.tests[0].hours = '24'
    Device.tests[0].LBA = '0'
    Device.tests[0].type = 'foo-type'
    Device.tests[0].status = 'foo-status'
    Device.attributes = [None] * 256
    Device.attributes[12] = MagicMock()
    Device.attributes[12].raw = '11'
    Device.assessment = 'PASS'
    test = TestDataStorage()
    test.run('/foo/bar', length=TestDataStorageLength.Short)
    assert test.lifetime == 24
    assert test.type == 'TestDataStorage'
    assert not test.error
    assert test.status == 'foo-status'
    assert test.lifetime == 24
    assert test.assessment
    assert test.power_cycle_count == 11


def test_tester_no_smart(Device: pySMART.Device):
    """
    Tests the smart tester with a hard-drive that doesn't support SMART.
    """

    def init(_):
        warn('')

    Device.__init__ = init
    t = TestDataStorage()
    t.run('/foo/bar', length=TestDataStorageLength.Short)
    assert t.error
    assert t.status == 'SMART cannot be enabled on this device.'
