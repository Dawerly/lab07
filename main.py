"""Демонстрація завантажувача та рейтингу, варіант 14."""

from operator import attrgetter
from pathlib import Path

from core import rank_shipments, total_cost
from loaders import load_shipments


def main() -> None:
    folder = Path(__file__).parent
    json_rows = load_shipments(folder / "sample_data.json")
    csv_rows = load_shipments(folder / "sample_data.csv")
    ranked = rank_shipments(json_rows)
    print("=== ЛОГІСТИЧНІ ВІДПРАВЛЕННЯ | ВАРІАНТ 14 ===")
    print("Формула: (cost + weight * 2 + distance * 0.1) * 1.2")
    print("Пріоритет: high; Top-3")
    for shipment in ranked:
        print(
            f"#{shipment.id}: {shipment.weight:g} кг, {shipment.distance:g} км, вартість {shipment.adjusted_cost:.2f}"
        )
    print(f"Загальна скоригована вартість: {total_cost(ranked):.2f}")
    print("JSON і CSV дають однаковий рейтинг:", ranked == rank_shipments(csv_rows))
    print("Сортування через total_ordering:", [s.id for s in sorted(ranked)])
    print("Атрибути id через attrgetter:", list(map(attrgetter("id"), ranked)))
    print(
        "Порівняння першого й другого:", ranked[0] < ranked[1], ranked[0] <= ranked[1]
    )


if __name__ == "__main__":
    main()
