import json

from ereuse_workbench.utils import Dumpeable


def test_dumpeable():
    foo = Dumpeable()
    foo.foo = 'fooz'
    foo._foo = '_f'
    foo.bar = Dumpeable()
    foo.bar.bar = 'barz'
    foo.bar.foo_bar = 1

    d = foo.dump()
    assert d == {'foo': 'fooz', 'bar': foo.bar}

    j = foo.to_json()
    assert json.loads(j) == {'foo': 'fooz', 'bar': {'bar': 'barz', 'fooBar': 1}}
