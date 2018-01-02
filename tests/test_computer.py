from unittest import TestCase

from ereuse_workbench.computer import Computer


class TestComputer(TestCase):
    def test_get(self):
        """Test removing values we don't want and returning None when meaningless ones"""
        self.assertEqual('foo', Computer.get({'a': 'none foo'}, 'a'))
        self.assertEqual('foo', Computer.get({'a': 'foo(O.E.M)'}, 'a'))
        self.assertEqual('foo', Computer.get({'a': 'foo(o.e.m)'}, 'a'))
        self.assertEqual('foo', Computer.get({'a': 'foo(o.e.M)'}, 'a'))
        self.assertEqual('System', Computer.get({'a': 'System[[n/a]'}, 'a'))
        # system in serial
        self.assertEqual('system', Computer.get({'a': 'system[[n/a]'}, 'a'))
        self.assertEqual(None, Computer.get({'a': 'system serial[[n/a]'}, 'a'))
        self.assertEqual(None, Computer.get({'a': 'system SERIAL[[n/a]'}, 'a'))
        self.assertEqual('systemserial', Computer.get({'a': 'systemserial[[n/a]'}, 'a'))
