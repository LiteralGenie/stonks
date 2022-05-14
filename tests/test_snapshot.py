from unittest import TestCase
from unittest.mock import Mock

from classes.parser.snapshot import Snapshot
from tests.utils import make_node


class SnapshotTest(TestCase):
    def test_totals(self):
        nodes = [
            make_node(1, 'a'),
            make_node(2, 'a'),
            make_node(4, 'b'),
        ]

        ss = Snapshot(tsn=None, nodes=nodes)
        expected = dict(a=3, b=4)
        self.assertDictEqual(ss.totals, expected)