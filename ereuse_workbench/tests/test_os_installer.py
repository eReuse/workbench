from pathlib import Path
from unittest.mock import patch

from ereuse_workbench.os_installer import Installer


def test_installer():
    with patch('ereuse_workbench.os_installer.subprocess.run') as mocked_run:
        # Run module
        image_path = Path('/media/workbench-images/FooBarOS-18.3-English')
        installer = Installer()
        dict_return = installer.install(image_path)

        # Do checks
        assert mocked_run.call_count == 8

        fscall = [args[0] for args, kwargs in mocked_run.call_args_list if args[0][0] == 'fsarchiver'][0]
        assert fscall[2] == str(image_path) + '.fsa', 'Failed to add extension to image name'

        assert dict_return['label'] == str(image_path)
        assert dict_return['success'] is True


"""
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
