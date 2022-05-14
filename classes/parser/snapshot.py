import copy
from dataclasses import dataclass
from functools import cached_property

from .node import Node
from .tsn import Tsn


@dataclass
class Snapshot:
    """
    Essentially an immutable list of all the leaf nodes.
    """

    nodes: list[Node]
    tsn: Tsn = None

    def copy(self) -> 'Snapshot':
        # @todo optimize this by assuming ancestor nodes are immutable
        return copy.deepcopy(self)

    @cached_property
    def totals(self) -> dict[str, float]:
        """
        Get totals for each currency
        """

        totals = dict()
        for n in self.nodes:
            currency = n.value.currency

            totals.setdefault(currency, 0)
            totals[currency] += n.value.quantity
        
        return totals