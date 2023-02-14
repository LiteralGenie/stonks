from datetime import datetime, timedelta

import config.configure_logging
from classes.services.kraken_service import KrakenService
from classes.services.gecko_service import GeckoService
import logging
import time
from tools.calc_wallet import Wallet, HistoryParser, Deduction, Wad, Value

LOG = logging.getLogger(__name__)

K2G_ID_MAP = {
    "ADA": "cardano",
    "ALGO": "algorand",
    "ATOM": "cosmos",
    "ATOM.S": "cosmos",
    "AAVE": "aave",
    "BAL": "balancer",
    "BAT": "basic-attention-token",
    "BICO": "biconomy",
    "DOT": "polkadot",
    "FIL": "filecoin",
    "KEEP": "keep-network",
    "MATIC": "matic-network",
    "NANO": "nano",
    "OMG": "omisego",
    "OXT": "orchid-protocol",
    "SC": "siacoin",
    "SCRT": "secret",
    "SOL": "solana",
    "SUSHI": "sushi",
    "UNI": "uniswap",
    "USD": "usd",
    "USDC": "usd-coin",
    "XETC": "ethereum-classic",
    "XETH": "ethereum",
    "XTZ": "tezos",
    "XXBT": "bitcoin",
    "XXMR": "monero",
    "YFI": "yearn-finance",
}

if __name__ == "__main__":
    kraken = KrakenService()
    history = kraken.fetch_history()
    tsns = HistoryParser.parse_history(history)
    wallet = Wallet()
    [wallet.transact(tsn) for tsn in tsns]

    deductions: list[Deduction] = []
    for stack in wallet.stacks.values():
        for wad in stack.wads:
            for ddt in wad.deductions:
                deductions.append(ddt)

    staking_rewards: list[Wad] = []
    for stack in wallet.stacks.values():
        for wad in stack.wads:
            if wad.tsn.meta.get("type") == "staking":
                staking_rewards.append(wad)

    balance: dict[str, list[Wad]] = dict()
    for stack in wallet.stacks.values():
        for wad in stack.wads:
            if wad.available.quantity > 0:
                balance.setdefault(wad.available.currency, [])
                balance[wad.available.currency].append(wad)

    ###

    gecko = GeckoService()

    gains = dict()
    deductions.sort(key=lambda ddt: ddt.tsn.date)
    for ddt in deductions:
        if ddt.dst:
            src_val = ddt.value
            assert src_val.currency in K2G_ID_MAP, src_val.currency

            val = ddt.dst.total
            assert val.currency in K2G_ID_MAP, val.currency

            (src_rate, time_diff) = gecko.get_rate(
                ddt.src.tsn.date, K2G_ID_MAP[src_val.currency], "usd"
            )
            if abs(time_diff) > 2 * 86400:
                (src_rate, time_diff) = gecko.get_rate(
                    ddt.src.tsn.date, K2G_ID_MAP[src_val.currency], "usd", live=True
                )
                assert abs(time_diff) <= 86400

            (rate, time_diff) = gecko.get_rate(
                ddt.dst.tsn.date, K2G_ID_MAP[val.currency], "usd"
            )
            if abs(time_diff) > 2 * 86400:
                (rate, time_diff) = gecko.get_rate(
                    ddt.dst.tsn.date, K2G_ID_MAP[val.currency], "usd", live=True
                )
                assert abs(time_diff) <= 86400

            src_usd = src_val.quantity * src_rate
            dst_usd = val.quantity * rate

            diff = dst_usd - src_usd
            dt = datetime.fromtimestamp(ddt.dst.tsn.date)
            gains.setdefault(dt.year, [])
            gains[dt.year].append(diff)

            if abs(diff) > 1:
                src_dt = datetime.fromtimestamp(ddt.src.tsn.date)
                diff_text = f"{dst_usd - src_usd:+.2f}"
                diff_text = f"{diff_text:>8}"
                print(
                    f"{src_dt.strftime('%Y-%m-%d')} | {dt.strftime('%Y-%m-%d')} | {src_val.quantity:>8.3f} {src_val.currency:>5} -> {val.quantity:>8.3f}  {val.currency:<8} | ${src_usd:07.2f} -> ${dst_usd:07.2f}\t| {diff_text}"
                )

    print("\ngains without staking")
    for year, gs in gains.items():
        print(f"{year} = {sum(gs):.2f}")

    for reward in staking_rewards:
        (rate, time_diff) = gecko.get_rate(
            reward.tsn.date, K2G_ID_MAP[reward.total.currency], "usd"
        )
        if abs(time_diff) > 2 * 86400:
            (rate, time_diff) = gecko.get_rate(
                reward.tsn.date, K2G_ID_MAP[reward.total.currency], "usd", live=True
            )
            assert abs(time_diff) <= 86400

        val_usd = rate * reward.total.quantity
        dt = datetime.fromtimestamp(reward.tsn.date)
        gains.setdefault(dt.year, [])
        gains[dt.year].append(val_usd)

    print("\ngains with staking")
    for year, gs in gains.items():
        print(f"{year} = {sum(gs):.2f}")

    print("\nunrealized gains")
    unrealized_gains = dict()
    for stack in balance.values():
        for wad in stack:
            val: Value = wad.available
            assert val.currency in K2G_ID_MAP, val.currency

            # current value
            (current_rate, time_diff) = gecko.get_rate(
                time.time(), K2G_ID_MAP[val.currency], "usd"
            )
            if abs(time_diff) > 2 * 86400:
                (current_rate, time_diff) = gecko.get_rate(
                    time.time(), K2G_ID_MAP[val.currency], "usd", live=True
                )
                assert time_diff <= 86400
            current_value = current_rate * val.quantity

            # cost basis
            (original_rate, time_diff) = gecko.get_rate(
                wad.tsn.date, K2G_ID_MAP[val.currency], "usd"
            )
            if abs(time_diff) > 2 * 86400:
                (original_rate, time_diff) = gecko.get_rate(
                    wad.tsn.date, K2G_ID_MAP[val.currency], "usd", live=True
                )
                assert time_diff <= 86400
            original_value = original_rate * val.quantity

            net_usd = current_value - original_value
            dt_orignal = datetime.fromtimestamp(wad.tsn.date)
            elapsed = datetime.now() - dt_orignal
            if abs(net_usd) > 2:
                print(
                    f"\t{net_usd:.2f} ({val.currency})\t{elapsed.days} days ago on {dt_orignal.strftime('%Y-%m-%d')}"
                )

            unrealized_gains.setdefault(val.currency, [])
            unrealized_gains[val.currency].append([original_value, current_value])

    for currency, gains in unrealized_gains.items():
        total_net = 0
        total_original = 0
        total_current = 0
        for [original, current] in gains:
            net = current - original

            total_original += original
            total_current += current
            total_net += net

        if abs(total_net) > 0.5:
            print(
                f"{currency:<5} | {total_net:>9.2f} from {total_current:>9.2f} bought at {total_original:>9.2f}"
            )
