from unittest.mock import MagicMock

from classes.parser.node import Node
from classes.parser.value import Value


def make_node(quantity: float, currency: str) -> Node:    
    return Node(
        value = Value(quantity=quantity, currency=currency),
        tsn = None
    )