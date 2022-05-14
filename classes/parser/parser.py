from __future__ import annotations

import dataclasses as ds
from dataclasses import dataclass
from functools import cached_property


@dataclass
class Value:
    quantity: int
    currency: str

    def __rmul__(self, other):
        if isinstance(other, int) or isinstance(other, float):
            q = other * self.quantity
            return ds.replace(self, quantity=q)
        else:
            raise NotImplementedError

@dataclass
class Tsn:
    date: float
    dst_value: Value
    dst_market: str = ''

    src_value: Value = None
    src_market: str = None

    fee: Value = None
 
@dataclass
class Node:
    value: Value
    tsn: Tsn
    
    children: list['Node'] = ds.field(default_factory=list)
    to_parent_rate: int = 1
    parent: 'Node' = None
 
    @property
    def leafs(self) -> list[Node]:
        if self.children:
            return [leaf for child in self.children for leaf in child.leafs]
        else:
            return [self]

    def _get_basis_rate(self, currency: str) -> Value:
        if (self.parent is None) or (self.value.currency == currency):
            return ds.replace(self.value, quantity=self.to_parent_rate)
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
 
@dataclass
class Snapshot:
    tsn: Tsn
    nodes: list[Node]

    def get_total_basis(self, currency: str):
        totals = dict()

        for node in self.nodes:
            basis = node.get_basis(currency)
            totals.setdefault(basis.currency, 0)
            totals[basis.currency] += basis.quantity
        
        return totals
    
    def get_changes(self) -> tuple[list[Node], list[Node]]:
        children = [
            n for n in self.nodes
            if n.tsn is self.tsn
        ]
        assert all(n.value.currency == self.tsn.dst_value.currency for n in children)

        temp = [n.parent for n in children if n.parent]
        parents = []
        for n in temp:
            if n not in parents:
                parents.append(n)

        return children, parents

class Parser:
    @classmethod
    def tree(cls, tsns: list[Tsn]) -> list[Node]:
        root_nodes: list[Node] = []
        tsn_order = []
    
        for tsn in tsns:
            leaves = [n for node in root_nodes for n in node.leafs]
    
            # add funds if no source
            if tsn.src_value is None:
                root = Node(
                    value = tsn.dst_value,
                    tsn = tsn
                )
    
                root_nodes.append(root)
                leaves.append(root)
                tsn_order.append(tsn)
                continue
    
            # add funds if source is greater than current funds
            srcs: list[Node] = [node for node in leaves]
            srcs = [node for node in srcs if node.value.currency == tsn.src_value.currency]
            srcs = [node for node in srcs if node.market == tsn.src_market]
    
            src_total = sum(x.value.quantity for x in srcs)
            diff = tsn.src_value.quantity - src_total
            if diff > 0:
                root_value = Value(quantity=diff, currency=tsn.src_value.currency)
                root_tsn = Tsn(
                    date = tsn.date,
                    dst_value = root_value,
                    dst_market = tsn.src_market
                )
                root = Node(
                    value = root_value,
                    tsn = root_tsn
                )
    
                root_nodes.append(root)
                srcs.append(root)
    
            # apply transaction by creating child nodes
            rem = tsn.src_value.quantity
            cvn_rate = tsn.dst_value.quantity / tsn.src_value.quantity
            for src in srcs:
                # create post-conversion node
                deduction = min(src.value.quantity, rem)
    
                child = Node(
                    value = Value(
                        quantity = deduction * cvn_rate,
                        currency = tsn.dst_value.currency
                    ),
                    tsn = tsn,
                    to_parent_rate = 1 / cvn_rate
                )
    
                rem -= deduction
                src.add_child(child)
                assert child.tsn is not src.tsn
    
                # create remainder node
                src_rem = src.value.quantity - deduction
                if src_rem > 0:
                    child = Node(
                        value = Value(
                            quantity = src_rem,
                            currency = src.value.currency
                        ),
                        tsn = tsn,
                        to_parent_rate = 1
                    )
                    src.add_child(child)
                    assert child.tsn is not src.tsn

                assert src.tsn not in [n.tsn for n in src.children]
    
            # verify conversion amount
            if rem != 0:
                if rem > (1 / 10**10):
                    raise ValueError(rem)
    
        # whew
        return root_nodes
    
    @classmethod
    def snapshot(cls, roots: list[Node]) -> list[Snapshot]:
        # get tsns
        tsns = []
        for root in roots:
            for node in root.walk():
                if node.tsn not in tsns:
                    tsns.append(node.tsn)

        # sort by date
        tmp = tsns.copy()
        tsns = sorted(tsns, key=lambda tsn: (tsn.date, tmp.index(tsn)))

        # pre-allocate
        snapshots: list[Snapshot] = [Snapshot(tsn=tsn, nodes=[]) for tsn in tsns]
    
        # populate snapshots
        to_visit = roots.copy()
        index = lambda node: tsns.index(node.tsn)

        for ss_ind in range(len(snapshots)):
            next_visit = []
            for node in to_visit:
                # if node.children and index(node.children[0]) == ss_ind:
                #     assert(all(index(node.children[0]) == index(c) for c in node.children))
                #     snapshots[ss_ind].nodes.extend(node.children)
                #     next_visit.extend(node.children)
                # elif index(node) <= ss_ind:
                #     snapshots[ss_ind].nodes.append(node)
                #     next_visit.append(node)
                # else:
                #     next_visit.append(node)

                if node.parent:
                    assert index(node) > index(node.parent)

                if node.children:
                    assert(all(index(node.children[0]) == index(c) for c in node.children))
                    if index(node.children[0]) == ss_ind:
                        snapshots[ss_ind].nodes.extend(node.children)
                        next_visit.extend(node.children)
                    elif index(node.children[0]) > ss_ind:
                        snapshots[ss_ind].nodes.append(node)
                        next_visit.append(node)
                    else:
                        raise ValueError
                else:
                    snapshots[ss_ind].nodes.append(node)
                    next_visit.append(node)
    
            to_visit = next_visit
    
        assert all(len(node.children) == 0 for node in to_visit)
        return snapshots
     
if __name__ == '__main__':
    data = [
        Tsn(dst_value=Value(5, 'a'), date=1, dst_market=''),
        Tsn(dst_value=Value(20, 'a'), date=2, dst_market=''),
        Tsn(src_value=Value(15, 'a'), dst_value=Value(30, 'c'), date=3, src_market='', dst_market='')
    ]
    
    tree = Parser.tree(data)
    snapshots = Parser.snapshot(tree)
    pass
