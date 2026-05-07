from __future__ import annotations

import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any


def ensure_parent(path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)

    if not target.exists():
        target.touch()

    return target


def append_jsonl(path: str | Path, row: dict[str, Any]) -> None:
    target = ensure_parent(path)

    with target.open("a", encoding="utf-8") as file:
        file.write(json.dumps(row, ensure_ascii=False) + "\n")


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    target = ensure_parent(path)

    rows: list[dict[str, Any]] = []

    with target.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()

            if not line:
                continue

            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    return rows


def write_jsonl(path: str | Path, rows: list[dict[str, Any]]) -> None:
    target = ensure_parent(path)

    with NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=str(target.parent),
        delete=False,
    ) as tmp:
        tmp_path = Path(tmp.name)

        for row in rows:
            tmp.write(json.dumps(row, ensure_ascii=False) + "\n")

    os.replace(tmp_path, target)
