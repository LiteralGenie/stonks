from dataclasses import dataclass
import dataclasses

@dataclass
class Value:
    quantity: int
    currency: str

    def __mul__(self, other) -> 'Value':
        if isinstance(other, int) or isinstance(other, float):
            q = other * self.quantity
            return dataclasses.replace(self, quantity=q)
        else:
            raise NotImplementedError
    
    def __rmul__(self, other):
        return self.__mul__(other)

    def __eq__(self, other: 'Value') -> bool:
        return all([
            self.quantity == other.quantity,
            self.currency == other.currency
        ])