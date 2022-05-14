from dataclasses import dataclass
from .value import Value

@dataclass
class Tsn:
    date: float
    dst_value: Value
    dst_market: str = ''

    src_value: Value|None = None
    src_market: str|None = None

    fee: Value|None = None