from unittest import TestCase

from classes.parser import Parser, Snapshot, Tsn
from classes.parser.value import Value

from tests.utils import make_node


class TestTransact(TestCase):
    tsn: Tsn
    ss: Snapshot

    def setUp(self):
        # Tsn that converts 100a to 50b
        self.tsn = Tsn(
            src_value = Value(100, 'a'),
            dst_value = Value(50, 'b'),
            date = None
        )

        # Empty snapshot
        self.ss = Snapshot(nodes=[])

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
        # Make available funds equal to tsn value
        self.ss.nodes = [
            make_node(50, 'a'),
            make_node(50, 'a'),
        ]
        result = Parser.transact(tsn=self.tsn, snapshot=self.ss)

        # Result should contain one snapshot
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].tsn, self.tsn)

        # Snapshot should contain two nodes
        nodes = result[0].nodes
        self.assertEqual(len(nodes), 2)

        # Node values should be correct
        expected_value = Value(quantity=25, currency='b')
        self.assertEqual(nodes[0].value, expected_value)
        self.assertEqual(nodes[1].value, expected_value)

    def test_partial_deduction(self):
        # Make available funds greater than tsn value
        self.ss.nodes = [
            make_node(50, 'a'),
            make_node(51, 'a'),
        ]
        result = Parser.transact(tsn=self.tsn, snapshot=self.ss)

        # Result should contain one snapshot
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].tsn, self.tsn)

        # Snapshot should contain three nodes (2 cvns, 1 remainder)
        nodes = result[0].nodes
        self.assertEqual(len(nodes), 3)

        # Node values should be correct
        self.assertEqual(nodes[0].value, Value(quantity=25, currency='b'))
        self.assertEqual(nodes[1].value, Value(quantity=25, currency='b'))
        self.assertEqual(nodes[2].value, Value(quantity=1, currency='a'))

    def test_over_deduction(self):
        # Make available funds less than tsn value
        self.ss.nodes = [
            make_node(50, 'a'),
            make_node(49, 'a'),
        ]
        result = Parser.transact(tsn=self.tsn, snapshot=self.ss)

        # Result should have an additional Snapshot / Tsn
        self.assertEqual(len(result), 2)
        self.assertEqual(result[1].tsn, self.tsn)

        self.assertEqual(result[0].tsn.src_value, None)
        self.assertEqual(result[0].tsn.dst_value, Value(quantity=1, currency='a'))
        self.assertEqual(
            set(n.value for n in result[0].nodes),
            set([Value(50, 'a'), Value(49, 'a'), Value(1, 'a')])
        )

        # Final snapshot should contain three nodes (3 cvns)
        nodes = result[1].nodes
        self.assertEqual(len(nodes), 3)

        self.assertEqual(
            set(n.value for n in result[1].nodes),
            set([
                Value(quantity=25.0, currency='b'),
                Value(quantity=24.5, currency='b'),
                Value(quantity=0.5, currency='b')
            ])
        )

    def test_multiple_currencies(self):
        # Add extraneous node
        self.ss.nodes = [
            make_node(50, 'a'),
            make_node(1, 'c'),
            make_node(50, 'a'),
        ]
        result = Parser.transact(tsn=self.tsn, snapshot=self.ss)

        # Result should still contain one snapshot
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].tsn, self.tsn)

        # Only the 'a' nodes should have gotten converted
        self.assertEqual(
            set(n.value for n in result[0].nodes),
            set([
                Value(quantity=25.0, currency='b'),
                Value(quantity=25.0, currency='b'),
                Value(quantity=1, currency='c')
            ])
        )

    def test_parent(self):
        # Perform transaction with remainder of 1a
        self.ss.nodes = [make_node(101, 'a')]
        result = Parser.transact(tsn=self.tsn, snapshot=self.ss)

        # Check first node
        parent_0 = result[0].nodes[0].parent
        self.assertEqual(len(parent_0.children), 2)
        self.assertEqual(result[0].nodes, parent_0.children)

        # Check second node
        parent_1 = result[0].nodes[1].parent
        self.assertEqual(len(parent_1.children), 2)
        self.assertEqual(result[0].nodes, parent_1.children)

        # Compare both
        self.assertIs(parent_0, parent_1)
