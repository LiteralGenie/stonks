from dataclasses import dataclass
import dataclasses
from functools import cached_property

from .tsn import Tsn
from .value import Value


@dataclass
class Node:
    value: Value
    tsn: Tsn
    
    children: list['Node'] = dataclasses.field(default_factory=list)
    to_parent_rate: int = 1
    parent: 'Node' = None
 
    @property
    def leafs(self) -> list['Node']:
        if self.children:
            return [leaf for child in self.children for leaf in child.leafs]
        else:
            return [self]

    def _get_basis_rate(self, currency: str) -> Value:
        if (self.parent is None) or (self.value.currency == currency):
            return dataclasses.replace(self.value, quantity=self.to_parent_rate)
        else:
            return self.to_parent_rate * self.parent._get_basis_rate(currency)
    
    def get_basis(self, currency: str) -> Value:
        return self.value.quantity * self._get_basis_rate(currency)

    @cached_property
    def market(self):
        return self.tsn.dst_market
 
    def walk(self):
        return [self] + [node for child in self.children for node in child.walk()]
    
    def add_child(self, node: 'Node'):
        self.children.append(node)
        node.parent = self
