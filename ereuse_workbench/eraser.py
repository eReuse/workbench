import subprocess
from enum import Enum

from ereuse_utils import now


class EraseType(Enum):
    EraseBasic = 'EraseBasic'
    EraseSectors = 'EraseSectors'

    def __str__(self):
        return self.value


class Eraser:
    def __init__(self, mode: EraseType, steps: int, zeros: bool) -> None:
        self.mode = mode
        self.steps = steps
        self.zeros = zeros

    def erase(self, dev: str):
        """
        Erases a hard-drive.

        See `a detailed explanation of the erasure process in the FAQ
        <https://ereuse-org.gitbooks.io/faq/content/
        w-hich-is-the-data-wiping-process-performed.html>`_.

        If you set :attr:`.mode` as
        :attr:`ereuse_workbench.eraser.EraseType.EraseSectors` and
        :attr:`.zeros` as ``True``, you will erase following the
        HMG IS5 standard.
        """
        time_start = now()
        remaining_steps = self.steps
        steps_performed = []

        total_success = True

        if self.zeros:
            # Zeroes with shred
            # We need to erase zeros first to follow HMG IS5
            success = self.erase_process(dev, '-zvn', 0)
            if not success:
                total_success = False
            steps_performed.append({
                '@type': 'Zeros',
                'startingTime': now(),
                'success': success,
                'endingTime': now(),
            })

        if self.mode == EraseType.EraseBasic:
            # random with shred
            while remaining_steps != 0:
                success = self.erase_process(dev, '-vn', 1)
                if not success:
                    total_success = False
                steps_performed.append({
                    '@type': 'Random',
                    'startingTime': now(),
                    'success': success,
                    'endingTime': now(),
                })
                remaining_steps -= 1
        elif self.mode == EraseType.EraseSectors:
            # random with badblock
            while remaining_steps != 0:
                output = '/tmp/badblocks'
                success = self.erase_sectors(dev, output)
                if not success:
                    total_success = False
                steps_performed.append({
                    '@type': 'Random',
                    'startingTime': now(),
                    'success': success,
                    'endingTime': now(),
                })
                remaining_steps -= 1

        time_end = now()
        return {
            '@type': self.mode,
            'secureRandomSteps': self.steps,
            'cleanWithZeros': self.zeros,
            'startingTime': time_start,
            'endingTime': time_end,
            'success': total_success,
            'steps': steps_performed
        }

    @staticmethod
    def erase_process(dev, options, steps):
        # Erasing
        try:
            subprocess.check_call(['shred', options, str(steps), dev])
            state = True
        except subprocess.CalledProcessError:
            state = False
            print('Cannot erase the hard drive {}'.format(dev))
        return state

    @staticmethod
    def erase_sectors(disk, output):
        try:
            subprocess.check_output(['badblocks', '-st', 'random', '-w', disk, '-o', output])
            return True
        except subprocess.CalledProcessError:
            print('Cannot erase the hard drive {}'.format(disk))
            return False
