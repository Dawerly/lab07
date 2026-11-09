"""Чистий конвеєр: normalize → adjust → filter → sort → Top-N."""

from collections.abc import Callable, Iterable, Mapping
from dataclasses import replace
from functools import partial, reduce
from itertools import islice
from math import isfinite
from operator import attrgetter, itemgetter, methodcaller
from typing import TypeVar

from models import ShipmentRank

T = TypeVar("T")


def pipeline(value: T, *funcs: Callable[[T], T]) -> T:
    return reduce(lambda current, fn: fn(current), funcs, value)


def normalize(row: Mapping[str, object]) -> ShipmentRank:
    try:
        identifier = int(str(itemgetter("id")(row)).strip())
        numbers = [
            float(str(itemgetter(key)(row)).strip())
            for key in ("weight", "distance", "cost")
        ]
        priority = str(methodcaller("strip")(str(itemgetter("priority")(row))))
        priority = str(methodcaller("lower")(priority))
        weight, distance, cost = numbers
        return ShipmentRank(identifier, weight, distance, priority, cost, cost)
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(f"Некоректний запис відправлення: {row!r}") from error


def adjust(
    shipment: ShipmentRank, *, per_kg: float, per_km: float, factor: float
) -> ShipmentRank:
    cost = (
        shipment.cost + shipment.weight * per_kg + shipment.distance * per_km
    ) * factor
    return replace(shipment, adjusted_cost=cost)


def has_priority(shipment: ShipmentRank, *, priority: str) -> bool:
    return shipment.priority == priority


def take_top(items: Iterable[ShipmentRank], *, n: int) -> list[ShipmentRank]:
    return list(islice(items, n))


def rank_shipments(
    rows: Iterable[Mapping[str, object]],
    *,
    top: int = 3,
    priority: str = "high",
    per_kg: float = 2.0,
    per_km: float = 0.1,
    factor: float = 1.2,
) -> list[ShipmentRank]:
    if top < 0 or priority not in {"high", "normal", "low"}:
        raise ValueError("Некоректний top або priority")
    if any(not isfinite(x) or x < 0 for x in (per_kg, per_km, factor)):
        raise ValueError("Тарифи мають бути скінченними й невід'ємними")
    stages: tuple[Callable[[Iterable[ShipmentRank]], Iterable[ShipmentRank]], ...] = (
        partial(map, partial(adjust, per_kg=per_kg, per_km=per_km, factor=factor)),
        partial(filter, partial(has_priority, priority=priority)),
        partial(sorted, key=attrgetter("id")),
        partial(sorted, key=attrgetter("adjusted_cost"), reverse=True),
        partial(take_top, n=top),
    )
    normalized: Iterable[ShipmentRank] = map(normalize, rows)
    return list(pipeline(normalized, *stages))


def total_cost(shipments: Iterable[ShipmentRank]) -> float:
    return reduce(
        lambda total, shipment: total + shipment.adjusted_cost, shipments, 0.0
    )


def clean_and_rank(source: object, *, top: int = 3) -> list[ShipmentRank]:
    """Оболонка завантаження та чистого конвеєра; підтримує всі джерела loader."""
    from loaders import load_shipments

    return rank_shipments(load_shipments(source), top=top)
