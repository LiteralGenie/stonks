import logging
from datetime import datetime
from math import ceil

import requests
from decimal import Decimal
from classes.json_cache import JsonCache
from config import paths
from utils.misc import limit
from yarl import URL

from .rate_service import RateService

LOG = logging.getLogger(__name__)


class GeckoService(RateService):
    session: requests.Session
    api_url = URL("https://api.coingecko.com/api/v3")

    PRICE_CACHE = JsonCache(paths.CACHE_DIR / "gecko" / "prices.json", default={})
    price_data: dict = PRICE_CACHE.load()

    def __init__(self) -> None:
        super().__init__()
        self.session = requests.session()

    # timestamp is utc
    def get_rate(
        self, timestamp, src: str, dst: str, live=False
    ) -> tuple[Decimal, float]:
        if src == dst:
            return (Decimal(1), 0)

        if live or self.price_data.get(src, dict()).get(dst) is None:
            self._fetch_market_chart(src, dst, timestamp)
            self.PRICE_CACHE.dump(self.price_data)

        return self._get_closest_rate(timestamp, src, dst)

    def _get_closest_rate(
        self, timestamp: float, src: str, dst: str
    ) -> tuple[Decimal, float]:
        data: dict = self.price_data[src][dst]["prices"]

        cvt = lambda ts_str: float(ts_str) / 1000
        closest_key = min(data.keys(), key=lambda ts: abs(timestamp - cvt(ts)))

        return (Decimal(data[closest_key]), timestamp - cvt(closest_key))

    @limit(calls=1, period=7, scope="gecko")
    def _fetch_market_chart(self, src: str, dst: str, timestamp: float) -> dict:
        max_age_days = ceil((datetime.timestamp(datetime.utcnow()) - timestamp) / 86400)
        ep = (
            self.api_url
            / "coins"
            / src
            / "market_chart"
            % {"days": str(max_age_days), "vs_currency": dst}
        )
        LOG.info(f"Fetching price for {src} / {dst} -- {ep}")

        resp = self.session.get(str(ep)).json()
        assert "error" not in resp

        self.price_data.setdefault(src, dict()).setdefault(
            dst, dict(prices=dict(), market_caps=dict(), total_volumes=dict())
        )
        tgt = self.price_data[src][dst]
        for k in tgt:
            update = {d[0]: d[1] for d in resp[k]}
            tgt[k].update(update)

        self.PRICE_CACHE.dump(self.price_data)
        return self.price_data[src][dst]
