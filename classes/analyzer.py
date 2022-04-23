import dataclasses as ds

from config.services import GeckoService

from .parser import Snapshot, Tsn

FIAT = 'usd'

@ds.dataclass
class GeckoTransaction(Tsn):
    net_fiat: int = None

    def __post_init__(self):
        super().__post_init__()

        gross = self.dst_value.total * GeckoService.get_rate(self.tsn.metadata.date, self.tsn.dst.currency, FIAT)
        basis = self.src_value.basis.total * GeckoService.get_rate(self.tsn.metadata.date, self.basis.currency, FIAT)
        self.net_fiat = gross - basis
 
    @classmethod
    def from_tsn(cls, tsn: Tsn):
        return cls(ds.asdict(tsn))
 
@ds.dataclass
class GeckoKeyFrame(Snapshot):
   total_fiat_basis: int
   total_fiat: int
 
   def __post_init__(self):
       super().__post_init__()

       for node in self.nodes:
           if node.value.currency == FIAT:
               self.total_fiat += node.value.total
      
       for basis in self.total_basis.values():
           val = basis.total * GeckoService.get_rate(self.tsn.metadata.date, basis.currency, FIAT)
           self.total_fiat_basis += val
 
   def from_snapshot(cls, ss):
       return cls(**ss.as_dict())

@ds.dataclass
class GeckoFrame:
   date: int
   keyframe: GeckoKeyFrame
 
   _total_fiat_converted: int
   net_by_root: int
   net_by_ancestor: int
 
   def __post_init__(self):
       for node in self.keyframe.nodes:
           value = node.value.quantity
           if node.value.currency is not FIAT:
               value *= GeckoService.get_rate(self.date, src_currency, dst_currency)
       self._total_fiat_converted = value
 
       self.net_by_root = self._total_converted - self.keyframe.total_fiat_basis
       self.net_by_ancestor  = self.total_converted - self.total_fiat
 
class Analyzer:
   snapshots: list[Snapshot]
 
   def total_@_date(
       date: int
   ) -> Result:
       '''
       desc
       '''
      
       net = 0
       basis = 0
       closest: Snapshot = self.get_closest_ss(date, self.snapshots)
       for node in closest.nodes:
           basis += node.basis
           net += node.basis - convert_to_fiat(node.value, date)
 
   def get_closest_ss(date, snapshots):
       diffs = [abs(ss.metadata.date) - date for ss in snapshots]
       idx_min = diffs.index(min(diffs))
 
        return snapshots[idx_min]
 
   def total_in_range(start: int, end: int):
       pass
 
