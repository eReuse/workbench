import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from ereuse_workbench.os_installer import Installer

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


@pytest.fixture()
def run() -> MagicMock:
    with patch('ereuse_workbench.os_installer.run') as mocked_run:
        yield mocked_run


def test_installer(run: MagicMock):
    # Run module
    image_path = Path('/media/workbench-images/FooBarOS-18.3-English')
    installer = Installer()
    dict_return = installer.install(image_path)

    # Do checks
    assert run.call_count == 8

    fscall = next(args[0]
                  for args, kwargs in run.call_args_list
                  if args[0][0] == 'fsarchiver')
    assert fscall[2] == str(image_path) + '.fsa', \
        'Failed to add extension to image name'

    assert dict_return['label'] == str(image_path)
    assert dict_return['success'] is True


def test_installer_with_known_error(run: MagicMock):
    run.side_effect = subprocess.CalledProcessError(69, 'test')
    image_path = Path('/media/workbench-images/FooBarOS-18.3-English')
    installer = Installer()
    dict_return = installer.install(image_path)
    assert dict_return['success'] is False


def test_installer_with_unknown_error(run: MagicMock):
    run.side_effect = Exception()
    image_path = Path('/media/workbench-images/FooBarOS-18.3-English')
    installer = Installer()
    with pytest.raises(Exception):
        installer.install(image_path)
