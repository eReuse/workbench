from contextlib import contextmanager
from datetime import datetime, timezone
from enum import Enum
from subprocess import CalledProcessError

from ereuse_utils import cmd

from ereuse_workbench.utils import Dumpeable, Severity


class EraseType(Enum):
    EraseBasic = 'EraseBasic'
    EraseSectors = 'EraseSectors'

    def __str__(self):
        return self.value


class Measurable(Dumpeable):
    @contextmanager
    def measure(self):
        self.start_time = datetime.now(timezone.utc)
        yield
        self.end_time = datetime.now(timezone.utc)
        assert self.end_time > self.start_time


class Erase(Measurable):
    """Erase data storage units (HDD / SSD) and saves a report."""

    def __init__(self, type: EraseType, steps: int, zeros: bool, callback) -> None:
        assert steps >= 1, 'Steps must be 1 or more.'
        self.type = type
        self._steps = steps
        self._zeros = zeros
        self.steps = []
        self.severity = Severity.Info
        self.callback = callback

    def run(self, dev: str):
        with self.measure():
            try:
                self._run(dev)
            except CannotErase:
                self.severity = Severity.Error
                raise
            self.callback(100)  # shred/badblocks do not output 100% when done

    def _run(self, dev: str):
        if self._zeros:
            # Erase zeros first to follow HMG IS5
            step = Step(StepType.StepZero, self.callback)
            step.erase_basic(dev)
            self.steps.append(step)

        for i in range(self._steps):
            step = Step(StepType.StepRandom, self.callback)
            if self.type == EraseType.EraseBasic:
                step.erase_basic(dev)
            else:
                step.erase_sectors(dev)
            self.steps.append(step)


class StepType(Enum):
    StepZero = 'StepZero'
    StepRandom = 'StepRandom'


class Step(Measurable):
    def __init__(self, type: StepType, callback) -> None:
        self.type = type
        self.severity = Severity.Info
        self._options = '-vn 1' if type == StepType.StepRandom else '-zvn 0'
        self._callback = callback

    @contextmanager
    def _manage_erasure(self, dev):
        with self.measure():
            try:
                yield
            except CalledProcessError:
                self.severity = Severity.Error
                raise CannotErase(dev)

    def erase_basic(self, dev: str):
        with self._manage_erasure(dev):
            self._badblocks = False
            progress = cmd.ProgressiveCmd('shred', *self._options, dev, callback=self._callback)
            progress.run()

    def erase_sectors(self, dev: str):
        with self._manage_erasure(dev):
            self._badblocks = True
            progress = cmd.ProgressiveCmd('badblocks',
                                          '-st', 'random',
                                          '-w', dev,
                                          '-o', '/tmp/badblocks',
                                          number_chars=cmd.ProgressiveCmd.DECIMALS,
                                          read=10,
                                          callback=self._callback)
            progress.run()


class CannotErase(Exception):
    def __str__(self) -> str:
        return 'Cannot erase the data storage {}'.format(self.args[0])
