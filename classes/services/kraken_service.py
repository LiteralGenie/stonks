import base64
import hashlib
import hmac
import logging
import time
import urllib.parse

import requests
from classes.parser import Tsn, Value
from classes.json_cache import JsonCache

from config import secrets, paths
from utils.misc import limit

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

            if trd['type'] == 'buy':
                src_value = Value(quantity=trd['cost'], currency=pair['quote'])
                dst_value = Value(quantity=trd['vol'], currency=pair['base'])
            else:
                src_value = Value(quantity=trd['vol'], currency=pair['base'])
                dst_value = Value(quantity=trd['cost'], currency=pair['quote'])
                

            tsns.append(Tsn(
                date = trd['time'],
                src_value = src_value,
                src_market = "kraken",
                dst_value = dst_value,
                dst_market = "kraken",
                fee = Value(quantity=trd['fee'], currency=pair['fee_volume_currency'])
            ))
        
        return tsns

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
