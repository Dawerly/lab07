"""Типізований запис рейтингу відправлень."""

from dataclasses import dataclass
from functools import total_ordering
from math import isfinite


@total_ordering
@dataclass(frozen=True, slots=True, eq=False)
class ShipmentRank:
    id: int
    weight: float
    distance: float
    priority: str
    cost: float
    adjusted_cost: float

    def __post_init__(self) -> None:
        if (
            self.id < 0
            or self.weight <= 0
            or self.priority not in {"high", "normal", "low"}
        ):
            raise ValueError("Некоректний id, weight або priority")
        if any(
            not isfinite(x) or x < 0
            for x in (self.weight, self.distance, self.cost, self.adjusted_cost)
        ):
            raise ValueError("Числові поля мають бути скінченними й невід'ємними")

    def rank_key(self) -> tuple[float, int]:
        return -self.adjusted_cost, self.id

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ShipmentRank):
            return NotImplemented
        return self.rank_key() == other.rank_key()

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, ShipmentRank):
            return NotImplemented
        return self.rank_key() < other.rank_key()
