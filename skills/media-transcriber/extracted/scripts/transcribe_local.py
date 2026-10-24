#!/usr/bin/env python3
"""Local ASR using an installed faster-whisper or mlx-whisper engine."""

import argparse
import json
import platform
from pathlib import Path


def faster(args):
    from faster_whisper import WhisperModel

    model = WhisperModel(args.model or "small", device=args.device,
                         compute_type=args.compute_type,
                         local_files_only=args.local_files_only)
    segments, info = model.transcribe(str(args.input), language=args.language,
                                      condition_on_previous_text=False, vad_filter=True)
    rows = []
    # Keep completed segments available if a long run is interrupted.
    with (args.output_dir / "segments.partial.jsonl").open("x", encoding="utf-8") as handle:
        for segment in segments:
            row = {"start": segment.start, "end": segment.end, "text": segment.text.strip()}
            rows.append(row)
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            handle.flush()
    return {"language": info.language, "duration": info.duration, "segments": rows}


def mlx(args):
    import mlx_whisper

    result = mlx_whisper.transcribe(str(args.input),
        path_or_hf_repo=args.model or "mlx-community/whisper-large-v3-turbo",
        language=args.language, condition_on_previous_text=False, verbose=None)
    return {"language": result.get("language"), "segments": [
        {"start": row["start"], "end": row["end"], "text": row["text"].strip()}
        for row in result["segments"]]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Local media file; URLs are not accepted")
    parser.add_argument("--output-dir", type=Path, required=True, help="New directory; existing paths are rejected")
    parser.add_argument("--engine", choices=("faster-whisper", "mlx"), default="faster-whisper")
    parser.add_argument("--model", help="Engine-specific model name or local model path")
    parser.add_argument("--language", help="Actual spoken language, e.g. zh/en; omitted means detection")
    parser.add_argument("--device", choices=("cpu", "cuda", "auto"), default="cpu")
    parser.add_argument("--compute-type", default="int8")
    parser.add_argument("--local-files-only", action="store_true", help="faster-whisper: use cached/local model only")
    args = parser.parse_args()
    if not args.input.is_file():
        parser.error("Input must be an existing local media file")
    if args.output_dir.exists():
        parser.error("Output directory exists; inspect prior artifacts or choose a new directory")
    if args.engine == "mlx":
        if platform.system() != "Darwin" or platform.machine().lower() not in ("arm64", "aarch64"):
            parser.error("MLX requires Apple Silicon macOS; use faster-whisper on this host")
        if args.local_files_only:
            parser.error("--local-files-only is only supported with faster-whisper")
        if args.device != "cpu" or args.compute_type != "int8":
            parser.error("--device and --compute-type apply only to faster-whisper")
    args.output_dir.mkdir(parents=True)
    try:
        result = faster(args) if args.engine == "faster-whisper" else mlx(args)
    except ImportError as error:
        parser.error(f"ASR dependency unavailable: {error}. Use the isolated environment from README.md.")
    if not any(row["text"].strip() for row in result["segments"]):
        parser.error("No speech text returned; inspect the audio and language before retrying")
    result.update({"engine": args.engine, "model": args.model or (
        "small" if args.engine == "faster-whisper" else "mlx-community/whisper-large-v3-turbo")})
    (args.output_dir / "transcript.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    (args.output_dir / "transcript.txt").write_text(
        "\n".join(row["text"].strip() for row in result["segments"]) + "\n", encoding="utf-8")
    print(json.dumps({"status": "transcribed_needs_review", "segments": len(result["segments"]),
                      "language": result["language"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
