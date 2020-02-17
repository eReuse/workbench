import logging
import pathlib
import textwrap
from pathlib import Path

from ereuse_utils import cmd

from ereuse_workbench.utils import Measurable, Severity


class Install(Measurable):
    """Install an OS in a data storage unit.

    Important: GPT partition scheme and UEFI-based boot not yet supported. All relevant
    code is just placeholder.
    """
    def __init__(self,
                 image_path: Path,
                 logical_name: str = '/dev/sda',
                 swap: bool = True):
        """Initializes values.
        :param logical_name: Target disk's device name (ex. '/dev/sda').
                             It must exist.
        :param swap: Whether to create a swap partition of 1GB.
        :param image_path: A path to the '.fsa' file to install.
        """
        super().__init__()
        self._data_storage = logical_name
        self._swap_space = swap
        self._path = image_path
        self.type = self.__class__.__name__
        self.severity = Severity.Info
        self.name = image_path.name
        if '32' in self.name or 'x86' in self.name:
            self.address = 32
        elif '64' in self.name:
            self.address = 64
        else:
            self.address = None

    def run(self, callback):
        """Partitions the data storage unit and installs an OS.

        This method softly erases all previous data from the disk.
        """
        logging.info('Install %s to %s', self._path, self._data_storage)
        with self.measure():
            try:
                self._run(callback)
            except Exception as e:
                self.severity = Severity.Error
                logging.error('Failed install on %s:', self._data_storage)
                logging.exception(e)
                raise CannotInstall(e) from e

    def _run(self, callback):
        assert isinstance(self._path, Path)
        # Steps:
        # Zero out disk label
        #   TODO (low prio): ensure disk not mounted (findmnt?)
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
        #   fsarchiver vs tar/rsync? Much to my surprise, fsarchiver looks more suited
        #   https://forums.fsarchiver.org/viewtopic.php?t=922
        # Install bootloader
        #   BIOS: GRUB to MBR + VBR
        #   UEFI: GRUB to ESP

        # Zero out disk label
        self.zero_out(self._data_storage)

        # Partition main disk (must set os_partition appropriately in every possible case)
        os_partition = self.partition(self._data_storage, self._swap_space)

        # Install OS
        self.install(self._path, os_partition, callback)

        # Install bootloader
        self.install_bootloader(self._data_storage)

        # sync at the end to prepare for abrupt poweroff
        self.sync()

        # TODO rewrite fstab to use swap space correctly. sth like:
        # OLD_SWAP_UUID=$(grep swap $tmproot/etc/fstab | get_uuid)
        # sed -i "s/$OLD_SWAP_UUID/$NEW_SWAP_UUID/g" $tmproot/etc/fstab

    @classmethod
    def zero_out(cls, drive: str):
        cmd.run('dd', 'if=/dev/zero', 'of={}'.format(drive), 'bs=512', 'count=1')
        cls.sync()

    @staticmethod
    def partition(data_storage: str, swap: bool):
        """Partitions the whole data storage unit to keep a booteable
        OS by a regular BIOS / GPT scheme.
        :param data_storage: The name of the disk to partition
                            (ex. "/dev/sda").
        :param swap: Whether to create an additional partition
               of 1GB for swap.
        :return: The name of the partition where the OS has been
                 installed (ex. "/dev/sda1").
        """
        if swap:
            parted_commands = textwrap.dedent("""\
                mklabel msdos \
                mkpart primary ext2 1MiB -1GiB \
                mkpart primary linux-swap -1GiB 100% \
                """)
        else:
            parted_commands = textwrap.dedent("""\
                mklabel msdos \
                mkpart primary ext2 1MiB 100% \
            """)
        cmd.run('parted', '--script', data_storage, '--', parted_commands)
        return '{}{}'.format(data_storage, 1)  # "/dev/sda1"

    @staticmethod
    def install(path_to_os_image: Path, target_partition: str, callback):
        """Installs an OS image to a partition.
        :param path_to_os_image: The path where the fsa file is.
        :param target_partition: The name of the partition (ex. "dev/sda1")
                                 where to install it.
        """
        assert path_to_os_image.suffix == '.fsa', 'Set the .fsa extension'
        i = cmd.ProgressiveCmd('fsarchiver',
                               'restfs',
                               '-v',
                               path_to_os_image,
                               'id=0,dest={}'.format(target_partition),
                               number_chars={1, 2, 3},
                               callback=callback)
        i.run()

    @staticmethod
    def install_bootloader(data_storage: str):
        """Installs the grub2 bootloader to the target disk.
        :param data_storage: The name of the disk (ex. "/dev/sda").
        """
        # Must install grub via 'grub-install', but it will complain if --boot-directory is not used.
        pathlib.Path('/tmp/mnt').mkdir(exist_ok=True)  # Exist_ok in case of double wb execution
        cmd.run('mount', '{}1'.format(data_storage), '/tmp/mnt')
        cmd.run('grub-install', '--boot-directory=/tmp/mnt/boot/', data_storage)
        cmd.run('umount', '/tmp/mnt')

    @staticmethod
    def sync():
        cmd.run('sync')


class CannotInstall(Exception):
    def __init__(self, e: Exception) -> None:
        super().__init__()
        self.e = e

    def __str__(self) -> str:
        return ('OS installation failed: {e}'.format(e=self.e))
