from unittest import TestCase
from unittest.mock import Mock

from classes.parser.snapshot import Snapshot
from tests.utils import make_node


class SnapshotTest(TestCase):
    def test_totals(self):
        nodes = [
            make_node('a', 1),
            make_node('a', 2),
            make_node('b', 4),
        ]

        ss = Snapshot(tsn=None, nodes=nodes)
        expected = dict(a=3, b=4)
        self.assertDictEqual(ss.totals, expected)