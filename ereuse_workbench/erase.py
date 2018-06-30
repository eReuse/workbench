from contextlib import contextmanager
from datetime import datetime
from enum import Enum
from subprocess import CalledProcessError, run


class EraseType(Enum):
    EraseBasic = 'EraseBasic'
    EraseSectors = 'EraseSectors'

    def __str__(self):
        return self.value


class Measurable:
    @contextmanager
    def measure(self):
        self.start_time = datetime.now()
        yield
        self.end_time = datetime.now()


class Erase(Measurable):
    def __init__(self, type: EraseType, steps: int, zeros: bool) -> None:
        self.type = type
        self._steps = steps
        self.zeros = zeros
        self.steps = []
        self.error = False

    def run(self, dev: str):
        with self.measure():
            try:
                self._run(dev)
            except CannotErase:
                self.error = True
                raise

    def _run(self, dev: str):
        if self.zeros:
            # Erase zeros first to follow HMG IS5
            step = Step(StepType.StepZero)
            step.erase_basic(dev)
            self.steps.append(step)

        for _ in range(self._steps):
            step = Step(StepType.StepRandom)
            if self.type == EraseType.EraseBasic:
                step.erase_basic(dev)
            else:
                step.erase_sectors(dev)
            self.steps.append(step)


class StepType(Enum):
    StepZero = 'StepZero'
    StepRandom = 'StepRandom'


class Step(Measurable):
    def __init__(self, type: StepType) -> None:
        self.type = type
        self.error = False
        self._options = '-vn' if type == StepType.StepRandom else '-zvn'
        self._steps = 1 if type == StepType.StepRandom else 0

    def erase_basic(self, dev: str):
        with self.measure():
            try:
                run(('shred', self._options, str(self._steps), dev), check=True)
            except CalledProcessError:
                self.error = True
                raise CannotErase(dev)

    def erase_sectors(self, dev: str):
        with self.measure():
            try:
                run(('badblocks', '-st', 'random', '-w', dev, '-o', '/tmp/badblocks'), check=True)
            except CalledProcessError:
                self.error = True
                raise CannotErase(dev)


class CannotErase(Exception):
    def __str__(self) -> str:
        return 'Cannot erase the data storage {}'.format(self.args[0])
