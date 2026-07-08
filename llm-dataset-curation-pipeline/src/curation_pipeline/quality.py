from __future__ import annotations

from collections import Counter
from statistics import mean


def distribution(records: list[dict], field: str) -> dict[str, int]:
    return dict(Counter(str(record.get(field, "unknown")) for record in records))


def numeric_summary(records: list[dict], field: str) -> dict[str, float | int]:
    values = [int(record.get(field, 0)) for record in records if record.get(field) is not None]
    if not values:
        return {"min": 0, "max": 0, "mean": 0, "total": 0}
    return {
        "min": min(values),
        "max": max(values),
        "mean": round(mean(values), 2),
        "total": sum(values),
    }


def drop_reason_distribution(rejected_records: list[dict]) -> dict[str, int]:
    return distribution(rejected_records, "drop_reason")

