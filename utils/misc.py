import functools


def method_cache(fp: str):
    import functools
    import json
    from pathlib import Path

    fp: Path = Path(fp)

    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            hash = list(args[1:]) + sorted(kwargs.items(), key=lambda k,v: k)
            hash = str(hash)

            if not fp.parent.exists():
                fp.parent.mkdir(parents=True, exist_ok=True)

            with open(fp, 'r+', encoding='utf-8') as file:
                try: cache = json.load(file)
                except json.JSONDecodeError: cache = {}
    
                if hash not in cache:
                    result = f(*args, **kwargs)
                    cache[hash] = result
                
            with open(fp, 'w+', encoding='utf-8') as file:
                json.dump(cache, file, indent=2)
            
            return cache[hash]
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

            while len(history) > 0:
                if (now - history[0]) > period:
                    history.pop(0)
            
            if len(history) >= calls:
                oldest = history[0]
                time.sleep(period - oldest)
                history.pop(0)

            history.append(now)

            return f(*args, **kwargs)
        return wrapper
    return decorator
