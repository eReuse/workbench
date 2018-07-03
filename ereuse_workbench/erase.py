from contextlib import contextmanager
from datetime import datetime
from enum import Enum
from subprocess import CalledProcessError, DEVNULL, PIPE, Popen
from typing import TextIO

from click._termui_impl import ProgressBar

from ereuse_workbench.utils import Dumpeable, progressbar


class EraseType(Enum):
    EraseBasic = 'EraseBasic'
    EraseSectors = 'EraseSectors'

    def __str__(self):
        return self.value


class Measurable(Dumpeable):
    @contextmanager
    def measure(self):
        self.start_time = datetime.now()
        yield
        self.end_time = datetime.now()


class Erase(Measurable):
    """Erase data storage units (HDD / SSD) and saves a report."""

    def __init__(self, type: EraseType, steps: int, zeros: bool) -> None:
        self.type = type
        self._steps = steps
        self.zeros = zeros
        self._total_steps = self._steps + int(self.zeros)
        self.steps = []
        self.error = False

    def run(self, dev: str):
        with self.measure(), progressbar(length=100, title='Erase {}'.format(dev)) as bar:
            try:
                self._run(dev, bar)
            except CannotErase:
                self.error = True
                raise
            bar.update(100)  # shred/badblocks do not output 100% when done

    def _run(self, dev: str, bar: ProgressBar):
        if self.zeros:
            # Erase zeros first to follow HMG IS5
            step = Step(StepType.StepZero, bar, self._total_steps)
            step.erase_basic(dev)
            self.steps.append(step)

        for i in range(self._steps):
            step = Step(StepType.StepRandom, bar, self._total_steps)
            if self.type == EraseType.EraseBasic:
                step.erase_basic(dev)
            else:
                step.erase_sectors(dev)
            self.steps.append(step)


class StepType(Enum):
    StepZero = 'StepZero'
    StepRandom = 'StepRandom'


class Step(Measurable):
    def __init__(self, type: StepType, bar: ProgressBar, total_steps: int) -> None:
        self.type = type
        self.error = False
        self._options = '-vn 1' if type == StepType.StepRandom else '-zvn 0'
        self._bar = bar
        self._total_steps = total_steps

    def erase_basic(self, dev: str):
        with self.measure():
            try:
                process = Popen(('shred', self._options, dev),
                                universal_newlines=True,
                                stdout=DEVNULL,
                                stderr=PIPE)
                self._update(process.stderr, badblocks=False)
            except CalledProcessError:
                self.error = True
                raise CannotErase(dev)

    def erase_sectors(self, dev: str):
        with self.measure():
            try:
                process = Popen(('badblocks', '-st', 'random', '-w', dev, '-o', '/tmp/badblocks'),
                                universal_newlines=True,
                                stdout=DEVNULL,
                                stderr=PIPE)
                self._update(process.stderr, badblocks=True)
            except CalledProcessError:
                self.error = True
                raise CannotErase(dev)

    def _update(self, output: TextIO, badblocks: bool):
        """
        Consumes the ``process`` stderr output and updates the
        progressbar when there is a percentage in the output.
        """
        # badblocks print the output without EOL so we need to keep
        # reading from a constant flow of streaming (stderr.read(10))
        # and badblocks does 2 steps: 1 for erase + 1 for check
        last_percentage = 0
        while True:
            line = output.read(10) if badblocks else output.readline()
            if line:
                try:
                    i = line.rindex('%')
                    # If the value is a decimal, we need to take 5 chars:
                    # len('99.99') == 5 (we don't care here about 100%)
                    # Otherwise is up to 3: len('100') == 3
                    percentage = int(float(line[i - (5 if badblocks else 3):i]))
                except ValueError:
                    pass
                else:
                    # for badblocks the increment can be negative at the
                    # beginning of the second step where last_percentage
                    # is 100 and percentage is 0. By using min we
                    # kind-of reset the increment and start counting for
                    # the second step
                    increment = max(percentage - last_percentage, 0)
                    self._bar.update(increment // (self._total_steps + int(badblocks)))
                    last_percentage = percentage
            else:
                break  # No more output


class CannotErase(Exception):
    def __str__(self) -> str:
        return 'Cannot erase the data storage {}'.format(self.args[0])
