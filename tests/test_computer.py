from typing import Set

from ereuse_workbench.computer import Device

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
