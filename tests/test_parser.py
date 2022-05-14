from unittest import TestCase
from unittest.mock import MagicMock, Mock

from classes.parser import Parser, Tsn, Snapshot
from classes.parser.value import Value

from tests.utils import make_node


class TestTransact(TestCase):
    tsn: Tsn
    ss: Snapshot

    def setUp(self):
        # Tsn that converts 100a to 50b
        self.tsn = Mock()
        self.tsn.src_value.currency = 'a'
        self.tsn.src_value.quantity = 100
        self.tsn.dst_value.currency = 'b'
        self.tsn.dst_value.quantity = 50

        # Empty snapshot
        self.ss = MagicMock()
        self.ss.nodes = []

    def test_empty_src(self):
        self.tsn.src_value = None # tsn with no source
        self.ss.nodes = [] # empty snapshot
        result = Parser.transact(tsn=self.tsn, snapshot=self.ss)

        # Result should be single Snapshot with single Node
        self.assertEqual(len(result), 1)
        self.assertEqual(len(result[0].nodes), 1)

        # Node value should be exactly Tsn.dst_value
        node = result[0].nodes[0]
        self.assertEqual(node.value, self.tsn.dst_value)
        self.assertIs(node.tsn, self.tsn)

    def test_full_deduction(self):
        # Create snapshot that contains exactly the src_value
        self.ss.nodes = [
            make_node('a', 50),
            make_node('a', 50),
        ]
        self.ss.totals.get.return_value = 100
        result = Parser.transact(tsn=self.tsn, snapshot=self.ss)

        # Result should contain one snapshot
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].tsn, self.tsn)

        # Snapshot should contain two nodes
        nodes = result[0].nodes
        self.assertEqual(len(nodes), 2)

        # Node values should be correrct
        expected_value = Value(quantity=25, currency='b')
        self.assertEqual(nodes[0].value, expected_value)
        self.assertEqual(nodes[1].value, expected_value)