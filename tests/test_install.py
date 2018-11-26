import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ereuse_workbench.install import CannotInstall, Install
from ereuse_workbench.utils import Severity

"""
Tests the OSInstaller. 

How to create a lightweight fsa for testing purposes:
dd if=/dev/zero of=mockdev bs=1M count=2
losetup /dev/loop0 mockdev
mkfs.ext4 /dev/loop0
mkdir lomount; mount /dev/loop0 lomount
echo "samplecontents" >lomount/samplefile
umount lomount
fsarchiver savefs mockfs.fsa /dev/loop0
ezpzlmnsqz
"""

image_path = Path('/media/workbench-images/FooBarOS-18.3-English-32.fsa')


@pytest.fixture()
def run() -> MagicMock:
    with patch('ereuse_utils.cmd.run') as mocked_run:
        yield mocked_run


def test_install(run: MagicMock):
    # Run module
    install = Install(image_path)
    install.run()

    # Do checks
    assert run.call_count == 9

    fscall = next(args
                  for args, kwargs in run.call_args_list
                  if args[0] == 'fsarchiver')
    assert fscall[2] == image_path

    assert install.name == str(image_path.name)
    assert install.severity != Severity.Error
    assert install.address == 32
    i = json.loads(install.to_json())
    assert {
        'elapsed': 0,
        'type': 'Install',
        'severity': 'Info',
        'name': 'FooBarOS-18.3-English-32.fsa',
        'address': 32
    } == i


def test_installer_with_known_error(run: MagicMock):
    run.side_effect = subprocess.CalledProcessError(69, 'test')
    with pytest.raises(CannotInstall):
        Install(image_path).run()


def test_installer_with_unknown_error(run: MagicMock):
    run.side_effect = Exception()
    with pytest.raises(Exception):
        Install(image_path).run()
