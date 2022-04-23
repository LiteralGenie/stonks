from classes.services import GeckoService

if __name__ == '__main__':
    import time
    ds = GeckoService()
    result = ds.get_rate(time.time()-86400*2, 'cosmos', 'usd')
    pass