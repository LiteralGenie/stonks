from dataclasses import dataclass, field

from .value import Value


@dataclass
class Tsn:
    date: float
    fee: Value
    dst_value: Value | None = None
    src_value: Value | None = None
    meta: dict = field(default_factory=dict)
