import logging
from datetime import datetime

import requests
from classes.json_cache import JsonCache
from config import paths
from utils.misc import limit, memoize
from yarl import URL

from .rate_service import RateService

LOG = logging.getLogger(__name__)

class GeckoService(RateService):
    session: requests.Session
    api_url = URL('https://api.coingecko.com/api/v3')

    LIST_CACHE = JsonCache(paths.CACHE_DIR / 'coingecko' / 'coin_list.json', default=dict())

    def __init__(self) -> None:
        super().__init__()
        self.session = requests.session()

    def get_rate(self, timestamp, src: str, dst: str):
        if src == dst:
            return 1
        if src == 'usd':
            return 1 / self.get_rate(timestamp, dst, src)

        dst_symbol = self.fetch_coin_symbol(dst)
        date = self._epoch_to_date(timestamp)
        resp = self._fetch_coin_price(src, date)
        return resp['market_data']['current_price'][dst_symbol]

    @memoize(paths.CACHE_DIR / 'coingecko' / 'coin_prices.json')
    @limit(calls=1, period=1, scope='gecko')
    def _fetch_coin_price(self, id: str, date: str) -> dict:
        LOG.info(f'fetching price for {id} at {date}')
        ep = self.api_url / 'coins' / id % { date: date }
        return self.session.get(str(ep)).json()

    def _epoch_to_date(self, timestamp: float):
        return datetime.fromtimestamp(timestamp).strftime(r'%m-%d-%Y')

    _COIN_LIST = LIST_CACHE.load()
    def fetch_coin_symbol(self, id: str):
        if id in ['usd']:
            return 'usd'

        if id not in self._COIN_LIST:
            assert id in self._COIN_LIST
            self.LIST_CACHE.dump(self._COIN_LIST)
        return self._COIN_LIST[id]

    @limit(calls=1, period=1, scope='gecko')
    def _update_coin_list(self):
        LOG.info(f'updating gecko coin list because [{id}] was not found')
        ep = self.api_url / 'coins' / 'list'
        resp = self.session.get(str(ep)).json()
        self._COIN_LIST = { x['id']: x for x in resp }