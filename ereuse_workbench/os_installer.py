"""
This module provides functionality to install an OS in the system being tested.

Important: GPT partition scheme and UEFI-based boot not yet supported. All relevant
code is just placeholder.
"""

import subprocess
import textwrap
from enum import Enum
from ereuse_utils import now


class PartitionType(Enum):
    """
    Indicates disk partitioning scheme. Implies whether the system will boot via legacy BIOS
    or UEFI.
    """
    GPT = 0
    MBR = 1


GPT = PartitionType.GPT
MBR = PartitionType.MBR


def do_sync():
    print("Syncing block devices - 10 second timeout")
    subprocess.run('sync', timeout=10)


def zero_out(drive: str):
    command = 'dd', 'if=/dev/zero', 'of={}'.format(drive), 'bs=512', 'count=1'
    subprocess.run(command, check=True)
    do_sync()


def do_partition(target_disk: str, swap_space: bool, part_type):
    """
    :return: A string representing the partition that has been allocated
             to the OS
    """
    if part_type == GPT:
        raise NotImplementedError("GPT partition types not yet implemented!")
    else:  # part_type == BIOS
        if swap_space:
            parted_commands = textwrap.dedent("""\
                mklabel msdos \
                mkpart primary ext2 1MiB -1GiB \
                mkpart primary linux-swap -1GiB 100% \
                """)
            os_partition = '{}{}'.format(target_disk, 1)  # "/dev/sda1"
        else:
            parted_commands = textwrap.dedent("""\
                mklabel msdos \
                mkpart primary ext2 1MiB 100% \
            """)
            os_partition = '{}{}'.format(target_disk, 1)  # "/dev/sda1"
    command = 'parted', '--script', target_disk, '--', parted_commands
    subprocess.run(command, check=True)
    return os_partition


def do_install(path_to_os_image: str, target_partition: str):
    """
    Installs an OS image to a target partition.
    :param path_to_os_image:
    :param target_partition:
    :return:
    """
    command = 'fsarchiver', 'restfs', path_to_os_image + '.fsa', 'id=0,dest={}'.format(target_partition)
    subprocess.run(command, check=True)


def do_install_bootloader(target_disk: str, part_type):
    """
    Installs the grub2 bootloader to the target disk.
    :param target_disk:
    :param part_type:
    :return:
    """
    if part_type == GPT:
        raise NotImplementedError("GPT partition types not yet implemented!")
    # Must install grub via 'grub-install', but it will complain if --boot-directory is not used.
    command = 'mkdir', '/tmp/mnt'
    subprocess.run(command, check=True)
    command = 'mount', '{}1'.format(target_disk), '/tmp/mnt'
    subprocess.run(command, check=True)
    command = 'grub-install', '--boot-directory=/tmp/mnt/boot/', '/dev/sda'
    subprocess.run(command, check=True)
    command = 'umount', '/tmp/mnt'
    subprocess.run(command, check=True)


def install(path_to_os_image: str, target_disk='/dev/sda', swap_space=True, part_type=MBR):
    """
    Partitions block device(s) and installs an OS.

    :param path_to_os_image: A filesystem path to the OS .fsa. It must
                             be somewhere in the client's filesystem
                             hiearchy.
    :param target_disk: Target disk's device name (e.g. /dev/sda).
                        It must exist.
    :param swap_space: Whether to provision a swap partition.
    :param part_type: Whether to use BIOS/MBR or UEFI/GPT schemes.
    :return: A dictonary with the summary of the operation.
    """
    # Steps:
    # Zero out disk label
    #   TODO: ensure disk not mounted (findmnt?)
    # Partition according to BIOS or GPT scheme
    #   TODO: SERIOUSLY consider replacing parted with (s)gdisk
    #   BIOS
    #   ----
    #     Swap: [1MB buffer, 1st part OS from 1M to -4G,
    #       2nd part swap from -4G to 100%]
    #     No swap: [1MB buffer, 1st part OS from 1M to 100%]
    #   UEFI
    #     Swap: [1st part ESP 0% to 100M, 2nd part OS from 100M to -4G,
    #      3rd part swap from -4G to 100%]
    #     No swap: [1st part ESP 0% to 100M, 2nd part OS from 100M to -4G]
    # Install OS to OS partition
    #   debootstrap (with a pre-primed cache?)
    #   fsarchive?
    # Install bootloader
    #   BIOS: GRUB to MBR + VBR
    #   UEFI: GRUB to ESP

    init_time = now()
    try:
        # Zero out disk label
        zero_out(target_disk)
        # Partition main disk (must set os_partition appropriately in every possible case)
        os_partition = do_partition(target_disk, swap_space, part_type)
        # Install OS
        do_install(path_to_os_image, os_partition)
        # Install bootloader
        do_install_bootloader(target_disk, part_type)
        success = True
    except Exception as e:
        print('OS installation failed. An "{}" exception with '
              'message "{}" was raised by the installation routines.'
              .format(type(e).__name__, str(e)))
        success = False
    return {
        'elapsed': now() - init_time,
        'label': install,
        'success': success
    }


    # TODO rewrite fstab to use swap space correctly. sth like:
    # OLD_SWAP_UUID=$(grep swap $tmproot/etc/fstab | get_uuid)
    # sed -i "s/$OLD_SWAP_UUID/$NEW_SWAP_UUID/g" $tmproot/etc/fstab
