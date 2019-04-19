from typing import Set

import pytest

from ereuse_workbench.computer import Device, Processor

"""
Test removing values we don't want and returning None when meaningless
ones.
"""


def get(value: str, remove: Set[str] = None):
    return Device.get({'x': value}, 'x', remove=remove)


def test_parenthesis():
    """Parenthesis, square brackets..."""
    assert get('Foo (NONE)') == 'Foo'
    assert get('Foo (none)') == 'Foo'
    assert get('foo(O.E.M)') == 'foo'
    assert get('foo(o.e.m)') == 'foo'
    assert get('foo(o.e.M)') == 'foo'
    assert get('System[[n/a]') == 'System'
    assert get('system[[n/a]') == 'system'
    assert get('system serial[[n/a]') is None
    assert get('system SERIAL[[n/a]') is None
    assert get('systemserial[[n/a]') == 'systemserial'


def test_none():
    assert get('none') is None
    assert get('NONE') is None
    assert get('none foo') == 'foo'


def test_unknown():
    assert get('Unknown') is None
    assert get('unknown') is None


def test_remove():
    assert get('foobar', remove={'foobar'}) is None
    assert get('foobarx', remove={'foobar'}) == 'foobarx'


def test_cpu_values():
    # Note that we still remove the S/N of cpus in computer.processors()
    assert get('0001-067A-0000-0000-0000-0000') is None
    assert get('0001-067A-0000-0000') is None


@pytest.mark.parametrize('value', [
    ('Intel(R) Core(TM) i7-2620M CPU @ 2.70GHz', 'Core i7', 2),
    ('Intel Core2 Duo CPU E8400 @ 3.00GHz', 'Core2 Duo', None),
    ('Intel Core2 Quad CPU E8400 @ 3.00GHz', 'Core2 Quad', None),  # assumed
    ('Intel Core i3 CPU 530 @ 2.93GHz', 'Core i3', 1),
    ('Intel Atom CPU N270 @ 1.60GHz', 'Atom', None),
    ('Intel Core m3-6Y30', 'Core m3', None),
    ('Intel Atom CPU 330 @ 1.60GHz', 'Atom', None),  # assumed
    ('Intel Celeron CPU N3050 @ 1.60GHz', 'Celeron', None),
    ('Intel Celeron CPU 450 @ 1.60GHz', 'Celeron', None),  # assumed
    ('Intel Pentium CPU G645 @ 2.90GHz', 'Pentium', None),
    ('Intel Xeon CPU E5520 @ 2.27GHz', 'Xeon', 1),
    ('Intel Xeon E5-1220W V2 @ 2.27GHz', 'Xeon', 2),  # assumed
    ('Intel Xeon Platinum 8380M @ 2.27GHz', 'Xeon Platinum', 3),  # assumed
    ('Intel Xeon Gold 5820T @ 2.27GHz', 'Xeon Gold', 8),  # assumed
    ('Intel Core i5-6200U CPU @ 2.30GHz', 'Core i5', 6),
    ('Intel Core i7 CPU 920 @ 2.67GHz', 'Core i7', 1),
    ('foo bar', None, None)
])
def test_processor_brand_generation(value):
    # todo add brand / generation to test_wrong_computers
    model, r_brand, r_generation = value
    brand, generation = Processor.processor_brand_generation(model)
    assert brand == r_brand
    assert generation == r_generation
