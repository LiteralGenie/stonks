from unittest.mock import MagicMock

from classes.parser.node import Node
from classes.parser.value import Value


def make_node(currency: str, quantity: float) -> Node:    
    return Node(
        value = Value(quantity=quantity, currency=currency),
        tsn = None
    )