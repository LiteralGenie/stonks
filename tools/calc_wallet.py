from dataclasses import dataclass, field

import config.configure_logging
from classes.parser.tsn import Tsn, Value
from classes.services.kraken_service import HistoryItem, KrakenService
import logging
import datetime

LOG = logging.getLogger(__name__)


class HistoryParser:
    CURRENCY_MAP = {"ZUSD": "USD", "USD.HOLD": "USD", "ATOM.S": "ATOM"}

    @classmethod
    def parse_history(cls, history: list[HistoryItem]) -> list[Tsn]:
        history = sorted(history, key=lambda it: it.time)

        # Create transactions
        tsns = []
        idx = -1
        while True:
            idx += 1
            if idx == len(history):
                break
            item: HistoryItem = history[idx]
            item = cls._map_currency(item)

            if item.asset in cls.CURRENCY_MAP:
                item.asset = cls.CURRENCY_MAP[item.asset]

            match item.type:
                case "deposit":
                    assert item.amount > 0

                    tsns.append(
                        Tsn(
                            date=item.time,
                            dst_value=Value(item.amount, item.asset),
                            fee=Value(item.fee, item.asset),
                            meta=dict(type="deposit", id=item.refid),
                        )
                    )
                case "withdrawal":
                    assert item.amount < 0

                    tsns.append(
                        Tsn(
                            date=item.time,
                            src_value=Value(-1 * item.amount, item.asset),
                            fee=Value(item.fee, item.asset),
                            meta=dict(type="withdrawal", id=item.refid),
                        )
                    )
                case "spend":
                    assert item.amount < 0

                    idx_next = idx + 1
                    assert idx_next < len(history)
                    item_next = cls._map_currency(history[idx_next])
                    assert item.refid == item_next.refid
                    assert item_next.amount > 0

                    assert item.fee == 0 or item_next.fee == 0
                    if item.fee > 0:
                        fee = Value(quantity=item.fee, currency=item.asset)
                    else:
                        fee = Value(quantity=item_next.fee, currency=item_next.asset)

                    tsns.append(
                        Tsn(
                            date=item.time,
                            src_value=Value(-1 * item.amount, item.asset),
                            dst_value=Value(item_next.amount, item_next.asset),
                            fee=fee,
                            meta=dict(type="trade", id=item.refid),
                        )
                    )

                    idx += 1
                case "receive":
                    raise ValueError
                case "staking":
                    assert item.amount > 0

                    tsns.append(
                        Tsn(
                            date=item.time,
                            dst_value=Value(item.amount, item.asset),
                            fee=Value(item.fee, item.asset),
                            meta=dict(type="staking", id=item.refid),
                        )
                    )
                case "trade":
                    idx_next = idx + 1
                    assert idx_next < len(history)

                    item_next = cls._map_currency(history[idx_next])
                    if item.refid != item_next.refid:
                        LOG.warning(
                            f"Skipping. No pair for {item.asset} {item.amount} ({item.refid})."
                        )
                        continue
                    else:
                        assert item.amount < 0
                        assert item_next.amount > 0

                    assert item.fee == 0 or item_next.fee == 0
                    if item.fee > 0:
                        fee = Value(quantity=item.fee, currency=item.asset)
                    else:
                        fee = Value(quantity=item_next.fee, currency=item_next.asset)

                    tsns.append(
                        Tsn(
                            date=item.time,
                            src_value=Value(-1 * item.amount, item.asset),
                            dst_value=Value(item_next.amount, item_next.asset),
                            fee=fee,
                            meta=dict(type="trade", id=item.refid),
                        )
                    )

                    idx += 1
                case "transfer":
                    pass
                case default:
                    raise ValueError

        return tsns

    @classmethod
    def _map_currency(cls, item: HistoryItem) -> HistoryItem:
        item = item.copy()
        new_val = cls.CURRENCY_MAP.get(item.asset)
        if new_val:
            item.asset = new_val
        return item


# Create currency stacks
@dataclass
class Deduction:
    value: Value
    tsn: Tsn
    src: "Wad"
    dst: "Wad | None" = None


@dataclass
class Wad:
    total: Value
    tsn: Tsn

    deductions: list[Deduction] = field(default_factory=list)
    src: "Wad | None" = None

    def deduct(self, value: Value, tsn: Tsn, dst: "Wad | None" = None) -> None:
        assert value.currency == self.total.currency
        assert value.quantity <= self.available.quantity

        self.deductions.append(
            Deduction(
                value=Value(quantity=value.quantity, currency=value.currency),
                tsn=tsn,
                src=self,
                dst=dst,
            )
        )

    @property
    def available(self) -> Value:
        total_deductions = sum(x.value.quantity for x in self.deductions)
        result = self.total.quantity - total_deductions
        return Value(quantity=result, currency=self.total.currency)

    def __repr__(self):
        # Default __repr__ was slowing down debugger
        a = self.available
        return f"{a.currency} {a.quantity:.3f} / {self.total.quantity:.3f}"


@dataclass
class Stack:
    currency: str
    wads: list[Wad] = field(default_factory=list)

    def pull(self, value: Value, tsn: Tsn, create_dst=True) -> list[Wad]:
        """
        @todo: instead of null checks, make a sep fn
        """
        assert value.currency == self.currency

        dst = tsn.dst_value
        if create_dst:
            assert dst is not None

        # Get non-zero wads
        rem = value.quantity
        tgts: list[Wad] = []
        for wad in self.wads:
            available = wad.available.quantity

            if available > 0:
                tgts.append(wad)
                rem -= min(rem, available)

            if rem == 0:
                break
        else:
            if rem > 10**-3:
                raise ValueError(
                    f"Attempted to deduct {value.quantity} {value.currency} but stack only contains {value.quantity - rem} {self.currency}"
                )

        # Deduct
        result: list[Wad] = []
        rem = value.quantity
        for tgt in tgts:
            amount = min(rem, tgt.available.quantity)

            if create_dst:
                val = (amount * dst.quantity) / tsn.src_value.quantity  # type: ignore
                new_wad = Wad(total=Value(quantity=val, currency=dst.currency), tsn=tsn, src=tgt)  # type: ignore
                result.append(new_wad)
            else:
                new_wad = None

            tgt.deduct(
                value=Value(quantity=amount, currency=self.currency),
                tsn=tsn,
                dst=new_wad,
            )

            rem -= amount
            if rem == 0:
                break
            elif rem < 0:
                raise ValueError

        return result

    def push(self, x: Value | Wad, tsn: Tsn) -> None:
        if isinstance(x, Value):
            x = Wad(total=x, tsn=tsn)
        assert x.total.currency == self.currency
        self.wads.append(x)

    @property
    def available(self) -> Value:
        quantity = sum(x.available.quantity for x in self.wads)
        return Value(quantity=quantity, currency=self.currency)


@dataclass
class Wallet:
    tsns: list[Tsn] = field(default_factory=list)
    stacks: dict[str, Stack] = field(default_factory=dict)

    def transact(self, tsn: Tsn) -> None:
        src_stack: Stack | None = None
        if tsn.src_value:
            src_stack = self.get_stack(tsn.src_value.currency)

        dst_stack: Stack | None = None
        if tsn.dst_value:
            dst_stack = self.get_stack(tsn.dst_value.currency)

        match tsn.meta.get("type"):
            case "trade":
                wads = src_stack.pull(tsn.src_value, tsn=tsn)  # type: ignore
                for new_wad in wads:
                    dst_stack.push(new_wad, tsn=tsn)  # type: ignore
            case "deposit":
                dst_stack.push(tsn.dst_value, tsn=tsn)  # type: ignore
            case "withdrawal":
                src_stack.pull(tsn.src_value, tsn=tsn, create_dst=False)  # type: ignore
            case "staking":
                dst_stack.push(tsn.dst_value, tsn=tsn)  # type: ignore

        fee_stack = self.get_stack(tsn.fee.currency)
        if tsn.fee.quantity > 0:
            fee_stack.pull(tsn.fee, tsn=tsn, create_dst=False)

        self.tsns.append(tsn)

    def get_stack(self, currency: str) -> Stack:
        if currency not in self.stacks:
            self.stacks[currency] = Stack(currency)
        return self.stacks[currency]


if __name__ == "__main__":
    kraken = KrakenService()
    history = kraken.fetch_history()
    tsns = HistoryParser.parse_history(history)

    wallet = Wallet()
    for tsn in tsns:
        dt = datetime.datetime.fromtimestamp(tsn.date)
        wallet.transact(tsn)

    print(wallet)
