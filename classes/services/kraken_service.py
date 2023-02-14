import base64
import datetime
import hashlib
import hmac
import logging
import time
import urllib.parse
from dataclasses import dataclass
from typing import Literal
from decimal import Decimal

import requests
from classes.json_cache import JsonCache
from classes.parser import Tsn, Value
from config import paths, secrets
from utils.misc import limit, memoize

LOG = logging.getLogger(__name__)


class KrakenService:
    API_URL = "https://api.kraken.com"
    HISTORY_CACHE = JsonCache(paths.CACHE_DIR / "kraken" / "history.json", default=[])

    def fetch_history(self):
        history = [HistoryItem.from_raw(x) for x in self._fetch_history()]
        return history

    def _fetch_history(self):
        history: list = self.HISTORY_CACHE.load()
        return history

        end = time.time()
        while True:
            payload = dict(trades=True, end=end)
            LOG.info(
                f"fetching kraken history before {datetime.datetime.fromtimestamp(end)}"
            )

            resp = self._post("/0/private/Ledgers", payload)
            results = resp["result"]["ledger"]

            newItems = {
                k: v
                for k, v in results.items()
                if not any(k == y["id"] for y in history)
            }
            if not len(newItems):
                break

            for id, data in newItems.items():
                data["id"] = id
            newItems = sorted(
                list(newItems.values()), key=lambda trade: trade["time"], reverse=True
            )

            history += newItems
            end = history[-1]["time"]

        self.HISTORY_CACHE.dump(history)
        history = list(reversed(history))
        return history

    def _get_src_dst(self, trade: dict, pair: dict) -> tuple[Value, Value]:
        quote = pair["quote"]
        base = pair["base"]

        if trade["type"] == "buy":
            src = Value(quantity=float(trade["cost"]), currency=quote)
            dst = Value(quantity=float(trade["vol"]), currency=base)
        else:
            src = Value(quantity=float(trade["vol"]), currency=base)
            dst = Value(quantity=float(trade["cost"]), currency=quote)

        return src, dst

    @memoize(paths.CACHE_DIR / "kraken" / "prices.json")
    @limit(calls=1, period=2, scope="kraken")
    def _fetch_coin_price(self, id: str, date: str) -> dict:
        LOG.info(f"fetching price for {id} at {date}")
        ep = self.api_url / "coins" / id % {date: date}
        return self.session.get(str(ep)).json()

    @limit(calls=1, period=5, scope="kraken")
    def _post(self, path: str, data: dict):
        data["nonce"] = str(int(time.time() * 1000))

        headers = {}
        headers["API-Key"] = secrets.KRAKEN_API_KEY
        headers["API-Sign"] = self._sign(path, data)

        resp = requests.post(self.API_URL + path, headers=headers, data=data)
        resp = resp.json()
        return resp

    def _sign(self, path: str, data):
        postdata = urllib.parse.urlencode(data)
        encoded = (str(data["nonce"]) + postdata).encode()
        message = path.encode() + hashlib.sha256(encoded).digest()

        mac = hmac.new(
            base64.b64decode(secrets.KRAKEN_PRIVATE_KEY), message, hashlib.sha512
        )
        sigdigest = base64.b64encode(mac.digest())
        return sigdigest.decode()


@dataclass
class HistoryItem:
    aclass: str
    amount: Decimal
    asset: str
    balance: Decimal
    fee: Decimal
    refid: str
    time: float
    type: Literal["deposit", "withdrawal", "spend", "receive", "staking"]
    subtype: str
    id: str

    @classmethod
    def from_raw(cls, d: dict) -> "HistoryItem":
        d = d.copy()
        d["amount"] = Decimal(d["amount"])
        d["balance"] = Decimal(d["balance"])
        d["fee"] = Decimal(d["fee"])
        return cls(**d)

    def copy(self) -> "HistoryItem":
        return HistoryItem(**self.__dict__)


if __name__ == "__main__":
    import config.configure_logging

    resp = KrakenService().fetch_transactions()
    pass
