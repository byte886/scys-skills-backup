#!/usr/bin/env python3
"""Render a standalone AI enterprise/FDE assessment report from JSON."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REQUIRED_SCORES = ("ai_service", "fde", "commercial", "confidence")
FORBIDDEN_PERSON_NAMES = {
    "匿名学员",
    "匿名用户",
    "学员",
    "用户",
    "直播学员",
    "未填写",
    "待补充",
    "姓名待补充",
}


def validate(data: dict[str, Any]) -> None:
    if not isinstance(data, dict):
        raise ValueError("report data must be a JSON object")
    scores = data.get("scores")
    if not isinstance(scores, dict):
        raise ValueError("scores must be an object")
    for key in REQUIRED_SCORES:
        value = scores.get(key)
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError(f"scores.{key} must be a number")
        if not 0 <= value <= 100:
            raise ValueError(f"scores.{key} must be between 0 and 100")
    for key in ("person_name", "summary", "positioning"):
        if not isinstance(data.get(key), str) or not data[key].strip():
            raise ValueError(f"{key} must be a non-empty string")
    person_name = data["person_name"].strip()
    if person_name in FORBIDDEN_PERSON_NAMES:
        raise ValueError(
            "person_name must be a name or nickname explicitly provided by the user; "
            f"placeholder {person_name!r} is not allowed"
        )


def safe_script_json(data: dict[str, Any]) -> str:
    raw = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return raw.replace("</", "<\\/").replace("<!--", "<\\!--")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="assessment JSON")
    parser.add_argument("--output", type=Path, required=True, help="output HTML")
    args = parser.parse_args()

    data = json.loads(args.input.read_text(encoding="utf-8"))
    validate(data)
    template = Path(__file__).resolve().parents[1] / "assets" / "report-template.html"
    html = template.read_text(encoding="utf-8")
    marker = "__REPORT_DATA__"
    if marker not in html:
        raise ValueError("report template marker is missing")
    html = html.replace(marker, safe_script_json(data), 1)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(html, encoding="utf-8")
    print(f"Report written to {args.output.resolve()}")


if __name__ == "__main__":
    main()
