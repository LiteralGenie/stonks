from classes.parser.node import Node
from classes.parser.snapshot import Snapshot
from classes.parser.tsn import Tsn
from classes.parser.value import Value


class Parser:
    @classmethod
    def transact(cls, tsn: Tsn, snapshot: Snapshot|None) -> list[Snapshot]:
        """
        Derives a new set of nodes (Snapshot) given a change in total node value (Tsn).
        
        This returns a list rather than a single Snapshot because intermediate Tsns will be inferred
        when there are insufficient funds in the given Snapshot to complete the Tsn.
        (ie if the current total is insufficient, a new transaction / snapshot that adds the funds is created)
        """

        ss = snapshot or Snapshot(nodes=[])
        snaps = []

        src = tsn.src_value
        dst = tsn.dst_value

        # If no src, return snapshot with single node
        if tsn.src_value is None:
            node = Node(value=dst, tsn=tsn)
            snaps.append(Snapshot(tsn=tsn, nodes=[node]))
            return snaps

        # If insufficient funds, create generative transaction
        total_src = ss.totals.get(src.currency, 0.0)
        if total_src < src.quantity:
            gen_val = Value(
                currency = src.currency,
                quantity = src.quantity - total_src
            )
            gen_tsn = Tsn(
                date=tsn.date,
                dst_value=gen_val
            )
            nodes = ss.nodes.copy() + [Node(value=gen_val, tsn=gen_tsn)]
            ss = Snapshot(tsn=gen_tsn, nodes=nodes)
            snaps.append(ss)

        # Deduct from current ss nodes and create new Snapshot
        new_nodes = []
        rem = src.quantity
        cvn_rate = dst.quantity / src.quantity

        for node in ss.nodes:
            # Ignore currencies other than the deducation currency
            if node.value.currency != src.currency:
                new_nodes.append(node)
                continue
            
            # Ignore if nothing left to deduct
            if rem == 0:
                new_nodes.append(node)
                continue
            
            # Deduct
            if rem >= node.value.quantity:
                # Full deduction, replace with single node
                cvn_value = Value(
                    quantity = node.value.quantity * cvn_rate,
                    currency = dst.currency
                )
                cvn_node = Node(value=cvn_value, tsn=tsn)
                node.add_child(cvn_node)
                new_nodes.append(cvn_node)

                rem -= node.value.quantity
            else:
                # Partial deduction, create conversion node and remainder node
                cvn_value = Value(quantity=rem*cvn_rate, currency=dst.currency)
                cvn_node = Node(value=cvn_value, tsn=tsn)
                node.add_child(cvn_node)

                leftover = node.value.quantity - rem
                rem_node = Node(
                    value = Value(quantity=leftover, currency=src.currency),
                    tsn=tsn
                )
                node.add_child(rem_node)

                rem = 0

        assert rem == 0, rem

        ss = Snapshot(nodes=new_nodes, tsn=tsn)
        snaps.append(ss)

        return snaps