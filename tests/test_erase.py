from typing import Tuple
from unittest.mock import MagicMock, call

import pytest

from ereuse_workbench.erase import Step, StepType


@pytest.fixture()
def step_mock():
    stderr = MagicMock()
    stderr.readline = MagicMock()
    stderr.read = MagicMock()
    step = Step(StepType.StepRandom, MagicMock(), 4)
    return step, stderr


def test_erase_basic_update(step_mock: Tuple[Step, MagicMock]):
    """Ensures that the update bar works correctly for EraseBasic."""
    step, output = step_mock
    t = 'shred: /dev/sda: pass 1/1 (random)...111MiB/5.0GiB {}%'

    output.readline.side_effect = ['shred: /dev/sda: pass 1/1 (random)...', None]
    step._update(output, False)
    assert step._bar.call_count == 0

    output.readline.side_effect = [t.format(20), t.format(100), None]
    step._update(output, False)
    # first increment is 5, which is 20 / 4
    # second increment is 20, which is 100 / 4 - 5
    assert step._bar.update.call_args_list == [call(5), call(20)]


def test_erase_sectors_update(step_mock: Tuple[Step, MagicMock]):
    """Ensures that the update bar works correctly for EraseSectors."""
    step, output = step_mock
    t = 'Reading and comparing: {}% done, 0:50 elapsed. (0/0/0 errors)'

    output.read.side_effect = [t.format(20.44), t.format(90.00), t.format(30.00), t.format(80.01), None]
    step._update(output, True)
    assert step._bar.update.call_args_list == [call(4), call(14), call(0), call(10)]

    output.read.side_effect = ['Testing with random pattern: done', None]
    step._update(output, True)
    assert step._bar.update.call_count == 4
