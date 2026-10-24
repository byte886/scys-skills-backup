#!/usr/bin/env python3
"""Normalize SRT/VTT/Whisper JSON without overwriting the source; stdlib only."""

import argparse
import html
import json
import math
import re
from pathlib import Path


STAMP = r"(?:\d+:)?\d{2}:\d{2}[.,]\d{3}"
TIMING = re.compile(rf"^\s*({STAMP})\s+-->\s+({STAMP})(?:\s.*)?$")
TAGS = re.compile(rf"</?(?:c(?:\.[^ >]+)?|v|lang|b|i|u|ruby|rt)(?:\s[^>]*)?>|<{STAMP}>")


def seconds(value):
    parts = value.replace(",", ".").split(":")
    return sum(float(part) * 60 ** i for i, part in enumerate(reversed(parts)))


def clean(text):
    return re.sub(r"\s+", " ", html.unescape(TAGS.sub("", text))).strip()


def read_segments(path):
    raw = path.read_text(encoding="utf-8-sig")
    if path.suffix.lower() == ".json":
        data = json.loads(raw)
        rows = data.get("segments") if isinstance(data, dict) else data
        if not isinstance(rows, list):
            raise ValueError("JSON must contain a segments list with start, end and text")
    else:
        rows = []
        for block in re.split(r"\n\s*\n", raw.replace("\r\n", "\n")):
            lines = block.splitlines()
            if lines and re.match(r"^(NOTE(?:\s|$)|STYLE$|REGION$)", lines[0]):
                continue
            for index, line in enumerate(lines):
                match = TIMING.match(line)
                if match:
                    rows.append({"start": seconds(match[1]), "end": seconds(match[2]),
                                 "text": " ".join(lines[index + 1:])})
                    break
    result = []
    for row in rows:
        start, end = float(row["start"]), float(row["end"])
        if not (math.isfinite(start) and math.isfinite(end) and 0 <= start <= end):
            raise ValueError("Invalid segment timestamp")
        if not isinstance(row["text"], str):
            raise ValueError("Segment text must be a string")
        text = clean(row["text"])
        if text:
            result.append({"start": start, "end": end, "text": text})
    if not result:
        raise ValueError("No non-empty timed transcript segments found")
    if any(b["start"] < a["start"] for a, b in zip(result, result[1:])):
        raise ValueError("Segments are out of order; inspect the source before normalization")
    return result


def overlap_length(previous, current):
    for size in range(min(len(previous), len(current)), 0, -1):
        if not previous.endswith(current[:size]):
            continue
        # A partial English word is not a repeated caption window.
        left = len(previous) - size
        if left and previous[left - 1].isascii() and previous[left - 1].isalnum() and current[0].isascii() and current[0].isalnum():
            continue
        if size < len(current) and current[size - 1].isascii() and current[size - 1].isalnum() and current[size].isascii() and current[size].isalnum():
            continue
        if size == 1 and previous != current:
            continue
        return size
    return 0


def normalize(rows, rolling):
    text, removed, previous = "", 0, None
    for row in rows:
        overlap = 0
        if rolling and previous and row["start"] <= previous["end"] + 0.05:
            overlap = overlap_length(previous["text"], row["text"])
        if overlap:
            text += row["text"][overlap:]
            removed += overlap
        else:
            text += ("\n" if text else "") + row["text"]
        previous = row
    return text + "\n", removed


def coverage(rows, duration):
    last = max(row["end"] for row in rows)
    limit = duration if duration is not None else last
    cursor, covered, largest_gap = 0.0, 0.0, 0.0
    for row in rows:
        start, end = min(row["start"], limit), min(row["end"], limit)
        largest_gap = max(largest_gap, start - cursor)
        covered += max(0, end - max(start, cursor))
        cursor = max(cursor, end)
    largest_gap = max(largest_gap, limit - cursor)
    return {"first_start_seconds": rows[0]["start"], "last_end_seconds": last,
            "expected_duration_seconds": duration, "timed_text_seconds": round(covered, 3),
            "largest_uncovered_interval_seconds": round(largest_gap, 3),
            "end_exceeds_expected_duration": duration is not None and last > duration + 1,
            "note": "Timing is a review signal, not proof of completeness; gaps may be silence."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True, help="New directory; existing paths are rejected")
    parser.add_argument("--rolling", action="store_true", help="Only for verified rolling SRT/VTT captions")
    parser.add_argument("--duration", type=float, help="Actual media duration in seconds")
    args = parser.parse_args()
    if args.duration is not None and (not math.isfinite(args.duration) or args.duration <= 0):
        parser.error("--duration must be a finite positive number")
    if args.rolling and args.input.suffix.lower() == ".json":
        parser.error("--rolling is for subtitle cues, not ASR JSON")
    if args.output_dir.exists():
        parser.error("Output directory exists; choose a new directory to preserve prior artifacts")
    try:
        rows = read_segments(args.input)
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.error(str(error))
    text, removed = normalize(rows, args.rolling)
    report = coverage(rows, args.duration)
    report.update({"segments": len(rows), "characters": len(text.strip()),
                   "rolling_overlap_characters_removed": removed})
    args.output_dir.mkdir(parents=True)
    (args.output_dir / "transcript.txt").write_text(text, encoding="utf-8")
    (args.output_dir / "segments.json").write_text(json.dumps({"segments": rows}, ensure_ascii=False, indent=2), encoding="utf-8")
    (args.output_dir / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
