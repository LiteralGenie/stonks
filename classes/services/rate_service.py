from abc import ABCMeta, abstractmethod

class RateService(metaclass=ABCMeta):
    @abstractmethod
    def get_rate(self, timestamp: float, src: str, dst: str):
        pass
