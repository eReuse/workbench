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

    def erase(self, dev):
        time_start = now()
        steps = []

        # RANDOM WITH SHRED
        total_success = True
        if self.mode == EraseType.EraseBasic:
            while self.steps != 0:
                success = self.erase_process(dev, '-vn', 1)
                if not success:
                    total_success = False
                steps.append({
                    '@type': 'Random',
                    'startingTime': now(),
                    'success': success,
                    'endingTime': now(),
                })
                self.steps -= 1
        # RANDOM WITH BADBLOCK
        elif self.mode == EraseType.EraseSectors:
            while self.steps != 0:
                output = "/tmp/badblocks"
                success = self.erase_sectors(dev, output)
                if not success:
                    total_success = False
                steps.append({
                    '@type': 'Random',
                    'startingTime': now(),
                    'success': success,
                    'endingTime': now(),
                })
                self.steps -= 1
        else:
            raise ValueError("Unknown erase mode '{0}'".format(self.mode))

        # ZEROS WITH SHRED
        if self.zeros:
            success = self.erase_process(dev, '-zvn', 0)
            if not success:
                total_success = False
            steps.append({
                '@type': 'Zeros',
                'startingTime': now(),
                'success': success,
                'endingTime': now(),
            })

        time_end = now()
        return {
            '@type': self.mode,
            'secureRandomSteps': self.steps,
            'cleanWithZeros': self.zeros,
            'startingTime': time_start,
            'endingTime': time_end,
            'success': total_success,
            'steps': steps
        }

    @staticmethod
    def erase_process(dev, options, steps):
        # Erasing
        try:
            subprocess.check_call(["shred", options, str(steps), dev])
            state = True
        except subprocess.CalledProcessError:
            state = False
            print("Cannot erase the hard drive '{0}'".format(dev))
        return state

    @staticmethod
    def erase_sectors(disk, output):
        try:
            subprocess.check_output(["badblocks", "-st", "random", "-w", disk,
                                     "-o", output])
            return True
        except subprocess.CalledProcessError:
            print("Cannot erase the hard drive '{0}'".format(disk))
            return False
