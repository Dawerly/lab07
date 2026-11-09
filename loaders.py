"""Поліморфне завантаження JSON/CSV. I/O ізольовано в цьому модулі."""

import csv
import io
import json
from functools import singledispatch
from pathlib import Path

Row = dict[str, object]


def validate_rows(data: object) -> list[Row]:
    if not isinstance(data, list):
        raise ValueError("Очікується список словників")
    result: list[Row] = []
    for row in data:
        if not isinstance(row, dict) or not all(isinstance(key, str) for key in row):
            raise ValueError("Кожний запис має бути словником із рядковими ключами")
        result.append(dict(row))
    return result


def parse_text(text: str, *, csv_format: bool = False) -> list[Row]:
    if csv_format:
        return validate_rows(list(csv.DictReader(io.StringIO(text), strict=True)))
    data: object = json.loads(text)
    return validate_rows(data)


@singledispatch
def load_shipments(source: object) -> list[Row]:
    raise TypeError(f"Непідтримуваний тип джерела: {type(source).__name__}")


@load_shipments.register
def from_string(source: str) -> list[Row]:
    stripped = source.strip()
    if stripped.startswith(("[", "{")):
        return parse_text(stripped)
    if "\n" in source:
        return parse_text(source, csv_format=True)
    return load_shipments(Path(source))


@load_shipments.register
def from_path(source: Path) -> list[Row]:
    if source.suffix.lower() not in {".json", ".csv"}:
        raise ValueError("Файл має мати розширення .json або .csv")
    return parse_text(
        source.read_text(encoding="utf-8"), csv_format=source.suffix.lower() == ".csv"
    )


@load_shipments.register
def from_file(source: io.TextIOBase) -> list[Row]:
    text = source.read()
    name = str(getattr(source, "name", ""))
    csv_format = name.lower().endswith(".csv") or (
        not name.lower().endswith(".json") and not text.lstrip().startswith(("[", "{"))
    )
    return parse_text(text, csv_format=csv_format)


@load_shipments.register(list)
def from_list(source: list[object]) -> list[Row]:
    return validate_rows(source)
