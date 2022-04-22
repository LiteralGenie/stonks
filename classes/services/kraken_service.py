import base64
import hashlib
import hmac
import time
import urllib.parse

import requests

from config import secrets
from utils.misc import limit

class KrakenService:
    API_URL = 'https://api.kraken.com'

    def fetch_history(self):
        trades = []
        
        while True:
            payload = dict(trades=True, ofs=len(trades))
            
            resp = self._post('/0/private/TradesHistory', payload)
            results = resp['result']['trades']

            if len(trades) == resp['result']['count']:
                break

            for id, data in results.items():
                data['id'] = id
            results = sorted(list(results.values()), key=lambda trade: trade['time'], reverse=True)

            trades.extend(results)

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
    resp = KrakenService().fetch_history()
    pass
