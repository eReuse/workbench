import json

from ereuse_workbench import utils


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


# todo make through tests of units
def test_convert_capacity():
    assert utils.convert_capacity(1200, 'kB', 'MB')
    assert utils.convert_capacity(1200, 'KB', 'MB')
    assert utils.convert_capacity(1200, 'bytes', 'MB')
