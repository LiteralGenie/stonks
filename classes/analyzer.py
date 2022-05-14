from config.services import GeckoService

from .parser import Node, Snapshot, Tsn

FIAT = 'usd'

class Analyzer:    
    def get_tsn_profits(self, snapshots: list[Snapshot]):
        result = []
        for ss in snapshots:
            tsn = ss.tsn
            gross = tsn.dst_value.quantity * GeckoService.get_rate(tsn.date, tsn.dst_value.currency, FIAT)

            [children, parents] = ss.get_changes()
            basis = [p.get_basis(FIAT) for p in parents]
            basis = [b.quantity * GeckoService.get_rate(tsn.date, b.currency, FIAT) for b in basis]
            basis = sum(basis)

            diff = gross - basis
            result.append(diff)

        return result