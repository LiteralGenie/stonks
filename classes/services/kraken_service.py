import base64
import hashlib
import hmac
import logging
import time
import urllib.parse

import requests
from classes.json_cache import JsonCache
from classes.parser import Tsn, Value
from config import paths, secrets
from utils.misc import limit, memoize

LOG = logging.getLogger(__name__)

class KrakenService:
    API_URL = 'https://api.kraken.com'
    TRADE_CACHE = JsonCache(paths.CACHE_DIR / 'kraken' / 'trades.json', default=[])
    PAIR_CACHE = JsonCache(paths.CACHE_DIR / 'kraken' / 'pairs.json', default={})

    def fetch_transactions(self) -> list[Tsn]:
        trades = self._fetch_trades()
        tsns = []

        for trd in trades:
            pair = self._fetch_pair(trd['pair'])
            src, dst = self._get_src_dst(trd, pair)

            tsns.append(Tsn(
                date = trd['time'],
                src_value = src,
                src_market = "kraken",
                dst_value = dst,
                dst_market = "kraken",
                fee = Value(quantity=trd['fee'], currency=pair['fee_volume_currency'])
            ))
        
        return tsns

    def _get_src_dst(self, trade: dict, pair: dict) -> tuple[Value, Value]:
        quote = pair['quote']
        base = pair['base']

        if trade['type'] == 'buy':
            src = Value(quantity=float(trade['cost']), currency=quote)
            dst = Value(quantity=float(trade['vol']), currency=base)
        else:
            src = Value(quantity=float(trade['vol']), currency=base)
            dst = Value(quantity=float(trade['cost']), currency=quote)

        return src, dst

    _PAIRS = PAIR_CACHE.load()
    def _fetch_pair(self, name: str) -> dict:
        fetch = lambda: requests.get(self.API_URL + '/0/public/AssetPairs').json()
        fetch = limit(calls=1, period=2, scope='kraken')(fetch)

        if name not in self._PAIRS:
            LOG.info(f'pair [{name}] not found, updating cache')

            self._PAIRS = fetch()['result']
            assert name in self._PAIRS

            self.PAIR_CACHE.dump(self._PAIRS)
        
        return self._PAIRS[name]

    def _fetch_trades(self) -> list:
        trades = self.TRADE_CACHE.load()
        
        while True:
            payload = dict(trades=True, ofs=len(trades))
            LOG.info(f'fetching kraken trades with offset {len(trades)}')

            resp = self._post('/0/private/TradesHistory', payload)
            results = resp['result']['trades']

            if len(trades) == resp['result']['count']:
                break

            for id, data in results.items():
                data['id'] = id
            results = sorted(list(results.values()), key=lambda trade: trade['time'], reverse=True)

            trades.extend(results)

        self.TRADE_CACHE.dump(trades)
        trades = list(reversed(trades))
        return trades

    @memoize(paths.CACHE_DIR / 'kraken' / 'prices.json')
    @limit(calls=1, period=2, scope='kraken')
    def _fetch_coin_price(self, id: str, date: str) -> dict:
        LOG.info(f'fetching price for {id} at {date}')
        ep = self.api_url / 'coins' / id % { date: date }
        return self.session.get(str(ep)).json()

    @limit(calls=1, period=2, scope='kraken')
    def _post(self, path: str, data: dict):
        data['nonce'] = str(int(time.time() * 1000))

        headers = {}
        headers['API-Key'] = secrets.KRAKEN_API_KEY
        headers['API-Sign'] = self._sign(path, data)           

        resp = requests.post(self.API_URL + path, headers=headers, data=data)
        resp = resp.json()
        return resp

    def _sign(self, path: str, data):
        postdata = urllib.parse.urlencode(data)
        encoded = (str(data['nonce']) + postdata).encode()
        message = path.encode() + hashlib.sha256(encoded).digest()

        mac = hmac.new(base64.b64decode(secrets.KRAKEN_PRIVATE_KEY), message, hashlib.sha512)
        sigdigest = base64.b64encode(mac.digest())
        return sigdigest.decode()

if __name__ == '__main__':
    import config.configure_logging
    resp = KrakenService().fetch_transactions()
    pass
