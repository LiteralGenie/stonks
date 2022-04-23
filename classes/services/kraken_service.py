import base64
import hashlib
import hmac
import logging
import time
import urllib.parse

import requests
from classes.json_cache import JsonCache

from config import secrets, paths
from utils.misc import limit

LOG = logging.getLogger(__name__)

class KrakenService:
    API_URL = 'https://api.kraken.com'
    CACHE_PATH = paths.CACHE_DIR / 'kraken.json'

    def fetch_history(self):
        cache_file = JsonCache(self.CACHE_PATH, default=[])
        trades = cache_file.load()
        
        while True:
            payload = dict(trades=True, ofs=len(trades))
            LOG.info(f'fetching kraken trades with offset {len(trades)}')

            resp = self._post('/0/private/TradesHistory', payload)
            results = resp['result']['trades']

            if len(trades) == resp['result']['count']:
                break

            for id, data in results.items():
                data['id'] = id
            results = sorted(list(results.values()), key=lambda trade: trade['time'])

            trades.extend(results)

        trades = list(reversed(trades))
        cache_file.dump(trades)
        return trades

    @limit(calls=1, period=2, scope='gecko')
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
    resp = KrakenService().fetch_history()
    pass
