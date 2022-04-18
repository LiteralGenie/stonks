from datetime import datetime

import requests
from .rate_service import RateService
from config import paths
from utils.misc import limit, method_cache
from yarl import URL


class GeckoService(RateService):
    session: requests.Session
    api_url = URL('https://api.coingecko.com/api/v3')

    def __init__(self) -> None:
        super().__init__()
        self.session = requests.session()

    def get_rate(self, timestamp, src, dst):
        date = self._epoch_to_date(timestamp)
        resp = self._fetch_coin_price(src, date)
        return resp['market_data']['current_price'][dst]

    @limit(calls=1, period=1, scope='gecko')
    @method_cache(paths.CACHE_DIR / 'coingecko' / 'coin_prices.json')
    def _fetch_coin_price(self, coin: str, date: str) -> dict:
        ep = self.api_url / 'coins' / coin % { date: date }
        return self.session.get(str(ep)).json()

    def _epoch_to_date(self, timestamp: float):
        return datetime.fromtimestamp(timestamp).strftime(r'%m-%d-%Y')
