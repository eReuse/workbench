import json

from ereuse_workbench import base2, unit, utils


def test_dumpeable():
    foo = utils.Dumpeable()
    foo.foo = 'fooz'
    foo._foo = '_f'
    foo.bar = utils.Dumpeable()
    foo.bar.bar = 'barz'
    foo.bar.foo_bar = 1

    d = foo.dump()
    assert d == {'foo': 'fooz', 'bar': foo.bar}

    j = foo.to_json()
    assert json.loads(j) == {'foo': 'fooz', 'bar': {'bar': 'barz', 'fooBar': 1}}
    assert foo.foo == 'fooz'
    assert foo._foo == '_f'
    assert foo.bar.foo_bar == 1
    assert not hasattr(foo.bar, 'fooBar')


def test_convert_capacity():
    assert unit.Quantity(1200, 'kb').to('MB').magnitude == 1.2
    assert unit.Quantity(1200, 'KB').to('MB').magnitude == 1.2
    assert unit.Quantity(1200, 'bytes').to('MB')

    assert base2.Quantity(1024, 'kb').to('mb').magnitude == 1
