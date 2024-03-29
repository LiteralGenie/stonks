from dataclasses import dataclass
import json
import os
from pathlib import Path
from typing import Callable, Union


@dataclass
class JsonCache:
    fp: Union[str, Path]
    default: Union[Callable[[], list | dict], list | dict]
    encoding = "utf-8"

    def load(self) -> list | dict:
        import json

        if not isinstance(self.fp, Path):
            self.fp = Path(self.fp)
        os.makedirs(self.fp.parent, exist_ok=True)

        try:
            with open(self.fp, "r+", encoding=self.encoding) as file:
                result = json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            if callable(self.default):
                result = self.default()
            else:
                result = self.default

        return result

    def dump(self, data: Union[list, dict]):
        with open(self.fp, "w+", encoding=self.encoding) as file:
            json.dump(data, file, indent=2)
