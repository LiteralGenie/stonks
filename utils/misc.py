import functools
from typing import Union
from pathlib import Path

from classes.json_cache import JsonCache


def memoize(fp: Union[Path, str]):
    import functools

    cache_file = JsonCache(fp, default=dict())

    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            hash = list(args[1:]) + sorted(kwargs.items(), key=lambda k,v: k)
            hash = str(hash)

            if not fp.parent.exists():
                fp.parent.mkdir(parents=True, exist_ok=True)

            data = cache_file.load()
    
            if hash not in data:
                result = f(*args, **kwargs)
                data[hash] = result

            cache_file.dump(data)

            return data[hash]
        return wrapper
    return decorator


CALL_LOG = dict()
def limit(calls: int, period: float = 1, scope = ''):
    import time

    CALL_LOG.setdefault(scope, [])

    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            history = CALL_LOG[scope]
            now = time.time()

            while True:
                if len(history) == 0:
                    break

                elapsed = now - history[0]
                if elapsed > period:
                    history.pop(0)
                else:
                    break
            
            if len(history) >= calls:
                oldest = history[0]
                elapsed = now - oldest
                rem = period - elapsed
                if rem >= 0:
                    time.sleep(rem)
                    history.pop(0)

            result = f(*args, **kwargs)
            history.append(time.time())
            return result
        return wrapper
    return decorator
