import base64
import hashlib
import hmac
import time
import urllib.parse

import requests

from config import secrets


class KrakenService:
    API_URL = 'https://api.kraken.com'

    def fetch_history(self):
        resp = self._post('/0/private/TradesHistory', dict(trades=True))
        return resp

    def _post(self, path: str, data: dict):
        data['nonce'] = str(int(time.time() * 1000))

        headers = {}
        headers['API-Key'] = secrets.KRAKEN_API_KEY
        headers['API-Sign'] = self._sign(path, data)           

        # data = urllib.parse.urlencode(data)
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
