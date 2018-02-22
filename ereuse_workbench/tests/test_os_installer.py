from ereuse_workbench import os_installer
from unittest.mock import call


def test_full_run(subprocess_os_installer):
    run = subprocess_os_installer.run
    os_installer.install('/tmp/linuxmint.fsa')
    assert run.call_count == 5
    print(run.call_args_list)

#    calls = run.call_args_list

#    assert calls == expected_calls




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