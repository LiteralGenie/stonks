from pathlib import Path


ROOT_DIR = Path(__file__).parent.parent

CACHE_DIR = ROOT_DIR / 'cache'
DATA_DIR = ROOT_DIR / 'data'


for dir in [ROOT_DIR, CACHE_DIR, DATA_DIR]:
    dir.mkdir(exist_ok=True, parents=True)
