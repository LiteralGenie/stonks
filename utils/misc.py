import os


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

            with open(fp, 'a+', encoding='utf-8') as file:
                try: cache = json.load(file)
                except json.JSONDecodeError: cache = {}
    
                if hash not in cache:
                    result = f(*args, **kwargs)
                    cache[hash] = result
                
                json.dump(cache, file)
            
            return cache[hash]
        return wrapper
    return decorator
