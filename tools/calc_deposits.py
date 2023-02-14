from decimal import Decimal
from classes.parser.value import Value
from classes.services.gecko_service import GeckoService
from tools.calc_gains import K2G_ID_MAP
from tools.calc_wallet import HistoryParser, Wallet
from classes.services.kraken_service import KrakenService
from datetime import datetime

if __name__ == "__main__":
    gecko = GeckoService()
    kraken = KrakenService()
    history = kraken.fetch_history()
    wallet = Wallet()

    tgts = [x for x in history if x.type == "deposit" or x.type == "withdrawal"]

    net = 0
    for x in tgts:
        dt = datetime.fromtimestamp(x.time)
        amt = x.amount
        asset = HistoryParser.CURRENCY_MAP.get(x.asset, x.asset)

        raw = Value(Decimal(amt), asset)
        cvt = Value(Decimal(amt), asset)
        if cvt.currency != "USD":
            (rate, time_diff) = gecko.get_rate(x.time, K2G_ID_MAP[cvt.currency], "usd")
            if abs(time_diff) > 2 * 86400:
                (rate, time_diff) = gecko.get_rate(
                    x.time, K2G_ID_MAP[cvt.currency], "usd", live=True
                )
                assert abs(time_diff) <= 86400

            cvt = Value(cvt.quantity * rate, "USD")

        net += cvt.quantity

        msg = f'{dt.strftime("%d-%m-%Y")} {cvt.quantity:>9.2f}'
        if raw.currency != "USD":
            msg += f"\t(approx of {raw.quantity:.2f} {raw.currency})"
        print(msg)

    print(f"------\ntotal balance: {net:>10,.2f}")
