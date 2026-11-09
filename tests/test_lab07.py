import io
import json
from copy import deepcopy
from dataclasses import asdict
from functools import partial
from operator import attrgetter, itemgetter, methodcaller
from pathlib import Path

import pytest

from core import adjust, clean_and_rank, normalize, pipeline, rank_shipments, total_cost
from loaders import load_shipments


@pytest.fixture
def rows() -> list[dict[str, object]]:
    return [
        {"id": 3, "weight": 5, "distance": 100, "priority": " HIGH ", "cost": 50},
        {"id": 1, "weight": 5, "distance": 100, "priority": "high", "cost": 50},
        {"id": 2, "weight": 10, "distance": 200, "priority": "normal", "cost": 80},
        {"id": 4, "weight": 2, "distance": 50, "priority": "high", "cost": 20},
    ]


def test_pipeline_and_partial(rows: list[dict[str, object]]) -> None:
    assert pipeline(3, lambda x: x + 1, lambda x: x * 2, lambda x: x + 1) == 9
    assert pipeline(3) == 3
    operation = partial(adjust, per_kg=2, per_km=0.1, factor=1.2)
    assert operation(normalize(rows[0])).adjusted_cost == pytest.approx(84)


def test_rank_total_and_no_mutation(rows: list[dict[str, object]]) -> None:
    original = deepcopy(rows)
    ranked = rank_shipments(iter(rows))
    assert [s.id for s in ranked] == [1, 3, 4]
    assert total_cost(ranked) == pytest.approx(202.8)
    assert rows == original
    assert [s.id for s in rank_shipments(rows, top=1)] == [1]
    assert rank_shipments(rows, top=0) == []
    assert rank_shipments([]) == [] and total_cost([]) == 0
    assert [s.id for s in rank_shipments(rows, priority="normal")] == [2]


def test_all_sources(tmp_path: Path, rows: list[dict[str, object]]) -> None:
    text = json.dumps(rows)
    csv_text = "id,weight,distance,priority,cost\n3,5,100, HIGH ,50\n1,5,100,high,50\n2,10,200,normal,80\n4,2,50,high,20\n"
    json_file, csv_file = tmp_path / "data.json", tmp_path / "data.csv"
    json_file.write_text(text, encoding="utf-8")
    csv_file.write_text(csv_text, encoding="utf-8")
    expected = rank_shipments(rows)
    for source in (
        rows,
        text,
        json_file,
        str(json_file),
        csv_file,
        str(csv_file),
        io.StringIO(text),
        io.StringIO(csv_text),
        csv_text,
    ):
        actual = rank_shipments(load_shipments(source))
        assert [asdict(s) for s in actual] == [asdict(s) for s in expected]
    for path in (json_file, csv_file):
        with path.open(encoding="utf-8") as file:
            assert clean_and_rank(file) == expected
            assert not file.closed
    loaded = load_shipments(rows)
    loaded[0]["cost"] = 999
    assert rows[0]["cost"] == 50


def test_all_comparisons_and_foreign_types(rows: list[dict[str, object]]) -> None:
    a, b = rank_shipments(rows, top=2)
    equivalent = normalize(
        {"id": 1, "weight": 1, "distance": 0, "priority": "high", "cost": 84}
    )
    assert a == equivalent and not a != equivalent
    assert a != b and a < b and a <= b and b > a and b >= a
    assert a <= equivalent and a >= equivalent
    assert sorted([b, a]) == [a, b]
    assert a.__eq__(1) is NotImplemented
    assert a.__lt__(1) is NotImplemented
    assert a != 1
    with pytest.raises(TypeError):
        _ = a < 1


def test_operator_tools(rows: list[dict[str, object]]) -> None:
    assert itemgetter("id", "weight")(rows[0]) == (3, 5)
    assert methodcaller("strip")(" high ") == "high"
    assert list(map(attrgetter("id"), rank_shipments(rows))) == [1, 3, 4]


@pytest.mark.parametrize("source", [123, (), None])
def test_unsupported_source(source: object) -> None:
    with pytest.raises(TypeError):
        load_shipments(source)


@pytest.mark.parametrize("source", ["{}", "[1]", "[{}", [1]])
def test_invalid_payload(source: object) -> None:
    with pytest.raises((ValueError, json.JSONDecodeError)):
        load_shipments(source)


@pytest.mark.parametrize(
    "change",
    [
        {"weight": 0},
        {"cost": "nan"},
        {"priority": "urgent"},
        {"id": -1},
        {"distance": -1},
    ],
)
def test_invalid_record(
    rows: list[dict[str, object]], change: dict[str, object]
) -> None:
    with pytest.raises(ValueError):
        rank_shipments([{**rows[0], **change}])


def test_invalid_options_and_empty_csv(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        rank_shipments([], top=-1)
    with pytest.raises(ValueError):
        rank_shipments([], factor=float("inf"))
    with pytest.raises(ValueError):
        load_shipments(tmp_path / "x.txt")
    assert load_shipments(io.StringIO("id,weight,distance,priority,cost\n")) == []
